import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from semantic_router.encoders import HuggingFaceEncoder
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from typing import List, Dict, Any, Optional
from langchain.embeddings.base import Embeddings

class CustomHuggingFaceEmbeddings(Embeddings):
    def __init__(self, model_name: str = "dwzhu/e5-base-4k"):
        self.encoder = HuggingFaceEncoder(model_name=model_name)
        test_embed = self.encoder(['test'])
        self.embedding_dim = len(test_embed[0])
        print(f"Embedding dimension: {self.embedding_dim}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.encoder(texts)
    
    def embed_query(self, text: str) -> List[float]:
        return self.encoder([text])[0]
    
    def __call__(self, text: str) -> List[float]:
        return self.embed_query(text)

# Example usage
if __name__ == "__main__":
    # Configuration
    PERSIST_DIR = "faiss_db"  # Directory to save the vector store
    os.makedirs(PERSIST_DIR, exist_ok=True)
    
    # Initialize embeddings
    embeddings = CustomHuggingFaceEmbeddings(model_name="dwzhu/e5-base-4k")
    
    # Create some documents
    documents = [
        Document(page_content="This is a document about cats", metadata={"source": "cat.txt"}),
        Document(page_content="This is a document about dogs", metadata={"source": "dog.txt"}),
        Document(page_content="This is a document about birds", metadata={"source": "bird.txt"}),
        Document(page_content="This is a document about car", metadata={"source": "car.txt"}),
    ]
    
    # Create and save FAISS vector store
    vector_store = FAISS.from_documents(
        documents, 
        embedding=embeddings
    )
    
    # Save to disk
    vector_store.save_local(PERSIST_DIR)
    print(f"Saved FAISS index to {PERSIST_DIR}")
    
    # Later, you can load it back:
    loaded_store = FAISS.load_local(
        PERSIST_DIR,
        embeddings,
        allow_dangerous_deserialization=True  # Required for security warning
    )
    
    # Search
    query = "I love cars"
    results = loaded_store.similarity_search_with_score(query, k=2)
    
    # Print results
    print("\nSearch Results:")
    for doc, score in results:
        print(f"Score: {score:.4f} | Content: {doc.page_content} | Source: {doc.metadata['source']}")