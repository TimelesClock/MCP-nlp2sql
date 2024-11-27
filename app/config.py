import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # MCP Settings
    MCP_SERVER_PATH: str = "./mysql_mcp_server.py"
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    class Config:
        env_file = ".env"

settings = Settings()