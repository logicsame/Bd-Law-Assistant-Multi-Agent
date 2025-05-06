from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_groq import ChatGroq
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

from bd_law_multi_agent.core.common import logger
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.services.legal_service import LegalAnalyzer
from bd_law_multi_agent.prompts.case_analysis_prompt import CASE_ANALYSIS_PROMPT
from bd_law_multi_agent.services.vector_store import CustomHuggingFaceEmbeddings
from bd_law_multi_agent.database.database import get_db
from bd_law_multi_agent.models.document_model import DocumentChunk

class PersistentLegalRAG:
    """
    Production-ready implementation of a persistent RAG system for legal analysis,
    using FAISS vector store and OpenAI embeddings.
    """
    def __init__(self, persist_dir: Optional[str] = None):
        """
        Initialize the RAG system with a vector database.
        
        Args:
            persist_dir: Directory to persist vector store. If None, uses config value.
        """
        # Use config path if no custom path is provided
        self.persist_dir = persist_dir or config.VECTOR_DB_PATH
        
        # Ensure directory exists
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize components
        self.embeddings = self._init_embeddings()
        self.llm = self._init_llm()
        self.vector_store = self._load_vector_store()
        
        logger.info(f"PersistentLegalRAG initialized with vector store at {self.persist_dir}")

    # def _init_embeddings(self) -> OpenAIEmbeddings:
    #     """Initialize the embeddings model from configuration."""
    #     logger.debug(f"Initializing embeddings with model {config.EMBEDDING_MODEL}")
        
    #     return OpenAIEmbeddings(
    #         api_key=config.OPENAI_API_KEY, 
    #         model=config.EMBEDDING_MODEL, 
    #         dimensions=config.DIMENSIONS, 
    #         encoding_format="float"
    #     )
    
    def _init_embeddings(self):
        """Initialize the embeddings model from configuration."""
        logger.debug(f"Initializing HuggingFace embeddings {config.TEMP_EMBEDDING_MODEL}")
    
        return CustomHuggingFaceEmbeddings(
            model_name=config.TEMP_EMBEDDING_MODEL
        )

    # def _init_llm(self) -> ChatOpenAI:
    #     """Initialize the language model from configuration."""
    #     logger.debug(f"Initializing LLM with model {config.LLM_MODEL}")
        
    #     return ChatOpenAI(
    #         api_key=config.OPENAI_API_KEY, 
    #         model=config.LLM_MODEL, 
    #         temperature=config.TEMPERATURE, 
    #         max_tokens=config.MAX_TOKENS
    #     )
    
    # ======== FOR TEMP FUNCTION DEVLOPMENT ==============
    
    def _init_llm(self) -> ChatGroq:
        """Initialize the language model from configuration."""
        logger.debug(f"Initializing Groq LLM with model {config.GROQ_LLM_MODEL}")
    
        return ChatGroq(
            model_name=config.GROQ_LLM_MODEL,
            temperature=config.TEMPERATURE,
        )

    def _load_vector_store(self) -> FAISS:
        """
        Load or initialize vector store with proper file creation handling
        """
        index_path = os.path.join(self.persist_dir, "index.faiss")
        pkl_path = os.path.join(self.persist_dir, "index.pkl")
    
        # Create directory structure if needed
        os.makedirs(self.persist_dir, exist_ok=True)

        if os.path.exists(index_path) and os.path.exists(pkl_path):
            logger.info(f"Loading existing vector store from {self.persist_dir}")
            try:
                return FAISS.load_local(
                    self.persist_dir,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")
                raise RuntimeError(f"Vector store loading failed: {e}")
        else:
            logger.info(f"Initializing new vector store at {self.persist_dir}")
        
            # Create initial empty store with system document
            initial_docs = [Document(
                page_content="System Initial Document",
                metadata={
                    "document_id": "system-init",
                    "source_type": "system",
                    "source_path": "system",
                    "timestamp": datetime.now().isoformat()
                }
            )]
        
            new_store = FAISS.from_documents(initial_docs, self.embeddings)
            new_store.save_local(self.persist_dir)
            logger.info("Successfully created new vector store with initial document")
            return new_store
    
    
        
    # def get_document_sources(self) -> List[str]:
    #     """
    #     Retrieve a list of unique document sources in the vector store.
    #     Useful for tracking what documents have been added.
    #     """
    #     if not self.vector_store:
    #         return []
        
    #     sources = set()
    #     for doc_id, doc in self.vector_store.docstore._dict.items():
    #         source = doc.metadata.get('source', 'Unknown')
    #         sources.add(source)
        
    #     return list(sources)
    
    
    
    
    def get_document_sources(self) -> List[str]:
        """
        Retrieve a list of unique document sources in the vector store.
        Useful for tracking what documents have been added.
    
        Returns:
            List of unique source paths from all documents in the vector store
        """
        if not self.vector_store:
            return []
    
        # First attempt: try using FAISS docstore if it has the right structure
        sources = set()
    
        try:
            # Try to get metadata from FAISS docstore
            for doc_id, doc in self.vector_store.docstore._dict.items():
                if hasattr(doc, 'metadata'):
                    source = doc.metadata.get('source_path', None)
                    if source:
                        sources.add(source)
        except (AttributeError, KeyError):
            # If that fails, fallback to database query
            pass
        
        # If no sources found in FAISS, query the database
        if not sources:
            with next(get_db()) as db:
                # Get distinct source paths from the document chunks table
                chunks = db.query(DocumentChunk.chunk_metadata).distinct().all()
                for chunk in chunks:
                    if chunk.chunk_metadata and 'source_path' in chunk.chunk_metadata:
                        sources.add(chunk.chunk_metadata['source_path'])
    
        return list(sources)
    
    
    

    def analyze_case(self, query: str) -> Dict[str, Any]:
        """
        Analyze a legal case query and provide relevant information.
        
        Args:
            query: The case description or query to analyze
            
        Returns:
            Dictionary containing analysis, classification, follow-up questions, and sources
        """
        logger.info(f"Analyzing case: {query[:50]}...")
        
        try:
            # Retrieve relevant documents
            docs = self.vector_store.similarity_search(
                query, 
                k=config.MAX_RETRIEVED_DOCS,
                similarity_threshold=config.SIMILARITY_THRESHOLD
            )
            
            logger.info(f"Retrieved {len(docs)} relevant documents")
            
            # Build context
            context = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                f"Page: {doc.metadata.get('page', 'N/A')}\n"
                f"Content:\n{doc.page_content[:config.CITATION_LENGTH]}"
                for doc in docs
            ])

            # Classify case
            classification = LegalAnalyzer.classify_case(query, context)
            logger.debug(f"Case classified as {classification.get('primary_category', 'N/A')}")

            # Generate analysis
            prompt = CASE_ANALYSIS_PROMPT.get_legal_analysis_prompt().format(
                classification_context=(
                    f"Category: {classification.get('primary_category', 'N/A')}\n"
                    f"Complexity: {classification.get('complexity_level', 'N/A')}"
                ),
                context=context,
                query=query
            )
            
            analysis = self.llm.invoke(prompt).content

            # Generate follow-ups
            follow_ups = LegalAnalyzer.generate_follow_up_questions(analysis, [])

            return {
                "analysis": analysis,
                "classification": classification,
                "follow_ups": follow_ups,
                "sources": docs
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
        
    def generate_argument(self, case_details: str) -> Dict[str, Any]:
        """
        Generate defense argument with legal citations.
        
        Args:
            case_details: Description of the case
            
        Returns:
            Dictionary containing the generated argument, category, and sources
        """
        logger.info(f"Generating argument for case: {case_details[:50]}...")
        
        try:
            # First analyze the case to get classification
            classification = self.analyze_case(case_details)["classification"]
            primary_category = classification["primary_category"]
            
            # Retrieve relevant legislation documents
            docs = self.vector_store.similarity_search(
                case_details,
                k=config.MAX_RETRIEVED_DOCS,
                filter={"document_type": "Legislation"},
                similarity_threshold=config.SIMILARITY_THRESHOLD
            )
            
            logger.info(f"Retrieved {len(docs)} relevant legislation documents")
            
            context = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                f"Content:\n{doc.page_content[:config.CITATION_LENGTH]}"
                for doc in docs
            ])
            
            # Generate the legal argument
            argument = LegalAnalyzer.generate_legal_argument(
                case_details=case_details,
                context=context,
                category=primary_category
            )
            
            return {
                "argument": argument,
                "category": primary_category,
                "sources": docs
            }
        except Exception as e:
            logger.error(f"Argument generation failed: {e}")
            raise