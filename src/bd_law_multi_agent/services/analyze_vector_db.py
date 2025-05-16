import os
import uuid
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.database.database import get_db,get_analysis_db
from bd_law_multi_agent.models.document_model import DocumentChunk
from bd_law_multi_agent.services.vector_store import CustomHuggingFaceEmbeddings
from bd_law_multi_agent.utils.logger import logger

from datetime import datetime
from bd_law_multi_agent.models.document_model import AnalysisChunk, AnalysisDocument



class AnalysisVectorDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AnalysisVectorDB, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    
    
    def __init__(self):
        if not self._initialized:
            """Initialize analysis database with proper SQLite and FAISS integration"""
            self.embeddings = CustomHuggingFaceEmbeddings(
                model_name=config.TEMP_EMBEDDING_MODEL
            )
            self.persist_dir = config.ANALYSIS_VECTOR_DB_PATH
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                length_function=len,
            )
            self.vector_store = self._init_vector_store()
            self._initialized = True





    def _init_vector_store(self) -> FAISS:
        """Initialize FAISS store with SQLite backend"""
        os.makedirs(self.persist_dir, exist_ok=True)

        index_path = os.path.join(self.persist_dir, "index.faiss")
        pkl_path = os.path.join(self.persist_dir, "index.pkl")

        if os.path.exists(index_path) and os.path.exists(pkl_path):
            try:
                return FAISS.load_local(
                    self.persist_dir,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")
                raise
        else:
            logger.info("Creating new analysis vector store")
            store = FAISS.from_texts(
                texts=["System Initial Document"],
                embedding=self.embeddings,
                metadatas=[{
                    "document_id": "system-init",
                    "source": "system",
                    "unique_id": str(uuid.uuid4())  
                }]
            )
            store.save_local(self.persist_dir)
            return store


    def _create_analysis_document(self, metadata: Dict[str, Any], db: Session) -> str:
        """Use analysis-specific session"""
        existing = db.query(AnalysisDocument)\
            .filter(AnalysisDocument.source_path == metadata["source_path"])\
            .first()
        
        if existing:
            return existing.id

        document_id = str(uuid.uuid4())
        new_doc = AnalysisDocument(
            id=document_id,
            user_id=metadata.get("user_id", "system"),
            source_type=metadata.get("source_type", "analysis"),  
            source_path=metadata["source_path"],
            document_type=metadata.get("document_type", "RawCase"),
            created_at=datetime.utcnow(),
            full_text=metadata.get("full_text", "")
        )
        db.add(new_doc)
        db.commit()
        return document_id

    def _store_chunks(self, document_id: str, texts: List[str], metadata: Dict[str, Any]):
        """Store chunks in analysis database"""
        db: Session = next(get_analysis_db())  # Use analysis session
        try:
            for idx, chunk in enumerate(texts):
                db_chunk = AnalysisChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk,
                    chunk_metadata=str(metadata)
                )
                db.add(db_chunk)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Chunk storage failed: {e}")
            raise
        finally:
            db.close()

    def add_documents(self, documents: List[Document]):
        """Use analysis database connection"""
        try:
            db = next(get_analysis_db())  
            for doc in documents:
                metadata = doc.metadata.copy()
                metadata.update({
                    "source_path": metadata.get("source_path", str(uuid.uuid4())),
                    "source_type": metadata.get("source_type", "analysis"), 
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                document_id = self._create_analysis_document(metadata, db)
                texts = self.text_splitter.split_text(doc.page_content)
                self._store_chunks(document_id, texts, metadata)
                
                faiss_docs = [
                    Document(
                        page_content=chunk,
                        metadata={
                            "document_id": document_id,
                            **metadata
                        }
                    ) for chunk in texts
                ]
                self.vector_store.add_documents(faiss_docs)
            
            self.vector_store.save_local(self.persist_dir)
            logger.info(f"Added {len(documents)} analysis documents")

        except Exception as e:
            logger.error(f"Document addition failed: {e}")
            raise
        finally:
            db.close()

    def search_with_scores(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search documents with similarity scores"""
        try:
            docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            } for doc, score in docs_with_scores]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_document_by_source(self, source: str) -> Dict[str, Any]:
        """Get document by source identifier"""
        try:
            docs = self.vector_store.similarity_search(
                "",
                filter={"source": source},
                k=1
            )
            return docs[0].metadata if docs else None
        except Exception as e:
            logger.error(f"Failed to get document by source: {e}")
            return None

    def get_document_count(self) -> int:
        """Get total number of documents in the vector store"""
        try:
            return self.vector_store.index.ntotal if self.vector_store else 0
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks"""
        db: Session = next(get_db())
        try:
            db.query(DocumentChunk)\
                .filter(DocumentChunk.document_id == document_id)\
                .delete()
            db.commit()

            docs_to_delete = [
                doc.metadata["unique_id"]
                for doc in self.vector_store.similarity_search(
                    "",
                    filter={"document_id": document_id}
                )
            ]
            if docs_to_delete:
                self.vector_store.delete(docs_to_delete)
                self.vector_store.save_local(self.persist_dir)

            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Delete failed: {e}")
            return False
        finally:
            db.close()
            
    from typing import Dict, Any
    import logging

    def update_document(self, source_hash: str, metadata: Dict[str, Any]):
        """Update existing document metadata in both stores"""
        db = next(get_analysis_db())
        try:
            doc = db.query(AnalysisDocument)\
                .filter(AnalysisDocument.source_path == source_hash)\
                .first()
    
            if doc:
                if 'analysis_result' in metadata:
                    doc.full_text = metadata.get('analysis_result', doc.full_text)
                doc.last_accessed = metadata.get('last_accessed', datetime.utcnow().isoformat())
                db.commit()


            docs = self.vector_store.similarity_search(
                "",
                filter={"source_path": source_hash},
                k=1000  
            )
    
            if docs:
                faiss_ids = [
                    self.vector_store.index_to_docstore_id[i]
                    for i in range(len(docs))
                    if i in self.vector_store.index_to_docstore_id
                ]
        
                if faiss_ids:
                    self.vector_store.delete(faiss_ids)
        
                updated_doc = Document(
                    page_content=docs[0].page_content,
                    metadata={
                        **docs[0].metadata,
                        **metadata
                    }
                )
                self.vector_store.add_documents([updated_doc])
                self.vector_store.save_local(self.persist_dir)

        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            raise
        finally:
            db.close()