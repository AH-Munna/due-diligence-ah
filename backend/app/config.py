from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "Due Diligence AH"
    debug: bool = True
    
    # Database
    database_url: str = "sqlite:///./due_diligence.db"
    
    # Vector Store
    chroma_persist_dir: str = "./chroma_db"
    
    # NVIDIA NIM API
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_model: str = "z-ai/glm4.7"  # or moonshotai/kimi-k2.5, deepseek-ai/deepseek-v3.2
    
    # Answer Generation
    answer_temp_a: float = 0.7  # First parallel call
    answer_temp_b: float = 0.9  # Second parallel call
    merge_temp: float = 0.3     # Merge call (lower for consistency)
    max_tokens: int = 4096
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
