"""Custom middleware for the application."""
import time
import uuid
from typing import Callable
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window."""
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = defaultdict(list)
        self.hour_requests = defaultdict(list)
        self._cleanup_task = None
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (IP or user ID)."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use token hash as identifier for authenticated users
            return f"token:{hash(auth_header)}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, client_id: str, now: datetime):
        """Remove old requests from tracking."""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.minute_requests[client_id] = [
            t for t in self.minute_requests[client_id] if t > minute_ago
        ]
        self.hour_requests[client_id] = [
            t for t in self.hour_requests[client_id] if t > hour_ago
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and CORS preflight
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS (CORS preflight) requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        now = datetime.now()
        
        # Cleanup old requests
        self._cleanup_old_requests(client_id, now)
        
        # Check rate limits
        minute_count = len(self.minute_requests[client_id])
        hour_count = len(self.hour_requests[client_id])
        
        if minute_count >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded (minute)",
                client_id=client_id,
                count=minute_count,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please wait a minute.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )
        
        if hour_count >= self.requests_per_hour:
            logger.warning(
                "Rate limit exceeded (hour)",
                client_id=client_id,
                count=hour_count,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please wait an hour.",
                    "retry_after": 3600,
                },
                headers={"Retry-After": "3600"},
            )
        
        # Track this request
        self.minute_requests[client_id].append(now)
        self.hour_requests[client_id].append(now)
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(self.requests_per_minute - minute_count - 1)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(self.requests_per_hour - hour_count - 1)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        
        except ValueError as e:
            logger.warning("Validation error", error=str(e), path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e), "type": "validation_error"},
            )
        
        except PermissionError as e:
            logger.warning("Permission denied", error=str(e), path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(e), "type": "permission_error"},
            )
        
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception(
                "Unhandled exception",
                request_id=request_id,
                error=str(e),
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred. Please try again later.",
                    "type": "internal_error",
                    "request_id": request_id,
                },
            )

