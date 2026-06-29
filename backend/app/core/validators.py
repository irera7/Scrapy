"""Environment and startup validators."""
import os
import structlog
from typing import List, Tuple
import asyncio

logger = structlog.get_logger()


class StartupValidator:
    """Validates environment and dependencies on startup."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_env_vars(self) -> None:
        """Validate required environment variables."""
        from app.core.config import settings
        
        # Check if settings were loaded with non-default values
        if settings.SECRET_KEY == "your-super-secret-key-change-in-production":
            self.warnings.append("Using default SECRET_KEY - change this in production!")
        
        logger.info("Environment variables loaded from settings")
    
    async def validate_database(self) -> None:
        """Validate database connection."""
        from app.core.config import settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        try:
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            logger.info("Database connection validated")
        except Exception as e:
            self.errors.append(f"Database connection failed: {str(e)}")
    
    async def validate_redis(self) -> None:
        """Validate Redis connection."""
        from app.core.config import settings
        import redis.asyncio as redis
        
        try:
            client = redis.from_url(settings.REDIS_URL)
            await client.ping()
            await client.close()
            logger.info("Redis connection validated")
        except Exception as e:
            self.warnings.append(f"Redis connection failed: {str(e)} - Celery tasks may not work")
    
    async def validate_minio(self) -> None:
        """Validate MinIO connection."""
        from app.core.config import settings
        from minio import Minio
        
        try:
            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            # Try to list buckets
            client.list_buckets()
            logger.info("MinIO connection validated")
        except Exception as e:
            self.warnings.append(f"MinIO connection failed: {str(e)} - File storage may not work")
    
    async def run_all_validations(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations and return results."""
        logger.info("Running startup validations...")
        
        # Sync validations
        self.validate_env_vars()
        
        # Async validations
        await self.validate_database()
        await self.validate_redis()
        await self.validate_minio()
        
        # Log results
        for warning in self.warnings:
            logger.warning(warning)
        
        for error in self.errors:
            logger.error(error)
        
        is_valid = len(self.errors) == 0
        
        if is_valid:
            logger.info("All startup validations passed")
        else:
            logger.error(f"Startup validation failed with {len(self.errors)} error(s)")
        
        return is_valid, self.errors, self.warnings


async def validate_startup() -> None:
    """Run startup validation - raises exception if critical errors."""
    validator = StartupValidator()
    is_valid, errors, warnings = await validator.run_all_validations()
    
    if not is_valid:
        error_msg = "Startup validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(error_msg)

