from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import ScrapingJob, JobLog
from app.models.data_item import DataItem
from app.schemas.job import (
    JobCreate, JobUpdate, JobResponse, JobLogResponse,
    JobRunRequest, JobStatus
)
from app.workers.tasks import run_scraping_job

router = APIRouter()
logger = structlog.get_logger()


async def verify_project_access(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Project:
    """Verify user has access to the project."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == user_id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    project_id: Optional[UUID] = None,
    status_filter: Optional[JobStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List scraping jobs."""
    # Build query with project access check
    query = (
        select(ScrapingJob)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )
    
    if project_id:
        query = query.where(ScrapingJob.project_id == project_id)
    
    if status_filter:
        query = query.where(ScrapingJob.status == status_filter.value)
    
    query = query.order_by(ScrapingJob.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    # Get item counts
    response = []
    for job in jobs:
        count_result = await db.execute(
            select(func.count(DataItem.id)).where(DataItem.job_id == job.id)
        )
        job_response = JobResponse.model_validate(job)
        job_response.items_collected = count_result.scalar() or 0
        response.append(job_response)
    
    return response


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new scraping job."""
    # Verify project access
    await verify_project_access(job_data.project_id, current_user.id, db)
    
    job = ScrapingJob(
        project_id=job_data.project_id,
        name=job_data.name,
        provider=job_data.provider.value,
        config=job_data.config,
        schedule=job_data.schedule,
        priority=job_data.priority or 0,
        max_retries=job_data.max_retries or 3,
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    logger.info(f"Job created: {job.name} ({job.provider})")
    
    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific job."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Get item count
    count_result = await db.execute(
        select(func.count(DataItem.id)).where(DataItem.job_id == job.id)
    )
    
    job_response = JobResponse.model_validate(job)
    job_response.items_collected = count_result.scalar() or 0
    
    return job_response


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a job."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Update fields
    if job_update.name is not None:
        job.name = job_update.name
    if job_update.config is not None:
        job.config = job_update.config
    if job_update.schedule is not None:
        job.schedule = job_update.schedule
    if job_update.priority is not None:
        job.priority = job_update.priority
    if job_update.max_retries is not None:
        job.max_retries = job_update.max_retries
    if job_update.status is not None:
        job.status = job_update.status.value
    
    await db.commit()
    await db.refresh(job)
    
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a job."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    await db.delete(job)
    await db.commit()
    
    logger.info(f"Job deleted: {job.name}")


@router.post("/{job_id}/run", response_model=JobResponse)
async def run_job(
    job_id: UUID,
    request: JobRunRequest = JobRunRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run a job manually."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status == "running" and not request.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already running"
        )
    
    # Update status
    job.status = "queued"
    await db.commit()
    
    # Queue the job
    run_scraping_job.delay(str(job_id))
    
    logger.info(f"Job queued for execution: {job.name}")
    
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running job."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in ["pending", "queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled"
        )
    
    job.status = "cancelled"
    await db.commit()
    
    logger.info(f"Job cancelled: {job.name}")
    
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed job."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried"
        )
    
    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum retries ({job.max_retries}) exceeded. Reset job to retry again."
        )
    
    # Reset status and queue for retry
    job.status = "queued"
    await db.commit()
    
    # Queue the job with retry
    from app.workers.tasks import retry_failed_scraping_job
    retry_failed_scraping_job.delay(str(job_id))
    
    logger.info(f"Job queued for retry: {job.name} (attempt {job.retry_count + 1}/{job.max_retries})")
    
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/reset", response_model=JobResponse)
async def reset_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset a job's retry count and status."""
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Reset job
    job.status = "pending"
    job.retry_count = 0
    job.error_message = None
    await db.commit()
    
    logger.info(f"Job reset: {job.name}")
    
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("/{job_id}/logs", response_model=List[JobLogResponse])
async def get_job_logs(
    job_id: UUID,
    level: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get logs for a job."""
    # Verify access
    result = await db.execute(
        select(ScrapingJob)
        .join(Project)
        .where(
            and_(ScrapingJob.id == job_id, Project.user_id == current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    query = select(JobLog).where(JobLog.job_id == job_id)
    
    if level:
        query = query.where(JobLog.level == level)
    
    query = query.order_by(JobLog.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [JobLogResponse.model_validate(log) for log in logs]

