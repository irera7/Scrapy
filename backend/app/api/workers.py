"""Celery Worker Monitor API.

This API provides endpoints for monitoring Celery workers, tasks, and queues.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import structlog

from app.core.security import get_current_user
from app.models.user import User
from app.workers.celery_app import celery_app

router = APIRouter()
logger = structlog.get_logger()


@router.get("/status")
async def get_workers_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get status of all Celery workers."""
    try:
        # Get worker stats using Celery's inspect
        inspect = celery_app.control.inspect()
        
        # Get various worker information
        stats = inspect.stats() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        registered = inspect.registered() or {}
        
        workers = []
        for worker_name, worker_stats in stats.items():
            worker_info = {
                "name": worker_name,
                "status": "online",
                "pool": worker_stats.get("pool", {}),
                "broker": worker_stats.get("broker", {}),
                "prefetch_count": worker_stats.get("prefetch_count", 0),
                "total_tasks": worker_stats.get("total", {}),
                "active_tasks": len(active.get(worker_name, [])),
                "reserved_tasks": len(reserved.get(worker_name, [])),
                "scheduled_tasks": len(scheduled.get(worker_name, [])),
                "registered_tasks": registered.get(worker_name, []),
                "rusage": worker_stats.get("rusage", {}),
                "clock": worker_stats.get("clock"),
            }
            workers.append(worker_info)
        
        # Check if workers are offline
        if not workers:
            return {
                "online": False,
                "workers": [],
                "total_workers": 0,
                "total_active_tasks": 0,
                "message": "No workers are currently online"
            }
        
        total_active = sum(len(active.get(w, [])) for w in stats.keys())
        
        return {
            "online": True,
            "workers": workers,
            "total_workers": len(workers),
            "total_active_tasks": total_active,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        return {
            "online": False,
            "workers": [],
            "total_workers": 0,
            "total_active_tasks": 0,
            "error": str(e),
            "message": "Could not connect to Celery broker"
        }


@router.get("/tasks/active")
async def get_active_tasks(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get currently active tasks."""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        
        tasks = []
        for worker_name, worker_tasks in active.items():
            for task in worker_tasks:
                tasks.append({
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "worker": worker_name,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {}),
                    "time_start": task.get("time_start"),
                    "acknowledged": task.get("acknowledged", False),
                })
        
        return {
            "tasks": tasks,
            "count": len(tasks)
        }
    
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        return {"tasks": [], "count": 0, "error": str(e)}


@router.get("/tasks/scheduled")
async def get_scheduled_tasks(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get scheduled tasks."""
    try:
        inspect = celery_app.control.inspect()
        scheduled = inspect.scheduled() or {}
        
        tasks = []
        for worker_name, worker_tasks in scheduled.items():
            for task in worker_tasks:
                tasks.append({
                    "id": task.get("request", {}).get("id"),
                    "name": task.get("request", {}).get("name"),
                    "worker": worker_name,
                    "eta": task.get("eta"),
                    "priority": task.get("priority"),
                })
        
        return {
            "tasks": tasks,
            "count": len(tasks)
        }
    
    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {e}")
        return {"tasks": [], "count": 0, "error": str(e)}


@router.get("/tasks/reserved")
async def get_reserved_tasks(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get reserved (queued) tasks."""
    try:
        inspect = celery_app.control.inspect()
        reserved = inspect.reserved() or {}
        
        tasks = []
        for worker_name, worker_tasks in reserved.items():
            for task in worker_tasks:
                tasks.append({
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "worker": worker_name,
                    "args": task.get("args", []),
                })
        
        return {
            "tasks": tasks,
            "count": len(tasks)
        }
    
    except Exception as e:
        logger.error(f"Failed to get reserved tasks: {e}")
        return {"tasks": [], "count": 0, "error": str(e)}


@router.get("/queues")
async def get_queue_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get information about task queues."""
    try:
        inspect = celery_app.control.inspect()
        active_queues = inspect.active_queues() or {}
        
        queues = {}
        for worker_name, worker_queues in active_queues.items():
            for queue in worker_queues:
                queue_name = queue.get("name")
                if queue_name not in queues:
                    queues[queue_name] = {
                        "name": queue_name,
                        "workers": [],
                        "routing_key": queue.get("routing_key"),
                        "exchange": queue.get("exchange", {}).get("name"),
                    }
                queues[queue_name]["workers"].append(worker_name)
        
        return {
            "queues": list(queues.values()),
            "count": len(queues)
        }
    
    except Exception as e:
        logger.error(f"Failed to get queue info: {e}")
        return {"queues": [], "count": 0, "error": str(e)}


@router.post("/tasks/{task_id}/revoke")
async def revoke_task(
    task_id: str,
    terminate: bool = False,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Revoke (cancel) a task."""
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        logger.info(f"Task {task_id} revoked by {current_user.email}")
        
        return {
            "success": True,
            "task_id": task_id,
            "terminated": terminate
        }
    
    except Exception as e:
        logger.error(f"Failed to revoke task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/purge/{queue_name}")
async def purge_queue(
    queue_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Purge all tasks from a queue."""
    try:
        # This requires direct broker access
        result = celery_app.control.purge()
        logger.info(f"Queue purged by {current_user.email}")
        
        return {
            "success": True,
            "queue": queue_name,
            "purged_count": result
        }
    
    except Exception as e:
        logger.error(f"Failed to purge queue {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_worker_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed worker statistics."""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats() or {}
        
        result = {}
        for worker_name, worker_stats in stats.items():
            result[worker_name] = {
                "pool": {
                    "implementation": worker_stats.get("pool", {}).get("implementation"),
                    "max_concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
                    "processes": worker_stats.get("pool", {}).get("processes", []),
                },
                "total_tasks": worker_stats.get("total", {}),
                "uptime": worker_stats.get("uptime"),
                "pid": worker_stats.get("pid"),
                "sw_ident": worker_stats.get("sw_ident"),
                "sw_ver": worker_stats.get("sw_ver"),
            }
        
        return {
            "stats": result,
            "worker_count": len(result)
        }
    
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return {"stats": {}, "worker_count": 0, "error": str(e)}


@router.get("/task/{task_id}")
async def get_task_result(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the result of a specific task."""
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=celery_app)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.successful() else None,
            "traceback": result.traceback if result.failed() else None,
            "date_done": result.date_done.isoformat() if result.date_done else None,
            "successful": result.successful(),
            "failed": result.failed(),
            "ready": result.ready(),
        }
    
    except Exception as e:
        logger.error(f"Failed to get task result {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
