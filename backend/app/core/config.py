import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "BCCL Enterprise AI Knowledge Retrieval System"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "bccl-enterprise-rag-secret-key-super-secure-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    RATE_LIMIT_PER_MINUTE: int = 120

    # Database
    DATABASE_URL: str = "sqlite:///./data/bccl_rag.db"
    
    # Storage Paths
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    RAW_DATA_DIR: str = os.path.join(DATA_DIR, "raw")
    PROCESSED_DATA_DIR: str = os.path.join(DATA_DIR, "processed")

    # AI & RAG Configuration
    LLM_PROVIDER: str = "auto"  # auto, gemini, openai, ollama, mock
    EMBEDDING_PROVIDER: str = "auto"  # auto, local, gemini, openai
    OCR_PROVIDER: str = "tesseract"
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Chunking Hyperparameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 60
    MIN_CHUNK_LENGTH: int = 40

    # Retrieval & Reranking Hyperparameters
    DENSE_SEARCH_WEIGHT: float = 0.65
    SPARSE_SEARCH_WEIGHT: float = 0.35
    RETRIEVAL_TOP_K: int = 5
    RERANKER_TOP_N: int = 10
    ENABLE_RERANKER: bool = True
    ABSTENTION_THRESHOLD: float = 0.25

settings = Settings()
