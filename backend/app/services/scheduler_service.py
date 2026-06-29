from datetime import datetime, timezone
from uuid import UUID
import structlog
from croniter import croniter

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.job import ScrapingJob
from app.workers.tasks import run_scraping_job

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


async def check_and_queue_scheduled_jobs() -> int:
    """Check for scheduled jobs that need to run and queue them."""
    engine, db = create_worker_session()
    
    try:
        now = datetime.now(timezone.utc)
        
        # Get jobs that are due to run
        result = await db.execute(
            select(ScrapingJob).where(
                and_(
                    ScrapingJob.schedule.isnot(None),
                    ScrapingJob.status.in_(["pending", "completed", "failed"]),
                    ScrapingJob.next_run <= now
                )
            )
        )
        jobs = result.scalars().all()
        
        queued = 0
        for job in jobs:
            try:
                # Update status and queue
                job.status = "queued"
                
                # Calculate next run time
                if job.schedule:
                    cron = croniter(job.schedule, now)
                    job.next_run = cron.get_next(datetime)
                
                await db.commit()
                
                # Queue the job
                run_scraping_job.delay(str(job.id))
                
                queued += 1
                logger.info(f"Queued scheduled job: {job.name}")
                
            except Exception as e:
                logger.error(f"Error queuing job {job.id}: {e}")
                continue
        
        return queued
    
    finally:
        await db.close()
        await engine.dispose()


async def update_job_schedule(job_id: UUID, schedule: str) -> bool:
    """Update a job's schedule and calculate next run time."""
    engine, db = create_worker_session()
    
    try:
        result = await db.execute(
            select(ScrapingJob).where(ScrapingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return False
        
        # Validate cron expression
        try:
            now = datetime.now(timezone.utc)
            cron = croniter(schedule, now)
            next_run = cron.get_next(datetime)
            
            job.schedule = schedule
            job.next_run = next_run
            await db.commit()
            
            logger.info(f"Updated schedule for job {job.name}: {schedule}, next run: {next_run}")
            return True
            
        except Exception as e:
            logger.error(f"Invalid cron expression: {schedule}, error: {e}")
            return False
    
    finally:
        await db.close()
        await engine.dispose()

