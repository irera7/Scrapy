from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.models.user import User
from app.models.project import Project
from app.models.export import Export
from app.schemas.export import ExportCreate, ExportResponse, ExportStatus
from app.workers.tasks import run_export_task

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


@router.get("", response_model=List[ExportResponse])
async def list_exports(
    project_id: Optional[UUID] = None,
    status_filter: Optional[ExportStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List exports."""
    query = select(Export).where(Export.user_id == current_user.id)
    
    if project_id:
        query = query.where(Export.project_id == project_id)
    
    if status_filter:
        query = query.where(Export.status == status_filter.value)
    
    query = query.order_by(Export.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    exports = result.scalars().all()
    
    # Add download URLs
    response = []
    for export in exports:
        export_response = ExportResponse.model_validate(export)
        if export.file_path and export.status == "completed":
            try:
                export_response.download_url = storage_service.get_presigned_url(export.file_path)
            except Exception:
                pass
        response.append(export_response)
    
    return response


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    export_data: ExportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new export."""
    await verify_project_access(export_data.project_id, current_user.id, db)
    
    # Convert filters to dict if it's a Pydantic model
    filters_dict = {}
    if export_data.filters:
        if hasattr(export_data.filters, 'model_dump'):
            filters_dict = export_data.filters.model_dump(exclude_none=True)
        elif isinstance(export_data.filters, dict):
            filters_dict = export_data.filters
    
    export = Export(
        project_id=export_data.project_id,
        user_id=current_user.id,
        name=export_data.name,
        format=export_data.format.value,
        filters=filters_dict,
        base_export_id=export_data.base_export_id,
        is_incremental=export_data.is_incremental or False,
        dataset_version_id=export_data.dataset_version_id,
    )
    
    db.add(export)
    await db.commit()
    await db.refresh(export)
    
    # Queue export task
    run_export_task.delay(str(export.id))
    
    logger.info(f"Export created: {export.name} ({export.format})")
    
    return ExportResponse.model_validate(export)


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific export."""
    result = await db.execute(
        select(Export).where(
            and_(Export.id == export_id, Export.user_id == current_user.id)
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )
    
    export_response = ExportResponse.model_validate(export)
    if export.file_path and export.status == "completed":
        try:
            export_response.download_url = storage_service.get_presigned_url(export.file_path)
        except Exception:
            pass
    
    return export_response


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an export."""
    result = await db.execute(
        select(Export).where(
            and_(Export.id == export_id, Export.user_id == current_user.id)
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )
    
    # Delete file from storage
    if export.file_path:
        storage_service.delete_file(export.file_path)
    
    await db.delete(export)
    await db.commit()
    
    logger.info(f"Export deleted: {export.name}")


@router.get("/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download an export file."""
    result = await db.execute(
        select(Export).where(
            and_(Export.id == export_id, Export.user_id == current_user.id)
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )
    
    if export.status != "completed" or not export.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export is not ready for download"
        )
    
    # Get file from storage
    try:
        file_data = storage_service.download_file(export.file_path)
        
        # Determine content type
        content_type_map = {
            "jsonl": "application/jsonl",
            "csv": "text/csv",
            "parquet": "application/octet-stream",
            "tfrecord": "application/octet-stream",
            "huggingface": "application/zip",
            "coco": "application/json",
            "webdataset": "application/tar",
        }
        content_type = content_type_map.get(export.format, "application/octet-stream")
        
        # Get filename
        extension_map = {
            "jsonl": "jsonl",
            "csv": "csv",
            "parquet": "parquet",
            "tfrecord": "tfrecord",
            "huggingface": "zip",
            "coco": "json",
            "webdataset": "tar",
        }
        extension = extension_map.get(export.format, "bin")
        filename = f"{export.name}.{extension}"
        
        return StreamingResponse(
            iter([file_data]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading export file"
        )

