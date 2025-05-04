from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    LLM_MODEL: str = "gpt-4-turbo"
    
    class Config:
        env_file = ".env"

settings = Settings()
