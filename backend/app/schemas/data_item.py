from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DataItemType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"


class DataItemCreate(BaseModel):
    """Schema for creating a data item."""
    project_id: UUID
    job_id: Optional[UUID] = None
    data_type: DataItemType
    source_url: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class DataItemUpdate(BaseModel):
    """Schema for updating a data item."""
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    labels: Optional[List[str]] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    is_labeled: Optional[bool] = None
    dataset_split: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None


class DataItemResponse(BaseModel):
    """Schema for data item response."""
    id: UUID
    project_id: UUID
    job_id: Optional[UUID]
    data_type: str
    source_url: Optional[str]
    content: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    metadata: Dict[str, Any] = Field(default={}, validation_alias="item_metadata")
    labels: List[str]
    quality_score: Optional[float]
    is_processed: bool
    is_labeled: bool
    created_at: datetime
    
    # ML Training fields
    dataset_split: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None
    uncertainty_score: Optional[float] = None
    augmented_from: Optional[UUID] = None
    augmentation_type: Optional[str] = None
    
    # Computed fields
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DataItemListResponse(BaseModel):
    """Schema for paginated data items response."""
    items: List[DataItemResponse]
    total: int
    skip: int
    limit: int
    # Breakdown counts
    labeled_count: int = 0
    processed_count: int = 0


class DataItemBulkLabel(BaseModel):
    """Schema for bulk labeling items."""
    item_ids: List[UUID]
    labels: List[str]
    action: str = "add"  # add, remove, replace


class DataItemFilter(BaseModel):
    """Schema for filtering data items."""
    data_types: Optional[List[DataItemType]] = None
    is_labeled: Optional[bool] = None
    is_processed: Optional[bool] = None
    labels: Optional[List[str]] = None
    min_quality: Optional[float] = None
    max_quality: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class LabelCategoryCreate(BaseModel):
    """Schema for creating a label category."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    color: Optional[str] = "#3B82F6"
    description: Optional[str] = None


class LabelCategoryUpdate(BaseModel):
    """Schema for updating a label category."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = None
    description: Optional[str] = None


class LabelCategoryResponse(BaseModel):
    """Schema for label category response."""
    id: UUID
    project_id: UUID
    name: str
    color: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

