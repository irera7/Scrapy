from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
)
from app.core.validators import validate_startup
from app.api import auth, projects, jobs, data_items, exports, providers, websocket, health, processing
from app.api import visual_scraper, templates, scheduler, dataset, workers, quality

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting AI Data Collector API")
    
    # Run startup validations
    try:
        await validate_startup()
    except RuntimeError as e:
        logger.error(f"Startup validation failed: {e}")
        # Continue anyway in development, but log warning
        logger.warning("Continuing despite validation errors (development mode)")
    
    yield
    
    logger.info("Shutting down AI Data Collector API")


app = FastAPI(
    title="AI Data Collector",
    description="Web scraping and data collection platform for AI model training",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware (order matters - last added is outermost/first to execute)
# CORS must be outermost to handle preflight OPTIONS requests
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    requests_per_hour=2000,
)
# CORS middleware MUST be added last to be the outermost layer
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Scraping Jobs"])
app.include_router(data_items.router, prefix="/api/data", tags=["Data Items"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(providers.router, prefix="/api/providers", tags=["Providers"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(processing.router, prefix="/api/processing", tags=["Processing"])
app.include_router(visual_scraper.router, prefix="/api/visual-scraper", tags=["Visual Scraper"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(dataset.router, prefix="/api/dataset", tags=["Dataset Management"])
app.include_router(workers.router, prefix="/api/workers", tags=["Worker Monitor"])
app.include_router(quality.router, prefix="/api/quality", tags=["Quality & Validation"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI Data Collector API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def simple_health():
    """Simple health check for load balancers."""
    return {"status": "healthy"}
