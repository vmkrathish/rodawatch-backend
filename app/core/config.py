from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # SQLite for MVP (no server needed — just run and go)
    DATABASE_URL: str = "sqlite:///./roadwatch.db"

    SECRET_KEY: str = "roadwatch-super-secret-jwt-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080   # 7 days
    UPLOAD_DIR: str = "./uploads"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_BASE_URL: str = "http://localhost:8000"  # overridden in .env

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
