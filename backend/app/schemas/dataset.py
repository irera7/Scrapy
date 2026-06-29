"""Schemas for dataset management features."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DatasetSplit(str, Enum):
    """Dataset split types."""
    TRAIN = "train"
    VAL = "val"
    TEST = "test"
    UNASSIGNED = "unassigned"


class SplitConfig(BaseModel):
    """Configuration for dataset splitting."""
    train_ratio: float = Field(0.8, ge=0, le=1)
    val_ratio: float = Field(0.1, ge=0, le=1)
    test_ratio: float = Field(0.1, ge=0, le=1)
    stratify_by: Optional[str] = None  # Column to stratify by (e.g., "labels")
    random_seed: Optional[int] = 42
    shuffle: bool = True


class SplitAssignment(BaseModel):
    """Assign items to a specific split."""
    item_ids: List[UUID]
    split: DatasetSplit


class AutoSplitRequest(BaseModel):
    """Request for automatic dataset splitting."""
    project_id: UUID
    config: SplitConfig
    filter_labeled_only: bool = False
    filter_processed_only: bool = False
    min_quality_score: Optional[float] = None
    create_version: bool = True
    version_name: Optional[str] = None
    version_description: Optional[str] = None


class SplitStats(BaseModel):
    """Statistics for dataset splits."""
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    unassigned_count: int = 0
    total: int = 0
    by_label: Optional[Dict[str, Dict[str, int]]] = None


# Dataset Version Schemas
class DatasetVersionCreate(BaseModel):
    """Create a new dataset version."""
    project_id: UUID
    version: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    parent_version_id: Optional[UUID] = None
    include_splits: bool = True


class DatasetVersionResponse(BaseModel):
    """Dataset version response."""
    id: UUID
    project_id: UUID
    version: str
    description: Optional[str]
    parent_version_id: Optional[UUID]
    item_count: int
    train_count: int
    val_count: int
    test_count: int
    split_config: Dict[str, Any]
    statistics: Dict[str, Any]
    is_published: bool
    created_at: datetime
    created_by: Optional[UUID]
    
    class Config:
        from_attributes = True


class DatasetVersionDiff(BaseModel):
    """Diff between two dataset versions."""
    added_items: List[UUID]
    removed_items: List[UUID]
    added_count: int
    removed_count: int


# Dataset Card Schemas
class DatasetCardCreate(BaseModel):
    """Create a dataset card."""
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    citation: Optional[str] = None
    languages: List[str] = []
    task_categories: List[str] = []
    task_ids: List[str] = []
    size_categories: Optional[str] = None
    source_datasets: List[str] = []
    annotations_creators: List[str] = []
    language_creators: List[str] = []
    multilinguality: Optional[str] = None
    pretty_name: Optional[str] = None
    tags: List[str] = []
    bias_risks: Optional[str] = None
    ethical_considerations: Optional[str] = None
    curation_rationale: Optional[str] = None


class DatasetCardUpdate(BaseModel):
    """Update a dataset card."""
    title: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    citation: Optional[str] = None
    languages: Optional[List[str]] = None
    task_categories: Optional[List[str]] = None
    task_ids: Optional[List[str]] = None
    size_categories: Optional[str] = None
    source_datasets: Optional[List[str]] = None
    annotations_creators: Optional[List[str]] = None
    language_creators: Optional[List[str]] = None
    multilinguality: Optional[str] = None
    pretty_name: Optional[str] = None
    tags: Optional[List[str]] = None
    bias_risks: Optional[str] = None
    ethical_considerations: Optional[str] = None
    curation_rationale: Optional[str] = None


class DatasetCardResponse(BaseModel):
    """Dataset card response."""
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    homepage: Optional[str]
    license: Optional[str]
    citation: Optional[str]
    languages: List[str]
    task_categories: List[str]
    task_ids: List[str]
    size_categories: Optional[str]
    source_datasets: List[str]
    annotations_creators: List[str]
    language_creators: List[str]
    multilinguality: Optional[str]
    pretty_name: Optional[str]
    tags: List[str]
    bias_risks: Optional[str]
    ethical_considerations: Optional[str]
    curation_rationale: Optional[str]
    created_at: datetime
    updated_at: datetime
    yaml_content: Optional[str] = None
    
    class Config:
        from_attributes = True


# Annotation Schemas
class AnnotationKind(str, Enum):
    """Types of annotations."""
    BBOX = "bbox"  # Bounding box
    POLYGON = "polygon"  # Polygon segmentation
    POLYLINE = "polyline"  # Line annotation
    POINT = "point"  # Point annotation
    NER = "ner"  # Named Entity Recognition
    CLASSIFICATION = "classification"  # Multi-label classification
    RELATION = "relation"  # Relation between entities
    KEYPOINTS = "keypoints"  # Skeleton/keypoint annotation


class AnnotationTypeCreate(BaseModel):
    """Create an annotation type."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    annotation_kind: AnnotationKind
    type_schema: Dict[str, Any] = Field(default={}, alias="schema")
    color: str = "#3B82F6"
    shortcut_key: Optional[str] = None
    
    class Config:
        populate_by_name = True


class AnnotationTypeResponse(BaseModel):
    """Annotation type response."""
    id: UUID
    project_id: UUID
    name: str
    annotation_kind: str
    type_schema: Dict[str, Any] = Field(default={}, validation_alias="schema", serialization_alias="schema")
    color: str
    shortcut_key: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True
    
    class Config:
        from_attributes = True


class BBoxAnnotation(BaseModel):
    """Bounding box annotation."""
    type_id: UUID
    label: str
    x: float
    y: float
    width: float
    height: float
    confidence: Optional[float] = None
    attributes: Dict[str, Any] = {}


class PolygonAnnotation(BaseModel):
    """Polygon annotation for segmentation."""
    type_id: UUID
    label: str
    points: List[List[float]]  # [[x1,y1], [x2,y2], ...]
    confidence: Optional[float] = None
    attributes: Dict[str, Any] = {}


class NERAnnotation(BaseModel):
    """Named Entity Recognition annotation."""
    type_id: UUID
    label: str
    start: int  # Character offset start
    end: int  # Character offset end
    text: str  # The annotated text
    confidence: Optional[float] = None
    attributes: Dict[str, Any] = {}


class ItemAnnotations(BaseModel):
    """All annotations for an item."""
    bboxes: List[BBoxAnnotation] = []
    polygons: List[PolygonAnnotation] = []
    ner: List[NERAnnotation] = []
    classifications: List[str] = []
    keypoints: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []


class AnnotateItemRequest(BaseModel):
    """Request to annotate an item."""
    annotations: ItemAnnotations
    merge: bool = True  # Merge with existing or replace


# Augmentation Schemas
class AugmentationType(str, Enum):
    """Types of data augmentation."""
    # Text augmentations
    TEXT_SYNONYM = "text_synonym"
    TEXT_BACK_TRANSLATION = "text_back_translation"
    TEXT_RANDOM_SWAP = "text_random_swap"
    TEXT_RANDOM_DELETE = "text_random_delete"
    TEXT_RANDOM_INSERT = "text_random_insert"
    TEXT_PARAPHRASE = "text_paraphrase"
    TEXT_NOISE = "text_noise"
    
    # Image augmentations
    IMAGE_FLIP_HORIZONTAL = "image_flip_horizontal"
    IMAGE_FLIP_VERTICAL = "image_flip_vertical"
    IMAGE_ROTATE = "image_rotate"
    IMAGE_BRIGHTNESS = "image_brightness"
    IMAGE_CONTRAST = "image_contrast"
    IMAGE_CROP = "image_crop"
    IMAGE_NOISE = "image_noise"
    IMAGE_BLUR = "image_blur"
    IMAGE_COLOR_JITTER = "image_color_jitter"
    IMAGE_GRAYSCALE = "image_grayscale"
    
    # Audio augmentations (enhanced)
    AUDIO_SPEED = "audio_speed"
    AUDIO_PITCH = "audio_pitch"
    AUDIO_NOISE = "audio_noise"
    AUDIO_TIME_STRETCH = "audio_time_stretch"
    AUDIO_REVERB = "audio_reverb"
    AUDIO_TIME_SHIFT = "audio_time_shift"
    AUDIO_VOLUME = "audio_volume"
    AUDIO_LOW_PASS = "audio_low_pass"
    
    # Video augmentations (new)
    VIDEO_FLIP_HORIZONTAL = "video_flip_horizontal"
    VIDEO_FLIP_VERTICAL = "video_flip_vertical"
    VIDEO_ROTATE = "video_rotate"
    VIDEO_SPEED = "video_speed"
    VIDEO_BRIGHTNESS = "video_brightness"
    VIDEO_CONTRAST = "video_contrast"
    VIDEO_SATURATION = "video_saturation"
    VIDEO_CROP = "video_crop"
    VIDEO_NOISE = "video_noise"
    VIDEO_BLUR = "video_blur"
    VIDEO_COLOR_JITTER = "video_color_jitter"
    VIDEO_GRAYSCALE = "video_grayscale"


class AugmentationRuleCreate(BaseModel):
    """Create an augmentation rule."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    data_type: str  # text, image, audio
    augmentation_type: AugmentationType
    parameters: Dict[str, Any] = {}
    probability: float = Field(1.0, ge=0, le=1)
    is_active: bool = True


class AugmentationRuleResponse(BaseModel):
    """Augmentation rule response."""
    id: UUID
    project_id: UUID
    name: str
    data_type: str
    augmentation_type: str
    parameters: Dict[str, Any]
    probability: float
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class RunAugmentationRequest(BaseModel):
    """Request to run augmentation."""
    project_id: UUID
    rule_ids: Optional[List[UUID]] = None  # Run specific rules, or all if None
    item_ids: Optional[List[UUID]] = None  # Augment specific items, or all if None
    max_augmented_per_item: int = 1
    only_labeled: bool = True


class AugmentationResult(BaseModel):
    """Result of augmentation."""
    original_count: int
    augmented_count: int
    items_created: List[UUID]
    errors: List[str] = []


# Dataset Statistics Schemas  
class LabelDistribution(BaseModel):
    """Distribution of labels."""
    label: str
    count: int
    percentage: float
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0


class DataTypeDistribution(BaseModel):
    """Distribution of data types."""
    data_type: str
    count: int
    percentage: float
    avg_size: Optional[float] = None


class QualityDistribution(BaseModel):
    """Distribution of quality scores."""
    range: str  # e.g., "0.0-0.2", "0.2-0.4", etc.
    count: int
    percentage: float


class DatasetStatistics(BaseModel):
    """Comprehensive dataset statistics."""
    project_id: UUID
    total_items: int
    labeled_items: int
    processed_items: int
    
    # Split distribution
    split_distribution: SplitStats
    
    # Label distribution
    label_distribution: List[LabelDistribution]
    unique_labels: int
    avg_labels_per_item: float
    
    # Data type distribution
    data_type_distribution: List[DataTypeDistribution]
    
    # Quality distribution
    quality_distribution: List[QualityDistribution]
    avg_quality_score: Optional[float]
    
    # Size metrics
    total_storage_bytes: int
    avg_file_size: Optional[float]
    
    # Text metrics (if applicable)
    avg_text_length: Optional[float]
    avg_word_count: Optional[float]
    
    # Image metrics (if applicable)
    avg_image_width: Optional[float]
    avg_image_height: Optional[float]
    
    # Class imbalance metrics
    class_imbalance_ratio: Optional[float]  # max_count / min_count
    is_balanced: bool  # True if ratio < 3
    
    # Recommendations
    recommendations: List[str] = []


# Active Learning Schemas
class ActiveLearningConfig(BaseModel):
    """Configuration for active learning."""
    strategy: str = "uncertainty"  # uncertainty, diversity, random
    batch_size: int = 10
    min_confidence: float = 0.0
    max_confidence: float = 0.5  # Items with confidence below this
    exclude_labeled: bool = True


class ActiveLearningSuggestion(BaseModel):
    """Suggested items for labeling."""
    item_id: UUID
    uncertainty_score: float
    reason: str
    data_type: str
    preview: Optional[str] = None


class ActiveLearningResponse(BaseModel):
    """Response with suggested items."""
    suggestions: List[ActiveLearningSuggestion]
    total_unlabeled: int
    strategy_used: str
