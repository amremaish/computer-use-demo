import os
from typing import Optional

class Settings:
    # Database settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "computeruse")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "computeruse123")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "chat_sessions")
    
    # API settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    @property
    def DATABASE_URL(self) -> str:
        # Allow override via DATABASE_URL env (useful for tests/CI)
        override = os.getenv("DATABASE_URL")
        if override:
            return override
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings() 