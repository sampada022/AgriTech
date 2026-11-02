import sys
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = True
    DEMO_MODE: bool = True
    DEMO_FORCE_CACHED_AI: bool = True
    DATA_DIR: str = "data"
    DEMO_DIR: str = "demo"
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""
    PUBLIC_TUNNEL_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

