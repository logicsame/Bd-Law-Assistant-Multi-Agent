from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

class Config(BaseSettings):
    """
    Configuration settings for the legal analysis system.
    Uses Pydantic for type validation and environment variable loading.
    """
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow",  
    }
    
    # ================================= Tex Extractor Config with Mistral ================================
    Mistral_LLM_MODEL: str = Field(default="mistral-ocr-latest", description="mistral LLM model name")
    MISTRAL_API_KEY: str = Field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""), description="Mistral API key")
    
    
    # =========================================== Database Settings =========================================
    # Add your database configuration here if needed
    
    
    # ================================= ANALYSIS AND ARGUEMENT GENERATION CONFIGURATION ================================
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-large", description="Model used for text embeddings")
    LLM_MODEL: str = Field(default="gpt-4-1106-preview", description="Large language model for text generation")
    
    # Text Splitting Configuration
    CHUNK_SIZE: int = Field(default=1000, description="Size of text chunks for processing")
    CHUNK_OVERLAP: int = Field(default=200, description="Overlap between consecutive text chunks")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Threshold for similarity matching")
    TEMPERATURE: float = Field(default=0.2, description="Temperature parameter for text generation")
    DIMENSIONS: int = Field(default=1536, description="Dimensions for embedding vectors")
    MAX_TOKENS: int = Field(default=4096, description="Maximum tokens for text generation")
    
    # Case Classification Configuration
    CASE_CATEGORIES: List[str] = Field(
        default=[
            "Civil Dispute", 
            "Criminal Case", 
            "Family Law", 
            "Property Dispute", 
            "Contract Law", 
            "Labor Law"
        ],
        description="Categories for legal case classification"
    )
    
    CASE_SEVERITY_LEVELS: List[str] = Field(
        default=[
            "Low Complexity", 
            "Medium Complexity", 
            "High Complexity", 
            "Extreme Complexity"
        ],
        description="Severity levels for case complexity classification"
    )
    
    MAX_RETRIEVED_DOCS: int = Field(default=5, description="Maximum number of documents to retrieve")
    CITATION_LENGTH: int = Field(default=500, description="Length limit for citations")
    
    # ================================= SEARCH SYSTEM CONFIGURATION ==========================================
    SERPER_API_BASE_URL: str = Field(
        default="https://google.serper.dev/search", 
        description="Base URL for Serper API"
    )
    MAX_SEARCH_RESULTS: int = Field(default=10, description="Maximum number of search results to return")
    SEARCH_COUNTRY_CODE: str = Field(default="bd", description="Country code for search localization")
    MAX_ITERATIONS: int = Field(default=10, description="Maximum number of search iterations")
    MAX_EXECUTION_TIME: int = Field(default=120, description="Maximum execution time in seconds")
    KNOWLEDGE_VECTOR_DB_PATH: str = Field(
        default="data/vector_db", 
        description="Path to vector database for knowledge storage"
    )
    
    # API Keys with environment variable fallback
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key")
    SERPER_API_KEY: str = Field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""), description="Serper API key")
    
    LEGAL_DOMAINS: List[str] = Field(
        default=[
            "bdlaws.minlaw.gov.bd",
            "supremecourt.gov.bd",
            "lawcommissionbangladesh.org",
            "bangladeshsupremecourtbar.com",
            "pmo.gov.bd",
            "mljpa.gov.bd"
        ],
        description="Trusted legal domains for search"
    )
    SEARCH_RATE_LIMIT: int = Field(default=15, description="Rate limit for search requests")
    
    # ================================= CONFLICT RESOLUTION CONFIGURATION =========================================
    CONFLICT_TEMPERATURE: float = Field(default=0.1, description="Temperature for conflict resolution")
    CONFLICT_MAX_TOKENS: int = Field(default=4096, description="Maximum tokens for conflict resolution")
    CONFLICT_MODEL: str = Field(default="gpt-4-1106-preview", description="Model for conflict resolution")
    ANALYSIS_VECTOR_DB_PATH: str = Field(
        default="data/analysis_vector_db", 
        description="Path to vector database for analysis storage"
    )

config = Config()