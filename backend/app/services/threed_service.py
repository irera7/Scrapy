"""3D Dataset Processing Service.

Supports:
- Point cloud processing
- Mesh handling (basic)
- 3D bounding box annotations
- Export to common 3D formats
"""
import json
import struct
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import io
import math
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class Point3D:
    """Represents a 3D point."""
    
    def __init__(
        self, 
        x: float, 
        y: float, 
        z: float,
        r: int = 255,
        g: int = 255,
        b: int = 255,
        intensity: float = 0.0,
        attributes: Dict[str, Any] = None
    ):
        self.x = x
        self.y = y
        self.z = z
        self.r = r
        self.g = g
        self.b = b
        self.intensity = intensity
        self.attributes = attributes or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "intensity": self.intensity,
            **self.attributes
        }
    
    def distance_to(self, other: "Point3D") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )


class BoundingBox3D:
    """Represents a 3D bounding box."""
    
    def __init__(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        length: float,
        width: float,
        height: float,
        rotation_z: float = 0.0,
        label: str = "",
        confidence: float = 1.0
    ):
        self.center_x = center_x
        self.center_y = center_y
        self.center_z = center_z
        self.length = length  # x dimension
        self.width = width    # y dimension
        self.height = height  # z dimension
        self.rotation_z = rotation_z  # yaw rotation
        self.label = label
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "center": [self.center_x, self.center_y, self.center_z],
            "dimensions": [self.length, self.width, self.height],
            "rotation_z": self.rotation_z,
            "label": self.label,
            "confidence": self.confidence
        }
    
    def get_corners(self) -> List[Tuple[float, float, float]]:
        """Get 8 corners of the bounding box."""
        cos_r = math.cos(self.rotation_z)
        sin_r = math.sin(self.rotation_z)
        
        l, w, h = self.length / 2, self.width / 2, self.height / 2
        
        corners = []
        for dz in [-h, h]:
            for dy in [-w, w]:
                for dx in [-l, l]:
                    # Rotate around z-axis
                    rx = dx * cos_r - dy * sin_r
                    ry = dx * sin_r + dy * cos_r
                    corners.append((
                        self.center_x + rx,
                        self.center_y + ry,
                        self.center_z + dz
                    ))
        
        return corners
    
    def volume(self) -> float:
        """Calculate volume of bounding box."""
        return self.length * self.width * self.height


class PointCloud:
    """Point cloud data structure."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.points: List[Point3D] = []
        self.bounding_boxes: List[BoundingBox3D] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_point(
        self,
        x: float,
        y: float,
        z: float,
        **kwargs
    ) -> Point3D:
        """Add a point to the cloud."""
        point = Point3D(x, y, z, **kwargs)
        self.points.append(point)
        return point
    
    def add_bounding_box(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        length: float,
        width: float,
        height: float,
        **kwargs
    ) -> BoundingBox3D:
        """Add a 3D bounding box annotation."""
        bbox = BoundingBox3D(
            center_x, center_y, center_z,
            length, width, height,
            **kwargs
        )
        self.bounding_boxes.append(bbox)
        return bbox
    
    def get_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Get min/max bounds of point cloud."""
        if not self.points:
            return {}
        
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        zs = [p.z for p in self.points]
        
        return {
            "x": (min(xs), max(xs)),
            "y": (min(ys), max(ys)),
            "z": (min(zs), max(zs))
        }
    
    def get_center(self) -> Tuple[float, float, float]:
        """Get center of point cloud."""
        if not self.points:
            return (0, 0, 0)
        
        n = len(self.points)
        return (
            sum(p.x for p in self.points) / n,
            sum(p.y for p in self.points) / n,
            sum(p.z for p in self.points) / n
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "num_points": len(self.points),
            "points": [p.to_dict() for p in self.points[:1000]],  # Limit for JSON
            "bounding_boxes": [b.to_dict() for b in self.bounding_boxes],
            "metadata": self.metadata,
            "bounds": self.get_bounds()
        }


class PointCloudAnalyzer:
    """Analyze point cloud data."""
    
    def compute_statistics(self, cloud: PointCloud) -> Dict[str, Any]:
        """Compute point cloud statistics."""
        if not cloud.points:
            return {"error": "Empty point cloud"}
        
        n = len(cloud.points)
        bounds = cloud.get_bounds()
        center = cloud.get_center()
        
        # Distance statistics
        distances_to_center = [
            math.sqrt(
                (p.x - center[0]) ** 2 +
                (p.y - center[1]) ** 2 +
                (p.z - center[2]) ** 2
            )
            for p in cloud.points
        ]
        
        avg_dist = sum(distances_to_center) / n
        max_dist = max(distances_to_center)
        
        # Density estimation
        volume = 1.0
        for axis in ['x', 'y', 'z']:
            if axis in bounds:
                volume *= (bounds[axis][1] - bounds[axis][0]) or 1
        
        density = n / volume if volume > 0 else 0
        
        # Color statistics if available
        has_color = any(
            p.r != 255 or p.g != 255 or p.b != 255 
            for p in cloud.points[:100]
        )
        
        return {
            "num_points": n,
            "bounds": bounds,
            "center": center,
            "volume": round(volume, 4),
            "density": round(density, 6),
            "avg_distance_to_center": round(avg_dist, 4),
            "max_distance_to_center": round(max_dist, 4),
            "has_color": has_color,
            "num_annotations": len(cloud.bounding_boxes)
        }
    
    def detect_ground_plane(
        self, 
        cloud: PointCloud,
        z_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """Detect ground plane (simple z-based method)."""
        if not cloud.points:
            return {"error": "Empty point cloud"}
        
        # Find lowest points
        z_values = sorted([p.z for p in cloud.points])
        
        # Ground is likely near minimum z
        min_z = z_values[0]
        ground_points = [p for p in cloud.points if p.z < min_z + z_threshold]
        
        if not ground_points:
            return {"found": False}
        
        avg_z = sum(p.z for p in ground_points) / len(ground_points)
        
        return {
            "found": True,
            "ground_z": round(avg_z, 4),
            "ground_points_count": len(ground_points),
            "ground_percentage": round(len(ground_points) / len(cloud.points) * 100, 2)
        }
    
    def segment_by_height(
        self,
        cloud: PointCloud,
        num_segments: int = 5
    ) -> List[Dict[str, Any]]:
        """Segment point cloud by height."""
        if not cloud.points:
            return []
        
        z_values = [p.z for p in cloud.points]
        min_z, max_z = min(z_values), max(z_values)
        
        if max_z == min_z:
            return [{"segment": 0, "z_range": [min_z, max_z], "count": len(cloud.points)}]
        
        segment_height = (max_z - min_z) / num_segments
        segments = []
        
        for i in range(num_segments):
            z_start = min_z + i * segment_height
            z_end = z_start + segment_height
            
            count = sum(1 for p in cloud.points if z_start <= p.z < z_end)
            
            segments.append({
                "segment": i,
                "z_range": [round(z_start, 4), round(z_end, 4)],
                "count": count,
                "percentage": round(count / len(cloud.points) * 100, 2)
            })
        
        return segments
    
    def compute_normals(
        self, 
        cloud: PointCloud, 
        k_neighbors: int = 10
    ) -> List[Tuple[float, float, float]]:
        """Estimate surface normals using k-nearest neighbors."""
        if not cloud.points or len(cloud.points) < k_neighbors:
            return []
        
        normals = []
        points_array = [(p.x, p.y, p.z) for p in cloud.points]
        
        for i, point in enumerate(cloud.points):
            # Find k nearest neighbors (simple distance)
            distances = []
            for j, other in enumerate(points_array):
                if i != j:
                    d = math.sqrt(
                        (point.x - other[0])**2 +
                        (point.y - other[1])**2 +
                        (point.z - other[2])**2
                    )
                    distances.append((d, j))
            
            distances.sort()
            neighbors = [points_array[j] for _, j in distances[:k_neighbors]]
            
            # Simple normal estimation using cross product of two vectors
            if len(neighbors) >= 2:
                v1 = (
                    neighbors[0][0] - point.x,
                    neighbors[0][1] - point.y,
                    neighbors[0][2] - point.z
                )
                v2 = (
                    neighbors[1][0] - point.x,
                    neighbors[1][1] - point.y,
                    neighbors[1][2] - point.z
                )
                
                # Cross product
                nx = v1[1] * v2[2] - v1[2] * v2[1]
                ny = v1[2] * v2[0] - v1[0] * v2[2]
                nz = v1[0] * v2[1] - v1[1] * v2[0]
                
                # Normalize
                length = math.sqrt(nx**2 + ny**2 + nz**2)
                if length > 0:
                    normals.append((nx/length, ny/length, nz/length))
                else:
                    normals.append((0, 0, 1))
            else:
                normals.append((0, 0, 1))
        
        return normals
    
    def downsample_voxel(
        self, 
        cloud: PointCloud, 
        voxel_size: float = 0.1
    ) -> PointCloud:
        """Downsample point cloud using voxel grid."""
        if not cloud.points:
            return cloud
        
        # Create voxel grid
        voxels = {}
        
        for point in cloud.points:
            # Compute voxel index
            vx = int(point.x / voxel_size)
            vy = int(point.y / voxel_size)
            vz = int(point.z / voxel_size)
            key = (vx, vy, vz)
            
            if key not in voxels:
                voxels[key] = []
            voxels[key].append(point)
        
        # Average points in each voxel
        downsampled = PointCloud(name=cloud.name + "_downsampled")
        
        for voxel_points in voxels.values():
            avg_x = sum(p.x for p in voxel_points) / len(voxel_points)
            avg_y = sum(p.y for p in voxel_points) / len(voxel_points)
            avg_z = sum(p.z for p in voxel_points) / len(voxel_points)
            avg_r = int(sum(p.r for p in voxel_points) / len(voxel_points))
            avg_g = int(sum(p.g for p in voxel_points) / len(voxel_points))
            avg_b = int(sum(p.b for p in voxel_points) / len(voxel_points))
            
            downsampled.add_point(avg_x, avg_y, avg_z, r=avg_r, g=avg_g, b=avg_b)
        
        return downsampled
    
    def remove_outliers(
        self, 
        cloud: PointCloud, 
        k_neighbors: int = 10,
        std_ratio: float = 2.0
    ) -> PointCloud:
        """Remove outliers using statistical analysis."""
        if not cloud.points or len(cloud.points) < k_neighbors:
            return cloud
        
        points_array = [(p.x, p.y, p.z) for p in cloud.points]
        
        # Compute mean distance to k nearest neighbors
        mean_distances = []
        
        for i, point in enumerate(cloud.points):
            distances = []
            for j, other in enumerate(points_array):
                if i != j:
                    d = math.sqrt(
                        (point.x - other[0])**2 +
                        (point.y - other[1])**2 +
                        (point.z - other[2])**2
                    )
                    distances.append(d)
            
            distances.sort()
            mean_dist = sum(distances[:k_neighbors]) / k_neighbors if distances else 0
            mean_distances.append(mean_dist)
        
        # Compute threshold
        global_mean = sum(mean_distances) / len(mean_distances)
        std_dev = math.sqrt(
            sum((d - global_mean)**2 for d in mean_distances) / len(mean_distances)
        )
        threshold = global_mean + std_ratio * std_dev
        
        # Filter points
        filtered = PointCloud(name=cloud.name + "_filtered")
        for i, point in enumerate(cloud.points):
            if mean_distances[i] <= threshold:
                filtered.add_point(
                    point.x, point.y, point.z,
                    r=point.r, g=point.g, b=point.b
                )
        
        return filtered


class ThreeDExporter:
    """Export 3D data to various formats."""
    
    def to_ply(self, cloud: PointCloud, binary: bool = False) -> bytes:
        """Export to PLY format."""
        header = [
            "ply",
            f"format {'binary_little_endian' if binary else 'ascii'} 1.0",
            f"element vertex {len(cloud.points)}",
            "property float x",
            "property float y",
            "property float z",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "end_header"
        ]
        
        if binary:
            content = "\n".join(header) + "\n"
            content = content.encode('ascii')
            
            for p in cloud.points:
                content += struct.pack(
                    '<fffBBB',
                    p.x, p.y, p.z, p.r, p.g, p.b
                )
            return content
        else:
            lines = header.copy()
            for p in cloud.points:
                lines.append(f"{p.x} {p.y} {p.z} {p.r} {p.g} {p.b}")
            return "\n".join(lines).encode('ascii')
    
    def to_pcd(self, cloud: PointCloud) -> str:
        """Export to PCD format (Point Cloud Data)."""
        lines = [
            "# .PCD v0.7 - Point Cloud Data file format",
            "VERSION 0.7",
            "FIELDS x y z rgb",
            "SIZE 4 4 4 4",
            "TYPE F F F U",
            "COUNT 1 1 1 1",
            f"WIDTH {len(cloud.points)}",
            "HEIGHT 1",
            "VIEWPOINT 0 0 0 1 0 0 0",
            f"POINTS {len(cloud.points)}",
            "DATA ascii"
        ]
        
        for p in cloud.points:
            # Pack RGB into single int
            rgb = (p.r << 16) | (p.g << 8) | p.b
            lines.append(f"{p.x} {p.y} {p.z} {rgb}")
        
        return "\n".join(lines)
    
    def to_xyz(self, cloud: PointCloud) -> str:
        """Export to XYZ format (simple text)."""
        lines = []
        for p in cloud.points:
            lines.append(f"{p.x} {p.y} {p.z}")
        return "\n".join(lines)
    
    def to_kitti(self, boxes: List[BoundingBox3D]) -> str:
        """Export bounding boxes to KITTI format."""
        lines = []
        for box in boxes:
            # KITTI format: type truncated occluded alpha bbox3d dimensions location rotation_y
            line = f"{box.label} 0 0 0 0 0 0 0 {box.height} {box.width} {box.length} {box.center_x} {box.center_y} {box.center_z} {box.rotation_z}"
            lines.append(line)
        return "\n".join(lines)


class ThreeDService:
    """Main service for 3D data processing."""
    
    def __init__(self):
        self.analyzer = PointCloudAnalyzer()
        self.exporter = ThreeDExporter()
    
    async def parse_point_cloud(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Parse point cloud from item data."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": "Item not found"}
        
        cloud = PointCloud(name=item.name or "")
        
        # Try to parse from content or metadata
        if item.content:
            try:
                data = json.loads(item.content)
                if isinstance(data, list):
                    for pt in data[:10000]:  # Limit
                        if isinstance(pt, dict):
                            cloud.add_point(
                                pt.get('x', 0),
                                pt.get('y', 0),
                                pt.get('z', 0),
                                r=pt.get('r', 255),
                                g=pt.get('g', 255),
                                b=pt.get('b', 255)
                            )
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                            cloud.add_point(pt[0], pt[1], pt[2])
            except json.JSONDecodeError:
                pass
        
        # Try metadata
        if not cloud.points and item.item_metadata:
            points_data = item.item_metadata.get('points', [])
            for pt in points_data[:10000]:
                if isinstance(pt, dict):
                    cloud.add_point(
                        pt.get('x', 0),
                        pt.get('y', 0),
                        pt.get('z', 0)
                    )
        
        # Parse annotations as bounding boxes
        if item.annotations:
            for ann in item.annotations:
                if isinstance(ann, dict) and 'center' in ann:
                    center = ann['center']
                    dims = ann.get('dimensions', [1, 1, 1])
                    cloud.add_bounding_box(
                        center[0], center[1], center[2],
                        dims[0], dims[1], dims[2],
                        rotation_z=ann.get('rotation_z', 0),
                        label=ann.get('label', '')
                    )
        
        stats = self.analyzer.compute_statistics(cloud)
        
        return {
            "cloud": cloud.to_dict(),
            "statistics": stats
        }
    
    async def analyze_3d_data(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Analyze all 3D data in project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == "3d"
            )
        )
        items = result.scalars().all()
        
        if not items:
            # Try items with 3D metadata
            result = await db.execute(
                select(DataItem).where(DataItem.project_id == project_id)
            )
            items = [
                i for i in result.scalars().all()
                if i.item_metadata and 'points' in i.item_metadata
            ]
        
        total_points = 0
        total_annotations = 0
        all_labels = set()
        
        for item in items:
            cloud_result = await self.parse_point_cloud(db, item.id)
            if "error" not in cloud_result:
                stats = cloud_result.get("statistics", {})
                total_points += stats.get("num_points", 0)
                total_annotations += stats.get("num_annotations", 0)
                
                for box in cloud_result.get("cloud", {}).get("bounding_boxes", []):
                    if box.get("label"):
                        all_labels.add(box["label"])
        
        return {
            "items_count": len(items),
            "total_points": total_points,
            "total_annotations": total_annotations,
            "unique_labels": list(all_labels),
            "avg_points_per_item": total_points // len(items) if items else 0
        }
    
    async def export_3d(
        self,
        db: AsyncSession,
        item_id: UUID,
        format: str = "ply"
    ) -> Dict[str, Any]:
        """Export 3D data to specified format."""
        cloud_result = await self.parse_point_cloud(db, item_id)
        
        if "error" in cloud_result:
            return cloud_result
        
        cloud_data = cloud_result["cloud"]
        
        # Reconstruct cloud
        cloud = PointCloud(name=cloud_data.get("name", ""))
        for pt in cloud_data.get("points", []):
            cloud.add_point(
                pt.get("x", 0),
                pt.get("y", 0),
                pt.get("z", 0),
                r=pt.get("r", 255),
                g=pt.get("g", 255),
                b=pt.get("b", 255)
            )
        
        # Reconstruct bboxes
        for box in cloud_data.get("bounding_boxes", []):
            center = box.get("center", [0, 0, 0])
            dims = box.get("dimensions", [1, 1, 1])
            cloud.add_bounding_box(
                center[0], center[1], center[2],
                dims[0], dims[1], dims[2],
                rotation_z=box.get("rotation_z", 0),
                label=box.get("label", "")
            )
        
        # Export
        if format == "ply":
            content = self.exporter.to_ply(cloud)
            ext = "ply"
            mime = "application/octet-stream"
        elif format == "pcd":
            content = self.exporter.to_pcd(cloud).encode('utf-8')
            ext = "pcd"
            mime = "text/plain"
        elif format == "xyz":
            content = self.exporter.to_xyz(cloud).encode('utf-8')
            ext = "xyz"
            mime = "text/plain"
        elif format == "kitti":
            content = self.exporter.to_kitti(cloud.bounding_boxes).encode('utf-8')
            ext = "txt"
            mime = "text/plain"
        else:
            return {"error": f"Unsupported format: {format}"}
        
        filename = f"3d_export_{item_id}.{ext}"
        storage_path = storage_service.upload_file(
            io.BytesIO(content),
            filename,
            mime,
            f"exports/3d"
        )
        
        return {
            "format": format,
            "download_path": storage_path,
            "filename": filename,
            "points": len(cloud.points),
            "annotations": len(cloud.bounding_boxes)
        }


# Global instance
threed_service = ThreeDService()
