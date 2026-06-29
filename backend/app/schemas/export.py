from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ExportFormat(str, Enum):
    JSONL = "jsonl"
    CSV = "csv"
    PARQUET = "parquet"
    TFRECORD = "tfrecord"
    HUGGINGFACE = "huggingface"
    COCO = "coco"
    WEBDATASET = "webdataset"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFilters(BaseModel):
    """Filters for export."""
    data_types: Optional[List[str]] = None
    is_labeled: Optional[bool] = None
    is_processed: Optional[bool] = None
    min_quality_score: Optional[float] = None
    labels: Optional[List[str]] = None
    limit: Optional[int] = None
    # Split filtering
    splits: Optional[List[str]] = None  # ["train", "val", "test"]
    # Stratified sampling
    stratified_sample: Optional[bool] = False
    stratify_by: Optional[str] = "labels"
    sample_size: Optional[int] = None
    # Include options
    include_metadata: Optional[bool] = True
    include_content: Optional[bool] = True
    include_annotations: Optional[bool] = True
    # Output options
    options: Optional[Dict[str, Any]] = {}


class ExportCreate(BaseModel):
    """Schema for creating an export."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    format: ExportFormat
    filters: Optional[ExportFilters] = None
    # Incremental export
    base_export_id: Optional[UUID] = None  # For incremental exports
    is_incremental: Optional[bool] = False
    # Dataset version
    dataset_version_id: Optional[UUID] = None


class ExportResponse(BaseModel):
    """Schema for export response."""
    id: UUID
    project_id: UUID
    user_id: UUID
    name: str
    format: str
    file_path: Optional[str]
    file_size: Optional[int]
    record_count: Optional[int]
    filters: Dict[str, Any]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    # Incremental export fields
    base_export_id: Optional[UUID] = None
    is_incremental: Optional[bool] = False
    dataset_version_id: Optional[UUID] = None
    
    # Computed
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ExportProgress(BaseModel):
    """Schema for export progress updates."""
    export_id: UUID
    status: ExportStatus
    progress: float = 0.0  # 0.0 to 1.0
    records_processed: int = 0
    total_records: int = 0
    message: Optional[str] = None

