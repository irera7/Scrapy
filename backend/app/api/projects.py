from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import ScrapingJob
from app.models.data_item import DataItem
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats

router = APIRouter()
logger = structlog.get_logger()


async def verify_project_access(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Project:
    """Verify that the user has access to the project and return it."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all projects for the current user."""
    query = select(Project).where(Project.user_id == current_user.id)
    
    if is_active is not None:
        query = query.where(Project.is_active == is_active)
    
    query = query.order_by(Project.updated_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Get counts for each project
    response = []
    for project in projects:
        # Get job count
        job_count_result = await db.execute(
            select(func.count(ScrapingJob.id)).where(ScrapingJob.project_id == project.id)
        )
        job_count = job_count_result.scalar() or 0
        
        # Get total data count
        data_count_result = await db.execute(
            select(func.count(DataItem.id)).where(DataItem.project_id == project.id)
        )
        data_count = data_count_result.scalar() or 0
        
        # Get data type breakdown counts
        text_count_result = await db.execute(
            select(func.count(DataItem.id)).where(
                and_(DataItem.project_id == project.id, DataItem.data_type == "text")
            )
        )
        image_count_result = await db.execute(
            select(func.count(DataItem.id)).where(
                and_(DataItem.project_id == project.id, DataItem.data_type == "image")
            )
        )
        audio_count_result = await db.execute(
            select(func.count(DataItem.id)).where(
                and_(DataItem.project_id == project.id, DataItem.data_type == "audio")
            )
        )
        video_count_result = await db.execute(
            select(func.count(DataItem.id)).where(
                and_(DataItem.project_id == project.id, DataItem.data_type == "video")
            )
        )
        
        project_response = ProjectResponse.model_validate(project)
        project_response.job_count = job_count
        project_response.data_count = data_count
        project_response.text_count = text_count_result.scalar() or 0
        project_response.image_count = image_count_result.scalar() or 0
        project_response.audio_count = audio_count_result.scalar() or 0
        project_response.video_count = video_count_result.scalar() or 0
        response.append(project_response)
    
    return response


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    project = Project(
        user_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        data_type=project_data.data_type.value,
        settings=project_data.settings or {},
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Project created: {project.name} by {current_user.email}")
    
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get counts
    job_count_result = await db.execute(
        select(func.count(ScrapingJob.id)).where(ScrapingJob.project_id == project.id)
    )
    data_count_result = await db.execute(
        select(func.count(DataItem.id)).where(DataItem.project_id == project.id)
    )
    
    # Get data type breakdown counts
    text_count_result = await db.execute(
        select(func.count(DataItem.id)).where(
            and_(DataItem.project_id == project.id, DataItem.data_type == "text")
        )
    )
    image_count_result = await db.execute(
        select(func.count(DataItem.id)).where(
            and_(DataItem.project_id == project.id, DataItem.data_type == "image")
        )
    )
    audio_count_result = await db.execute(
        select(func.count(DataItem.id)).where(
            and_(DataItem.project_id == project.id, DataItem.data_type == "audio")
        )
    )
    video_count_result = await db.execute(
        select(func.count(DataItem.id)).where(
            and_(DataItem.project_id == project.id, DataItem.data_type == "video")
        )
    )
    
    project_response = ProjectResponse.model_validate(project)
    project_response.job_count = job_count_result.scalar() or 0
    project_response.data_count = data_count_result.scalar() or 0
    project_response.text_count = text_count_result.scalar() or 0
    project_response.image_count = image_count_result.scalar() or 0
    project_response.audio_count = audio_count_result.scalar() or 0
    project_response.video_count = video_count_result.scalar() or 0
    
    return project_response


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a project."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update fields
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description
    if project_update.data_type is not None:
        project.data_type = project_update.data_type.value
    if project_update.settings is not None:
        project.settings = project_update.settings
    if project_update.is_active is not None:
        project.is_active = project_update.is_active
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    await db.delete(project)
    await db.commit()
    
    logger.info(f"Project deleted: {project.name}")


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project statistics."""
    result = await db.execute(
        select(Project).where(
            and_(Project.id == project_id, Project.user_id == current_user.id)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get job counts
    total_jobs = await db.execute(
        select(func.count(ScrapingJob.id)).where(ScrapingJob.project_id == project_id)
    )
    active_jobs = await db.execute(
        select(func.count(ScrapingJob.id)).where(
            and_(ScrapingJob.project_id == project_id, ScrapingJob.status == "running")
        )
    )
    completed_jobs = await db.execute(
        select(func.count(ScrapingJob.id)).where(
            and_(ScrapingJob.project_id == project_id, ScrapingJob.status == "completed")
        )
    )
    failed_jobs = await db.execute(
        select(func.count(ScrapingJob.id)).where(
            and_(ScrapingJob.project_id == project_id, ScrapingJob.status == "failed")
        )
    )
    
    # Get data counts
    total_data = await db.execute(
        select(func.count(DataItem.id)).where(DataItem.project_id == project_id)
    )
    labeled_data = await db.execute(
        select(func.count(DataItem.id)).where(
            and_(DataItem.project_id == project_id, DataItem.is_labeled == True)
        )
    )
    
    # Get storage used
    storage_result = await db.execute(
        select(func.coalesce(func.sum(DataItem.file_size), 0)).where(
            DataItem.project_id == project_id
        )
    )
    
    return ProjectStats(
        total_jobs=total_jobs.scalar() or 0,
        active_jobs=active_jobs.scalar() or 0,
        completed_jobs=completed_jobs.scalar() or 0,
        failed_jobs=failed_jobs.scalar() or 0,
        total_data_items=total_data.scalar() or 0,
        labeled_items=labeled_data.scalar() or 0,
        storage_used=storage_result.scalar() or 0,
    )

