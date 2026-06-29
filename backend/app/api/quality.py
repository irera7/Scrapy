"""Quality and Validation API endpoints.

Provides endpoints for:
- Inter-annotator agreement
- Data leakage detection
- Advanced quality metrics
- Data validation and schema
- Temporal splitting
- Backup management
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.api.projects import verify_project_access

from app.services.annotation_quality_service import annotation_quality_service
from app.services.data_leakage_service import data_leakage_service
from app.services.advanced_quality_service import advanced_quality_service
from app.services.data_validation_service import data_validation_service
from app.services.backup_service import backup_service

router = APIRouter()


# ==================== Request/Response Models ====================

class AgreementRequest(BaseModel):
    """Request for agreement calculation."""
    project_id: UUID
    annotation_field: str = "labels"


class LeakageCheckRequest(BaseModel):
    """Request for leakage detection."""
    project_id: UUID
    similarity_threshold: float = Field(0.8, ge=0.5, le=1.0)


class SchemaValidationRequest(BaseModel):
    """Request for schema validation."""
    project_id: UUID
    schema: Dict[str, Any] = Field(..., description="JSON Schema definition")


class TemporalSplitRequest(BaseModel):
    """Request for temporal split."""
    project_id: UUID
    train_ratio: float = Field(0.7, ge=0.1, le=0.9)
    val_ratio: float = Field(0.15, ge=0.05, le=0.4)
    test_ratio: float = Field(0.15, ge=0.05, le=0.4)
    gap_days: int = Field(0, ge=0, le=365)


class BackupRequest(BaseModel):
    """Request for creating backup."""
    project_id: UUID
    include_files: bool = True
    compress: bool = True


class RestoreRequest(BaseModel):
    """Request for restoring backup."""
    backup_path: str
    new_project_name: Optional[str] = None


class OutlierDetectionRequest(BaseModel):
    """Request for outlier detection."""
    project_id: UUID
    field: str
    method: str = Field("iqr", pattern="^(iqr|zscore)$")


# ==================== Inter-Annotator Agreement ====================

@router.post("/agreement/calculate")
async def calculate_agreement(
    request: AgreementRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate inter-annotator agreement for a project.
    
    Returns Cohen's Kappa, Fleiss' Kappa, and percentage agreement
    for annotators who have labeled items in the project.
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    result = await annotation_quality_service.calculate_project_agreement(
        db, request.project_id, request.annotation_field
    )
    
    return result


@router.get("/agreement/disagreements/{project_id}")
async def get_disagreements(
    project_id: UUID,
    min_annotators: int = 2,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get items where annotators disagree.
    
    Returns items sorted by disagreement level (highest first).
    Useful for identifying items that need review.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    disagreements = await annotation_quality_service.identify_disagreements(
        db, project_id, min_annotators
    )
    
    return {
        "project_id": str(project_id),
        "disagreements": disagreements,
        "count": len(disagreements)
    }


@router.post("/agreement/resolve/{item_id}")
async def resolve_disagreement(
    item_id: UUID,
    final_label: str,
    resolution_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve a labeling disagreement with final decision."""
    result = await annotation_quality_service.resolve_disagreement(
        db, item_id, final_label, current_user.id, resolution_notes
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# ==================== Data Leakage Detection ====================

@router.post("/leakage/check")
async def check_leakage(
    request: LeakageCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run comprehensive data leakage detection.
    
    Checks for:
    - Exact duplicates between splits
    - Near-duplicates (similar content)
    - Source URL overlap
    - Temporal leakage
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    result = await data_leakage_service.run_full_leakage_check(
        db, request.project_id
    )
    
    return result


@router.get("/leakage/exact-duplicates/{project_id}")
async def check_exact_duplicates(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check for exact duplicate content between splits."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await data_leakage_service.detect_exact_duplicates(db, project_id)


@router.get("/leakage/near-duplicates/{project_id}")
async def check_near_duplicates(
    project_id: UUID,
    threshold: float = 0.8,
    sample_size: int = 500,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check for near-duplicate content between splits."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await data_leakage_service.detect_near_duplicates(
        db, project_id, threshold, sample_size
    )


@router.get("/leakage/temporal/{project_id}")
async def check_temporal_leakage(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check for temporal leakage (future data in training)."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await data_leakage_service.detect_temporal_leakage(db, project_id)


# ==================== Advanced Quality Metrics ====================

@router.get("/metrics/item/{item_id}")
async def analyze_item_quality(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run comprehensive quality analysis on a single item.
    
    For images: blur detection, brightness/contrast analysis
    For text: readability scores, coherence metrics
    For audio: SNR estimation (if available)
    """
    result = await advanced_quality_service.analyze_item(db, item_id)
    
    if "error" in result and result["error"] == "Item not found":
        raise HTTPException(status_code=404, detail="Item not found")
    
    return result


@router.get("/metrics/batch/{project_id}")
async def batch_quality_check(
    project_id: UUID,
    data_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run quality check on multiple items in a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await advanced_quality_service.batch_quality_check(
        db, project_id, data_type, limit
    )


# ==================== Data Validation ====================

@router.post("/validation/schema")
async def validate_with_schema(
    request: SchemaValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate project data against a JSON schema.
    
    Schema format:
    ```json
    {
        "fields": {
            "name": {"type": "string", "required": true, "min_length": 1},
            "age": {"type": "integer", "min": 0, "max": 150},
            "email": {"type": "email", "required": true}
        },
        "allow_extra_fields": false
    }
    ```
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    return await data_validation_service.validate_project_data(
        db, request.project_id, request.schema
    )


@router.get("/validation/completeness/{project_id}")
async def check_completeness(
    project_id: UUID,
    fields: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze data completeness for a project.
    
    Returns missing value statistics per field.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    field_list = fields.split(",") if fields else None
    
    return await data_validation_service.analyze_completeness(
        db, project_id, field_list
    )


@router.post("/validation/outliers")
async def detect_outliers(
    request: OutlierDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect outliers in a numeric field.
    
    Methods:
    - iqr: Interquartile Range method
    - zscore: Z-score method
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    return await data_validation_service.detect_outliers(
        db, request.project_id, request.field, request.method
    )


# ==================== Temporal Split ====================

@router.post("/splits/temporal")
async def temporal_split(
    request: TemporalSplitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform temporal split on project data.
    
    Unlike random split, temporal split ensures:
    - Training data is always older than validation/test
    - No future data leakage
    - Optional gap between splits
    
    Recommended for time-series and news data.
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    # Validate ratios
    total = request.train_ratio + request.val_ratio + request.test_ratio
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Ratios must sum to 1.0, got {total}"
        )
    
    return await data_validation_service.temporal_split(
        db,
        request.project_id,
        request.train_ratio,
        request.val_ratio,
        request.test_ratio,
        request.gap_days
    )


@router.get("/splits/sliding-window/{project_id}")
async def sliding_window_split(
    project_id: UUID,
    window_size_days: int = 30,
    step_size_days: int = 7,
    forecast_horizon_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create sliding window splits for time series cross-validation.
    
    Returns multiple train/test windows for temporal cross-validation.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await data_validation_service.temporal_splitter.sliding_window_split(
        db, project_id, window_size_days, step_size_days, forecast_horizon_days
    )


# ==================== Backup Management ====================

@router.post("/backup/create")
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a full backup of a project.
    
    Includes:
    - All data items with metadata
    - Dataset versions
    - Dataset card
    - Annotation types
    - Optionally: media files
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    result = await backup_service.create_project_backup(
        db,
        request.project_id,
        request.include_files,
        request.compress
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/backup/restore")
async def restore_backup(
    request: RestoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore a project from backup.
    
    Creates a new project with the backed up data.
    """
    result = await backup_service.restore_project_backup(
        db,
        request.backup_path,
        current_user.id,
        request.new_project_name
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/backup/list")
async def list_backups(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user)
):
    """List available backups."""
    return {
        "backups": backup_service.list_backups(project_id)
    }


@router.delete("/backup/{backup_name}")
async def delete_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a backup."""
    result = backup_service.delete_backup(backup_name)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/backup/cleanup")
async def cleanup_backups(
    max_age_days: int = 30,
    max_backups_per_project: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Cleanup old backups.
    
    Deletes backups older than max_age_days and keeps only
    max_backups_per_project most recent backups per project.
    """
    return await backup_service.cleanup_old_backups(
        max_age_days, max_backups_per_project
    )


# ==================== Audio Processing Endpoints ====================

from app.services.audio_processor import audio_processor

class NoiseReductionRequest(BaseModel):
    """Request for noise reduction."""
    item_id: UUID
    noise_reduction_amount: float = Field(1.0, ge=0.0, le=1.0)
    stationary: bool = True


@router.post("/audio/reduce-noise")
async def reduce_audio_noise(
    request: NoiseReductionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reduce noise from an audio item.
    
    Creates a denoised version of the audio file.
    """
    from app.models.data_item import DataItem
    from sqlalchemy import select
    
    result = await db.execute(
        select(DataItem).where(DataItem.id == request.item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.data_type != "audio":
        raise HTTPException(status_code=400, detail="Item is not audio")
    
    await verify_project_access(item.project_id, current_user.id, db)
    
    import tempfile
    import os
    from app.core.storage import storage_service
    
    # Download audio
    audio_data = storage_service.download_file(item.file_path)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
        tmp_in.write(audio_data)
        input_path = tmp_in.name
    
    try:
        result = await audio_processor.reduce_noise(
            input_path,
            noise_reduction_amount=request.noise_reduction_amount,
            stationary=request.stationary
        )
        
        if result.get("success"):
            # Upload denoised file
            with open(result["output_path"], 'rb') as f:
                denoised_data = f.read()
            
            import io
            storage_path = storage_service.upload_file(
                io.BytesIO(denoised_data),
                f"denoised_{item.id}.wav",
                "audio/wav",
                f"projects/{item.project_id}/audio"
            )
            
            # Update metadata
            metadata = item.item_metadata or {}
            metadata["denoised_path"] = storage_path
            metadata["noise_reduction"] = {
                "amount": request.noise_reduction_amount,
                "method": result.get("method"),
                "noise_removed_db": result.get("noise_removed_db")
            }
            item.item_metadata = metadata
            await db.commit()
            
            result["storage_path"] = storage_path
            
            os.unlink(result["output_path"])
        
        return result
        
    finally:
        os.unlink(input_path)


@router.get("/audio/vad/{item_id}")
async def detect_voice_activity(
    item_id: UUID,
    energy_threshold: float = 0.02,
    min_speech_duration: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect voice activity regions in audio.
    
    Returns time segments where speech is detected.
    """
    from app.models.data_item import DataItem
    from sqlalchemy import select
    
    result = await db.execute(
        select(DataItem).where(DataItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await verify_project_access(item.project_id, current_user.id, db)
    
    import tempfile
    import os
    from app.core.storage import storage_service
    
    audio_data = storage_service.download_file(item.file_path)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name
    
    try:
        return await audio_processor.detect_voice_activity(
            tmp_path, energy_threshold, min_speech_duration
        )
    finally:
        os.unlink(tmp_path)


# ==================== Speaker Identification Endpoints ====================

from app.services.speaker_service import speaker_service

class SpeakerAnalysisRequest(BaseModel):
    """Request for speaker analysis."""
    project_id: UUID
    similarity_threshold: float = Field(0.75, ge=0.5, le=1.0)
    sample_limit: int = Field(100, ge=10, le=500)


@router.post("/speaker/analyze")
async def analyze_speakers(
    request: SpeakerAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze speakers across audio items in a project.
    
    Clusters audio items by speaker identity.
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    if not speaker_service.is_available:
        raise HTTPException(
            status_code=503, 
            detail="Speaker identification not available. Install resemblyzer or librosa."
        )
    
    result = await speaker_service.analyze_project_speakers(
        db,
        request.project_id,
        request.similarity_threshold,
        request.sample_limit
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/speaker/diarize/{item_id}")
async def diarize_audio(
    item_id: UUID,
    num_speakers: Optional[int] = None,
    min_segment_duration: float = 1.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform speaker diarization (who spoke when).
    
    Segments audio by different speakers.
    """
    from app.models.data_item import DataItem
    from sqlalchemy import select
    
    result = await db.execute(
        select(DataItem).where(DataItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await verify_project_access(item.project_id, current_user.id, db)
    
    import tempfile
    import os
    from app.core.storage import storage_service
    
    audio_data = storage_service.download_file(item.file_path)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name
    
    try:
        result = await speaker_service.diarize_audio(
            tmp_path, num_speakers, min_segment_duration
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    finally:
        os.unlink(tmp_path)


# ==================== Multimodal Endpoints ====================

from app.services.multimodal_service import multimodal_service

class MultimodalGroupRequest(BaseModel):
    """Request for creating multimodal group."""
    project_id: UUID
    item_ids: List[UUID]
    group_name: Optional[str] = None
    alignment_type: str = "parallel"


@router.post("/multimodal/group")
async def create_multimodal_group(
    request: MultimodalGroupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a multimodal group linking multiple data items.
    
    Groups items of different modalities (text, image, audio, video).
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    result = await multimodal_service.create_multimodal_group(
        db,
        request.project_id,
        request.item_ids,
        request.group_name,
        request.alignment_type
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/multimodal/group/{group_id}")
async def get_multimodal_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a multimodal group."""
    return await multimodal_service.get_group_details(db, group_id)


@router.get("/multimodal/alignment/{group_id}")
async def compute_multimodal_alignment(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute alignment scores for a multimodal group.
    
    Measures how well different modalities align with each other.
    """
    result = await multimodal_service.compute_group_alignment(db, group_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/multimodal/auto-align/{project_id}")
async def auto_align_multimodal(
    project_id: UUID,
    time_window_seconds: int = 60,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically create multimodal groups based on timestamp proximity.
    
    Items created within the time window are grouped together.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await multimodal_service.auto_align_by_timestamp(
        db, project_id, time_window_seconds
    )


@router.get("/multimodal/unaligned/{project_id}")
async def get_unaligned_items(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get items that are not part of any multimodal group."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await multimodal_service.find_unaligned_items(db, project_id)


@router.get("/multimodal/list/{project_id}")
async def list_multimodal_groups(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all multimodal groups in a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await multimodal_service.list_groups(db, project_id)


@router.delete("/multimodal/group/{group_id}")
async def delete_multimodal_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a multimodal group (removes group metadata from items)."""
    result = await multimodal_service.delete_group(db, group_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


class CrossModalSearchRequest(BaseModel):
    """Request for cross-modal search."""
    project_id: UUID
    query_text: str
    target_modality: str = "image"
    limit: int = Field(10, ge=1, le=100)


@router.post("/multimodal/search")
async def cross_modal_search(
    request: CrossModalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for items using text query across modalities.
    
    Uses CLIP or sentence embeddings to find relevant items.
    """
    await verify_project_access(request.project_id, current_user.id, db)
    
    return await multimodal_service.cross_modal_search(
        db,
        request.project_id,
        request.query_text,
        request.target_modality,
        request.limit
    )


class MergeGroupsRequest(BaseModel):
    """Request for merging multimodal groups."""
    group_ids: List[str]
    new_group_name: Optional[str] = None


@router.post("/multimodal/merge")
async def merge_multimodal_groups(
    request: MergeGroupsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Merge multiple multimodal groups into one."""
    if len(request.group_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 groups required to merge")
    
    result = await multimodal_service.merge_groups(
        db,
        request.group_ids,
        request.new_group_name
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/multimodal/auto-align-content/{project_id}")
async def auto_align_by_content(
    project_id: UUID,
    similarity_threshold: float = 0.3,
    max_group_size: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically create groups based on content similarity.
    
    Groups items with high cross-modal similarity scores.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await multimodal_service.auto_align_by_content_similarity(
        db,
        project_id,
        similarity_threshold,
        max_group_size
    )


@router.get("/multimodal/statistics/{project_id}")
async def get_multimodal_statistics(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive alignment statistics for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    return await multimodal_service.get_alignment_statistics(db, project_id)


# ==================== Time Series Endpoints ====================

from app.services.timeseries_service import timeseries_service

class TimeSeriesAnalysisRequest(BaseModel):
    """Request for time series analysis."""
    series: List[float]
    include_stationarity: bool = True
    include_decomposition: bool = True
    include_anomalies: bool = True


@router.post("/timeseries/analyze")
async def analyze_timeseries(
    request: TimeSeriesAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run comprehensive time series analysis.
    
    Includes statistics, stationarity tests, decomposition, and anomaly detection.
    """
    if len(request.series) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Series must have at least 10 data points"
        )
    
    return await timeseries_service.analyze_series(
        request.series,
        request.include_stationarity,
        request.include_decomposition,
        request.include_anomalies
    )


@router.get("/timeseries/project/{project_id}")
async def analyze_project_timeseries(
    project_id: UUID,
    value_field: str = "value",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze time series data in a project.
    
    Extracts numeric values from item metadata and performs analysis.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await timeseries_service.analyze_project_timeseries(
        db, project_id, value_field
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


class InterpolationRequest(BaseModel):
    """Request for interpolation."""
    series: List[Optional[float]]
    method: str = "linear"  # linear, spline, forward_fill, backward_fill


@router.post("/timeseries/interpolate")
async def interpolate_missing(
    request: InterpolationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Interpolate missing values in time series.
    
    Methods: linear, spline, forward_fill, backward_fill
    """
    result = timeseries_service.interpolator.interpolate(
        request.series, method=request.method
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""
    series: List[float]
    method: str = "zscore"  # zscore, iqr, isolation_forest
    threshold: float = 3.0


@router.post("/timeseries/anomalies")
async def detect_timeseries_anomalies(
    request: AnomalyDetectionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Detect anomalies in time series.
    
    Methods: zscore, iqr, isolation_forest
    """
    return timeseries_service.analyzer.detect_anomalies(
        request.series, request.method, request.threshold
    )


# ==================== Video Quality Endpoints ====================

from app.services.video_quality_service import video_quality_service


@router.post("/video/hash/{item_id}")
async def compute_video_hash(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute perceptual hash for a video.
    
    Used for duplicate detection.
    """
    result = await video_quality_service.compute_video_hash(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/video/duplicates/{project_id}")
async def find_duplicate_videos(
    project_id: UUID,
    similarity_threshold: float = 0.85,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find duplicate videos in a project.
    
    Uses perceptual hashing to find similar videos.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await video_quality_service.find_duplicate_videos(
        db, project_id, similarity_threshold
    )


@router.get("/video/scenes/{item_id}")
async def detect_video_scenes(
    item_id: UUID,
    threshold: float = 0.3,
    min_scene_length: float = 1.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect scene changes in a video.
    
    Returns list of scene boundaries with timestamps.
    """
    result = await video_quality_service.detect_scenes(
        db, item_id, threshold, min_scene_length
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/video/quality/{item_id}")
async def analyze_video_quality(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze video quality metrics.
    
    Returns blur score, brightness, contrast, stability, and quality grade.
    """
    result = await video_quality_service.analyze_video_quality(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/video/thumbnail/{item_id}")
async def generate_smart_thumbnail(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a smart thumbnail from the best quality frame.
    
    Automatically selects the sharpest, well-lit frame.
    """
    result = await video_quality_service.generate_smart_thumbnail(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/video/batch-analyze/{project_id}")
async def batch_analyze_videos(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch analyze all videos in a project.
    
    Returns quality summary and issues found.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await video_quality_service.batch_analyze_project(db, project_id)


# ==================== Image Quality Endpoints ====================

from app.services.image_quality_service import image_quality_service


@router.get("/image/exif/{item_id}")
async def extract_image_exif(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract full EXIF metadata from an image.
    
    Includes camera info, settings, GPS coordinates.
    """
    result = await image_quality_service.extract_full_exif(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/image/colors/{item_id}")
async def analyze_image_colors(
    item_id: UUID,
    include_histogram: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze colors in an image.
    
    Returns dominant colors, palette characteristics, brightness, contrast.
    """
    result = await image_quality_service.analyze_colors(db, item_id, include_histogram)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/image/hash/{item_id}")
async def compute_image_hash(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute perceptual hashes for an image.
    
    Used for similarity search and duplicate detection.
    """
    result = await image_quality_service.compute_image_hash(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/image/similar/{project_id}")
async def find_similar_images(
    project_id: UUID,
    similarity_threshold: float = 0.9,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find similar images in a project.
    
    Uses perceptual hashing to find visually similar images.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await image_quality_service.find_similar_images(
        db, project_id, similarity_threshold
    )


@router.get("/image/batch-analyze/{project_id}")
async def batch_analyze_images(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch analyze all images in a project.
    
    Extracts EXIF, analyzes colors for all images.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    return await image_quality_service.batch_analyze_project(db, project_id)


# ==================== Tabular Data Endpoints ====================

from app.services.tabular_service import tabular_service


@router.get("/tabular/schema/{project_id}")
async def analyze_tabular_schema(
    project_id: UUID,
    sample_size: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze schema of tabular data in a project.
    
    Auto-detects column types: numeric, categorical, datetime, boolean, text, id.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await tabular_service.analyze_schema(db, project_id, sample_size)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/tabular/correlations/{project_id}")
async def compute_tabular_correlations(
    project_id: UUID,
    method: str = "pearson",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute correlation matrix for numeric columns.
    
    Methods: pearson, spearman
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await tabular_service.compute_correlations(db, project_id, method=method)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/tabular/statistics/{project_id}")
async def compute_tabular_statistics(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute comprehensive statistics for all columns.
    
    Includes min, max, mean, median, quartiles for numeric columns.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await tabular_service.compute_statistics(db, project_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/tabular/quality-issues/{project_id}")
async def detect_tabular_quality_issues(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect data quality issues in tabular data.
    
    Finds high null ratios, low cardinality, high variance issues.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await tabular_service.detect_data_quality_issues(db, project_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ==================== External Annotation Tools Endpoints ====================

from app.services.annotation_tools_service import annotation_tools_service


@router.get("/export/cvat/{project_id}")
async def export_to_cvat(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export project to CVAT XML format.
    
    Supports image annotations, video tracks, bounding boxes, polygons.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await annotation_tools_service.export_to_cvat(db, project_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/import/cvat/{project_id}")
async def import_from_cvat(
    project_id: UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import annotations from CVAT XML format.
    
    Updates existing items with imported annotations.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    content = await file.read()
    result = await annotation_tools_service.import_from_cvat(db, project_id, content)
    
    return result


@router.get("/export/labelbox/{project_id}")
async def export_to_labelbox(
    project_id: UUID,
    include_predictions: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export project to Labelbox NDJSON format.
    
    Compatible with Labelbox import feature.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await annotation_tools_service.export_to_labelbox(
        db, project_id, include_predictions
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/import/labelbox/{project_id}")
async def import_from_labelbox(
    project_id: UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import annotations from Labelbox NDJSON format.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    content = await file.read()
    result = await annotation_tools_service.import_from_labelbox(db, project_id, content)
    
    return result


@router.get("/export/label-studio/{project_id}")
async def export_to_label_studio(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export project to Label Studio JSON format.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await annotation_tools_service.export_to_label_studio(db, project_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ==================== Graph Dataset Endpoints ====================

from app.services.graph_service import graph_service


@router.get("/graph/create/{project_id}")
async def create_graph_from_project(
    project_id: UUID,
    node_field: str = "id",
    edge_source_field: str = "source",
    edge_target_field: str = "target",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a graph structure from project items.
    
    Extracts nodes and edges from item metadata.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await graph_service.create_graph_from_items(
        db, project_id, node_field, edge_source_field, edge_target_field
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/graph/analyze/{project_id}")
async def analyze_graph(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze graph structure and compute metrics.
    
    Returns centrality, communities, and top nodes.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await graph_service.analyze_graph(db, project_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/graph/export/{project_id}")
async def export_graph(
    project_id: UUID,
    format: str = "graphml",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export graph to specified format.
    
    Formats: graphml, gml, networkx, cytoscape
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await graph_service.export_graph(db, project_id, format)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/graph/pagerank/{project_id}")
async def compute_graph_pagerank(
    project_id: UUID,
    damping: float = 0.85,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compute PageRank for graph nodes.
    
    Returns importance scores for each node.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    graph_result = await graph_service.create_graph_from_items(db, project_id)
    
    if "error" in graph_result:
        raise HTTPException(status_code=400, detail=graph_result["error"])
    
    from app.services.graph_service import Graph
    graph = Graph.from_dict(graph_result["graph"])
    
    pagerank = graph_service.metrics.compute_pagerank(graph, damping)
    
    # Sort by rank
    sorted_ranks = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "pagerank": pagerank,
        "top_10": [{"node": n, "rank": r} for n, r in sorted_ranks[:10]]
    }


@router.get("/graph/path/{project_id}")
async def find_graph_path(
    project_id: UUID,
    start: str,
    end: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find shortest path between two nodes.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    graph_result = await graph_service.create_graph_from_items(db, project_id)
    
    if "error" in graph_result:
        raise HTTPException(status_code=400, detail=graph_result["error"])
    
    from app.services.graph_service import Graph
    graph = Graph.from_dict(graph_result["graph"])
    
    path = graph_service.metrics.find_shortest_path(graph, start, end)
    
    return {
        "start": start,
        "end": end,
        "path": path,
        "length": len(path) - 1 if path else None,
        "found": path is not None
    }


@router.get("/graph/components/{project_id}")
async def get_graph_components(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find connected components in the graph.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    graph_result = await graph_service.create_graph_from_items(db, project_id)
    
    if "error" in graph_result:
        raise HTTPException(status_code=400, detail=graph_result["error"])
    
    from app.services.graph_service import Graph
    graph = Graph.from_dict(graph_result["graph"])
    
    components = graph_service.metrics.get_connected_components(graph)
    
    return {
        "num_components": len(components),
        "sizes": [len(c) for c in components],
        "largest_component_size": max(len(c) for c in components) if components else 0,
        "components": [list(c) for c in components[:10]]  # Return first 10
    }


# ==================== 3D Dataset Endpoints ====================

from app.services.threed_service import threed_service


@router.get("/3d/parse/{item_id}")
async def parse_point_cloud(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Parse point cloud data from an item.
    
    Supports JSON point arrays and metadata-based point clouds.
    """
    result = await threed_service.parse_point_cloud(db, item_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/3d/analyze/{project_id}")
async def analyze_3d_data(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze all 3D data in a project.
    
    Returns statistics on points, annotations, and labels.
    """
    await verify_project_access(project_id, current_user.id, db)
    
    result = await threed_service.analyze_3d_data(db, project_id)
    
    return result


@router.get("/3d/export/{item_id}")
async def export_3d_data(
    item_id: UUID,
    format: str = "ply",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export 3D data to specified format.
    
    Formats: ply, pcd, xyz, kitti
    """
    result = await threed_service.export_3d(db, item_id, format)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/3d/ground-plane/{item_id}")
async def detect_ground_plane(
    item_id: UUID,
    z_threshold: float = 0.1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect ground plane in point cloud.
    """
    cloud_result = await threed_service.parse_point_cloud(db, item_id)
    
    if "error" in cloud_result:
        raise HTTPException(status_code=400, detail=cloud_result["error"])
    
    from app.services.threed_service import PointCloud, Point3D
    
    cloud = PointCloud()
    for pt in cloud_result.get("cloud", {}).get("points", []):
        cloud.add_point(pt.get("x", 0), pt.get("y", 0), pt.get("z", 0))
    
    result = threed_service.analyzer.detect_ground_plane(cloud, z_threshold)
    return result


@router.get("/3d/segments/{item_id}")
async def segment_by_height(
    item_id: UUID,
    num_segments: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Segment point cloud by height.
    """
    cloud_result = await threed_service.parse_point_cloud(db, item_id)
    
    if "error" in cloud_result:
        raise HTTPException(status_code=400, detail=cloud_result["error"])
    
    from app.services.threed_service import PointCloud
    
    cloud = PointCloud()
    for pt in cloud_result.get("cloud", {}).get("points", []):
        cloud.add_point(pt.get("x", 0), pt.get("y", 0), pt.get("z", 0))
    
    segments = threed_service.analyzer.segment_by_height(cloud, num_segments)
    return {"segments": segments, "total_segments": len(segments)}


@router.post("/3d/downsample/{item_id}")
async def downsample_point_cloud(
    item_id: UUID,
    voxel_size: float = 0.1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Downsample point cloud using voxel grid.
    """
    cloud_result = await threed_service.parse_point_cloud(db, item_id)
    
    if "error" in cloud_result:
        raise HTTPException(status_code=400, detail=cloud_result["error"])
    
    from app.services.threed_service import PointCloud
    
    cloud = PointCloud()
    for pt in cloud_result.get("cloud", {}).get("points", []):
        cloud.add_point(
            pt.get("x", 0), pt.get("y", 0), pt.get("z", 0),
            r=pt.get("r", 255), g=pt.get("g", 255), b=pt.get("b", 255)
        )
    
    original_count = len(cloud.points)
    downsampled = threed_service.analyzer.downsample_voxel(cloud, voxel_size)
    
    return {
        "original_points": original_count,
        "downsampled_points": len(downsampled.points),
        "reduction_ratio": round(1 - len(downsampled.points) / original_count, 4) if original_count > 0 else 0
    }


@router.post("/3d/remove-outliers/{item_id}")
async def remove_outliers(
    item_id: UUID,
    k_neighbors: int = 10,
    std_ratio: float = 2.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove outlier points from point cloud.
    """
    cloud_result = await threed_service.parse_point_cloud(db, item_id)
    
    if "error" in cloud_result:
        raise HTTPException(status_code=400, detail=cloud_result["error"])
    
    from app.services.threed_service import PointCloud
    
    cloud = PointCloud()
    for pt in cloud_result.get("cloud", {}).get("points", []):
        cloud.add_point(
            pt.get("x", 0), pt.get("y", 0), pt.get("z", 0),
            r=pt.get("r", 255), g=pt.get("g", 255), b=pt.get("b", 255)
        )
    
    original_count = len(cloud.points)
    filtered = threed_service.analyzer.remove_outliers(cloud, k_neighbors, std_ratio)
    
    return {
        "original_points": original_count,
        "filtered_points": len(filtered.points),
        "removed_outliers": original_count - len(filtered.points)
    }
