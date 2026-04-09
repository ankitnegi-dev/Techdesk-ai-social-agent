from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    groq_api_key: str = ""
    twitter_bearer_token: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""
    perspective_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://agent:agentpass@localhost:5432/social_agent"
    agent_env: str = "development"
    hitl_enabled: bool = True
    safety_threshold: float = 0.7
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Add this to Settings class manually — rate limiting
SIGNAL_PROCESSING_DELAY: float = 2.0  # seconds between signals
