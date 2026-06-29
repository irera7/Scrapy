from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from contextvars import ContextVar
from typing import Optional

# Context variable to track if we're in a Celery worker
_celery_engine: ContextVar[Optional[any]] = ContextVar('celery_engine', default=None)

# Create async engine for main app
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


def create_celery_engine():
    """Create a fresh engine for Celery workers (new event loop)."""
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )


def get_celery_session_factory():
    """Get or create session factory for Celery worker."""
    celery_engine = _celery_engine.get()
    if celery_engine is None:
        celery_engine = create_celery_engine()
        _celery_engine.set(celery_engine)
    
    return async_sessionmaker(
        celery_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


class CeleryAsyncSession:
    """Context manager for async sessions in Celery workers."""
    
    def __init__(self):
        self._session = None
        self._engine = None
    
    async def __aenter__(self):
        # Create a fresh engine for this event loop
        self._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
        )
        session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        self._session = session_factory()
        return self._session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
        if self._engine:
            await self._engine.dispose()


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

