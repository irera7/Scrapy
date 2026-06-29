"""Export Service for generating ML-ready datasets.

This service generates exports with full ML feature support:
- Dataset splits (train/val/test)
- Annotations
- Augmented data handling
- Version snapshots
- Stratified sampling
- Incremental exports
"""
from datetime import datetime, timezone
from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
import json
import csv
import io
import os
import tempfile
import zipfile
import tarfile
import random
from collections import defaultdict
import structlog

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_, func

from app.core.config import settings
from app.core.storage import storage_service
from app.models.export import Export
from app.models.data_item import DataItem

logger = structlog.get_logger()


def create_worker_session():
    """Create a fresh async session for worker tasks.
    
    This creates a new engine each time to avoid event loop conflicts
    when running in Celery workers with different event loops.
    """
    engine = create_async_engine(
        settings.DATABASE_URL, 
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    return engine, session_factory()


class ExportGenerator:
    """Generates export files in various formats."""
    
    SUPPORTED_FORMATS = [
        'jsonl', 'csv', 'parquet', 'tfrecord', 
        'huggingface', 'coco', 'webdataset'
    ]
    
    def __init__(self, items: List[DataItem], options: Dict[str, Any] = None):
        self.items = items
        self.options = options or {}
    
    async def generate(self, format: str) -> Tuple[bytes, str, str]:
        """
        Generate export in specified format.
        
        Returns:
            Tuple of (data, content_type, extension)
        """
        format = format.lower()
        
        if format == 'jsonl':
            return self._generate_jsonl()
        elif format == 'csv':
            return self._generate_csv()
        elif format == 'parquet':
            return self._generate_parquet()
        elif format == 'tfrecord':
            return await self._generate_tfrecord()
        elif format == 'huggingface':
            return await self._generate_huggingface()
        elif format == 'coco':
            return self._generate_coco()
        elif format == 'webdataset':
            return await self._generate_webdataset()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_jsonl(self) -> Tuple[bytes, str, str]:
        """Generate JSONL format (JSON Lines) with full ML feature support."""
        include_metadata = self.options.get('include_metadata', True)
        include_content = self.options.get('include_content', True)
        include_annotations = self.options.get('include_annotations', True)
        include_ml_fields = self.options.get('include_ml_fields', True)
        
        lines = []
        for item in self.items:
            record = {
                "id": str(item.id),
                "type": item.data_type,
                "labels": item.labels or [],
            }
            
            if include_content and item.content:
                record["content"] = item.content
                record["text"] = item.content  # Alias for NLP tasks
            
            if item.source_url:
                record["source_url"] = item.source_url
            
            if item.file_path:
                record["file_path"] = item.file_path
            
            if include_metadata and item.item_metadata:
                record["metadata"] = item.item_metadata
            
            if item.quality_score is not None:
                record["quality_score"] = item.quality_score
            
            # ML Features
            if include_ml_fields:
                # Dataset split
                if hasattr(item, 'dataset_split') and item.dataset_split:
                    record["split"] = item.dataset_split
                
                # Annotations
                if include_annotations and hasattr(item, 'annotations') and item.annotations:
                    record["annotations"] = item.annotations
                
                # Augmentation info
                if hasattr(item, 'augmented_from') and item.augmented_from:
                    record["augmented_from"] = str(item.augmented_from)
                    record["augmentation_type"] = item.augmentation_type
                
                # Uncertainty score (for active learning)
                if hasattr(item, 'uncertainty_score') and item.uncertainty_score is not None:
                    record["uncertainty_score"] = item.uncertainty_score
            
            lines.append(json.dumps(record, ensure_ascii=False))
        
        data = "\n".join(lines).encode("utf-8")
        return data, "application/jsonl", "jsonl"
    
    def _generate_csv(self) -> Tuple[bytes, str, str]:
        """Generate CSV format with ML feature support."""
        include_metadata = self.options.get('include_metadata', False)
        include_annotations = self.options.get('include_annotations', True)
        include_ml_fields = self.options.get('include_ml_fields', True)
        custom_columns = self.options.get('columns')
        
        output = io.StringIO()
        
        # Determine columns
        if custom_columns:
            columns = custom_columns
        else:
            columns = ["id", "type", "content", "source_url", "labels", "quality_score"]
            if include_ml_fields:
                columns.extend(["split", "augmented_from", "augmentation_type"])
            if include_annotations:
                columns.append("annotations")
            if include_metadata:
                columns.append("metadata")
        
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        
        for item in self.items:
            row = {
                "id": str(item.id),
                "type": item.data_type,
                "content": item.content or "",
                "source_url": item.source_url or "",
                "labels": "|".join(item.labels or []),
                "quality_score": item.quality_score or "",
            }
            
            # ML fields
            if include_ml_fields:
                row["split"] = getattr(item, 'dataset_split', '') or ''
                row["augmented_from"] = str(item.augmented_from) if getattr(item, 'augmented_from', None) else ''
                row["augmentation_type"] = getattr(item, 'augmentation_type', '') or ''
            
            # Annotations
            if include_annotations:
                annotations = getattr(item, 'annotations', None)
                row["annotations"] = json.dumps(annotations) if annotations else ''
            
            if include_metadata:
                row["metadata"] = json.dumps(item.item_metadata or {})
            
            # Add metadata fields as columns if requested
            if item.item_metadata and self.options.get('flatten_metadata'):
                for key, value in item.item_metadata.items():
                    if key not in row:
                        row[key] = value if not isinstance(value, (dict, list)) else json.dumps(value)
            
            writer.writerow(row)
        
        data = output.getvalue().encode("utf-8")
        return data, "text/csv", "csv"
    
    def _generate_parquet(self) -> Tuple[bytes, str, str]:
        """Generate Apache Parquet format."""
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError("pyarrow is required for Parquet export")
        
        # Build columns
        data_dict = {
            "id": [str(item.id) for item in self.items],
            "type": [item.data_type for item in self.items],
            "content": [item.content or "" for item in self.items],
            "source_url": [item.source_url or "" for item in self.items],
            "file_path": [item.file_path or "" for item in self.items],
            "labels": [item.labels or [] for item in self.items],
            "quality_score": [item.quality_score or 0.0 for item in self.items],
            "is_labeled": [item.is_labeled for item in self.items],
            "is_processed": [item.is_processed for item in self.items],
        }
        
        # Add metadata fields if requested
        if self.options.get('include_metadata', True):
            data_dict["metadata_json"] = [
                json.dumps(item.item_metadata or {}) for item in self.items
            ]
        
        # Create schema
        schema = pa.schema([
            ("id", pa.string()),
            ("type", pa.string()),
            ("content", pa.string()),
            ("source_url", pa.string()),
            ("file_path", pa.string()),
            ("labels", pa.list_(pa.string())),
            ("quality_score", pa.float64()),
            ("is_labeled", pa.bool_()),
            ("is_processed", pa.bool_()),
        ])
        
        if self.options.get('include_metadata', True):
            schema = schema.append(pa.field("metadata_json", pa.string()))
        
        table = pa.Table.from_pydict(data_dict, schema=schema)
        
        output = io.BytesIO()
        pq.write_table(table, output, compression='snappy')
        data = output.getvalue()
        
        return data, "application/octet-stream", "parquet"
    
    async def _generate_tfrecord(self) -> Tuple[bytes, str, str]:
        """Generate TensorFlow TFRecord format."""
        try:
            import tensorflow as tf
        except ImportError:
            raise ImportError("tensorflow is required for TFRecord export")
        
        output = io.BytesIO()
        
        with tf.io.TFRecordWriter(output) as writer:
            for item in self.items:
                # Create feature dict
                feature = {
                    'id': tf.train.Feature(bytes_list=tf.train.BytesList(value=[str(item.id).encode()])),
                    'type': tf.train.Feature(bytes_list=tf.train.BytesList(value=[item.data_type.encode()])),
                }
                
                # Text content
                if item.content:
                    feature['text'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[item.content.encode('utf-8')])
                    )
                
                # Labels (for classification)
                if item.labels:
                    feature['label'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[item.labels[0].encode()])
                    )
                    feature['labels'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[l.encode() for l in item.labels])
                    )
                
                # Quality score
                if item.quality_score is not None:
                    feature['quality_score'] = tf.train.Feature(
                        float_list=tf.train.FloatList(value=[item.quality_score])
                    )
                
                # Image data (if available)
                if item.data_type == 'image' and item.file_path:
                    try:
                        image_data = storage_service.download_file(item.file_path)
                        feature['image'] = tf.train.Feature(
                            bytes_list=tf.train.BytesList(value=[image_data])
                        )
                        
                        # Image dimensions from metadata
                        if item.item_metadata:
                            if 'width' in item.item_metadata:
                                feature['width'] = tf.train.Feature(
                                    int64_list=tf.train.Int64List(value=[item.item_metadata['width']])
                                )
                            if 'height' in item.item_metadata:
                                feature['height'] = tf.train.Feature(
                                    int64_list=tf.train.Int64List(value=[item.item_metadata['height']])
                                )
                    except Exception as e:
                        logger.warning(f"Could not include image data: {e}")
                
                example = tf.train.Example(features=tf.train.Features(feature=feature))
                writer.write(example.SerializeToString())
        
        data = output.getvalue()
        return data, "application/octet-stream", "tfrecord"
    
    async def _generate_huggingface(self) -> Tuple[bytes, str, str]:
        """Generate HuggingFace Datasets format with proper split support.
        
        HuggingFace Datasets format:
        - dataset_info.json: Dataset metadata and features
        - dataset_dict.json: Split information
        - train.jsonl, validation.jsonl, test.jsonl: Data files per split
        - README.md: Dataset card for HuggingFace Hub
        """
        temp_dir = tempfile.mkdtemp()
        include_annotations = self.options.get('include_annotations', True)
        
        try:
            # Determine features based on data type
            data_types = set(item.data_type for item in self.items)
            
            # Group items by split
            split_items = defaultdict(list)
            for item in self.items:
                split = getattr(item, 'dataset_split', None) or 'train'
                if split == 'unassigned':
                    split = 'train'
                split_items[split].append(item)
            
            # Build features dict following HF's exact format
            features = {
                "id": {"dtype": "string", "_type": "Value"},
            }
            
            if 'text' in data_types:
                features["text"] = {"dtype": "string", "_type": "Value"}
            if 'image' in data_types:
                features["image"] = {"_type": "Image"}
            if 'audio' in data_types:
                features["audio"] = {"_type": "Audio"}
            if 'video' in data_types:
                features["video"] = {"dtype": "string", "_type": "Value"}
            
            features["label"] = {"dtype": "string", "_type": "Value"}
            features["labels"] = {
                "feature": {"dtype": "string", "_type": "Value"},
                "_type": "Sequence"
            }
            features["source_url"] = {"dtype": "string", "_type": "Value"}
            features["quality_score"] = {"dtype": "float32", "_type": "Value"}
            
            if include_annotations:
                features["annotations"] = {"dtype": "string", "_type": "Value"}
            
            features["metadata"] = {"dtype": "string", "_type": "Value"}
            
            # Create splits info
            splits_info = {}
            total_bytes = 0
            
            for split_name, items in split_items.items():
                # Create data file for this split
                data_file = os.path.join(temp_dir, f"{split_name}.jsonl")
                split_bytes = 0
                
                with open(data_file, "w", encoding="utf-8") as f:
                    for item in items:
                        record = {
                            "id": str(item.id),
                            "label": item.labels[0] if item.labels else "",
                            "labels": item.labels or [],
                            "source_url": item.source_url or "",
                            "quality_score": item.quality_score or 0.0,
                            "metadata": json.dumps(item.item_metadata or {}),
                        }
                        
                        # Add content based on data type
                        if item.content:
                            record["text"] = item.content
                        
                        if item.data_type == 'image':
                            record["image"] = item.file_path or item.source_url or ""
                        
                        if item.data_type == 'audio':
                            record["audio"] = item.file_path or item.source_url or ""
                        
                        if item.data_type == 'video':
                            record["video"] = item.file_path or item.source_url or ""
                        
                        # Add annotations if enabled
                        if include_annotations:
                            annotations = getattr(item, 'annotations', None)
                            record["annotations"] = json.dumps(annotations) if annotations else ""
                        
                        line = json.dumps(record, ensure_ascii=False) + "\n"
                        split_bytes += len(line.encode('utf-8'))
                        f.write(line)
                
                splits_info[split_name] = {
                    "name": split_name,
                    "num_bytes": split_bytes,
                    "num_examples": len(items),
                    "dataset_name": "ai_collector_export"
                }
                total_bytes += split_bytes
            
            # Create dataset info
            dataset_info = {
                "description": "Dataset exported from AI Data Collector with ML features",
                "citation": "",
                "homepage": "",
                "license": "",
                "features": features,
                "splits": splits_info,
                "download_size": total_bytes,
                "dataset_size": total_bytes,
            }
            
            # Save dataset_info.json
            with open(os.path.join(temp_dir, "dataset_info.json"), "w") as f:
                json.dump(dataset_info, f, indent=2)
            
            # Save dataset_dict.json
            dataset_dict = {
                "splits": list(split_items.keys())
            }
            with open(os.path.join(temp_dir, "dataset_dict.json"), "w") as f:
                json.dump(dataset_dict, f, indent=2)
            
            # Create README with split info
            split_info_str = "\n".join([
                f"  - **{name}**: {len(items)} examples"
                for name, items in split_items.items()
            ])
            
            readme_content = f"""---
dataset_info:
  features:
{chr(10).join(f"    - name: {k}" for k in features.keys())}
  splits:
{chr(10).join(f"    - name: {name}{chr(10)}      num_examples: {len(items)}" for name, items in split_items.items())}
---

# Dataset

This dataset was exported from AI Data Collector with full ML feature support.

## Dataset Information

- **Total examples**: {len(self.items)}
- **Data types**: {', '.join(data_types)}

## Splits

{split_info_str}

## Features

- Text content (for NLP tasks)
- Labels (multi-label support)
- Quality scores
- Annotations (bounding boxes, NER, etc.)
- Source metadata

## Usage

```python
from datasets import load_dataset

# Load all splits
dataset = load_dataset("path/to/dataset")

# Access specific split
train_data = dataset["train"]
val_data = dataset["validation"]
test_data = dataset["test"]
```
"""
            with open(os.path.join(temp_dir, "README.md"), "w") as f:
                f.write(readme_content)
            
            # Create zip file
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname)
            
            data = output.getvalue()
            return data, "application/zip", "zip"
        
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def _generate_coco(self) -> Tuple[bytes, str, str]:
        """Generate COCO JSON format for computer vision tasks with annotation support.
        
        COCO format specification:
        - info: Dataset description
        - licenses: License information
        - images: List of images with id, file_name, width, height
        - annotations: List of annotations with id, image_id, category_id
        - categories: List of categories with id, name, supercategory
        
        This version includes annotations from the ML Dataset annotation system.
        """
        coco_data = {
            "info": {
                "description": "AI Data Collector Export with ML Annotations",
                "url": "",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "AI Data Collector",
                "date_created": datetime.now(timezone.utc).isoformat()
            },
            "licenses": [
                {
                    "id": 1,
                    "name": "Unknown",
                    "url": ""
                }
            ],
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        # Collect unique labels as categories
        label_to_id = {}
        
        # First pass: collect all labels from both labels field and annotations
        for item in self.items:
            # From labels field
            for label in (item.labels or []):
                if label not in label_to_id:
                    cat_id = len(label_to_id) + 1
                    label_to_id[label] = cat_id
            
            # From annotations (bbox, polygon, etc.)
            item_annotations = getattr(item, 'annotations', None) or {}
            for ann_type, ann_list in item_annotations.items():
                if isinstance(ann_list, list):
                    for ann in ann_list:
                        if isinstance(ann, dict) and 'label' in ann:
                            label = ann['label']
                            if label not in label_to_id:
                                cat_id = len(label_to_id) + 1
                                label_to_id[label] = cat_id
        
        # Create categories
        for label, cat_id in label_to_id.items():
            coco_data["categories"].append({
                "id": cat_id,
                "name": label,
                "supercategory": "object"
            })
        
        # Add default category if none exist
        if not coco_data["categories"]:
            coco_data["categories"].append({
                "id": 1,
                "name": "object",
                "supercategory": "object"
            })
            label_to_id["object"] = 1
        
        # Add images and annotations
        annotation_id = 1
        for idx, item in enumerate(self.items):
            if item.data_type == "image":
                image_id = idx + 1
                
                # Get dimensions from metadata
                width = 0
                height = 0
                if item.item_metadata:
                    width = item.item_metadata.get("width") or item.item_metadata.get("image_width") or 0
                    height = item.item_metadata.get("height") or item.item_metadata.get("image_height") or 0
                    
                    try:
                        width = int(str(width).replace('px', '').strip() or 0)
                        height = int(str(height).replace('px', '').strip() or 0)
                    except (ValueError, TypeError):
                        width, height = 0, 0
                
                # Image entry
                image_entry = {
                    "id": image_id,
                    "file_name": item.file_path or item.source_url or str(item.id),
                    "width": width,
                    "height": height,
                    "coco_url": item.source_url or "",
                    "flickr_url": "",
                    "date_captured": item.created_at.isoformat() if item.created_at else "",
                    "license": 1,
                }
                
                # Add split info
                if hasattr(item, 'dataset_split') and item.dataset_split:
                    image_entry["split"] = item.dataset_split
                
                coco_data["images"].append(image_entry)
                
                # Process ML annotations (bboxes, polygons, etc.)
                item_annotations = getattr(item, 'annotations', None) or {}
                
                # Bounding boxes
                for bbox_ann in item_annotations.get('bboxes', []):
                    if isinstance(bbox_ann, dict):
                        label = bbox_ann.get('label', 'object')
                        cat_id = label_to_id.get(label, 1)
                        
                        # COCO bbox format: [x, y, width, height]
                        x = bbox_ann.get('x', 0)
                        y = bbox_ann.get('y', 0)
                        w = bbox_ann.get('width', 0)
                        h = bbox_ann.get('height', 0)
                        
                        annotation = {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": cat_id,
                            "bbox": [x, y, w, h],
                            "area": w * h,
                            "iscrowd": 0,
                        }
                        
                        coco_data["annotations"].append(annotation)
                        annotation_id += 1
                
                # Polygons (segmentation)
                for poly_ann in item_annotations.get('polygons', []):
                    if isinstance(poly_ann, dict):
                        label = poly_ann.get('label', 'object')
                        cat_id = label_to_id.get(label, 1)
                        points = poly_ann.get('points', [])
                        
                        if points:
                            # Flatten points for COCO format
                            flat_points = []
                            for pt in points:
                                if isinstance(pt, dict):
                                    flat_points.extend([pt.get('x', 0), pt.get('y', 0)])
                                elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                                    flat_points.extend([pt[0], pt[1]])
                            
                            annotation = {
                                "id": annotation_id,
                                "image_id": image_id,
                                "category_id": cat_id,
                                "segmentation": [flat_points],
                                "area": 0,  # Would need to calculate polygon area
                                "iscrowd": 0,
                            }
                            
                            coco_data["annotations"].append(annotation)
                            annotation_id += 1
                
                # Keypoints
                for kp_ann in item_annotations.get('keypoints', []):
                    if isinstance(kp_ann, dict):
                        label = kp_ann.get('label', 'object')
                        cat_id = label_to_id.get(label, 1)
                        points = kp_ann.get('points', [])
                        
                        if points:
                            # COCO keypoints format: [x1, y1, v1, x2, y2, v2, ...]
                            keypoints = []
                            for pt in points:
                                if isinstance(pt, dict):
                                    keypoints.extend([
                                        pt.get('x', 0),
                                        pt.get('y', 0),
                                        pt.get('visibility', 2)  # 2 = visible
                                    ])
                            
                            annotation = {
                                "id": annotation_id,
                                "image_id": image_id,
                                "category_id": cat_id,
                                "keypoints": keypoints,
                                "num_keypoints": len(points),
                                "iscrowd": 0,
                            }
                            
                            coco_data["annotations"].append(annotation)
                            annotation_id += 1
                
                # Fallback: use labels if no ML annotations
                if not item_annotations:
                    for label in (item.labels or []):
                        annotation = {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": label_to_id[label],
                            "iscrowd": 0,
                        }
                        
                        # Add bounding box if available in metadata
                        if item.item_metadata and "bbox" in item.item_metadata:
                            bbox = item.item_metadata["bbox"]
                            annotation["bbox"] = bbox
                            annotation["area"] = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                        
                        if item.item_metadata and "segmentation" in item.item_metadata:
                            annotation["segmentation"] = item.item_metadata["segmentation"]
                        
                        coco_data["annotations"].append(annotation)
                        annotation_id += 1
        
        data = json.dumps(coco_data, ensure_ascii=False, indent=2).encode("utf-8")
        return data, "application/json", "json"
    
    async def _generate_webdataset(self) -> Tuple[bytes, str, str]:
        """Generate WebDataset format (tar archive with paired files)."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            output = io.BytesIO()
            
            with tarfile.open(fileobj=output, mode='w') as tar:
                for idx, item in enumerate(self.items):
                    sample_key = f"{idx:08d}"
                    
                    # Add JSON metadata
                    metadata = {
                        "id": str(item.id),
                        "type": item.data_type,
                        "labels": item.labels or [],
                        "source_url": item.source_url,
                        "quality_score": item.quality_score,
                        "metadata": item.item_metadata or {},
                    }
                    
                    json_data = json.dumps(metadata, ensure_ascii=False).encode('utf-8')
                    json_info = tarfile.TarInfo(name=f"{sample_key}.json")
                    json_info.size = len(json_data)
                    tar.addfile(json_info, io.BytesIO(json_data))
                    
                    # Add text content
                    if item.content:
                        text_data = item.content.encode('utf-8')
                        text_info = tarfile.TarInfo(name=f"{sample_key}.txt")
                        text_info.size = len(text_data)
                        tar.addfile(text_info, io.BytesIO(text_data))
                    
                    # Add labels
                    if item.labels:
                        cls_data = item.labels[0].encode('utf-8')
                        cls_info = tarfile.TarInfo(name=f"{sample_key}.cls")
                        cls_info.size = len(cls_data)
                        tar.addfile(cls_info, io.BytesIO(cls_data))
                    
                    # Add media files
                    if item.file_path:
                        try:
                            file_data = storage_service.download_file(item.file_path)
                            ext = item.file_path.rsplit('.', 1)[-1] if '.' in item.file_path else 'bin'
                            
                            file_info = tarfile.TarInfo(name=f"{sample_key}.{ext}")
                            file_info.size = len(file_data)
                            tar.addfile(file_info, io.BytesIO(file_data))
                        except Exception as e:
                            logger.warning(f"Could not include file {item.file_path}: {e}")
            
            data = output.getvalue()
            return data, "application/x-tar", "tar"
        
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def stratified_sample(items: List[DataItem], sample_size: int) -> List[DataItem]:
    """
    Perform stratified sampling to maintain class distribution.
    
    Args:
        items: List of data items
        sample_size: Target sample size
        
    Returns:
        Sampled items with preserved class distribution
    """
    if len(items) <= sample_size:
        return items
    
    # Group items by label
    label_groups = defaultdict(list)
    unlabeled = []
    
    for item in items:
        if item.labels and len(item.labels) > 0:
            # Use first label for stratification
            label_groups[item.labels[0]].append(item)
        else:
            unlabeled.append(item)
    
    # Calculate proportions
    total = len(items)
    sampled = []
    
    for label, group_items in label_groups.items():
        # Calculate proportional sample size for this label
        proportion = len(group_items) / total
        group_sample_size = max(1, int(sample_size * proportion))
        
        # Sample from this group
        if len(group_items) <= group_sample_size:
            sampled.extend(group_items)
        else:
            sampled.extend(random.sample(group_items, group_sample_size))
    
    # Add unlabeled items proportionally
    if unlabeled:
        proportion = len(unlabeled) / total
        unlabeled_sample_size = max(0, int(sample_size * proportion))
        if len(unlabeled) <= unlabeled_sample_size:
            sampled.extend(unlabeled)
        else:
            sampled.extend(random.sample(unlabeled, unlabeled_sample_size))
    
    # If we're still under target, add more items
    remaining = sample_size - len(sampled)
    if remaining > 0:
        available = [item for item in items if item not in sampled]
        if available:
            sampled.extend(random.sample(available, min(remaining, len(available))))
    
    return sampled


async def execute_export(export_id: str) -> dict:
    """Execute an export task with full ML feature support.
    
    Creates a fresh database engine/session for Celery worker compatibility.
    This avoids event loop conflicts when running in different processes.
    """
    # Create fresh engine and session for this worker task
    engine, db = create_worker_session()
    
    try:
        # Get export
        result = await db.execute(
            select(Export).where(Export.id == UUID(export_id))
        )
        export = result.scalar_one_or_none()
        
        if not export:
            raise ValueError(f"Export not found: {export_id}")
        
        # Update status
        export.status = "processing"
        await db.commit()
        
        try:
            # Get data items
            query = select(DataItem).where(DataItem.project_id == export.project_id)
            
            # Apply filters
            filters = export.filters or {}
            
            # Basic filters
            if filters.get("data_types"):
                query = query.where(DataItem.data_type.in_(filters["data_types"]))
            
            if filters.get("is_labeled") is not None:
                query = query.where(DataItem.is_labeled == filters["is_labeled"])
            
            if filters.get("is_processed") is not None:
                query = query.where(DataItem.is_processed == filters["is_processed"])
            
            if filters.get("min_quality_score") is not None:
                query = query.where(DataItem.quality_score >= filters["min_quality_score"])
            
            if filters.get("labels"):
                # Filter by labels (JSONB array contains)
                for label in filters["labels"]:
                    query = query.where(DataItem.labels.contains([label]))
            
            # ML Feature Filters
            
            # Filter by dataset splits (train/val/test)
            if filters.get("splits"):
                query = query.where(DataItem.dataset_split.in_(filters["splits"]))
            
            # Filter by augmentation status
            if filters.get("include_augmented") is False:
                query = query.where(DataItem.augmented_from.is_(None))
            elif filters.get("only_augmented") is True:
                query = query.where(DataItem.augmented_from.isnot(None))
            
            # Filter by annotation status
            if filters.get("has_annotations") is True:
                query = query.where(DataItem.annotations != {})
                query = query.where(DataItem.annotations.isnot(None))
            
            # Note: exclude_quality_filtered and exclude_duplicates are handled post-query
            # for better compatibility with different PostgreSQL versions
            
            # Incremental export - only items created after base export
            if hasattr(export, 'base_export_id') and export.base_export_id:
                base_export_result = await db.execute(
                    select(Export.completed_at).where(Export.id == export.base_export_id)
                )
                base_completed_at = base_export_result.scalar_one_or_none()
                
                if base_completed_at:
                    query = query.where(DataItem.created_at > base_completed_at)
            
            # Version snapshot - items that existed at version creation time
            if hasattr(export, 'dataset_version_id') and export.dataset_version_id:
                from app.models.dataset import DatasetVersion
                
                version_result = await db.execute(
                    select(DatasetVersion.created_at).where(
                        DatasetVersion.id == export.dataset_version_id
                    )
                )
                version_created_at = version_result.scalar_one_or_none()
                
                if version_created_at:
                    query = query.where(DataItem.created_at <= version_created_at)
            
            result = await db.execute(query)
            items = list(result.scalars().all())
            
            # Post-query filters for metadata-based exclusions
            if filters.get("exclude_quality_filtered", False):
                items = [
                    item for item in items
                    if not (item.item_metadata and item.item_metadata.get('quality_filtered'))
                ]
            
            if filters.get("exclude_duplicates", False):
                items = [
                    item for item in items
                    if not (item.item_metadata and item.item_metadata.get('duplicate_of'))
                ]
            
            # Apply stratified sampling if requested
            if filters.get("stratified_sample") and filters.get("sample_size"):
                items = stratified_sample(items, filters["sample_size"])
            # Apply simple limit if specified
            elif filters.get("limit"):
                items = items[:filters["limit"]]
            
            if not items:
                export.status = "completed"
                export.record_count = 0
                export.file_size = 0
                export.completed_at = datetime.now(timezone.utc)
                await db.commit()
                
                return {
                    "success": True,
                    "export_id": export_id,
                    "record_count": 0,
                    "message": "No items matched the filters"
                }
            
            # Build options with ML feature flags
            options = filters.get("options", {})
            options['include_annotations'] = filters.get("include_annotations", True)
            options['include_ml_fields'] = True
            
            # Generate export file
            generator = ExportGenerator(items, options)
            file_data, content_type, extension = await generator.generate(export.format)
            
            # Upload to storage
            file_path = f"exports/{export.project_id}/{export.id}.{extension}"
            storage_service.upload_bytes(file_data, file_path, content_type)
            
            # Update export record
            export.status = "completed"
            export.file_path = file_path
            export.file_size = len(file_data)
            export.record_count = len(items)
            export.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Log statistics
            split_counts = defaultdict(int)
            for item in items:
                if hasattr(item, 'dataset_split') and item.dataset_split:
                    split_counts[item.dataset_split] += 1
            
            logger.info(
                f"Export completed: {export.name}, "
                f"{len(items)} records, {len(file_data)} bytes, "
                f"splits: {dict(split_counts)}"
            )
            
            return {
                "success": True,
                "export_id": export_id,
                "record_count": len(items),
                "file_size": len(file_data),
                "split_distribution": dict(split_counts)
            }
        
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            export.status = "failed"
            export.error_message = str(e)
            await db.commit()
            raise
    
    finally:
        # Always clean up: close session and dispose engine
        await db.close()
        await engine.dispose()


async def generate_export_file(items: list, format: str) -> tuple:
    """Generate export file in specified format (legacy function)."""
    generator = ExportGenerator(items)
    data, content_type, _ = await generator.generate(format)
    return data, content_type
