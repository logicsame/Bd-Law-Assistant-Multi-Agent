from typing import Dict, List,Any
from langchain_core.documents import Document
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.services.rag_service import PersistentLegalRAG
from bd_law_multi_agent.prompts.lega_chat_prompy import LegalChatbotPrompts
from langchain_openai import ChatOpenAI
from bd_law_multi_agent.utils.logger import logger



class LegalChatbot:
    def __init__(self, rag_system: PersistentLegalRAG):
        self.rag = rag_system
        self.llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS
        )

    def _retrieve_context(self, query: str, doc_type: str = "General") -> str:
        """Retrieve relevant legal context from vector store"""
        docs = self.rag.vector_store.similarity_search(
            query, 
            k=config.MAX_RETRIEVED_DOCS,
            filter={"document_type": doc_type},
            similarity_threshold=0.65
        )
        return "\n\n".join([
            f"Source: {doc.metadata.get('source_path', 'Unknown')}\n"  # Changed from 'source' to 'source_path'
            f"Content:\n{doc.page_content}"
            for doc in docs
        ])

    def process_query(self, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Main entry point for chatbot queries with conversation history support"""
        try:
            # Initialize conversation history if not provided
            if conversation_history is None:
                conversation_history = []
            
            # Check if this is a follow-up question
            is_followup = False
            previous_topic = None
        
            if conversation_history:
                # Get the most recent query and check if current query seems like a follow-up
                last_query = conversation_history[-1].get("query", "")

                # Extract potential legal terms from previous query
                for term_indicator in ["define", "what is", "meaning of", "analyze", "explain"]:
                    if term_indicator in last_query.lower():
                        previous_topic = last_query.lower().replace(term_indicator, "").strip()
                        break
            
                # Check if current query is a brief follow-up that refers to previous topic
                if previous_topic and (
                    query.lower().startswith("tell me about") or 
                    query.lower().startswith("more on") or
                    query.lower() == previous_topic or
                    previous_topic in query.lower()
                ):
                    is_followup = True
                    # Use the previous topic for context retrieval instead
                    retrieval_query = previous_topic
                    logger.info(f"Detected follow-up question about: {previous_topic}")
            
            # If not a follow-up, process normally
            if not is_followup:
                retrieval_query = query
            
            # Determine query type
            if any(keyword in query.lower() for keyword in ["define", "what is", "meaning of"]) or (is_followup and any(keyword in last_query.lower() for keyword in ["define", "what is", "meaning of"])):
                return self.handle_definition(retrieval_query)
            elif any(keyword in query.lower() for keyword in ["analyze", "explain", "implications of"]) or (is_followup and any(keyword in last_query.lower() for keyword in ["analyze", "explain", "implications of"])):
                return self.handle_analysis(retrieval_query)
            else:
                return self.handle_general_query(retrieval_query)
                
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return {"response": "Unable to process query at this time", "sources": []}
                
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return {"response": "Unable to process query at this time", "sources": []}

    def handle_definition(self, query: str) -> Dict[str, Any]:
        """Handle legal term definitions"""
        term = query.replace("define", "").replace("what is", "").strip()
        context = self._retrieve_context(term, "Dictionary")
        prompt = LegalChatbotPrompts.get_definition_prompt(term, context)
        response = self.llm.invoke(prompt).content
        return {
            "type": "definition",
            "response": response,
            "sources": self._get_sources(context)
        }

    def handle_analysis(self, query: str) -> Dict[str, Any]:
        """Handle in-depth term analysis"""
        term = query.replace("analyze", "").replace("explain", "").strip()
        context = self._retrieve_context(term, "Legal Doctrine")
        prompt = LegalChatbotPrompts.get_term_analysis_prompt(term, context)
        response = self.llm.invoke(prompt).content
        return {
            "type": "analysis",
            "response": response,
            "sources": self._get_sources(context)
        }

    def handle_general_query(self, query: str) -> Dict[str, Any]:
        """Handle general legal advice"""
        context = self._retrieve_context(query)
        prompt = LegalChatbotPrompts.get_general_advice_prompt(query, context)
        response = self.llm.invoke(prompt).content
        return {
            "type": "general_advice",
            "response": response,
            "sources": self._get_sources(context)
        }

    def _get_sources(self, context: str) -> List[Dict]:
        """Extract sources from context string"""
        sources = []
        current_source = None
        for line in context.split("\n"):
            if line.startswith("Source:"):
                if current_source:  # Save previous source
                    sources.append(current_source)
                current_source = {
                    "source": line.split("Source: ")[1].strip(),
                    "excerpt": ""
                }
            elif line.startswith("Content:"):
                if current_source:
                    current_source["excerpt"] = line.split("Content:")[1].strip()
        # Add final source
        if current_source:
            sources.append(current_source)
        return sources[:config.MAX_RETRIEVED_DOCS]  