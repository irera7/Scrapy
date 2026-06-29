from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from uuid import UUID
import structlog
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.models.user import User
from app.models.project import Project
from app.models.data_item import DataItem, LabelCategory
from app.schemas.data_item import (
    DataItemCreate, DataItemUpdate, DataItemResponse, DataItemListResponse,
    DataItemBulkLabel, DataItemFilter,
    LabelCategoryCreate, LabelCategoryUpdate, LabelCategoryResponse
)

router = APIRouter()
logger = structlog.get_logger()


async def verify_project_access(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Project:
    """Verify user has access to the project."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == user_id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.get("", response_model=DataItemListResponse)
async def list_data_items(
    project_id: UUID,
    data_type: Optional[str] = None,
    is_labeled: Optional[bool] = None,
    is_processed: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List data items for a project with pagination info."""
    await verify_project_access(project_id, current_user.id, db)
    
    # Base filter condition
    base_filter = DataItem.project_id == project_id
    filters = [base_filter]
    
    if data_type:
        filters.append(DataItem.data_type == data_type)
    if is_labeled is not None:
        filters.append(DataItem.is_labeled == is_labeled)
    if is_processed is not None:
        filters.append(DataItem.is_processed == is_processed)
    
    # Get total count with filters
    count_query = select(func.count(DataItem.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get labeled count
    labeled_query = select(func.count(DataItem.id)).where(
        and_(base_filter, DataItem.is_labeled == True)
    )
    labeled_result = await db.execute(labeled_query)
    labeled_count = labeled_result.scalar() or 0
    
    # Get processed count
    processed_query = select(func.count(DataItem.id)).where(
        and_(base_filter, DataItem.is_processed == True)
    )
    processed_result = await db.execute(processed_query)
    processed_count = processed_result.scalar() or 0
    
    # Get items with pagination
    query = select(DataItem).where(and_(*filters))
    query = query.order_by(DataItem.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Add download URLs for media files
    item_responses = []
    for item in items:
        item_response = DataItemResponse.model_validate(item)
        if item.file_path:
            try:
                item_response.download_url = storage_service.get_presigned_url(item.file_path)
            except Exception:
                pass
        item_responses.append(item_response)
    
    return DataItemListResponse(
        items=item_responses,
        total=total,
        skip=skip,
        limit=limit,
        labeled_count=labeled_count,
        processed_count=processed_count
    )


@router.post("", response_model=DataItemResponse, status_code=status.HTTP_201_CREATED)
async def create_data_item(
    item_data: DataItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new data item."""
    await verify_project_access(item_data.project_id, current_user.id, db)
    
    item = DataItem(
        project_id=item_data.project_id,
        job_id=item_data.job_id,
        data_type=item_data.data_type.value,
        source_url=item_data.source_url,
        content=item_data.content,
        item_metadata=item_data.metadata or {},
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    return DataItemResponse.model_validate(item)


@router.post("/upload", response_model=DataItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_data_item(
    project_id: UUID = Form(...),
    data_type: str = Form(...),
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file as a data item."""
    await verify_project_access(project_id, current_user.id, db)
    
    # Read file content
    content = await file.read()
    file_stream = io.BytesIO(content)
    
    # Upload to storage
    folder = f"projects/{project_id}/{data_type}"
    file_path = storage_service.upload_file(
        file_stream,
        file.filename,
        file.content_type or "application/octet-stream",
        folder
    )
    
    # Parse metadata
    import json
    meta = json.loads(metadata) if metadata else {}
    
    # Create data item
    item = DataItem(
        project_id=project_id,
        data_type=data_type,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        item_metadata=meta,
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    logger.info(f"File uploaded: {file.filename} -> {file_path}")
    
    item_response = DataItemResponse.model_validate(item)
    item_response.download_url = storage_service.get_presigned_url(file_path)
    
    return item_response


@router.get("/{item_id}", response_model=DataItemResponse)
async def get_data_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific data item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(
            and_(DataItem.id == item_id, Project.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    item_response = DataItemResponse.model_validate(item)
    if item.file_path:
        try:
            item_response.download_url = storage_service.get_presigned_url(item.file_path)
        except Exception:
            pass
    
    return item_response


@router.patch("/{item_id}", response_model=DataItemResponse)
async def update_data_item(
    item_id: UUID,
    item_update: DataItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a data item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(
            and_(DataItem.id == item_id, Project.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    # Update fields
    if item_update.content is not None:
        item.content = item_update.content
    if item_update.metadata is not None:
        item.item_metadata = item_update.metadata
    if item_update.labels is not None:
        item.labels = item_update.labels
        item.is_labeled = len(item_update.labels) > 0
    if item_update.quality_score is not None:
        item.quality_score = item_update.quality_score
    if item_update.is_labeled is not None:
        item.is_labeled = item_update.is_labeled
    
    await db.commit()
    await db.refresh(item)
    
    return DataItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a data item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(
            and_(DataItem.id == item_id, Project.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    # Delete file from storage
    if item.file_path:
        storage_service.delete_file(item.file_path)
    
    await db.delete(item)
    await db.commit()


@router.post("/bulk-label", response_model=dict)
async def bulk_label_items(
    bulk_data: DataItemBulkLabel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk label data items."""
    updated_count = 0
    
    for item_id in bulk_data.item_ids:
        result = await db.execute(
            select(DataItem)
            .join(Project)
            .where(
                and_(DataItem.id == item_id, Project.user_id == current_user.id)
            )
        )
        item = result.scalar_one_or_none()
        
        if item:
            if bulk_data.action == "add":
                current_labels = set(item.labels or [])
                current_labels.update(bulk_data.labels)
                item.labels = list(current_labels)
            elif bulk_data.action == "remove":
                current_labels = set(item.labels or [])
                current_labels -= set(bulk_data.labels)
                item.labels = list(current_labels)
            elif bulk_data.action == "replace":
                item.labels = bulk_data.labels
            
            item.is_labeled = len(item.labels) > 0
            updated_count += 1
    
    await db.commit()
    
    return {"updated_count": updated_count}


# Label Categories
@router.get("/categories/{project_id}", response_model=List[LabelCategoryResponse])
async def list_label_categories(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List label categories for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(LabelCategory)
        .where(LabelCategory.project_id == project_id)
        .order_by(LabelCategory.name)
    )
    categories = result.scalars().all()
    
    return [LabelCategoryResponse.model_validate(cat) for cat in categories]


@router.post("/categories", response_model=LabelCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_label_category(
    category_data: LabelCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new label category."""
    await verify_project_access(category_data.project_id, current_user.id, db)
    
    category = LabelCategory(
        project_id=category_data.project_id,
        name=category_data.name,
        color=category_data.color,
        description=category_data.description,
    )
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return LabelCategoryResponse.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a label category."""
    result = await db.execute(
        select(LabelCategory)
        .join(Project)
        .where(
            and_(LabelCategory.id == category_id, Project.user_id == current_user.id)
        )
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label category not found"
        )
    
    await db.delete(category)
    await db.commit()

