from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "ai-collector"
    MINIO_SECURE: bool = False
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Providers
    SERPAPI_KEY: Optional[str] = None
    APIFY_TOKEN: Optional[str] = None
    TWITTER_BEARER_TOKEN: Optional[str] = None
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    BROWSERLESS_TOKEN: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3899,https://scrap.nexairalab.net"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {
        "txt", "html", "pdf", "json", "csv",
        "jpg", "jpeg", "png", "gif", "webp", "svg",
        "mp3", "wav", "flac", "ogg", "m4a",
        "mp4", "webm", "avi", "mov", "mkv"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

