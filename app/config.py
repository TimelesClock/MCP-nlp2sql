import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-2024-11-20"
    ADMIN_KEY: str
    
    # MCP MySQL Settings
    MCP_MYSQL_ENV: Dict[str, str] = {
        "DB_HOST": "",
        "DB_PORT": "",
        "DB_USER": "",
        "DB_PASSWORD": "",
        "DB_NAME": ""
    }
    
    class Config:
        env_file = ".env"

settings = Settings()