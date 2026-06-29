from celery import shared_task
from datetime import datetime, timezone
import asyncio
import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def run_scraping_job(self, job_id: str):
    """Execute a scraping job."""
    from app.scrapers.executor import execute_scraping_job, JobNotFoundError
    
    logger.info(f"Starting scraping job: {job_id}")
    
    try:
        result = run_async(execute_scraping_job(job_id))
        logger.info(f"Scraping job completed: {job_id}, items: {result.get('items_count', 0)}")
        return result
    except JobNotFoundError as e:
        # Job doesn't exist or was cancelled - don't retry
        logger.warning(f"Scraping job not found or cancelled: {job_id}, error: {str(e)}")
        # Don't retry - job was deleted or cancelled
        return {"error": str(e), "items_count": 0}
    except Exception as e:
        logger.error(f"Scraping job failed: {job_id}, error: {str(e)}")
        # Retry with exponential backoff for other errors
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=5)
def retry_failed_scraping_job(self, job_id: str):
    """Retry a failed scraping job with exponential backoff."""
    from app.scrapers.executor import retry_failed_job, JobNotFoundError
    
    logger.info(f"Retrying scraping job: {job_id}")
    
    try:
        result = run_async(retry_failed_job(job_id))
        logger.info(f"Retry job completed: {job_id}, items: {result.get('items_count', 0)}")
        return result
    except JobNotFoundError as e:
        # Job doesn't exist or was cancelled - don't retry
        logger.warning(f"Retry job not found or cancelled: {job_id}, error: {str(e)}")
        return {"error": str(e), "items_count": 0}
    except Exception as e:
        logger.error(f"Retry job failed: {job_id}, error: {str(e)}")
        # Check if we should retry again
        if "Max retries" in str(e):
            raise  # Don't retry if max retries exceeded
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def run_export_task(self, export_id: str):
    """Execute an export task."""
    from app.services.export_service import execute_export
    
    logger.info(f"Starting export: {export_id}")
    
    try:
        result = run_async(execute_export(export_id))
        logger.info(f"Export completed: {export_id}")
        return result
    except Exception as e:
        logger.error(f"Export failed: {export_id}, error: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=2)
def process_data_item(self, item_id: str, processing_type: str):
    """Process a data item (text cleaning, image processing, etc.)."""
    from app.services.processing_service import process_item
    
    logger.info(f"Processing data item: {item_id}, type: {processing_type}")
    
    try:
        result = run_async(process_item(item_id, processing_type))
        return result
    except Exception as e:
        logger.error(f"Processing failed: {item_id}, error: {str(e)}")
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@celery_app.task
def check_scheduled_jobs():
    """Check for scheduled jobs that need to run."""
    from app.services.scheduler_service import check_and_queue_scheduled_jobs
    
    logger.info("Checking scheduled jobs...")
    
    try:
        queued_count = run_async(check_and_queue_scheduled_jobs())
        if queued_count > 0:
            logger.info(f"Queued {queued_count} scheduled jobs")
        return queued_count
    except Exception as e:
        logger.error(f"Error checking scheduled jobs: {str(e)}")
        return 0


@celery_app.task
def cleanup_old_exports(days: int = 7):
    """Clean up old export files."""
    from app.services.cleanup_service import cleanup_exports
    
    logger.info(f"Cleaning up exports older than {days} days")
    
    try:
        deleted_count = run_async(cleanup_exports(days))
        logger.info(f"Deleted {deleted_count} old exports")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up exports: {str(e)}")
        return 0

