"""API endpoints for data processing."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.data_item import DataItem
from app.services.nlp_processor import process_text_item, nlp_processor
from app.services.image_processor import process_image_item
from app.services.audio_processor import process_audio_item
from app.services.video_processor import process_video_item

router = APIRouter()
logger = structlog.get_logger()


class ProcessingType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    AUTO = "auto"


class TextProcessingOptions(BaseModel):
    """Options for text processing."""
    clean: bool = True
    clean_options: dict = Field(default_factory=lambda: {
        "normalize_unicode": True,
        "remove_control_chars": True,
        "normalize_whitespace": True,
    })
    detect_language: bool = True
    compute_stats: bool = True
    extract_keywords: bool = False
    keyword_count: int = 10
    extract_entities: bool = False
    summarize: bool = False
    summary_sentences: int = 3


class ImageProcessingOptions(BaseModel):
    """Options for image processing."""
    resize: Optional[List[int]] = None
    resize_method: str = "fit"
    convert_format: Optional[str] = None
    generate_thumbnail: bool = True
    compute_hash: bool = True
    run_ocr: bool = False
    ocr_language: str = "eng"
    enhance: Optional[dict] = None


class AudioProcessingOptions(BaseModel):
    """Options for audio processing."""
    get_info: bool = True
    transcribe: bool = False
    whisper_model: str = "base"
    language: Optional[str] = None
    transcribe_task: str = "transcribe"
    extract_features: bool = False
    convert_format: Optional[str] = None
    sample_rate: int = 16000


class VideoProcessingOptions(BaseModel):
    """Options for video processing."""
    get_info: bool = True
    generate_thumbnail: bool = True
    thumbnail_offset: float = 1.0
    # Transcription options
    transcribe: bool = False
    whisper_model: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = None  # e.g., 'en', 'fa', None for auto-detect
    transcribe_task: str = "transcribe"  # 'transcribe' or 'translate' (to English)
    include_segments: bool = True
    generate_subtitles: bool = False
    subtitle_format: str = "srt"  # 'srt', 'vtt', 'txt'
    # Frame extraction
    extract_frames: bool = False
    frame_fps: float = 1.0
    max_frames: int = 10
    # Audio extraction
    extract_audio: bool = False
    audio_format: str = "mp3"
    # GIF generation
    generate_gif: bool = False
    gif_duration: float = 3.0
    gif_fps: int = 10
    gif_width: int = 320
    gif_start: float = 0.0
    # Scene detection
    detect_scenes: bool = False
    scene_threshold: float = 0.3


class ProcessItemRequest(BaseModel):
    """Request to process a single item."""
    processing_type: ProcessingType = ProcessingType.AUTO
    text_options: Optional[TextProcessingOptions] = None
    image_options: Optional[ImageProcessingOptions] = None
    audio_options: Optional[AudioProcessingOptions] = None
    video_options: Optional[VideoProcessingOptions] = None


class BatchProcessRequest(BaseModel):
    """Request to process multiple items."""
    item_ids: List[UUID]
    processing_type: ProcessingType = ProcessingType.AUTO
    text_options: Optional[TextProcessingOptions] = None
    image_options: Optional[ImageProcessingOptions] = None
    audio_options: Optional[AudioProcessingOptions] = None
    video_options: Optional[VideoProcessingOptions] = None


class ProcessingResult(BaseModel):
    """Processing result."""
    item_id: str
    success: bool
    result: dict = Field(default_factory=dict)
    error: Optional[str] = None


class TextAnalyzeRequest(BaseModel):
    """Request for text analysis."""
    text: str


class TextCleanRequest(BaseModel):
    """Request for text cleaning."""
    text: str
    options: Optional[dict] = None


async def verify_item_access(
    item_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> DataItem:
    """Verify user has access to the data item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(
            and_(DataItem.id == item_id, Project.user_id == user_id)
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    return item


def determine_processing_type(item: DataItem) -> ProcessingType:
    """Determine the processing type based on data item type."""
    type_mapping = {
        "text": ProcessingType.TEXT,
        "image": ProcessingType.IMAGE,
        "audio": ProcessingType.AUDIO,
        "video": ProcessingType.VIDEO,
    }
    return type_mapping.get(item.data_type, ProcessingType.TEXT)


@router.post("/{item_id}/process", response_model=ProcessingResult)
async def process_item(
    item_id: UUID,
    request: ProcessItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a single data item."""
    item = await verify_item_access(item_id, current_user.id, db)
    
    # Determine processing type
    proc_type = request.processing_type
    if proc_type == ProcessingType.AUTO:
        proc_type = determine_processing_type(item)
    
    try:
        if proc_type == ProcessingType.TEXT:
            options = request.text_options.model_dump() if request.text_options else {}
            result = await process_text_item(item, db, options)
        
        elif proc_type == ProcessingType.IMAGE:
            options = request.image_options.model_dump() if request.image_options else {}
            result = await process_image_item(item, db, options)
        
        elif proc_type == ProcessingType.AUDIO:
            options = request.audio_options.model_dump() if request.audio_options else {}
            result = await process_audio_item(item, db, options)
        
        elif proc_type == ProcessingType.VIDEO:
            options = request.video_options.model_dump() if request.video_options else {}
            result = await process_video_item(item, db, options)
        
        else:
            raise ValueError(f"Unknown processing type: {proc_type}")
        
        return ProcessingResult(
            item_id=str(item_id),
            success="error" not in result,
            result=result,
            error=result.get("error")
        )
    
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return ProcessingResult(
            item_id=str(item_id),
            success=False,
            error=str(e)
        )


@router.post("/batch", response_model=List[ProcessingResult])
async def batch_process_items(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process multiple items in batch."""
    results = []
    
    for item_id in request.item_ids:
        try:
            item = await verify_item_access(item_id, current_user.id, db)
            
            proc_type = request.processing_type
            if proc_type == ProcessingType.AUTO:
                proc_type = determine_processing_type(item)
            
            if proc_type == ProcessingType.TEXT:
                options = request.text_options.model_dump() if request.text_options else {}
                result = await process_text_item(item, db, options)
            
            elif proc_type == ProcessingType.IMAGE:
                options = request.image_options.model_dump() if request.image_options else {}
                result = await process_image_item(item, db, options)
            
            elif proc_type == ProcessingType.AUDIO:
                options = request.audio_options.model_dump() if request.audio_options else {}
                result = await process_audio_item(item, db, options)
            
            elif proc_type == ProcessingType.VIDEO:
                options = request.video_options.model_dump() if request.video_options else {}
                result = await process_video_item(item, db, options)
            
            results.append(ProcessingResult(
                item_id=str(item_id),
                success="error" not in result,
                result=result,
                error=result.get("error")
            ))
        
        except Exception as e:
            results.append(ProcessingResult(
                item_id=str(item_id),
                success=False,
                error=str(e)
            ))
    
    return results


@router.post("/text/analyze")
async def analyze_text(
    request: TextAnalyzeRequest,
    current_user: User = Depends(get_current_user)
):
    """Analyze text without saving to database."""
    text = request.text
    
    language_info = await nlp_processor.detect_language(text)
    
    return {
        "language": language_info,
        "stats": nlp_processor.compute_text_stats(text),
        "keywords": nlp_processor.extract_keywords(text),
        "entities": nlp_processor.extract_entities(text),
    }


@router.post("/text/clean")
async def clean_text(
    request: TextCleanRequest,
    current_user: User = Depends(get_current_user)
):
    """Clean text without saving to database."""
    text = request.text
    options = request.options or {}
    
    cleaned = nlp_processor.clean_text(text, options)
    return {
        "original_length": len(text),
        "cleaned_length": len(cleaned),
        "cleaned_text": cleaned,
    }


@router.post("/compute-quality-scores")
async def compute_quality_scores(
    project_id: UUID = Query(...),
    recompute: bool = Query(False, description="Recompute even if score exists"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compute quality scores for all items in a project."""
    from app.services.processing_service import compute_quality_score
    
    # Verify project access
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get items (either all or only those without quality score)
    query = select(DataItem).where(DataItem.project_id == project_id)
    if not recompute:
        query = query.where(DataItem.quality_score.is_(None))
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    if not items:
        return {
            "processed": 0,
            "message": "No items to process"
        }
    
    for item in items:
        await compute_quality_score(item, db)
    
    await db.commit()
    
    return {
        "processed": len(items),
        "message": f"Computed quality scores for {len(items)} items"
    }


@router.post("/extract-labels")
async def extract_labels_from_metadata(
    project_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Extract labels from metadata fields (categories, tags, etc.) for all items."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all items in the project
    result = await db.execute(
        select(DataItem).where(DataItem.project_id == project_id)
    )
    items = result.scalars().all()
    
    if not items:
        return {
            "processed": 0,
            "labeled": 0,
            "message": "No items in project"
        }
    
    labeled_count = 0
    
    for item in items:
        metadata = item.item_metadata or {}
        extracted_labels = []
        
        # Extract from common metadata fields
        label_fields = ['labels', 'tags', 'categories', 'keywords', 'topics']
        
        for field in label_fields:
            if field in metadata:
                value = metadata[field]
                if isinstance(value, list):
                    extracted_labels.extend([str(v) for v in value if v])
                elif isinstance(value, str) and value:
                    extracted_labels.append(value)
        
        # Also check for primary_category
        if 'primary_category' in metadata and metadata['primary_category']:
            extracted_labels.append(str(metadata['primary_category']))
        
        # Update if we found labels
        if extracted_labels:
            # Merge with existing labels
            existing_labels = set(item.labels or [])
            unique_labels = list(dict.fromkeys(list(existing_labels) + extracted_labels))
            item.labels = unique_labels
            item.is_labeled = True
            labeled_count += 1
    
    await db.commit()
    
    return {
        "processed": len(items),
        "labeled": labeled_count,
        "message": f"Extracted labels for {labeled_count} items from metadata"
    }


@router.post("/process-all")
async def process_all_items(
    project_id: UUID = Query(...),
    processing_type: ProcessingType = Query(ProcessingType.AUTO),
    reprocess: bool = Query(False, description="Reprocess even if already processed"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process all unprocessed items in a project."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get items to process
    query = select(DataItem).where(DataItem.project_id == project_id)
    if not reprocess:
        query = query.where(DataItem.is_processed == False)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    if not items:
        return {
            "processed": 0,
            "failed": 0,
            "message": "No items to process"
        }
    
    processed_count = 0
    failed_count = 0
    errors = []
    
    for item in items:
        try:
            # Determine processing type
            proc_type = processing_type
            if proc_type == ProcessingType.AUTO:
                proc_type = determine_processing_type(item)
            
            if proc_type == ProcessingType.TEXT:
                await process_text_item(item, db, {})
            elif proc_type == ProcessingType.IMAGE:
                await process_image_item(item, db, {})
            elif proc_type == ProcessingType.AUDIO:
                await process_audio_item(item, db, {})
            elif proc_type == ProcessingType.VIDEO:
                await process_video_item(item, db, {})
            
            item.is_processed = True
            processed_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({"item_id": str(item.id), "error": str(e)})
            logger.warning(f"Failed to process item {item.id}: {e}")
    
    await db.commit()
    
    return {
        "processed": processed_count,
        "failed": failed_count,
        "total": len(items),
        "errors": errors[:10] if errors else [],  # Return first 10 errors
        "message": f"Processed {processed_count}/{len(items)} items"
    }


@router.post("/text/detect-duplicates")
async def detect_duplicates(
    project_id: UUID = Query(...),
    threshold: float = Query(0.8),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detect duplicate texts in a project."""
    # Verify project access
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all text items
    result = await db.execute(
        select(DataItem).where(
            and_(
                DataItem.project_id == project_id,
                DataItem.data_type == "text",
                DataItem.content.isnot(None)
            )
        )
    )
    items = result.scalars().all()
    
    if len(items) < 2:
        return {
            "total_items": len(items),
            "duplicate_pairs": 0,
            "duplicates": []
        }
    
    # Detect duplicates
    texts = [item.content for item in items]
    duplicates = nlp_processor.detect_duplicates(texts, threshold)
    
    return {
        "total_items": len(items),
        "duplicate_pairs": len(duplicates),
        "duplicates": [
            {
                "item1_id": str(items[i].id),
                "item2_id": str(items[j].id),
                "similarity": sim,
            }
            for i, j, sim in duplicates
        ]
    }
