import logging
import re
from typing import List, Dict, Any
import logging
from bd_law_multi_agent.services.analyze_vector_db import AnalysisVectorDB
from bd_law_multi_agent.utils.logger import logger
from langchain.schema import Document




analysis_db = AnalysisVectorDB()




def extract_case_title(text: str) -> str:
        """Extract the case title from text"""
        patterns = [
            r"Case File:?\s*(.*?)(?:\n|Case No)",
            r"(?:^|\\n)The State vs\.\s*(.*?)(?:\n|$)",
            r"(?:^|\\n)(.*?)\s*vs\.\s*.*?(?:\n|$)"
    ]
    
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
    
        return ""

def extract_case_parties(text: str) -> List[str]:
    """Extract plaintiff and defendant names"""
    parties = []
    
    # Try to extract from "vs." format
    vs_match = re.search(r"(.*?)\s*vs\.?\s*(.*?)(?:\n|Case No|Jurisdiction|$)", text)
    if vs_match:
        plaintiff = vs_match.group(1).strip()
        defendant = vs_match.group(2).strip()
        
        # Clean up common prefixes
        for party in [plaintiff, defendant]:
            clean_party = re.sub(r"^(?:The|Case File:)\s*", "", party).strip()
            if clean_party:
                parties.append(clean_party)
    
    return parties







def check_conflicts_in_raw_cases(
    entities: List[str], 
    similarity_threshold: float,
    current_file_id: str
) -> List[Dict[str, Any]]:
    conflicts = []
    matched_documents = set()
    
    generic_terms = {
        "the", "and", "of", "to", "court", "law", "case", "file", 
        "district", "summary", "background", "events", "conclusion", 
        "legal", "current", "status", "local residents", "government", 
        "state", "police", "lawyers", "journalists", "district court", 
        "legal battle", "law enforcement", "local authorities",
        "community", "human rights"
    }
    
    doc_count = analysis_db.get_document_count()
    
    if doc_count == 0:
        logger.warning("No documents in vector database, skipping conflict check")
        return []
    
    specific_entities = [e for e in entities if e.lower() not in generic_terms and len(e) > 4]
    
    if not specific_entities:
        return []
    
    for entity in specific_entities:
        try:
            k = min(3, doc_count)
            
            common_legal_entities = {"the state", "government", "supreme court"}
            entity_threshold = similarity_threshold + 0.1 if entity.lower() in common_legal_entities else similarity_threshold
            
            results = analysis_db.search_with_scores(query=entity, k=k) or []
            
            if not results:
                logger.debug(f"No matches found for entity: {entity}")
                continue

            for result in results:
                if not isinstance(result, dict):
                    logger.debug(f"Unexpected result format: {type(result)}")
                    continue
                
                doc_content = result.get("content", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0.0)

                # Score normalization
                try:
                    normalized_score = min(score / 2.0, 1.0) if score > 1.0 else score
                    if not (0 <= normalized_score <= 1.0):
                        raise ValueError(f"Invalid score: {normalized_score}")
                except Exception as e:
                    logger.error(f"Score error for {entity}: {str(e)}")
                    continue

                if normalized_score < entity_threshold:
                    logger.debug(f"Low score ({normalized_score:.2f}) for {entity}")
                    continue

                doc_id = metadata.get("source", "Unknown")
                unique_id = metadata.get("unique_id", "")

                # Validation checks
                if (
                    metadata.get("document_type") != "RawCase" 
                    or current_file_id == unique_id 
                    or doc_id in matched_documents
                ):
                    continue

                # Context extraction
                try:
                    context = extract_entity_context(doc_content, entity)
                    if not context:
                        continue
                except Exception as e:
                    logger.error(f"Context failed for {entity}: {str(e)}")
                    continue

                # Legal check
                try:
                    if not is_meaningful_legal_entity(entity, context):
                        continue
                except Exception as e:
                    logger.error(f"Legal check failed for {entity}: {str(e)}")
                    continue

                # Record conflict
                conflicts.append({
                    "entity": entity,
                    "matched_document": doc_id,
                    "document_type": "RawCase",
                    "similarity_score": normalized_score,
                    "context": sanitize_context(context),
                    "case_details": {
                        "case_id": doc_id,
                        "case_name": metadata.get("file_source", "Unknown"),
                        "date": metadata.get("created_at", "Unknown")
                    }
                })
                matched_documents.add(doc_id)

        except Exception as e:
            logger.error(f"Error processing {entity}: {str(e)}", exc_info=True)

    return conflicts



def is_meaningful_legal_entity(entity: str, context: str) -> bool:
    """Improved check for legally meaningful context"""
    # Enhanced legal significance indicators
    legal_patterns = [
        r"(represented|client|party|representing|counsel|plaintiff|defendant)",
        r"(vs\.?|versus)",
        r"(petitioner|respondent)",
        r"(witness|testimony)",
        r"(attorney|lawyer|law\s+firm)",
        r"(judge|justice|court\s+order)",
        r"(legal\s+proceeding|judgment|ruling)"
    ]
    
    if entity.lower() == "the state":
        state_patterns = [
            r"the\s+state\s+vs\.?",
            r"vs\.?\s+the\s+state",
            r"represented\s+by\s+the\s+state",
            r"the\s+state\s+as\s+(plaintiff|defendant|respondent|petitioner)"
        ]
        
        for pattern in state_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        # If "The State" but none of the specific patterns match, require higher confidence
        return False
    
    # Get longer context window for better matching
    entity_position = context.lower().find(entity.lower())
    if entity_position == -1:
        return False
    
    # Get more text around the entity
    window = 200  # Increased window
    context_window = context[max(0, entity_position-window):
                            min(len(context), entity_position+len(entity)+window)]
    
    for pattern in legal_patterns:
        if re.search(pattern, context_window, re.IGNORECASE):
            return True
    
    return False

def extract_entity_context(text: str, entity: str) -> str:
    """Extract better context showing where entity appears"""
    entity_lower = entity.lower()
    text_lower = text.lower()
    
    # Find all occurrences of entity
    positions = []
    start = 0
    while True:
        pos = text_lower.find(entity_lower, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + len(entity)
    
    if not positions:
        return text[:300]
    
    # Use the first 2 occurrences for better context
    contexts = []
    for i, pos in enumerate(positions[:2]):
        # Find sentence boundaries - look for multiple sentences
        sentence_start = max(0, text.rfind('.', 0, max(0, pos-100)) + 1)
        sentence_end = text.find('.', min(len(text), pos+100))
        if sentence_end == -1:
            sentence_end = min(len(text), pos + 300)
        
        # Get more context around the entity
        context = text[sentence_start:sentence_end+1]
        contexts.append(context)
    
    # Return the longest context
    best_context = max(contexts, key=len) if contexts else ""
    return best_context or text[max(0, positions[0]-150):min(len(text), positions[0]+len(entity)+150)]



def sanitize_context(text: str, max_length: int = 200) -> str:
    """Clean up context text for display"""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    cleaned = re.sub(r'[^\w\s.,-]', '', cleaned)
    return cleaned[:max_length] + "..." if len(cleaned) > max_length else cleaned







