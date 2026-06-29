"""External Annotation Tools Integration Service.

Supports:
- CVAT (Computer Vision Annotation Tool)
- Labelbox
- Label Studio
"""
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import io
import zipfile
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.models.project import Project
from app.core.storage import storage_service

logger = structlog.get_logger()


class CVATExporter:
    """Export data to CVAT format."""
    
    def __init__(self):
        self.supported_tasks = ['image_annotation', 'video_annotation', 'object_detection', 'segmentation']
    
    def export_project(
        self,
        items: List[DataItem],
        project_name: str,
        task_type: str = "image_annotation"
    ) -> Tuple[bytes, str]:
        """
        Export project to CVAT XML format.
        
        Returns: (xml_content, filename)
        """
        root = ET.Element("annotations")
        
        # Version info
        version = ET.SubElement(root, "version")
        version.text = "1.1"
        
        # Meta information
        meta = ET.SubElement(root, "meta")
        task = ET.SubElement(meta, "task")
        
        task_id = ET.SubElement(task, "id")
        task_id.text = "1"
        
        name = ET.SubElement(task, "name")
        name.text = project_name
        
        size = ET.SubElement(task, "size")
        size.text = str(len(items))
        
        mode = ET.SubElement(task, "mode")
        mode.text = "annotation"
        
        # Collect all labels
        all_labels = set()
        for item in items:
            annotations = item.annotations or []
            for ann in annotations:
                if isinstance(ann, dict) and 'label' in ann:
                    all_labels.add(ann['label'])
        
        labels_elem = ET.SubElement(task, "labels")
        for label in all_labels:
            label_elem = ET.SubElement(labels_elem, "label")
            label_name = ET.SubElement(label_elem, "name")
            label_name.text = label
        
        # Export images and annotations
        for idx, item in enumerate(items):
            if item.data_type == "image":
                self._add_image_element(root, item, idx)
            elif item.data_type == "video":
                self._add_track_element(root, item, idx)
        
        # Format XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        formatted_xml = dom.toprettyxml(indent="  ")
        
        return formatted_xml.encode('utf-8'), f"{project_name}_cvat.xml"
    
    def _add_image_element(self, root: ET.Element, item: DataItem, idx: int):
        """Add image element to CVAT XML."""
        image = ET.SubElement(root, "image")
        image.set("id", str(idx))
        image.set("name", item.name or f"image_{idx}")
        
        # Get dimensions from metadata
        metadata = item.item_metadata or {}
        image.set("width", str(metadata.get("width", 0)))
        image.set("height", str(metadata.get("height", 0)))
        
        # Add annotations
        annotations = item.annotations or []
        for ann_idx, ann in enumerate(annotations):
            if isinstance(ann, dict):
                self._add_annotation_element(image, ann, ann_idx)
    
    def _add_annotation_element(self, parent: ET.Element, ann: Dict, idx: int):
        """Add annotation element (box, polygon, polyline, points)."""
        ann_type = ann.get('type', 'box')
        label = ann.get('label', 'unknown')
        
        if ann_type == 'box' or ann_type == 'rectangle':
            box = ET.SubElement(parent, "box")
            box.set("label", label)
            box.set("xtl", str(ann.get('x', ann.get('xtl', 0))))
            box.set("ytl", str(ann.get('y', ann.get('ytl', 0))))
            box.set("xbr", str(ann.get('x', 0) + ann.get('width', 0) if 'width' in ann else ann.get('xbr', 0)))
            box.set("ybr", str(ann.get('y', 0) + ann.get('height', 0) if 'height' in ann else ann.get('ybr', 0)))
            box.set("occluded", str(int(ann.get('occluded', 0))))
            
        elif ann_type == 'polygon':
            polygon = ET.SubElement(parent, "polygon")
            polygon.set("label", label)
            points = ann.get('points', [])
            points_str = ";".join([f"{p['x']},{p['y']}" for p in points if isinstance(p, dict)])
            polygon.set("points", points_str)
            
        elif ann_type == 'polyline':
            polyline = ET.SubElement(parent, "polyline")
            polyline.set("label", label)
            points = ann.get('points', [])
            points_str = ";".join([f"{p['x']},{p['y']}" for p in points if isinstance(p, dict)])
            polyline.set("points", points_str)
            
        elif ann_type == 'points':
            points_elem = ET.SubElement(parent, "points")
            points_elem.set("label", label)
            points = ann.get('points', [])
            points_str = ";".join([f"{p['x']},{p['y']}" for p in points if isinstance(p, dict)])
            points_elem.set("points", points_str)
    
    def _add_track_element(self, root: ET.Element, item: DataItem, idx: int):
        """Add video track element."""
        track = ET.SubElement(root, "track")
        track.set("id", str(idx))
        
        annotations = item.annotations or []
        if annotations and isinstance(annotations[0], dict):
            track.set("label", annotations[0].get('label', 'object'))
        
        # Add frames
        for frame_idx, ann in enumerate(annotations):
            if isinstance(ann, dict):
                box = ET.SubElement(track, "box")
                box.set("frame", str(ann.get('frame', frame_idx)))
                box.set("xtl", str(ann.get('x', 0)))
                box.set("ytl", str(ann.get('y', 0)))
                box.set("xbr", str(ann.get('x', 0) + ann.get('width', 100)))
                box.set("ybr", str(ann.get('y', 0) + ann.get('height', 100)))
                box.set("outside", str(int(ann.get('outside', 0))))
                box.set("occluded", str(int(ann.get('occluded', 0))))
                box.set("keyframe", str(int(ann.get('keyframe', 1))))


class CVATImporter:
    """Import data from CVAT format."""
    
    def parse_xml(self, xml_content: bytes) -> Dict[str, Any]:
        """Parse CVAT XML format."""
        root = ET.fromstring(xml_content)
        
        result = {
            "version": None,
            "meta": {},
            "images": [],
            "tracks": []
        }
        
        # Parse version
        version_elem = root.find("version")
        if version_elem is not None:
            result["version"] = version_elem.text
        
        # Parse meta
        meta_elem = root.find("meta")
        if meta_elem is not None:
            task_elem = meta_elem.find("task")
            if task_elem is not None:
                result["meta"]["name"] = task_elem.findtext("name", "")
                result["meta"]["size"] = task_elem.findtext("size", "0")
                
                # Parse labels
                labels = []
                labels_elem = task_elem.find("labels")
                if labels_elem is not None:
                    for label_elem in labels_elem.findall("label"):
                        name = label_elem.findtext("name", "")
                        if name:
                            labels.append(name)
                result["meta"]["labels"] = labels
        
        # Parse images
        for image_elem in root.findall("image"):
            image_data = {
                "id": image_elem.get("id"),
                "name": image_elem.get("name"),
                "width": int(image_elem.get("width", 0)),
                "height": int(image_elem.get("height", 0)),
                "annotations": []
            }
            
            # Parse boxes
            for box in image_elem.findall("box"):
                image_data["annotations"].append({
                    "type": "box",
                    "label": box.get("label"),
                    "x": float(box.get("xtl", 0)),
                    "y": float(box.get("ytl", 0)),
                    "width": float(box.get("xbr", 0)) - float(box.get("xtl", 0)),
                    "height": float(box.get("ybr", 0)) - float(box.get("ytl", 0)),
                    "occluded": bool(int(box.get("occluded", 0)))
                })
            
            # Parse polygons
            for polygon in image_elem.findall("polygon"):
                points_str = polygon.get("points", "")
                points = []
                for pt in points_str.split(";"):
                    if "," in pt:
                        x, y = pt.split(",")
                        points.append({"x": float(x), "y": float(y)})
                
                image_data["annotations"].append({
                    "type": "polygon",
                    "label": polygon.get("label"),
                    "points": points
                })
            
            result["images"].append(image_data)
        
        # Parse tracks
        for track_elem in root.findall("track"):
            track_data = {
                "id": track_elem.get("id"),
                "label": track_elem.get("label"),
                "frames": []
            }
            
            for box in track_elem.findall("box"):
                track_data["frames"].append({
                    "frame": int(box.get("frame", 0)),
                    "x": float(box.get("xtl", 0)),
                    "y": float(box.get("ytl", 0)),
                    "width": float(box.get("xbr", 0)) - float(box.get("xtl", 0)),
                    "height": float(box.get("ybr", 0)) - float(box.get("ytl", 0)),
                    "outside": bool(int(box.get("outside", 0))),
                    "occluded": bool(int(box.get("occluded", 0))),
                    "keyframe": bool(int(box.get("keyframe", 1)))
                })
            
            result["tracks"].append(track_data)
        
        return result


class LabelboxExporter:
    """Export data to Labelbox format."""
    
    def export_project(
        self,
        items: List[DataItem],
        project_name: str,
        include_predictions: bool = False
    ) -> Tuple[bytes, str]:
        """
        Export project to Labelbox NDJSON format.
        
        Returns: (ndjson_content, filename)
        """
        lines = []
        
        for item in items:
            row = {
                "data_row": {
                    "external_id": str(item.id),
                    "row_data": item.file_path or item.content or ""
                },
                "media_attributes": self._get_media_attributes(item),
                "metadata_fields": []
            }
            
            # Add metadata
            if item.item_metadata:
                for key, value in item.item_metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        row["metadata_fields"].append({
                            "name": key,
                            "value": str(value)
                        })
            
            # Add labels/annotations
            if item.annotations:
                row["labels"] = self._convert_annotations(item.annotations, item.data_type)
            
            # Add predictions if requested
            if include_predictions and item.item_metadata:
                predictions = item.item_metadata.get("predictions", [])
                if predictions:
                    row["predictions"] = predictions
            
            lines.append(json.dumps(row))
        
        content = "\n".join(lines)
        return content.encode('utf-8'), f"{project_name}_labelbox.ndjson"
    
    def _get_media_attributes(self, item: DataItem) -> Dict[str, Any]:
        """Get media attributes for Labelbox."""
        attrs = {}
        metadata = item.item_metadata or {}
        
        if item.data_type == "image":
            attrs["mimeType"] = "image/jpeg"
            if "width" in metadata:
                attrs["width"] = metadata["width"]
            if "height" in metadata:
                attrs["height"] = metadata["height"]
        elif item.data_type == "video":
            attrs["mimeType"] = "video/mp4"
            if "duration" in metadata:
                attrs["duration"] = metadata["duration"]
        elif item.data_type == "audio":
            attrs["mimeType"] = "audio/mpeg"
        
        return attrs
    
    def _convert_annotations(
        self, 
        annotations: List[Dict],
        data_type: str
    ) -> List[Dict]:
        """Convert annotations to Labelbox format."""
        labels = []
        
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            
            label = {
                "id": str(uuid4()),
                "name": ann.get("label", "unknown")
            }
            
            ann_type = ann.get("type", "")
            
            if ann_type in ["box", "rectangle", "bounding_box"]:
                label["value"] = {
                    "bbox": {
                        "top": ann.get("y", ann.get("top", 0)),
                        "left": ann.get("x", ann.get("left", 0)),
                        "width": ann.get("width", 100),
                        "height": ann.get("height", 100)
                    }
                }
            elif ann_type == "polygon":
                points = ann.get("points", [])
                label["value"] = {
                    "polygon": [
                        {"x": p.get("x", 0), "y": p.get("y", 0)}
                        for p in points if isinstance(p, dict)
                    ]
                }
            elif ann_type == "point":
                label["value"] = {
                    "point": {
                        "x": ann.get("x", 0),
                        "y": ann.get("y", 0)
                    }
                }
            elif ann_type == "classification":
                label["value"] = {
                    "checklist": [ann.get("value", ann.get("label", ""))]
                }
            elif ann_type == "text":
                label["value"] = {
                    "text": ann.get("value", ann.get("text", ""))
                }
            else:
                # Generic annotation
                label["value"] = ann
            
            labels.append(label)
        
        return labels


class LabelboxImporter:
    """Import data from Labelbox format."""
    
    def parse_ndjson(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse Labelbox NDJSON format."""
        results = []
        
        for line in content.decode('utf-8').strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    parsed = self._parse_row(data)
                    results.append(parsed)
                except json.JSONDecodeError:
                    continue
        
        return results
    
    def _parse_row(self, data: Dict) -> Dict[str, Any]:
        """Parse a single Labelbox row."""
        result = {
            "external_id": data.get("data_row", {}).get("external_id"),
            "row_data": data.get("data_row", {}).get("row_data"),
            "metadata": {},
            "annotations": []
        }
        
        # Parse metadata
        for field in data.get("metadata_fields", []):
            if isinstance(field, dict):
                result["metadata"][field.get("name", "")] = field.get("value")
        
        # Parse labels
        for label in data.get("labels", []):
            if isinstance(label, dict):
                ann = self._parse_label(label)
                if ann:
                    result["annotations"].append(ann)
        
        return result
    
    def _parse_label(self, label: Dict) -> Optional[Dict]:
        """Parse a single Labelbox label."""
        value = label.get("value", {})
        name = label.get("name", "unknown")
        
        if "bbox" in value:
            bbox = value["bbox"]
            return {
                "type": "box",
                "label": name,
                "x": bbox.get("left", 0),
                "y": bbox.get("top", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0)
            }
        elif "polygon" in value:
            return {
                "type": "polygon",
                "label": name,
                "points": value["polygon"]
            }
        elif "point" in value:
            return {
                "type": "point",
                "label": name,
                "x": value["point"].get("x", 0),
                "y": value["point"].get("y", 0)
            }
        elif "text" in value:
            return {
                "type": "text",
                "label": name,
                "value": value["text"]
            }
        
        return None


class LabelStudioExporter:
    """Export data to Label Studio format."""
    
    def export_project(
        self,
        items: List[DataItem],
        project_name: str
    ) -> Tuple[bytes, str]:
        """Export to Label Studio JSON format."""
        tasks = []
        
        for idx, item in enumerate(items):
            task = {
                "id": idx + 1,
                "data": self._get_data(item),
                "annotations": [],
                "predictions": []
            }
            
            # Convert annotations
            if item.annotations:
                task["annotations"] = [{
                    "id": 1,
                    "completed_by": 1,
                    "result": self._convert_annotations(item.annotations, item.data_type)
                }]
            
            tasks.append(task)
        
        content = json.dumps(tasks, indent=2)
        return content.encode('utf-8'), f"{project_name}_label_studio.json"
    
    def _get_data(self, item: DataItem) -> Dict:
        """Get data field for Label Studio."""
        if item.data_type == "image":
            return {"image": item.file_path or ""}
        elif item.data_type == "audio":
            return {"audio": item.file_path or ""}
        elif item.data_type == "video":
            return {"video": item.file_path or ""}
        elif item.data_type == "text":
            return {"text": item.content or ""}
        else:
            return {"data": item.content or item.file_path or ""}
    
    def _convert_annotations(
        self, 
        annotations: List[Dict],
        data_type: str
    ) -> List[Dict]:
        """Convert to Label Studio result format."""
        results = []
        
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            
            ann_type = ann.get("type", "")
            
            if ann_type in ["box", "rectangle"]:
                results.append({
                    "id": str(uuid4())[:8],
                    "type": "rectanglelabels",
                    "from_name": "label",
                    "to_name": "image",
                    "value": {
                        "x": ann.get("x", 0) / 100,  # Label Studio uses percentages
                        "y": ann.get("y", 0) / 100,
                        "width": ann.get("width", 10) / 100,
                        "height": ann.get("height", 10) / 100,
                        "rectanglelabels": [ann.get("label", "unknown")]
                    }
                })
            elif ann_type == "polygon":
                points = ann.get("points", [])
                results.append({
                    "id": str(uuid4())[:8],
                    "type": "polygonlabels",
                    "from_name": "label",
                    "to_name": "image",
                    "value": {
                        "points": [[p.get("x", 0), p.get("y", 0)] for p in points],
                        "polygonlabels": [ann.get("label", "unknown")]
                    }
                })
            elif ann_type == "text" or data_type == "text":
                results.append({
                    "id": str(uuid4())[:8],
                    "type": "choices",
                    "from_name": "sentiment",
                    "to_name": "text",
                    "value": {
                        "choices": [ann.get("label", ann.get("value", "unknown"))]
                    }
                })
        
        return results


class AnnotationToolsService:
    """Main service for external annotation tools integration."""
    
    def __init__(self):
        self.cvat_exporter = CVATExporter()
        self.cvat_importer = CVATImporter()
        self.labelbox_exporter = LabelboxExporter()
        self.labelbox_importer = LabelboxImporter()
        self.label_studio_exporter = LabelStudioExporter()
    
    async def export_to_cvat(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Export project to CVAT format."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        # Get items
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items to export"}
        
        # Generate export
        xml_content, filename = self.cvat_exporter.export_project(
            items, project.name
        )
        
        # Store export
        storage_path = storage_service.upload_file(
            io.BytesIO(xml_content),
            filename,
            "application/xml",
            f"exports/{project_id}"
        )
        
        return {
            "format": "cvat",
            "items_count": len(items),
            "download_path": storage_path,
            "filename": filename
        }
    
    async def import_from_cvat(
        self,
        db: AsyncSession,
        project_id: UUID,
        xml_content: bytes
    ) -> Dict[str, Any]:
        """Import annotations from CVAT XML."""
        parsed = self.cvat_importer.parse_xml(xml_content)
        
        updated_count = 0
        
        # Update items with imported annotations
        for image_data in parsed.get("images", []):
            image_name = image_data.get("name", "")
            annotations = image_data.get("annotations", [])
            
            if not annotations:
                continue
            
            # Find matching item
            result = await db.execute(
                select(DataItem).where(
                    DataItem.project_id == project_id,
                    DataItem.name == image_name
                )
            )
            item = result.scalar_one_or_none()
            
            if item:
                item.annotations = annotations
                updated_count += 1
        
        await db.commit()
        
        return {
            "format": "cvat",
            "images_parsed": len(parsed.get("images", [])),
            "tracks_parsed": len(parsed.get("tracks", [])),
            "items_updated": updated_count
        }
    
    async def export_to_labelbox(
        self,
        db: AsyncSession,
        project_id: UUID,
        include_predictions: bool = False
    ) -> Dict[str, Any]:
        """Export project to Labelbox format."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items to export"}
        
        ndjson_content, filename = self.labelbox_exporter.export_project(
            items, project.name, include_predictions
        )
        
        storage_path = storage_service.upload_file(
            io.BytesIO(ndjson_content),
            filename,
            "application/x-ndjson",
            f"exports/{project_id}"
        )
        
        return {
            "format": "labelbox",
            "items_count": len(items),
            "download_path": storage_path,
            "filename": filename
        }
    
    async def import_from_labelbox(
        self,
        db: AsyncSession,
        project_id: UUID,
        ndjson_content: bytes
    ) -> Dict[str, Any]:
        """Import annotations from Labelbox NDJSON."""
        parsed = self.labelbox_importer.parse_ndjson(ndjson_content)
        
        updated_count = 0
        
        for row in parsed:
            external_id = row.get("external_id")
            annotations = row.get("annotations", [])
            
            if not external_id or not annotations:
                continue
            
            try:
                item_id = UUID(external_id)
                result = await db.execute(
                    select(DataItem).where(DataItem.id == item_id)
                )
                item = result.scalar_one_or_none()
                
                if item:
                    item.annotations = annotations
                    updated_count += 1
            except ValueError:
                continue
        
        await db.commit()
        
        return {
            "format": "labelbox",
            "rows_parsed": len(parsed),
            "items_updated": updated_count
        }
    
    async def export_to_label_studio(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Export project to Label Studio format."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items to export"}
        
        json_content, filename = self.label_studio_exporter.export_project(
            items, project.name
        )
        
        storage_path = storage_service.upload_file(
            io.BytesIO(json_content),
            filename,
            "application/json",
            f"exports/{project_id}"
        )
        
        return {
            "format": "label_studio",
            "items_count": len(items),
            "download_path": storage_path,
            "filename": filename
        }


# Global instance
annotation_tools_service = AnnotationToolsService()
