from typing import List, Dict, Any
import logging
import spacy
from bd_law_multi_agent.services.analyze_vector_db import AnalysisVectorDB
from bd_law_multi_agent.prompts.conflict_detection_prompt import CONFLICT_DETECTION_PROMPT
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from bd_law_multi_agent.core.config import config
import os
from bd_law_multi_agent.core.common import  extract_case_title, extract_case_parties
import re


os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
logger = logging.getLogger("ConflictDetectionService")

class ConflictDetectionService:
    def __init__(self):
        """Initialize the conflict detection service with necessary components"""
        try:
            self.nlp = None
            self.llm = ChatGroq(
                model=config.GROQ_LLM_MODEL, 
                temperature=config.CONFLICT_TEMPERATURE,  
                max_tokens=config.CONFLICT_MAX_TOKENS
            )
            
            self.analysis_db = AnalysisVectorDB()
            
            logger.info("Conflict detection service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize conflict detection service: {e}")
            raise
    
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities from text using both spaCy and LLM with improved filtering
        """
        try:
            # Lazy load spaCy only when needed
            if self.nlp is None:
                logger.info("Loading spaCy model")
                self.nlp = spacy.load("en_core_web_sm")
        
            # First extract the case title/number for special handling
            case_title = extract_case_title(text)
            case_parties = extract_case_parties(text)
        
            # Clean text and limit size 
            cleaned_text = re.sub(r'[`\*\_\n\t]', ' ', text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
            # First use spaCy for entity extraction
            doc = self.nlp(cleaned_text[:500000])  # Limit text size
            spacy_entities = []
        
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PERSON", "GPE", "FAC", "NORP"]:
                    spacy_entities.append(ent.text)
        
            # Use LLM for focused entity extraction
            prompt = CONFLICT_DETECTION_PROMPT.get_entity_extraction_prompt().format(
                document_text=cleaned_text[:5000]  # Truncate for LLM
            )
        
            llm_response = self.llm.invoke(prompt)
        
            try:
                # Try to parse the response as a list
                import ast
                llm_entities = ast.literal_eval(llm_response.content.strip())
                if not isinstance(llm_entities, list):
                    llm_entities = []
            except:
                
                llm_entities = [
                    line.strip().strip('-').strip() 
                    for line in llm_response.content.split('\n')
                    if line.strip() and not line.strip().startswith("Entities:")
                ]
        
            
            priority_entities = []
            if case_title:
                priority_entities.append(case_title)
        
            for party in case_parties:
                if party and len(party) > 2:
                    priority_entities.append(party)
        
            
            all_entities = priority_entities + list(set(spacy_entities + llm_entities))
        
            
            common_words = ["the", "and", "of", "to", "court", "law", "case", "file", 
                        "district", "summary", "background", "events", "conclusion", 
                        "legal", "current", "status", "```"]
                      
            filtered_entities = []
            for entity in all_entities:
                # Add additional filtering
                if any(c.isdigit() for c in entity):
                    continue
                if ':' in entity or '=' in entity:
                    continue
                if len(entity) < 3:
                    continue
                filtered_entities.append(entity)
        
            return filtered_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def check_conflicts(self, entities: List[str], 
                        similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Check for conflicts by comparing entities against analysis vector database
        
        Args:
            entities (List[str]): List of entity names to check
            similarity_threshold (float): Minimum similarity score to consider a match
            
        Returns:
            List[Dict]: List of conflict details
        """
        conflicts = []
        
        for entity in entities:
            try:
                clean_entity = re.sub(r'\b(vs|v\.|versus)\b', '', entity, flags=re.IGNORECASE).strip()
                similar_docs = self.analysis_db.search_similar(
                    query=clean_entity,
                    k=5  
                )
                
                
                for doc in similar_docs:
                    
                    metadata = doc.metadata
                    
                    
                    conflict = {
                        "entity": entity,
                        "matched_document": metadata.get("source", "Unknown"),
                        "document_type": metadata.get("document_type", "Analysis"),
                        "similarity_score": 0.9,  
                        "context": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "case_details": {
                            "case_id": metadata.get("source", "Unknown").replace("case_analysis_", ""),
                            "case_name": metadata.get("file_source", "Unknown"),
                            "date": metadata.get("created_at", "Unknown"),
                            "classification": metadata.get("classification", "Unknown"),
                            "complexity": metadata.get("complexity", "Unknown")
                        }
                    }
                    
                    conflicts.append(conflict)
            
            except Exception as e:
                logger.error(f"Conflict check failed for entity '{entity}': {e}")
        
        return conflicts
    
    def generate_conflict_explanation(self, conflicts: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable explanation of detected conflicts or clearance to proceed
    
        Args:
            conflicts (List[Dict]): List of conflict details
    
        Returns:
            str: Formatted explanation of conflicts or approval message if no conflicts
        """
        
    
        try:
            if not conflicts:
                
                prompt = CONFLICT_DETECTION_PROMPT.get_no_conflict_explanation_prompt()
                response = self.llm.invoke(prompt)
                return response.content
            
            docs_to_conflicts = {}
            for conflict in conflicts:
                doc_id = conflict['matched_document']
                if doc_id not in docs_to_conflicts:
                    docs_to_conflicts[doc_id] = []
                docs_to_conflicts[doc_id].append(conflict)
    
            
            prompt = CONFLICT_DETECTION_PROMPT.get_conflict_explanation_prompt().format(
                conflicts=str(conflicts)
            )
    
            response = self.llm.invoke(prompt)
            return response.content
    
        except Exception as e:
            logger.error(f"Failed to generate conflict explanation: {e}")
    
            
            explanation = "⚠️ POTENTIAL CONFLICTS OF INTEREST DETECTED ⚠️\n\n"
    
            for doc_id, doc_conflicts in docs_to_conflicts.items():
                explanation += f"Conflicts with '{doc_id}':\n"
        
                for conflict in doc_conflicts:
                    explanation += f"- Entity: {conflict['entity']}\n"
                    explanation += f"- Similarity: {conflict['similarity_score']:.2f}\n"
                    explanation += f"- Case: {conflict['case_details']['case_name']}\n"
                    explanation += f"- Context: {conflict['context']}\n\n"
    
            return explanation
        
    