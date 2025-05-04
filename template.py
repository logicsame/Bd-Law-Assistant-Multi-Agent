import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')

project_name = 'Bd Law Assitant Multi Agent'

list_of_files = [
    # GitHub Actions CI/CD
    '.github/workflows/ci-cd.yml',
    
    # Project structure
    f"src/{project_name}/__init__.py",
    f"src/{project_name}/main.py",
    
    # API Layer
    f"src/{project_name}/api/__init__.py",
    f"src/{project_name}/api/v1/__init__.py",
    f"src/{project_name}/api/v1/endpoints.py",
    f"src/{project_name}/api/v1/schemas.py",
    
    # Core components
    f"src/{project_name}/core/__init__.py",
    f"src/{project_name}/core/config.py",
    f"src/{project_name}/core/security.py",
    
    # Models
    f"src/{project_name}/models/__init__.py",
    f"src/{project_name}/models/legal_models.py",
    f"src/{project_name}/models/rag_models.py",
    
    # Services
    f"src/{project_name}/services/__init__.py",
    f"src/{project_name}/services/document_service.py",
    f"src/{project_name}/services/legal_service.py",
    
    # Utilities
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/common.py",
    f"src/{project_name}/utils/logger.py",
    f"src/{project_name}/utils/file_utils.py",
    
    # Tests
    f"tests/__init__.py",
    f"tests/test_api.py",
    f"tests/test_services.py",
    
    # Configurations
    ".env",
    "requirements.txt",
    "setup.py",
    "Dockerfile",
    "README.md",
    
    # Data storage (empty directories)
    "data/processed_documents/",
    "data/vector_store/",
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)
    
    # Create directory if it doesn't exist
    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory: {filedir} for {filename}")
    
    # Create empty file if it doesn't exist or is empty
    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, 'w') as f:
            if filepath.suffix == '.py':
                if filename == '__init__.py':
                    f.write('"""Package initialization."""\n')
                elif filename == 'main.py':
                    f.write('''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to Bangladesh Legal AI Assistant API"}
''')
                elif filename == 'config.py':
                    f.write('''from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    LLM_MODEL: str = "gpt-4-turbo"
    
    class Config:
        env_file = ".env"

settings = Settings()
''')
        logging.info(f'Creating file: {filepath}')
    else:
        logging.info(f'{filename} already exists')