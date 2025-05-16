from pydantic_settings import BaseSettings, SettingsConfigDict
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
    
    model_config = SettingsConfigDict(
        env_file=".env-",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    # ================================= Tex Extractor Config with Mistral ================================
    Mistral_LLM_MODEL: str = Field(default="mistral-ocr-latest", description="mistral LLM model name")
    MISTRAL_API_KEY: str = Field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""), description="Mistral API key")
    
    
    # =========================================== Database Settings =========================================
    VECTOR_DB_PATH: str = Field(
        default="data/vector_db")
    
     # Security settings
    SECRET_KEY: str = Field(default=os.environ.get("SECRET_KEY", "your-secret-key-change-in-production"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PROJECT_NAME: str = Field(default=os.environ.get("PROJECT_NAME", "Legal Analysis System"))
    # Database settings
    DATABASE_PATH: str = Field(
            default=os.path.join("data", "database", "database.db"),
            description="Path to SQLite database file"
            )

    DATABASE_URL: str = Field(
            default=f"sqlite:///{os.path.join('data', 'database', 'database.db')}",
            description="SQLAlchemy database URL"
        )
    API_V1_STR: str = Field(default=os.environ.get("API_V1_STR", "/api/v1"))
    
    
        # ================================= LEGAL TEXT ANALYSIS CONFIGURATION ==========================================
    LEGAL_STOPWORDS: set = Field(
        default_factory=lambda: {
            'shall', 'may', 'said', 'provided', 'whereas', 'therefore',
            'notwithstanding', 'according', 'hereby', 'thereof'
        },
        description="Set of legal stopwords to ignore during analysis"
    )
    CONTEXT_WINDOW_SIZE: int = Field(
        default=800,
        description="Size of the context window in characters for keyword extraction or context-aware tasks"
    )
    MIN_KEYWORD_LENGTH: int = Field(
        default=4,
        description="Minimum length of a keyword to be considered during extraction"
    )

    
    # ================================= ANALYSIS AND ARGUEMENT GENERATION CONFIGURATION ================================
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-large", description="Model used for text embeddings")
    TEMP_EMBEDDING_MODEL: str = Field(default="dwzhu/e5-base-4k", description="Temporary model for text embeddings")
    LLM_MODEL: str = Field(default="gpt-4.1-2025-04-14", description="Large language model for text generation")
    GROQ_LLM_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq model for text generation")
    OPENAI_API_BASE_URL: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""), description="Open API key")
    
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
    
    MAX_RETRIEVED_DOCS: int = Field(default=20, description="Maximum number of documents to retrieve")
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
    DISABLE_GROQ_PROXIES: bool = True
    # API Keys with environment variable fallback
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key")
    SERPER_API_KEY: str = Field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""), description="Serper API key")
    HUGGINGFACE_API_KEY: str = Field(
        default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY", ""), description="Hugging Face API key"
    )
    GROQ_API_KEY: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""), description="Groq API key")
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