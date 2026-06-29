"""Dataset management models for ML training."""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DatasetVersion(Base):
    """Dataset version for tracking dataset snapshots."""
    
    __tablename__ = "dataset_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)  # e.g., "v1.0.0"
    description = Column(Text)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="SET NULL"))
    
    # Counts
    item_count = Column(Integer, default=0)
    train_count = Column(Integer, default=0)
    val_count = Column(Integer, default=0)
    test_count = Column(Integer, default=0)
    
    # Data
    item_ids = Column(JSONB, default=[])  # List of item IDs in this version
    split_config = Column(JSONB, default={})  # Split configuration used
    statistics = Column(JSONB, default={})  # Computed statistics
    
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    project = relationship("Project", back_populates="dataset_versions")
    parent_version = relationship("DatasetVersion", remote_side=[id], backref="child_versions")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<DatasetVersion {self.version}>"


class DatasetCard(Base):
    """Dataset card following HuggingFace format."""
    
    __tablename__ = "dataset_cards"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Basic info
    title = Column(String(255), nullable=False)
    description = Column(Text)
    homepage = Column(String(500))
    license = Column(String(100))
    citation = Column(Text)
    
    # Classification
    languages = Column(JSONB, default=[])  # e.g., ["en", "fa"]
    task_categories = Column(JSONB, default=[])  # e.g., ["text-classification", "image-classification"]
    task_ids = Column(JSONB, default=[])  # e.g., ["sentiment-analysis"]
    size_categories = Column(String(50))  # e.g., "10K<n<100K"
    
    # Sources
    source_datasets = Column(JSONB, default=[])
    paperswithcode_id = Column(String(100))
    
    # Creators
    annotations_creators = Column(JSONB, default=[])  # e.g., ["machine-generated", "expert-generated"]
    language_creators = Column(JSONB, default=[])  # e.g., ["found", "crowdsourced"]
    multilinguality = Column(String(50))  # e.g., "monolingual", "multilingual"
    
    # Display
    pretty_name = Column(String(255))
    tags = Column(JSONB, default=[])
    configs = Column(JSONB, default=[])  # Dataset configurations
    
    # Ethics
    bias_risks = Column(Text)
    ethical_considerations = Column(Text)
    curation_rationale = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="dataset_card")
    
    def __repr__(self):
        return f"<DatasetCard {self.title}>"
    
    def to_yaml(self) -> str:
        """Generate YAML for HuggingFace dataset card."""
        import yaml
        
        card = {
            "language": self.languages or [],
            "license": self.license or "unknown",
            "task_categories": self.task_categories or [],
            "task_ids": self.task_ids or [],
            "pretty_name": self.pretty_name or self.title,
            "tags": self.tags or [],
        }
        
        if self.size_categories:
            card["size_categories"] = [self.size_categories]
        if self.source_datasets:
            card["source_datasets"] = self.source_datasets
        if self.annotations_creators:
            card["annotations_creators"] = self.annotations_creators
        if self.language_creators:
            card["language_creators"] = self.language_creators
        if self.multilinguality:
            card["multilinguality"] = self.multilinguality
        if self.paperswithcode_id:
            card["paperswithcode_id"] = self.paperswithcode_id
        if self.configs:
            card["configs"] = self.configs
            
        return yaml.dump(card, default_flow_style=False, allow_unicode=True)


class AnnotationType(Base):
    """Annotation type configuration for a project."""
    
    __tablename__ = "annotation_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    annotation_kind = Column(String(50), nullable=False)  # bbox, polygon, point, ner, classification, etc.
    schema = Column(JSONB, default={})  # JSON schema for validation
    color = Column(String(7), default="#3B82F6")
    shortcut_key = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="annotation_types")
    
    def __repr__(self):
        return f"<AnnotationType {self.name} ({self.annotation_kind})>"


class AugmentationRule(Base):
    """Data augmentation rule configuration."""
    
    __tablename__ = "augmentation_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)  # text, image, audio
    augmentation_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, default={})
    probability = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="augmentation_rules")
    
    def __repr__(self):
        return f"<AugmentationRule {self.name}>"
