from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class ScrapingJob(Base):
    """Scraping job model."""
    
    __tablename__ = "scraping_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)  # serpapi, apify, custom, twitter, reddit
    config = Column(JSONB, nullable=False)
    schedule = Column(String(100))  # cron expression
    status = Column(String(50), default="pending")  # pending, running, completed, failed, cancelled
    priority = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="scraping_jobs")
    data_items = relationship("DataItem", back_populates="job")
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScrapingJob {self.name} ({self.provider})>"


class JobLog(Base):
    """Job execution logs."""
    
    __tablename__ = "job_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), nullable=False)  # info, warning, error
    message = Column(Text, nullable=False)
    details = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("ScrapingJob", back_populates="logs")
    
    def __repr__(self):
        return f"<JobLog {self.level}: {self.message[:50]}>"

