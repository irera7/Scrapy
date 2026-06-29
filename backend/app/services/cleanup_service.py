from datetime import datetime, timezone, timedelta
import structlog

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.storage import storage_service
from app.models.export import Export

logger = structlog.get_logger()


def create_worker_session():
    """Create a fresh async session for worker tasks.
    
    This creates a new engine each time to avoid event loop conflicts
    when running in Celery workers with different event loops.
    """
    engine = create_async_engine(
        settings.DATABASE_URL, 
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    return engine, session_factory()


async def cleanup_exports(days: int = 7) -> int:
    """Clean up export files older than specified days."""
    engine, db = create_worker_session()
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get old exports
        result = await db.execute(
            select(Export).where(
                Export.created_at < cutoff_date,
                Export.status == "completed"
            )
        )
        exports = result.scalars().all()
        
        deleted = 0
        for export in exports:
            try:
                # Delete file from storage
                if export.file_path:
                    storage_service.delete_file(export.file_path)
                
                # Delete record
                await db.delete(export)
                deleted += 1
                
            except Exception as e:
                logger.error(f"Error deleting export {export.id}: {e}")
                continue
        
        await db.commit()
        
        logger.info(f"Cleaned up {deleted} old exports")
        return deleted
    
    finally:
        await db.close()
        await engine.dispose()


async def cleanup_failed_jobs_logs(days: int = 30) -> int:
    """Clean up logs for failed jobs older than specified days."""
    from app.models.job import JobLog
    
    engine, db = create_worker_session()
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Delete old logs
        result = await db.execute(
            delete(JobLog).where(JobLog.created_at < cutoff_date)
        )
        
        deleted = result.rowcount
        await db.commit()
        
        logger.info(f"Cleaned up {deleted} old job logs")
        return deleted
    
    finally:
        await db.close()
        await engine.dispose()

