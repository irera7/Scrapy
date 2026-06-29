from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Project(Base):
    """Project model for organizing data collection."""
    
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    data_type = Column(String(50), nullable=False)  # text, image, audio, video, mixed
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="projects")
    scraping_jobs = relationship("ScrapingJob", back_populates="project", cascade="all, delete-orphan")
    data_items = relationship("DataItem", back_populates="project", cascade="all, delete-orphan")
    label_categories = relationship("LabelCategory", back_populates="project", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="project", cascade="all, delete-orphan")
    
    # ML Training Features
    dataset_versions = relationship("DatasetVersion", back_populates="project", cascade="all, delete-orphan")
    dataset_card = relationship("DatasetCard", back_populates="project", uselist=False, cascade="all, delete-orphan")
    annotation_types = relationship("AnnotationType", back_populates="project", cascade="all, delete-orphan")
    augmentation_rules = relationship("AugmentationRule", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project {self.name}>"

