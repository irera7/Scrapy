from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, BigInteger, ForeignKey, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DataItem(Base):
    """Collected data item model."""
    
    __tablename__ = "data_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scraping_jobs.id", ondelete="SET NULL"))
    data_type = Column(String(50), nullable=False)  # text, image, audio, video, structured
    source_url = Column(Text)
    content = Column(Text)  # For text data
    file_path = Column(String(500))  # For media files
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    item_metadata = Column("metadata", JSONB, default={})
    labels = Column(JSONB, default=[])
    quality_score = Column(Float)
    is_processed = Column(Boolean, default=False)
    is_labeled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # ML Training Features
    dataset_split = Column(String(20), default="unassigned")  # train, val, test, unassigned
    annotations = Column(JSONB, default={})  # BBox, segmentation, NER annotations
    embedding = Column(ARRAY(Float))  # Vector embedding for similarity search
    uncertainty_score = Column(Float)  # For active learning
    augmented_from = Column(UUID(as_uuid=True), ForeignKey("data_items.id", ondelete="SET NULL"))
    augmentation_type = Column(String(100))  # Type of augmentation applied
    
    # Relationships
    project = relationship("Project", back_populates="data_items")
    job = relationship("ScrapingJob", back_populates="data_items")
    augmented_items = relationship("DataItem", backref="original_item", remote_side=[id])
    
    def __repr__(self):
        return f"<DataItem {self.data_type} - {self.id}>"


class LabelCategory(Base):
    """Label categories for data annotation."""
    
    __tablename__ = "label_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#3B82F6")
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="label_categories")
    
    def __repr__(self):
        return f"<LabelCategory {self.name}>"

