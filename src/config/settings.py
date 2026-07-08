from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    primary_llm_provider: str = "openai"
    fallback_llm_provider: str= "groq"
    
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DIM: int =1024
    #  redis for rate limiting and chaching   
    redis_url: str = "redis://localhost:6379/0"
    
    OPENAI_API_KEY :str =""
    
    
    
    MAX_RETRIEVAL_RETRIES:int = 2
    RATE_LIMIT_PER_MINUTE: int = 60
    
    
    environment: Literal["dev", "staging", "prod"] = "dev"
    
    class Config:
        env_file = ".env"
        
settings = Settings() 