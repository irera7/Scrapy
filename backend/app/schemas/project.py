from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DataType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MIXED = "mixed"


class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_type: DataType
    settings: Optional[Dict[str, Any]] = {}


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    data_type: Optional[DataType] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    data_type: str
    settings: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Stats
    job_count: Optional[int] = 0
    data_count: Optional[int] = 0
    
    # Data type breakdown counts
    text_count: Optional[int] = 0
    image_count: Optional[int] = 0
    audio_count: Optional[int] = 0
    video_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    """Schema for project statistics."""
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_data_items: int
    labeled_items: int
    storage_used: int  # bytes

