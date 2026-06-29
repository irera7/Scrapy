# Services

from app.services.nlp_processor import nlp_processor, process_text_item
from app.services.image_processor import image_processor, process_image_item
from app.services.audio_processor import audio_processor, process_audio_item
from app.services.video_processor import video_processor, process_video_item
from app.services.augmentation_service import (
    text_augmenter, 
    image_augmenter,
    audio_augmenter,
    video_augmenter,
    run_augmentation
)
from app.services.embedding_service import embedding_service
from app.services.export_service import ExportGenerator, execute_export

# New Quality & Validation Services
from app.services.annotation_quality_service import (
    annotation_quality_service,
    AnnotationAgreementCalculator,
    AnnotationQualityService
)
from app.services.data_leakage_service import (
    data_leakage_service,
    DataLeakageService,
    LeakageDetector
)
from app.services.advanced_quality_service import (
    advanced_quality_service,
    ImageQualityAnalyzer,
    AudioQualityAnalyzer,
    TextQualityAnalyzer
)
from app.services.data_validation_service import (
    data_validation_service,
    SchemaValidator,
    MissingValuesHandler,
    OutlierDetector,
    TemporalSplitter
)
from app.services.backup_service import backup_service, BackupService

# New Services (Phase 2)
from app.services.speaker_service import speaker_service, SpeakerService
from app.services.multimodal_service import multimodal_service, MultimodalService
from app.services.timeseries_service import timeseries_service, TimeSeriesService
from app.services.video_quality_service import video_quality_service, VideoQualityService
from app.services.image_quality_service import image_quality_service, ImageQualityService
from app.services.tabular_service import tabular_service, TabularService
from app.services.annotation_tools_service import annotation_tools_service, AnnotationToolsService
from app.services.graph_service import graph_service, GraphService
from app.services.threed_service import threed_service, ThreeDService

__all__ = [
    # NLP
    "nlp_processor",
    "process_text_item",
    
    # Image
    "image_processor",
    "process_image_item",
    
    # Audio
    "audio_processor",
    "process_audio_item",
    
    # Video
    "video_processor",
    "process_video_item",
    
    # Augmentation
    "text_augmenter",
    "image_augmenter",
    "audio_augmenter",
    "video_augmenter",
    "run_augmentation",
    
    # Embeddings
    "embedding_service",
    
    # Export
    "ExportGenerator",
    "execute_export",
    
    # Annotation Quality
    "annotation_quality_service",
    "AnnotationAgreementCalculator",
    "AnnotationQualityService",
    
    # Data Leakage
    "data_leakage_service",
    "DataLeakageService",
    "LeakageDetector",
    
    # Advanced Quality
    "advanced_quality_service",
    "ImageQualityAnalyzer",
    "AudioQualityAnalyzer",
    "TextQualityAnalyzer",
    
    # Data Validation
    "data_validation_service",
    "SchemaValidator",
    "MissingValuesHandler",
    "OutlierDetector",
    "TemporalSplitter",
    
    # Backup
    "backup_service",
    "BackupService",
    
    # Speaker Identification
    "speaker_service",
    "SpeakerService",
    
    # Multimodal
    "multimodal_service",
    "MultimodalService",
    
    # Time Series
    "timeseries_service",
    "TimeSeriesService",
    
    # Video Quality
    "video_quality_service",
    "VideoQualityService",
    
    # Image Quality
    "image_quality_service",
    "ImageQualityService",
    
    # Tabular
    "tabular_service",
    "TabularService",
    
    # Annotation Tools
    "annotation_tools_service",
    "AnnotationToolsService",
    
    # Graph
    "graph_service",
    "GraphService",
    
    # 3D
    "threed_service",
    "ThreeDService",
]
