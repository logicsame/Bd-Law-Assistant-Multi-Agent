import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from bd_law_multi_agent.core.config import config


class DocumentVectorDatabase:
    """
    A class to convert extracted document text to embeddings and store in FAISS vector database.
    """
    
    def __init__(self, persist_directory: str = None, allow_dangerous_deserialization: bool = False):
        """
        Initialize the DocumentVectorDatabase.
        
        Args:
            persist_directory: Directory to store the vector database. Uses config if None.
            allow_dangerous_deserialization: Whether to allow loading potentially unsafe pickle files.
        """
        # Use config path if not specified
        self.persist_directory = persist_directory or config.KNOWLEDGE_VECTOR_DB_PATH
        self.allow_dangerous_deserialization = allow_dangerous_deserialization
        
        # Get API key from config
        openai_api_key = config.OPENAI_API_KEY
        if not openai_api_key:
            raise ValueError("No OpenAI API key provided. Set the OPENAI_API_KEY in config.")
        
        # Initialize embeddings with config settings
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
    
    def add_document(self, text: str, document_id: str, source_type: str, source_path: str, description: Optional[str] = None) -> None:
        """
        Add a document to the vector store.
        
        Args:
            text: Extracted text from the document
            document_id: Unique identifier for the document
            source_type: Type of source (pdf, image, url)
            source_path: Path or URL of the original document
            description: Optional description of the document
        """
        metadata = {
            "document_id": document_id,
            "source_type": source_type,
            "source_path": source_path,
            "timestamp": self._get_current_timestamp()
        }
        
        if description:
            metadata["description"] = description
        
        documents = self._create_documents(text, metadata)
        
        if not documents:
            return
        
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        else:
            self.vector_store.add_documents(documents)
        
        self.save()
    
    def save(self) -> None:
        """Save the vector store to disk."""
        if self.vector_store:
            self.vector_store.save_local(self.persist_directory)
    
    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents in the vector store.
        
        Args:
            query: Search query
            top_k: Number of results to return (uses config if None)
            
        Returns:
            List of search results with document and score
        """
        if not self.vector_store:
            return []
        
        k = top_k or config.MAX_RETRIEVED_DOCS
        docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
        
        results = []
        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        
        return results
    
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