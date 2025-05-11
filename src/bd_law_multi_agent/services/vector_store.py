# import os
# from datetime import datetime
# from typing import List, Dict, Any, Optional
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain.docstore.document import Document
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from bd_law_multi_agent.core.config import config


# class DocumentVectorDatabase:
#     """
#     A class to convert extracted document text to embeddings and store in FAISS vector database.
#     """
    
#     def __init__(self, persist_directory: str = None, allow_dangerous_deserialization: bool = False):
#         """
#         Initialize the DocumentVectorDatabase.
        
#         Args:
#             persist_directory: Directory to store the vector database. Uses config if None.
#             allow_dangerous_deserialization: Whether to allow loading potentially unsafe pickle files.
#         """
#         # Use config path if not specified
#         self.persist_directory = persist_directory or config.KNOWLEDGE_VECTOR_DB_PATH
#         self.allow_dangerous_deserialization = allow_dangerous_deserialization
        
#         # Get API key from config
#         openai_api_key = config.OPENAI_API_KEY
#         if not openai_api_key:
#             raise ValueError("No OpenAI API key provided. Set the OPENAI_API_KEY in config.")
        
#         # Initialize embeddings with config settings
#         self.embeddings = OpenAIEmbeddings(
#             model=config.EMBEDDING_MODEL,
#             api_key=openai_api_key,
#             dimensions=config.DIMENSIONS
#         )
        
#         # Initialize text splitter with config settings
#         self.text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=config.CHUNK_SIZE,
#             chunk_overlap=config.CHUNK_OVERLAP,
#             length_function=len,
#         )
        
#         # Initialize vector store
#         if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
#             self.vector_store = FAISS.load_local(
#                 self.persist_directory, 
#                 self.embeddings,
#                 allow_dangerous_deserialization=self.allow_dangerous_deserialization
#             )
#         else:
#             os.makedirs(self.persist_directory, exist_ok=True)
#             self.vector_store = None
    
#     def _create_documents(self, text: str, metadata: Dict[str, Any]) -> List[Document]:
#         """
#         Split text into chunks and create Document objects.
        
#         Args:
#             text: Text content to split and embed
#             metadata: Metadata for the document
            
#         Returns:
#             List of Document objects
#         """
#         texts = self.text_splitter.split_text(text)
#         documents = [Document(page_content=chunk, metadata=metadata) for chunk in texts]
#         return documents
    
#     def _get_current_timestamp(self) -> str:
#         """Get current timestamp in ISO format."""
#         return datetime.now().isoformat()
    
#     def add_document(self, text: str, document_id: str, source_type: str, source_path: str, description: Optional[str] = None) -> None:
#         """
#         Add a document to the vector store.
        
#         Args:
#             text: Extracted text from the document
#             document_id: Unique identifier for the document
#             source_type: Type of source (pdf, image, url)
#             source_path: Path or URL of the original document
#             description: Optional description of the document
#         """
#         metadata = {
#             "document_id": document_id,
#             "source_type": source_type,
#             "source_path": source_path,
#             "timestamp": self._get_current_timestamp()
#         }
        
#         if description:
#             metadata["description"] = description
        
#         documents = self._create_documents(text, metadata)
        
#         if not documents:
#             return
        
#         if self.vector_store is None:
#             self.vector_store = FAISS.from_documents(documents, self.embeddings)
#         else:
#             self.vector_store.add_documents(documents)
        
#         self.save()
    
#     def save(self) -> None:
#         """Save the vector store to disk."""
#         if self.vector_store:
#             self.vector_store.save_local(self.persist_directory)
    
#     def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
#         """
#         Search for similar documents in the vector store.
        
#         Args:
#             query: Search query
#             top_k: Number of results to return (uses config if None)
            
#         Returns:
#             List of search results with document and score
#         """
#         if not self.vector_store:
#             return []
        
#         k = top_k or config.MAX_RETRIEVED_DOCS
#         docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
        
#         results = []
#         for doc, score in docs_with_scores:
#             results.append({
#                 "content": doc.page_content,
#                 "metadata": doc.metadata,
#                 "score": float(score)
#             })
        
#         return results
    
#     def get_document_by_id(self, document_id: str) -> List[Document]:
#         """
#         Retrieve all chunks for a specific document ID.
        
#         Args:
#             document_id: Document ID to retrieve
            
#         Returns:
#             List of document chunks with metadata
#         """
#         if not self.vector_store:
#             return []
        
#         # Get all documents matching the ID
#         docs = self.vector_store.similarity_search("", filter={"document_id": document_id})
#         return docs
    
#     def delete_document(self, document_id: str) -> bool:
#         """
#         Delete a document from the vector store.
        
#         Args:
#             document_id: Document ID to delete
            
#         Returns:
#             True if successful, False otherwise
#         """
#         if not self.vector_store:
#             return False
        
#         # Get all document IDs to delete
#         docs_to_delete = [doc.metadata["doc_id"] for doc in 
#                          self.vector_store.similarity_search("", filter={"document_id": document_id})]
        
#         if not docs_to_delete:
#             return False
            
#         # Delete documents (implementation depends on FAISS version)
#         try:
#             self.vector_store.delete(docs_to_delete)
#             self.save()
#             return True
#         except Exception as e:
#             print(f"Error deleting document: {e}")
#             return False






import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._config")

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.base import Embeddings
from semantic_router.encoders import HuggingFaceEncoder
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.models.document_model import DocumentChunk
from bd_law_multi_agent.database.database import get_db
import uuid
from sqlalchemy.orm import Session
class CustomHuggingFaceEmbeddings(Embeddings):
    """
    Custom embeddings class using HuggingFace models through semantic_router.
    """
    def __init__(self, model_name: str = "dwzhu/e5-base-4k"):
        """
        Initialize the embeddings model.
        
        Args:
            model_name: Name of the HuggingFace model to use
        """
        self.encoder = HuggingFaceEncoder(model_name=model_name)
        test_embed = self.encoder(['test'])
        self.embedding_dim = len(test_embed[0])
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self.encoder(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query string."""
        return self.encoder([text])[0]
    
    def __call__(self, text: str) -> List[float]:
        """Alternative interface to embed_query."""
        return self.embed_query(text)


class DocumentVectorDatabase:
    """
    A class to convert extracted document text to embeddings and store in FAISS vector database.
    """
    
    def __init__(self, 
                 persist_directory: str = None, 
                 allow_dangerous_deserialization: bool = False,
                 use_huggingface: bool = True,
                 hf_model_name: str = "dwzhu/e5-base-4k"):
        """
        Initialize the DocumentVectorDatabase.
        
        Args:
            persist_directory: Directory to store the vector database. Uses config if None.
            allow_dangerous_deserialization: Whether to allow loading potentially unsafe pickle files.
            use_huggingface: Whether to use HuggingFace embeddings instead of OpenAI.
            hf_model_name: HuggingFace model name to use for embeddings.
        """
        # Use config path if not specified
        self.persist_directory = persist_directory or config.KNOWLEDGE_VECTOR_DB_PATH
        self.allow_dangerous_deserialization = allow_dangerous_deserialization
        self.use_huggingface = use_huggingface
        
        # Initialize embeddings based on selected provider
        if use_huggingface:
            # Initialize HuggingFace embeddings
            self.embeddings = CustomHuggingFaceEmbeddings(model_name=hf_model_name)
        else:
            # Get API key from config
            openai_api_key = config.OPENAI_API_KEY
            if not openai_api_key:
                raise ValueError("No OpenAI API key provided. Set the OPENAI_API_KEY in config.")
            
            # Initialize OpenAI embeddings with config settings
            self.embeddings = OpenAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                api_key=openai_api_key,
                dimensions=config.DIMENSIONS
            )
        
        # Initialize text splitter with config settings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
        )
        
        # Initialize vector store
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            self.vector_store = FAISS.load_local(
                self.persist_directory, 
                self.embeddings,
                allow_dangerous_deserialization=self.allow_dangerous_deserialization
            )
        else:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.vector_store = None
    
    def _create_documents(self, text: str, metadata: Dict[str, Any]) -> List[Document]:
        """
        Split text into chunks and create Document objects.
        
        Args:
            text: Text content to split and embed
            metadata: Metadata for the document
            
        Returns:
            List of Document objects
        """
        texts = self.text_splitter.split_text(text)
        documents = [Document(page_content=chunk, metadata=metadata) for chunk in texts]
        return documents
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def add_document(self, text: str, document_id: str, source_type: str, 
                    source_path: str, description: str = None, db: Session = None):
        """
        Updated add_document method that stores chunks in SQLite
        """
        # Create metadata
        metadata = {
                "document_id": document_id,
                "source_type": source_type,
                "source_path": source_path,
                "timestamp": self._get_current_timestamp(),
                "document_type": "General"  
            }
        
        if description:
            metadata["description"] = description
        
        # Split document into chunks
        texts = self.text_splitter.split_text(text)
        
        # Store chunks in SQLite
        if db is None:
            db = next(get_db())
            
        try:
            for idx, chunk in enumerate(texts):
                db_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk,
                    chunk_metadata=metadata
                )
                db.add(db_chunk)
            db.commit()
        except Exception as e:
            db.rollback()
            raise
        
        # Create FAISS documents with just metadata
        documents = [Document(page_content=chunk, metadata=metadata) for chunk in texts]
        
        if not self.vector_store:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        else:
            self.vector_store.add_documents(documents)
        
        self.save()
    
    def save(self) -> None:
        """Save the vector store to disk."""
        if self.vector_store:
            self.vector_store.save_local(self.persist_directory)
    
    def get_document_by_id(self, document_id: str) -> List[Document]:
        """
        Retrieve all chunks for a specific document ID.
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            List of document chunks with metadata
        """
        if not self.vector_store:
            return []
        
        # Get all documents matching the ID
        docs = self.vector_store.similarity_search("", filter={"document_id": document_id})
        return docs
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vector_store:
            return False
        
        # Get all document IDs to delete
        docs_to_delete = [doc.metadata["doc_id"] for doc in 
                         self.vector_store.similarity_search("", filter={"document_id": document_id})]
        
        if not docs_to_delete:
            return False
            
        # Delete documents (implementation depends on FAISS version)
        try:
            self.vector_store.delete(docs_to_delete)
            self.save()
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
        
        