from sqlalchemy import Column, String, Integer, DateTime, Text, BigInteger, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Export(Base):
    """Export history model."""
    
    __tablename__ = "exports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False)  # jsonl, csv, parquet, tfrecord, huggingface, coco
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    record_count = Column(Integer)
    filters = Column(JSONB, default={})
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Incremental export support
    base_export_id = Column(UUID(as_uuid=True), ForeignKey("exports.id", ondelete="SET NULL"))
    is_incremental = Column(Boolean, default=False)
    dataset_version_id = Column(UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="SET NULL"))
    
    # Relationships
    project = relationship("Project", back_populates="exports")
    user = relationship("User", back_populates="exports")
    base_export = relationship("Export", remote_side=[id], backref="incremental_exports")
    dataset_version = relationship("DatasetVersion")
    
    def __repr__(self):
        return f"<Export {self.name} ({self.format})>"

