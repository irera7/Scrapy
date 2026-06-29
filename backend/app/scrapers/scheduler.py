"""Advanced scheduling system for scraping jobs."""
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import hashlib
import structlog
from croniter import croniter

logger = structlog.get_logger()


class ScheduleType(str, Enum):
    """Types of schedules."""
    CRON = "cron"  # Cron expression
    INTERVAL = "interval"  # Fixed interval
    ONCE = "once"  # Run once at specific time
    ON_CHANGE = "on_change"  # Run when content changes
    CONDITIONAL = "conditional"  # Run based on conditions
    WEBHOOK = "webhook"  # Triggered by webhook


@dataclass
class ScheduleConfig:
    """Configuration for a schedule."""
    schedule_type: ScheduleType
    
    # For CRON type
    cron_expression: Optional[str] = None
    
    # For INTERVAL type
    interval_seconds: Optional[int] = None
    
    # For ONCE type
    run_at: Optional[datetime] = None
    
    # For ON_CHANGE type
    check_interval_seconds: int = 3600  # Check every hour
    change_detection_selector: Optional[str] = None  # CSS selector to monitor
    
    # For CONDITIONAL type
    condition_url: Optional[str] = None  # URL to check
    condition_selector: Optional[str] = None  # Selector to find
    condition_value: Optional[str] = None  # Expected value
    
    # General options
    timezone: str = "UTC"
    max_runs: Optional[int] = None  # Max number of runs (None = unlimited)
    expires_at: Optional[datetime] = None  # Schedule expiration
    retry_on_failure: bool = True
    random_delay_seconds: int = 0  # Add random delay to avoid detection
    
    # Blackout windows (times when job shouldn't run)
    blackout_windows: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ScheduledJob:
    """A scheduled scraping job."""
    id: str
    name: str
    config: ScheduleConfig
    scrape_config: Dict[str, Any]
    project_id: str
    
    # State
    is_active: bool = True
    run_count: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_content_hash: Optional[str] = None
    last_error: Optional[str] = None
    
    # Callbacks
    on_complete: Optional[str] = None  # Webhook URL
    on_error: Optional[str] = None  # Webhook URL


class AdvancedScheduler:
    """Advanced scheduler with multiple trigger types."""
    
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, Callable] = {}
    
    def add_job(self, job: ScheduledJob):
        """Add a job to the scheduler."""
        # Calculate initial next_run
        job.next_run = self._calculate_next_run(job)
        self._jobs[job.id] = job
        logger.info(f"Added scheduled job: {job.name}, next run: {job.next_run}")
    
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Removed scheduled job: {job_id}")
    
    def pause_job(self, job_id: str):
        """Pause a job."""
        if job_id in self._jobs:
            self._jobs[job_id].is_active = False
    
    def resume_job(self, job_id: str):
        """Resume a paused job."""
        if job_id in self._jobs:
            self._jobs[job_id].is_active = True
            self._jobs[job_id].next_run = self._calculate_next_run(self._jobs[job_id])
    
    def set_callback(self, event: str, callback: Callable):
        """Set a callback for scheduler events."""
        self._callbacks[event] = callback
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now()
                
                for job_id, job in list(self._jobs.items()):
                    if not job.is_active:
                        continue
                    
                    # Check if job has expired
                    if job.config.expires_at and now > job.config.expires_at:
                        job.is_active = False
                        continue
                    
                    # Check if max runs reached
                    if job.config.max_runs and job.run_count >= job.config.max_runs:
                        job.is_active = False
                        continue
                    
                    # Check if in blackout window
                    if self._is_in_blackout(job, now):
                        continue
                    
                    # Check if job should run
                    should_run = False
                    
                    if job.config.schedule_type == ScheduleType.ON_CHANGE:
                        should_run = await self._check_for_changes(job, now)
                    elif job.config.schedule_type == ScheduleType.CONDITIONAL:
                        should_run = await self._check_condition(job)
                    elif job.next_run and now >= job.next_run:
                        should_run = True
                    
                    if should_run:
                        await self._execute_job(job)
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    def _calculate_next_run(self, job: ScheduledJob) -> Optional[datetime]:
        """Calculate the next run time for a job."""
        config = job.config
        now = datetime.now()
        
        if config.schedule_type == ScheduleType.CRON:
            if config.cron_expression:
                cron = croniter(config.cron_expression, now)
                return cron.get_next(datetime)
        
        elif config.schedule_type == ScheduleType.INTERVAL:
            if config.interval_seconds:
                base = job.last_run or now
                return base + timedelta(seconds=config.interval_seconds)
        
        elif config.schedule_type == ScheduleType.ONCE:
            if config.run_at and config.run_at > now:
                return config.run_at
            return None
        
        elif config.schedule_type == ScheduleType.ON_CHANGE:
            # Check at fixed intervals
            base = job.last_run or now
            return base + timedelta(seconds=config.check_interval_seconds)
        
        elif config.schedule_type == ScheduleType.CONDITIONAL:
            # Check frequently
            return now + timedelta(minutes=5)
        
        return None
    
    def _is_in_blackout(self, job: ScheduledJob, now: datetime) -> bool:
        """Check if current time is in a blackout window."""
        for window in job.config.blackout_windows:
            start_time = datetime.strptime(window.get("start", "00:00"), "%H:%M").time()
            end_time = datetime.strptime(window.get("end", "00:00"), "%H:%M").time()
            current_time = now.time()
            
            if start_time <= current_time <= end_time:
                return True
        
        return False
    
    async def _check_for_changes(self, job: ScheduledJob, now: datetime) -> bool:
        """Check if content has changed since last run."""
        if not job.next_run or now < job.next_run:
            return False
        
        import httpx
        from app.scrapers.anti_detection import anti_detection
        
        try:
            # Get the URL to check
            url = job.scrape_config.get("url") or job.scrape_config.get("urls", [None])[0]
            if not url:
                return True  # No URL to check, just run
            
            profile = anti_detection.generate_profile()
            headers = anti_detection.get_request_headers(profile)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30)
                
                if job.config.change_detection_selector:
                    # Check specific element
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "lxml")
                    element = soup.select_one(job.config.change_detection_selector)
                    content = element.get_text() if element else ""
                else:
                    content = response.text
                
                # Compute hash
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Compare with last hash
                if job.last_content_hash and job.last_content_hash == content_hash:
                    # No change, update next_run and return False
                    job.next_run = self._calculate_next_run(job)
                    return False
                
                job.last_content_hash = content_hash
                return True
        
        except Exception as e:
            logger.warning(f"Change detection failed for {job.name}: {e}")
            return True  # Run anyway on error
    
    async def _check_condition(self, job: ScheduledJob) -> bool:
        """Check if conditional trigger is met."""
        if not job.config.condition_url:
            return False
        
        import httpx
        from app.scrapers.anti_detection import anti_detection
        
        try:
            profile = anti_detection.generate_profile()
            headers = anti_detection.get_request_headers(profile)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    job.config.condition_url,
                    headers=headers,
                    timeout=30
                )
                
                if job.config.condition_selector:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "lxml")
                    element = soup.select_one(job.config.condition_selector)
                    
                    if not element:
                        return False
                    
                    value = element.get_text(strip=True)
                    
                    if job.config.condition_value:
                        return value == job.config.condition_value
                    
                    return bool(value)  # True if element exists and has content
                
                return response.status_code == 200
        
        except Exception as e:
            logger.warning(f"Condition check failed for {job.name}: {e}")
            return False
    
    async def _execute_job(self, job: ScheduledJob):
        """Execute a scheduled job."""
        import random
        
        # Apply random delay if configured
        if job.config.random_delay_seconds > 0:
            delay = random.uniform(0, job.config.random_delay_seconds)
            await asyncio.sleep(delay)
        
        logger.info(f"Executing scheduled job: {job.name}")
        
        job.last_run = datetime.now()
        job.run_count += 1
        
        try:
            # Trigger the actual scraping
            if "execute_job" in self._callbacks:
                await self._callbacks["execute_job"](job)
            
            job.last_error = None
            
            # Call on_complete webhook
            if job.on_complete:
                await self._call_webhook(job.on_complete, {
                    "job_id": job.id,
                    "job_name": job.name,
                    "status": "completed",
                    "run_count": job.run_count
                })
        
        except Exception as e:
            job.last_error = str(e)
            logger.error(f"Job execution failed: {job.name}, error: {e}")
            
            # Call on_error webhook
            if job.on_error:
                await self._call_webhook(job.on_error, {
                    "job_id": job.id,
                    "job_name": job.name,
                    "status": "failed",
                    "error": str(e)
                })
        
        finally:
            # Calculate next run
            job.next_run = self._calculate_next_run(job)
    
    async def _call_webhook(self, url: str, data: Dict[str, Any]):
        """Call a webhook URL."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    url,
                    json=data,
                    timeout=30
                )
        except Exception as e:
            logger.warning(f"Webhook call failed: {url}, error: {e}")
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[ScheduledJob]:
        """Get all scheduled jobs."""
        return list(self._jobs.values())
    
    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get jobs that are due to run."""
        now = datetime.now()
        return [
            job for job in self._jobs.values()
            if job.is_active and job.next_run and job.next_run <= now
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        total = len(self._jobs)
        active = sum(1 for j in self._jobs.values() if j.is_active)
        
        return {
            "total_jobs": total,
            "active_jobs": active,
            "paused_jobs": total - active,
            "running": self._running,
            "next_due": min(
                (j.next_run for j in self._jobs.values() if j.next_run),
                default=None
            )
        }


def parse_cron_expression(expression: str) -> Dict[str, Any]:
    """Parse a cron expression and return human-readable info."""
    parts = expression.split()
    
    if len(parts) != 5:
        raise ValueError("Invalid cron expression")
    
    minute, hour, day, month, weekday = parts
    
    def parse_field(field: str, max_val: int, names: Optional[List[str]] = None) -> str:
        if field == "*":
            return "every"
        if field.startswith("*/"):
            interval = int(field[2:])
            return f"every {interval}"
        if "," in field:
            return "specific values"
        if "-" in field:
            return "range"
        return field
    
    weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    return {
        "expression": expression,
        "minute": parse_field(minute, 59),
        "hour": parse_field(hour, 23),
        "day_of_month": parse_field(day, 31),
        "month": parse_field(month, 12, month_names),
        "day_of_week": parse_field(weekday, 6, weekday_names),
        "next_5_runs": get_next_runs(expression, 5)
    }


def get_next_runs(cron_expression: str, count: int = 5) -> List[str]:
    """Get the next N run times for a cron expression."""
    cron = croniter(cron_expression, datetime.now())
    runs = []
    
    for _ in range(count):
        next_run = cron.get_next(datetime)
        runs.append(next_run.isoformat())
    
    return runs


# Common cron expressions
COMMON_SCHEDULES = {
    "every_minute": "* * * * *",
    "every_5_minutes": "*/5 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "every_hour": "0 * * * *",
    "every_2_hours": "0 */2 * * *",
    "every_6_hours": "0 */6 * * *",
    "every_12_hours": "0 */12 * * *",
    "daily_midnight": "0 0 * * *",
    "daily_noon": "0 12 * * *",
    "weekly_monday": "0 0 * * 1",
    "weekly_sunday": "0 0 * * 0",
    "monthly_first": "0 0 1 * *",
    "monthly_last": "0 0 L * *",  # Note: L is not standard, needs special handling
}


# Global scheduler instance
advanced_scheduler = AdvancedScheduler()

