"""API endpoints for dataset management - splits, versions, statistics, annotations."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, distinct
from typing import List, Optional
from uuid import UUID
import random
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.data_item import DataItem
from app.models.dataset import DatasetVersion, DatasetCard, AnnotationType, AugmentationRule
from app.schemas.dataset import (
    DatasetSplit, SplitConfig, SplitAssignment, AutoSplitRequest, SplitStats,
    DatasetVersionCreate, DatasetVersionResponse, DatasetVersionDiff,
    DatasetCardCreate, DatasetCardUpdate, DatasetCardResponse,
    AnnotationTypeCreate, AnnotationTypeResponse, AnnotateItemRequest, ItemAnnotations,
    AugmentationRuleCreate, AugmentationRuleResponse, RunAugmentationRequest, AugmentationResult,
    DatasetStatistics, LabelDistribution, DataTypeDistribution, QualityDistribution,
    ActiveLearningConfig, ActiveLearningResponse, ActiveLearningSuggestion,
)

router = APIRouter()
logger = structlog.get_logger()


async def verify_project_access(project_id: UUID, user_id: UUID, db: AsyncSession) -> Project:
    """Verify user has access to the project."""
    result = await db.execute(
        select(Project).where(and_(Project.id == project_id, Project.user_id == user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# ==================== Dataset Splits ====================

@router.get("/splits/{project_id}/stats", response_model=SplitStats)
async def get_split_stats(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about dataset splits."""
    await verify_project_access(project_id, current_user.id, db)
    
    # Get counts by split
    result = await db.execute(
        select(
            DataItem.dataset_split,
            func.count(DataItem.id).label('count')
        )
        .where(DataItem.project_id == project_id)
        .group_by(DataItem.dataset_split)
    )
    rows = result.all()
    
    stats = SplitStats()
    for row in rows:
        split, count = row
        if split == "train":
            stats.train_count = count
        elif split == "val":
            stats.val_count = count
        elif split == "test":
            stats.test_count = count
        else:
            stats.unassigned_count = count
    
    stats.total = stats.train_count + stats.val_count + stats.test_count + stats.unassigned_count
    
    # Get label distribution per split
    label_result = await db.execute(
        select(DataItem.labels, DataItem.dataset_split)
        .where(and_(
            DataItem.project_id == project_id,
            DataItem.is_labeled == True
        ))
    )
    label_rows = label_result.all()
    
    by_label = {}
    for labels, split in label_rows:
        if labels:
            for label in labels:
                if label not in by_label:
                    by_label[label] = {"train": 0, "val": 0, "test": 0, "unassigned": 0}
                by_label[label][split or "unassigned"] += 1
    
    stats.by_label = by_label if by_label else None
    
    return stats


@router.post("/splits/assign")
async def assign_splits(
    assignment: SplitAssignment,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually assign items to a split."""
    if not assignment.item_ids:
        raise HTTPException(status_code=400, detail="No items provided")
    
    # Verify all items belong to user's projects
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(and_(
            DataItem.id.in_(assignment.item_ids),
            Project.user_id == current_user.id
        ))
    )
    items = result.scalars().all()
    
    if len(items) != len(assignment.item_ids):
        raise HTTPException(status_code=404, detail="Some items not found")
    
    for item in items:
        item.dataset_split = assignment.split.value
    
    await db.commit()
    
    return {"updated": len(items), "split": assignment.split.value}


@router.post("/splits/auto")
async def auto_split_dataset(
    request: AutoSplitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Automatically split dataset into train/val/test."""
    await verify_project_access(request.project_id, current_user.id, db)
    
    # Validate ratios
    total_ratio = request.config.train_ratio + request.config.val_ratio + request.config.test_ratio
    if abs(total_ratio - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Split ratios must sum to 1.0")
    
    # Build query with filters
    query = select(DataItem).where(DataItem.project_id == request.project_id)
    
    if request.filter_labeled_only:
        query = query.where(DataItem.is_labeled == True)
    if request.filter_processed_only:
        query = query.where(DataItem.is_processed == True)
    if request.min_quality_score is not None:
        query = query.where(DataItem.quality_score >= request.min_quality_score)
    
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    if not items:
        raise HTTPException(status_code=400, detail="No items match the criteria")
    
    # Shuffle if requested
    if request.config.shuffle:
        random.seed(request.config.random_seed)
        random.shuffle(items)
    
    # Stratified split if requested
    if request.config.stratify_by == "labels":
        # Group by primary label
        label_groups = {}
        for item in items:
            # Handle labels that might be None, empty list, or have different types
            labels = item.labels if isinstance(item.labels, list) else []
            label = labels[0] if labels else "_unlabeled_"
            # Ensure label is a string
            if not isinstance(label, str):
                label = str(label) if label else "_unlabeled_"
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(item)
        
        # Split each group proportionally
        train_items, val_items, test_items = [], [], []
        for label, group in label_groups.items():
            n = len(group)
            train_end = int(n * request.config.train_ratio)
            val_end = train_end + int(n * request.config.val_ratio)
            
            train_items.extend(group[:train_end])
            val_items.extend(group[train_end:val_end])
            test_items.extend(group[val_end:])
    else:
        # Simple split
        n = len(items)
        train_end = int(n * request.config.train_ratio)
        val_end = train_end + int(n * request.config.val_ratio)
        
        train_items = items[:train_end]
        val_items = items[train_end:val_end]
        test_items = items[val_end:]
    
    # Apply splits
    for item in train_items:
        item.dataset_split = "train"
    for item in val_items:
        item.dataset_split = "val"
    for item in test_items:
        item.dataset_split = "test"
    
    await db.commit()
    
    # Create version if requested
    version_id = None
    if request.create_version:
        version_name = request.version_name or f"v{len(items)}_split"
        version = DatasetVersion(
            project_id=request.project_id,
            version=version_name,
            description=request.version_description or f"Auto-split with {request.config.train_ratio}/{request.config.val_ratio}/{request.config.test_ratio} ratio",
            item_count=len(items),
            train_count=len(train_items),
            val_count=len(val_items),
            test_count=len(test_items),
            item_ids=[str(item.id) for item in items],
            split_config=request.config.model_dump(),
            created_by=current_user.id,
        )
        db.add(version)
        await db.commit()
        version_id = version.id
    
    return {
        "total": len(items),
        "train": len(train_items),
        "val": len(val_items),
        "test": len(test_items),
        "version_id": str(version_id) if version_id else None,
    }


@router.post("/splits/reset/{project_id}")
async def reset_splits(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset all items to unassigned split."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(DataItem).where(DataItem.project_id == project_id)
    )
    items = result.scalars().all()
    
    for item in items:
        item.dataset_split = "unassigned"
    
    await db.commit()
    
    return {"reset": len(items)}


# ==================== Dataset Versions ====================

@router.get("/versions/{project_id}", response_model=List[DatasetVersionResponse])
async def list_versions(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(DatasetVersion)
        .where(DatasetVersion.project_id == project_id)
        .order_by(DatasetVersion.created_at.desc())
    )
    versions = result.scalars().all()
    
    return [DatasetVersionResponse.model_validate(v) for v in versions]


@router.post("/versions", response_model=DatasetVersionResponse)
async def create_version(
    data: DatasetVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new dataset version snapshot."""
    await verify_project_access(data.project_id, current_user.id, db)
    
    # Check version doesn't exist
    existing = await db.execute(
        select(DatasetVersion).where(and_(
            DatasetVersion.project_id == data.project_id,
            DatasetVersion.version == data.version
        ))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Version already exists")
    
    # Get current items
    query = select(DataItem).where(DataItem.project_id == data.project_id)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Count splits
    train_count = sum(1 for i in items if i.dataset_split == "train")
    val_count = sum(1 for i in items if i.dataset_split == "val")
    test_count = sum(1 for i in items if i.dataset_split == "test")
    
    # Compute basic statistics
    statistics = {
        "labeled_count": sum(1 for i in items if i.is_labeled),
        "processed_count": sum(1 for i in items if i.is_processed),
        "data_types": {},
        "label_counts": {},
    }
    
    for item in items:
        # Data type counts
        dt = item.data_type
        statistics["data_types"][dt] = statistics["data_types"].get(dt, 0) + 1
        
        # Label counts
        for label in (item.labels or []):
            statistics["label_counts"][label] = statistics["label_counts"].get(label, 0) + 1
    
    version = DatasetVersion(
        project_id=data.project_id,
        version=data.version,
        description=data.description,
        parent_version_id=data.parent_version_id,
        item_count=len(items),
        train_count=train_count,
        val_count=val_count,
        test_count=test_count,
        item_ids=[str(i.id) for i in items],
        statistics=statistics,
        created_by=current_user.id,
    )
    
    db.add(version)
    await db.commit()
    await db.refresh(version)
    
    return DatasetVersionResponse.model_validate(version)


@router.get("/versions/{project_id}/{version_id}", response_model=DatasetVersionResponse)
async def get_version(
    project_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific version."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(DatasetVersion).where(and_(
            DatasetVersion.id == version_id,
            DatasetVersion.project_id == project_id
        ))
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return DatasetVersionResponse.model_validate(version)


@router.get("/versions/{project_id}/diff/{version1_id}/{version2_id}", response_model=DatasetVersionDiff)
async def diff_versions(
    project_id: UUID,
    version1_id: UUID,
    version2_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get diff between two versions."""
    await verify_project_access(project_id, current_user.id, db)
    
    result1 = await db.execute(
        select(DatasetVersion).where(DatasetVersion.id == version1_id)
    )
    result2 = await db.execute(
        select(DatasetVersion).where(DatasetVersion.id == version2_id)
    )
    
    v1 = result1.scalar_one_or_none()
    v2 = result2.scalar_one_or_none()
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    set1 = set(v1.item_ids or [])
    set2 = set(v2.item_ids or [])
    
    added = list(set2 - set1)
    removed = list(set1 - set2)
    
    return DatasetVersionDiff(
        added_items=[UUID(i) for i in added],
        removed_items=[UUID(i) for i in removed],
        added_count=len(added),
        removed_count=len(removed),
    )


@router.post("/versions/{version_id}/publish")
async def publish_version(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a version as published."""
    result = await db.execute(
        select(DatasetVersion)
        .join(Project)
        .where(and_(
            DatasetVersion.id == version_id,
            Project.user_id == current_user.id
        ))
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    version.is_published = True
    await db.commit()
    
    return {"published": True}


# ==================== Dataset Statistics ====================

@router.get("/statistics/{project_id}", response_model=DatasetStatistics)
async def get_dataset_statistics(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive dataset statistics."""
    await verify_project_access(project_id, current_user.id, db)
    
    # Get all items
    result = await db.execute(
        select(DataItem).where(DataItem.project_id == project_id)
    )
    items = result.scalars().all()
    
    total = len(items)
    if total == 0:
        return DatasetStatistics(
            project_id=project_id,
            total_items=0,
            labeled_items=0,
            processed_items=0,
            split_distribution=SplitStats(),
            label_distribution=[],
            unique_labels=0,
            avg_labels_per_item=0,
            data_type_distribution=[],
            quality_distribution=[],
            avg_quality_score=None,
            total_storage_bytes=0,
            avg_file_size=None,
            avg_text_length=None,
            avg_word_count=None,
            avg_image_width=None,
            avg_image_height=None,
            class_imbalance_ratio=None,
            is_balanced=True,
            recommendations=[],
        )
    
    labeled = sum(1 for i in items if i.is_labeled)
    processed = sum(1 for i in items if i.is_processed)
    
    # Split distribution
    split_counts = {"train": 0, "val": 0, "test": 0, "unassigned": 0}
    for item in items:
        split_counts[item.dataset_split or "unassigned"] += 1
    
    split_stats = SplitStats(
        train_count=split_counts["train"],
        val_count=split_counts["val"],
        test_count=split_counts["test"],
        unassigned_count=split_counts["unassigned"],
        total=total,
    )
    
    # Label distribution
    label_counts = {}
    label_splits = {}
    total_labels = 0
    for item in items:
        for label in (item.labels or []):
            label_counts[label] = label_counts.get(label, 0) + 1
            total_labels += 1
            
            if label not in label_splits:
                label_splits[label] = {"train": 0, "val": 0, "test": 0}
            split = item.dataset_split or "unassigned"
            if split in label_splits[label]:
                label_splits[label][split] += 1
    
    label_distribution = [
        LabelDistribution(
            label=label,
            count=count,
            percentage=count / total * 100,
            train_count=label_splits.get(label, {}).get("train", 0),
            val_count=label_splits.get(label, {}).get("val", 0),
            test_count=label_splits.get(label, {}).get("test", 0),
        )
        for label, count in sorted(label_counts.items(), key=lambda x: -x[1])
    ]
    
    # Data type distribution
    type_counts = {}
    type_sizes = {}
    for item in items:
        dt = item.data_type
        type_counts[dt] = type_counts.get(dt, 0) + 1
        if item.file_size:
            if dt not in type_sizes:
                type_sizes[dt] = []
            type_sizes[dt].append(item.file_size)
    
    data_type_distribution = [
        DataTypeDistribution(
            data_type=dt,
            count=count,
            percentage=count / total * 100,
            avg_size=sum(type_sizes.get(dt, [])) / len(type_sizes.get(dt, [1])) if type_sizes.get(dt) else None,
        )
        for dt, count in sorted(type_counts.items(), key=lambda x: -x[1])
    ]
    
    # Quality distribution
    quality_scores = [i.quality_score for i in items if i.quality_score is not None]
    quality_ranges = [
        ("0.0-0.2", 0.0, 0.2),
        ("0.2-0.4", 0.2, 0.4),
        ("0.4-0.6", 0.4, 0.6),
        ("0.6-0.8", 0.6, 0.8),
        ("0.8-1.0", 0.8, 1.0),
    ]
    quality_distribution = []
    for range_name, low, high in quality_ranges:
        count = sum(1 for q in quality_scores if low <= q < high or (high == 1.0 and q == 1.0))
        quality_distribution.append(QualityDistribution(
            range=range_name,
            count=count,
            percentage=count / len(quality_scores) * 100 if quality_scores else 0,
        ))
    
    # Storage
    total_storage = sum(i.file_size or 0 for i in items)
    files_with_size = [i for i in items if i.file_size]
    avg_file_size = total_storage / len(files_with_size) if files_with_size else None
    
    # Text metrics
    text_items = [i for i in items if i.data_type == "text" and i.content]
    avg_text_length = None
    avg_word_count = None
    if text_items:
        lengths = [len(i.content) for i in text_items]
        word_counts = [len(i.content.split()) for i in text_items]
        avg_text_length = sum(lengths) / len(lengths)
        avg_word_count = sum(word_counts) / len(word_counts)
    
    # Image metrics
    avg_image_width = None
    avg_image_height = None
    image_items = [i for i in items if i.data_type == "image" and i.item_metadata]
    if image_items:
        widths = [i.item_metadata.get("width", 0) for i in image_items if i.item_metadata.get("width")]
        heights = [i.item_metadata.get("height", 0) for i in image_items if i.item_metadata.get("height")]
        if widths:
            avg_image_width = sum(widths) / len(widths)
        if heights:
            avg_image_height = sum(heights) / len(heights)
    
    # Class imbalance
    class_imbalance_ratio = None
    is_balanced = True
    if label_counts:
        counts = list(label_counts.values())
        if min(counts) > 0:
            class_imbalance_ratio = max(counts) / min(counts)
            is_balanced = class_imbalance_ratio < 3
    
    # Recommendations
    recommendations = []
    if split_counts["unassigned"] > 0:
        recommendations.append(f"Split your dataset: {split_counts['unassigned']} items are unassigned")
    if labeled < total * 0.5:
        recommendations.append(f"Label more data: only {labeled}/{total} items are labeled")
    if class_imbalance_ratio and class_imbalance_ratio > 5:
        recommendations.append(f"Address class imbalance: ratio is {class_imbalance_ratio:.1f}x")
    if not quality_scores:
        recommendations.append("Compute quality scores to filter low-quality data")
    elif sum(1 for q in quality_scores if q < 0.5) > len(quality_scores) * 0.3:
        recommendations.append("Consider removing low-quality items (>30% have score < 0.5)")
    
    return DatasetStatistics(
        project_id=project_id,
        total_items=total,
        labeled_items=labeled,
        processed_items=processed,
        split_distribution=split_stats,
        label_distribution=label_distribution,
        unique_labels=len(label_counts),
        avg_labels_per_item=total_labels / labeled if labeled > 0 else 0,
        data_type_distribution=data_type_distribution,
        quality_distribution=quality_distribution,
        avg_quality_score=sum(quality_scores) / len(quality_scores) if quality_scores else None,
        total_storage_bytes=total_storage,
        avg_file_size=avg_file_size,
        avg_text_length=avg_text_length,
        avg_word_count=avg_word_count,
        avg_image_width=avg_image_width,
        avg_image_height=avg_image_height,
        class_imbalance_ratio=class_imbalance_ratio,
        is_balanced=is_balanced,
        recommendations=recommendations,
    )


# ==================== Dataset Cards ====================

@router.get("/cards/{project_id}", response_model=DatasetCardResponse)
async def get_dataset_card(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dataset card for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(DatasetCard).where(DatasetCard.project_id == project_id)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Dataset card not found")
    
    response = DatasetCardResponse.model_validate(card)
    response.yaml_content = card.to_yaml()
    return response


@router.post("/cards", response_model=DatasetCardResponse)
async def create_dataset_card(
    data: DatasetCardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a dataset card."""
    await verify_project_access(data.project_id, current_user.id, db)
    
    # Check if card exists
    existing = await db.execute(
        select(DatasetCard).where(DatasetCard.project_id == data.project_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Dataset card already exists")
    
    card = DatasetCard(**data.model_dump())
    db.add(card)
    await db.commit()
    await db.refresh(card)
    
    response = DatasetCardResponse.model_validate(card)
    response.yaml_content = card.to_yaml()
    return response


@router.patch("/cards/{project_id}", response_model=DatasetCardResponse)
async def update_dataset_card(
    project_id: UUID,
    data: DatasetCardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update dataset card."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(DatasetCard).where(DatasetCard.project_id == project_id)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Dataset card not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(card, field, value)
    
    await db.commit()
    await db.refresh(card)
    
    response = DatasetCardResponse.model_validate(card)
    response.yaml_content = card.to_yaml()
    return response


# ==================== Annotations ====================

@router.get("/annotations/types/{project_id}", response_model=List[AnnotationTypeResponse])
async def list_annotation_types(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List annotation types for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(AnnotationType).where(AnnotationType.project_id == project_id)
    )
    types = result.scalars().all()
    
    return [AnnotationTypeResponse.model_validate(t) for t in types]


@router.post("/annotations/types", response_model=AnnotationTypeResponse)
async def create_annotation_type(
    data: AnnotationTypeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an annotation type."""
    await verify_project_access(data.project_id, current_user.id, db)
    
    ann_type = AnnotationType(
        project_id=data.project_id,
        name=data.name,
        annotation_kind=data.annotation_kind.value,
        schema=data.type_schema,
        color=data.color,
        shortcut_key=data.shortcut_key,
    )
    db.add(ann_type)
    await db.commit()
    await db.refresh(ann_type)
    
    return AnnotationTypeResponse.model_validate(ann_type)


@router.delete("/annotations/types/{type_id}")
async def delete_annotation_type(
    type_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an annotation type."""
    result = await db.execute(
        select(AnnotationType)
        .join(Project)
        .where(and_(
            AnnotationType.id == type_id,
            Project.user_id == current_user.id
        ))
    )
    ann_type = result.scalar_one_or_none()
    
    if not ann_type:
        raise HTTPException(status_code=404, detail="Annotation type not found")
    
    await db.delete(ann_type)
    await db.commit()
    
    return {"deleted": True}


@router.post("/annotations/items/{item_id}")
async def annotate_item(
    item_id: UUID,
    request: AnnotateItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add or update annotations for an item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(and_(
            DataItem.id == item_id,
            Project.user_id == current_user.id
        ))
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    annotations_data = request.annotations.model_dump()
    
    if request.merge and item.annotations:
        # Merge with existing
        existing = item.annotations
        for key, value in annotations_data.items():
            if value:
                if key in existing and existing[key]:
                    existing[key].extend(value)
                else:
                    existing[key] = value
        item.annotations = existing
    else:
        item.annotations = annotations_data
    
    # Mark as labeled if has annotations
    if any(v for v in annotations_data.values()):
        item.is_labeled = True
    
    await db.commit()
    
    return {"success": True, "annotations": item.annotations}


@router.get("/annotations/items/{item_id}")
async def get_item_annotations(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get annotations for an item."""
    result = await db.execute(
        select(DataItem)
        .join(Project)
        .where(and_(
            DataItem.id == item_id,
            Project.user_id == current_user.id
        ))
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"item_id": str(item_id), "annotations": item.annotations or {}}


# ==================== Augmentation ====================

@router.get("/augmentation/rules/{project_id}", response_model=List[AugmentationRuleResponse])
async def list_augmentation_rules(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List augmentation rules for a project."""
    await verify_project_access(project_id, current_user.id, db)
    
    result = await db.execute(
        select(AugmentationRule).where(AugmentationRule.project_id == project_id)
    )
    rules = result.scalars().all()
    
    return [AugmentationRuleResponse.model_validate(r) for r in rules]


@router.post("/augmentation/rules", response_model=AugmentationRuleResponse)
async def create_augmentation_rule(
    data: AugmentationRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an augmentation rule."""
    await verify_project_access(data.project_id, current_user.id, db)
    
    rule = AugmentationRule(
        project_id=data.project_id,
        name=data.name,
        data_type=data.data_type,
        augmentation_type=data.augmentation_type.value,
        parameters=data.parameters,
        probability=data.probability,
        is_active=data.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return AugmentationRuleResponse.model_validate(rule)


@router.delete("/augmentation/rules/{rule_id}")
async def delete_augmentation_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an augmentation rule."""
    result = await db.execute(
        select(AugmentationRule)
        .join(Project)
        .where(and_(
            AugmentationRule.id == rule_id,
            Project.user_id == current_user.id
        ))
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()
    
    return {"deleted": True}


# ==================== Active Learning ====================

@router.post("/active-learning/{project_id}/suggestions", response_model=ActiveLearningResponse)
async def get_active_learning_suggestions(
    project_id: UUID,
    config: ActiveLearningConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get suggestions for items to label next using active learning."""
    await verify_project_access(project_id, current_user.id, db)
    
    # Query items
    query = select(DataItem).where(DataItem.project_id == project_id)
    
    if config.exclude_labeled:
        query = query.where(DataItem.is_labeled == False)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    total_unlabeled = len(items)
    
    suggestions = []
    
    if config.strategy == "uncertainty":
        # Sort by uncertainty score (if available) or quality score
        scored_items = []
        for item in items:
            score = item.uncertainty_score
            if score is None:
                # Use inverse quality as proxy for uncertainty
                score = 1 - (item.quality_score or 0.5)
            scored_items.append((item, score))
        
        # Filter by confidence range
        scored_items = [
            (item, score) for item, score in scored_items
            if config.min_confidence <= score <= config.max_confidence
        ]
        
        # Sort by highest uncertainty
        scored_items.sort(key=lambda x: -x[1])
        
        for item, score in scored_items[:config.batch_size]:
            preview = None
            if item.content:
                preview = item.content[:100] + "..." if len(item.content) > 100 else item.content
            
            suggestions.append(ActiveLearningSuggestion(
                item_id=item.id,
                uncertainty_score=score,
                reason="High uncertainty",
                data_type=item.data_type,
                preview=preview,
            ))
    
    elif config.strategy == "diversity":
        # Random diverse sampling
        import random
        random.shuffle(items)
        for item in items[:config.batch_size]:
            preview = None
            if item.content:
                preview = item.content[:100] + "..." if len(item.content) > 100 else item.content
            
            suggestions.append(ActiveLearningSuggestion(
                item_id=item.id,
                uncertainty_score=0.5,
                reason="Diverse sampling",
                data_type=item.data_type,
                preview=preview,
            ))
    
    elif config.strategy == "random":
        import random
        sampled = random.sample(items, min(config.batch_size, len(items)))
        for item in sampled:
            preview = None
            if item.content:
                preview = item.content[:100] + "..." if len(item.content) > 100 else item.content
            
            suggestions.append(ActiveLearningSuggestion(
                item_id=item.id,
                uncertainty_score=0.5,
                reason="Random sampling",
                data_type=item.data_type,
                preview=preview,
            ))
    
    return ActiveLearningResponse(
        suggestions=suggestions,
        total_unlabeled=total_unlabeled,
        strategy_used=config.strategy,
    )


# ==================== Run Augmentation ====================

@router.post("/augmentation/run", response_model=AugmentationResult)
async def run_augmentation(
    request: RunAugmentationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run augmentation on items."""
    await verify_project_access(request.project_id, current_user.id, db)
    
    from app.services.augmentation_service import run_augmentation as do_augmentation
    
    result = await do_augmentation(
        db=db,
        project_id=request.project_id,
        rule_ids=request.rule_ids,
        item_ids=request.item_ids,
        max_per_item=request.max_augmented_per_item,
        only_labeled=request.only_labeled,
    )
    
    return AugmentationResult(**result)


# ==================== Embeddings ====================

@router.post("/embeddings/{project_id}/generate")
async def generate_embeddings(
    project_id: UUID,
    recompute: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate embeddings for text items."""
    await verify_project_access(project_id, current_user.id, db)
    
    from app.services.embedding_service import generate_embeddings_for_project
    
    result = await generate_embeddings_for_project(db, project_id, recompute)
    
    return result


@router.get("/embeddings/{project_id}/similar/{item_id}")
async def find_similar(
    project_id: UUID,
    item_id: UUID,
    top_k: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find items similar to a given item."""
    await verify_project_access(project_id, current_user.id, db)
    
    from app.services.embedding_service import find_similar_items
    
    results = await find_similar_items(db, item_id, project_id, top_k)
    
    return {"similar_items": results}


@router.get("/embeddings/{project_id}/duplicates")
async def find_embedding_duplicates(
    project_id: UUID,
    threshold: float = Query(0.95, ge=0.5, le=1.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find duplicate items using embedding similarity."""
    await verify_project_access(project_id, current_user.id, db)
    
    from app.services.embedding_service import find_duplicates_by_embedding
    
    duplicates = await find_duplicates_by_embedding(db, project_id, threshold)
    
    return {"duplicates": duplicates, "count": len(duplicates)}
