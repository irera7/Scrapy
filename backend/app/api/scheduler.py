"""API endpoints for Advanced Scheduler."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
import structlog

from app.core.security import get_current_user
from app.models.user import User
from app.scrapers.scheduler import (
    advanced_scheduler,
    ScheduledJob,
    ScheduleConfig,
    ScheduleType,
    parse_cron_expression,
    get_next_runs,
    COMMON_SCHEDULES
)

router = APIRouter()
logger = structlog.get_logger()


# Request/Response schemas
class ScheduleConfigSchema(BaseModel):
    schedule_type: str  # cron, interval, once, on_change, conditional
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    check_interval_seconds: int = 3600
    change_detection_selector: Optional[str] = None
    condition_url: Optional[str] = None
    condition_selector: Optional[str] = None
    condition_value: Optional[str] = None
    timezone: str = "UTC"
    max_runs: Optional[int] = None
    expires_at: Optional[datetime] = None
    retry_on_failure: bool = True
    random_delay_seconds: int = 0
    blackout_windows: List[Dict[str, str]] = []


class ScheduledJobCreateRequest(BaseModel):
    name: str
    schedule: ScheduleConfigSchema
    scrape_config: Dict[str, Any]
    project_id: str
    on_complete_webhook: Optional[str] = None
    on_error_webhook: Optional[str] = None


class ScheduledJobResponse(BaseModel):
    id: str
    name: str
    schedule_type: str
    is_active: bool
    run_count: int
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    last_error: Optional[str]
    scrape_config: Dict[str, Any]
    project_id: str


class ScheduledJobDetailResponse(ScheduledJobResponse):
    schedule: Dict[str, Any]
    on_complete: Optional[str]
    on_error: Optional[str]


class SchedulerStatsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    paused_jobs: int
    running: bool
    next_due: Optional[datetime]


class CronParseRequest(BaseModel):
    expression: str


class CronParseResponse(BaseModel):
    expression: str
    minute: str
    hour: str
    day_of_month: str
    month: str
    day_of_week: str
    next_5_runs: List[str]


def job_to_response(job: ScheduledJob) -> ScheduledJobResponse:
    """Convert job to response model."""
    return ScheduledJobResponse(
        id=job.id,
        name=job.name,
        schedule_type=job.config.schedule_type.value,
        is_active=job.is_active,
        run_count=job.run_count,
        last_run=job.last_run,
        next_run=job.next_run,
        last_error=job.last_error,
        scrape_config=job.scrape_config,
        project_id=job.project_id
    )


def job_to_detail_response(job: ScheduledJob) -> ScheduledJobDetailResponse:
    """Convert job to detailed response model."""
    return ScheduledJobDetailResponse(
        id=job.id,
        name=job.name,
        schedule_type=job.config.schedule_type.value,
        is_active=job.is_active,
        run_count=job.run_count,
        last_run=job.last_run,
        next_run=job.next_run,
        last_error=job.last_error,
        scrape_config=job.scrape_config,
        project_id=job.project_id,
        schedule={
            "type": job.config.schedule_type.value,
            "cron_expression": job.config.cron_expression,
            "interval_seconds": job.config.interval_seconds,
            "run_at": job.config.run_at.isoformat() if job.config.run_at else None,
            "check_interval_seconds": job.config.check_interval_seconds,
            "timezone": job.config.timezone,
            "max_runs": job.config.max_runs,
            "expires_at": job.config.expires_at.isoformat() if job.config.expires_at else None,
            "blackout_windows": job.config.blackout_windows,
        },
        on_complete=job.on_complete,
        on_error=job.on_error
    )


# Scheduler control
@router.post("/start")
async def start_scheduler(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start the scheduler."""
    background_tasks.add_task(advanced_scheduler.start)
    return {"status": "starting"}


@router.post("/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user)
):
    """Stop the scheduler."""
    await advanced_scheduler.stop()
    return {"status": "stopped"}


@router.get("/stats", response_model=SchedulerStatsResponse)
async def get_scheduler_stats(
    current_user: User = Depends(get_current_user)
):
    """Get scheduler statistics."""
    stats = advanced_scheduler.get_stats()
    return SchedulerStatsResponse(**stats)


# Scheduled jobs management
@router.get("/jobs", response_model=List[ScheduledJobResponse])
async def list_scheduled_jobs(
    project_id: Optional[str] = None,
    active_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """List all scheduled jobs."""
    jobs = advanced_scheduler.get_all_jobs()
    
    # Filter by project
    if project_id:
        jobs = [j for j in jobs if j.project_id == project_id]
    
    # Filter by active status
    if active_only:
        jobs = [j for j in jobs if j.is_active]
    
    return [job_to_response(j) for j in jobs]


@router.post("/jobs", response_model=ScheduledJobDetailResponse)
async def create_scheduled_job(
    request: ScheduledJobCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new scheduled job."""
    # Parse schedule type
    try:
        schedule_type = ScheduleType(request.schedule.schedule_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule type: {request.schedule.schedule_type}"
        )
    
    # Validate cron expression
    if schedule_type == ScheduleType.CRON and request.schedule.cron_expression:
        try:
            parse_cron_expression(request.schedule.cron_expression)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {e}"
            )
    
    # Create config
    config = ScheduleConfig(
        schedule_type=schedule_type,
        cron_expression=request.schedule.cron_expression,
        interval_seconds=request.schedule.interval_seconds,
        run_at=request.schedule.run_at,
        check_interval_seconds=request.schedule.check_interval_seconds,
        change_detection_selector=request.schedule.change_detection_selector,
        condition_url=request.schedule.condition_url,
        condition_selector=request.schedule.condition_selector,
        condition_value=request.schedule.condition_value,
        timezone=request.schedule.timezone,
        max_runs=request.schedule.max_runs,
        expires_at=request.schedule.expires_at,
        retry_on_failure=request.schedule.retry_on_failure,
        random_delay_seconds=request.schedule.random_delay_seconds,
        blackout_windows=request.schedule.blackout_windows
    )
    
    # Create job
    job = ScheduledJob(
        id=str(uuid4()),
        name=request.name,
        config=config,
        scrape_config=request.scrape_config,
        project_id=request.project_id,
        on_complete=request.on_complete_webhook,
        on_error=request.on_error_webhook
    )
    
    advanced_scheduler.add_job(job)
    
    logger.info(f"Scheduled job created: {job.name}")
    
    return job_to_detail_response(job)


@router.get("/jobs/{job_id}", response_model=ScheduledJobDetailResponse)
async def get_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific scheduled job."""
    job = advanced_scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_to_detail_response(job)


@router.delete("/jobs/{job_id}")
async def delete_scheduled_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a scheduled job."""
    job = advanced_scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    advanced_scheduler.remove_job(job_id)
    
    return {"status": "ok"}


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Pause a scheduled job."""
    job = advanced_scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    advanced_scheduler.pause_job(job_id)
    
    return {"status": "paused"}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resume a paused job."""
    job = advanced_scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    advanced_scheduler.resume_job(job_id)
    
    return {"status": "resumed"}


@router.get("/jobs/{job_id}/next-runs")
async def get_next_runs_for_job(
    job_id: str,
    count: int = 5,
    current_user: User = Depends(get_current_user)
):
    """Get next N run times for a job."""
    job = advanced_scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.config.schedule_type != ScheduleType.CRON:
        return {"next_runs": [job.next_run.isoformat() if job.next_run else None]}
    
    runs = get_next_runs(job.config.cron_expression, count)
    return {"next_runs": runs}


# Cron utilities
@router.post("/cron/parse", response_model=CronParseResponse)
async def parse_cron(
    request: CronParseRequest,
    current_user: User = Depends(get_current_user)
):
    """Parse a cron expression and show schedule info."""
    try:
        result = parse_cron_expression(request.expression)
        return CronParseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cron/presets")
async def get_cron_presets(
    current_user: User = Depends(get_current_user)
):
    """Get common cron schedule presets."""
    presets = []
    
    for name, expression in COMMON_SCHEDULES.items():
        try:
            info = parse_cron_expression(expression)
            presets.append({
                "name": name.replace("_", " ").title(),
                "key": name,
                "expression": expression,
                "next_run": info["next_5_runs"][0] if info["next_5_runs"] else None
            })
        except:
            pass
    
    return {"presets": presets}


# Due jobs
@router.get("/jobs/due", response_model=List[ScheduledJobResponse])
async def get_due_jobs(
    current_user: User = Depends(get_current_user)
):
    """Get jobs that are due to run."""
    jobs = advanced_scheduler.get_due_jobs()
    return [job_to_response(j) for j in jobs]

