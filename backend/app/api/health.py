"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import redis.asyncio as redis
from pydantic import BaseModel
from typing import Dict, Optional
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.core.storage import storage_service

router = APIRouter()
logger = structlog.get_logger()


class ServiceHealth(BaseModel):
    """Health status for a service."""
    status: str  # healthy, unhealthy, degraded
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall health response."""
    status: str  # healthy, unhealthy, degraded
    timestamp: str
    version: str = "1.0.0"
    services: Dict[str, ServiceHealth]


async def check_database(db: AsyncSession) -> ServiceHealth:
    """Check database health."""
    try:
        start = datetime.now()
        await db.execute(text("SELECT 1"))
        latency = (datetime.now() - start).total_seconds() * 1000
        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ServiceHealth(status="unhealthy", message=str(e))


async def check_redis() -> ServiceHealth:
    """Check Redis health."""
    try:
        start = datetime.now()
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        latency = (datetime.now() - start).total_seconds() * 1000
        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceHealth(status="unhealthy", message=str(e))


async def check_minio() -> ServiceHealth:
    """Check MinIO health."""
    try:
        start = datetime.now()
        info = storage_service.client.list_buckets()
        latency = (datetime.now() - start).total_seconds() * 1000
        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        return ServiceHealth(status="unhealthy", message=str(e))


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check for all services.
    
    Returns the health status of:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Storage (MinIO)
    """
    services = {}
    
    # Check all services
    services["database"] = await check_database(db)
    services["redis"] = await check_redis()
    services["storage"] = await check_minio()
    
    # Determine overall status
    statuses = [s.status for s in services.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        services=services,
    )


@router.get("/live")
async def liveness():
    """
    Kubernetes liveness probe.
    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe.
    Returns 200 if the application can handle requests.
    """
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "reason": str(e)}

