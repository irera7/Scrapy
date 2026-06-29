"""Video Quality and Duplicate Detection Service."""
import os
import tempfile
import subprocess
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import structlog
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class VideoHasher:
    """Generate perceptual hashes for video comparison."""
    
    def __init__(self):
        self._imagehash_available = False
        self._cv2_available = False
        
        try:
            import imagehash
            self._imagehash_available = True
        except ImportError:
            logger.info("imagehash not available")
        
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            logger.info("OpenCV not available")
    
    def extract_frames_for_hash(
        self, 
        video_path: str, 
        num_frames: int = 8
    ) -> List[bytes]:
        """Extract evenly spaced frames for hashing."""
        frames = []
        
        if self._cv2_available:
            try:
                import cv2
                cap = cv2.VideoCapture(video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                if total_frames == 0:
                    cap.release()
                    return []
                
                # Get evenly spaced frame indices
                indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
                
                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret:
                        # Resize to standard size for consistent hashing
                        frame = cv2.resize(frame, (64, 64))
                        _, buffer = cv2.imencode('.jpg', frame)
                        frames.append(buffer.tobytes())
                
                cap.release()
                
            except Exception as e:
                logger.warning(f"Frame extraction error: {e}")
        
        return frames
    
    def compute_frame_hash(self, frame_data: bytes) -> Optional[str]:
        """Compute perceptual hash for a single frame."""
        if not self._imagehash_available:
            # Fallback to MD5
            return hashlib.md5(frame_data).hexdigest()
        
        try:
            import imagehash
            from PIL import Image
            import io
            
            img = Image.open(io.BytesIO(frame_data))
            
            # Compute multiple hash types for robustness
            phash = imagehash.phash(img)
            dhash = imagehash.dhash(img)
            
            return f"{phash}_{dhash}"
            
        except Exception as e:
            logger.warning(f"Hash computation error: {e}")
            return None
    
    def compute_video_hash(self, video_path: str) -> Dict[str, Any]:
        """
        Compute perceptual hash for entire video.
        
        Returns hash based on multiple keyframes.
        """
        frames = self.extract_frames_for_hash(video_path, num_frames=8)
        
        if not frames:
            return {"error": "Could not extract frames"}
        
        frame_hashes = []
        for frame in frames:
            h = self.compute_frame_hash(frame)
            if h:
                frame_hashes.append(h)
        
        if not frame_hashes:
            return {"error": "Could not compute hashes"}
        
        # Create combined hash
        combined = "_".join(frame_hashes)
        video_hash = hashlib.sha256(combined.encode()).hexdigest()[:32]
        
        return {
            "video_hash": video_hash,
            "frame_hashes": frame_hashes,
            "frames_analyzed": len(frame_hashes)
        }
    
    def compute_hash_similarity(
        self, 
        hash1: str, 
        hash2: str
    ) -> float:
        """Compute similarity between two hashes (0-1)."""
        if not self._imagehash_available:
            return 1.0 if hash1 == hash2 else 0.0
        
        try:
            import imagehash
            
            # Parse combined hash
            parts1 = hash1.split("_")
            parts2 = hash2.split("_")
            
            if len(parts1) != len(parts2):
                return 0.0
            
            similarities = []
            for p1, p2 in zip(parts1, parts2):
                try:
                    h1 = imagehash.hex_to_hash(p1)
                    h2 = imagehash.hex_to_hash(p2)
                    # Hamming distance to similarity
                    distance = h1 - h2
                    max_distance = 64  # Max for 8x8 hash
                    sim = 1 - (distance / max_distance)
                    similarities.append(sim)
                except:
                    continue
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception:
            return 1.0 if hash1 == hash2 else 0.0


class SceneDetector:
    """Advanced scene detection for videos."""
    
    def __init__(self):
        self._cv2_available = False
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            pass
    
    def detect_scenes_opencv(
        self, 
        video_path: str,
        threshold: float = 30.0,
        min_scene_length: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Detect scene changes using OpenCV histogram comparison."""
        if not self._cv2_available:
            return []
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            
            scenes = []
            prev_hist = None
            scene_start = 0
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Compute histogram
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                cv2.normalize(hist, hist)
                
                if prev_hist is not None:
                    # Compare histograms
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                    
                    current_time = frame_idx / fps
                    
                    if diff > threshold / 100:
                        scene_duration = current_time - scene_start
                        
                        if scene_duration >= min_scene_length:
                            scenes.append({
                                "start_time": scene_start,
                                "end_time": current_time,
                                "duration": scene_duration,
                                "change_score": round(diff, 4)
                            })
                        
                        scene_start = current_time
                
                prev_hist = hist.copy()
                frame_idx += 1
            
            # Add final scene
            total_duration = frame_idx / fps
            if total_duration - scene_start >= min_scene_length:
                scenes.append({
                    "start_time": scene_start,
                    "end_time": total_duration,
                    "duration": total_duration - scene_start,
                    "change_score": 0
                })
            
            cap.release()
            return scenes
            
        except Exception as e:
            logger.warning(f"Scene detection error: {e}")
            return []
    
    def detect_scenes_ffmpeg(
        self, 
        video_path: str,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Detect scene changes using FFmpeg."""
        try:
            result = subprocess.run([
                'ffprobe',
                '-v', 'quiet',
                '-show_frames',
                '-select_streams', 'v',
                '-of', 'json',
                '-f', 'lavfi',
                f'movie={video_path},select=gt(scene\\,{threshold})'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                scenes = []
                
                for frame in data.get('frames', []):
                    if 'pkt_pts_time' in frame:
                        scenes.append({
                            "time": float(frame['pkt_pts_time']),
                            "score": float(frame.get('tags', {}).get('lavfi.scene_score', 0))
                        })
                
                return scenes
            
        except Exception as e:
            logger.warning(f"FFmpeg scene detection error: {e}")
        
        return []


class VideoQualityAnalyzer:
    """Analyze video quality metrics."""
    
    def __init__(self):
        self._cv2_available = False
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            pass
    
    def analyze_quality(self, video_path: str) -> Dict[str, Any]:
        """Comprehensive video quality analysis."""
        result = {
            "blur_score": None,
            "brightness_avg": None,
            "contrast_avg": None,
            "frame_stability": None,
            "quality_grade": "unknown"
        }
        
        if not self._cv2_available:
            return result
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            
            blur_scores = []
            brightness_values = []
            contrast_values = []
            prev_gray = None
            motion_scores = []
            
            frame_count = 0
            sample_interval = 10  # Sample every 10th frame
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                if frame_count % sample_interval != 0:
                    continue
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Blur detection (Laplacian variance)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                blur_scores.append(laplacian_var)
                
                # Brightness
                brightness = np.mean(gray)
                brightness_values.append(brightness)
                
                # Contrast
                contrast = np.std(gray)
                contrast_values.append(contrast)
                
                # Motion/stability
                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    motion_scores.append(np.mean(diff))
                
                prev_gray = gray
            
            cap.release()
            
            if blur_scores:
                avg_blur = np.mean(blur_scores)
                result["blur_score"] = round(avg_blur, 2)
                result["is_blurry"] = avg_blur < 100
            
            if brightness_values:
                result["brightness_avg"] = round(np.mean(brightness_values), 2)
                result["brightness_std"] = round(np.std(brightness_values), 2)
            
            if contrast_values:
                result["contrast_avg"] = round(np.mean(contrast_values), 2)
            
            if motion_scores:
                result["frame_stability"] = round(100 - np.mean(motion_scores), 2)
                result["camera_shake"] = np.mean(motion_scores) > 20
            
            # Calculate quality grade
            score = 0
            if result.get("blur_score", 0) > 100:
                score += 25
            if 50 < result.get("brightness_avg", 0) < 200:
                score += 25
            if result.get("contrast_avg", 0) > 30:
                score += 25
            if result.get("frame_stability", 0) > 80:
                score += 25
            
            if score >= 75:
                result["quality_grade"] = "excellent"
            elif score >= 50:
                result["quality_grade"] = "good"
            elif score >= 25:
                result["quality_grade"] = "fair"
            else:
                result["quality_grade"] = "poor"
            
            result["quality_score"] = score
            result["frames_analyzed"] = len(blur_scores)
            
        except Exception as e:
            logger.warning(f"Quality analysis error: {e}")
        
        return result


class ThumbnailGenerator:
    """Generate smart thumbnails for videos."""
    
    def __init__(self):
        self.quality_analyzer = VideoQualityAnalyzer()
    
    async def generate_smart_thumbnail(
        self,
        video_path: str,
        output_path: str,
        size: Tuple[int, int] = (320, 180)
    ) -> Dict[str, Any]:
        """
        Generate thumbnail from the best quality frame.
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            
            best_frame = None
            best_score = -1
            best_time = 0
            
            # Sample frames at regular intervals
            sample_count = min(20, total_frames // 10)
            indices = np.linspace(
                int(total_frames * 0.1),  # Skip first 10%
                int(total_frames * 0.9),  # Skip last 10%
                sample_count, 
                dtype=int
            )
            
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Score based on: sharpness, brightness, contrast
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                brightness = np.mean(gray)
                contrast = np.std(gray)
                
                # Penalize too dark or too bright
                brightness_penalty = abs(brightness - 127) / 127
                
                score = sharpness * (1 - brightness_penalty * 0.5) + contrast
                
                if score > best_score:
                    best_score = score
                    best_frame = frame
                    best_time = idx / fps
            
            cap.release()
            
            if best_frame is not None:
                # Resize and save
                resized = cv2.resize(best_frame, size)
                cv2.imwrite(output_path, resized)
                
                return {
                    "success": True,
                    "time_offset": round(best_time, 2),
                    "quality_score": round(best_score, 2)
                }
            
            return {"error": "No suitable frame found"}
            
        except Exception as e:
            logger.error(f"Smart thumbnail error: {e}")
            return {"error": str(e)}
    
    async def generate_thumbnail_grid(
        self,
        video_path: str,
        output_path: str,
        grid_size: Tuple[int, int] = (3, 3),
        thumb_size: Tuple[int, int] = (160, 90)
    ) -> Dict[str, Any]:
        """Generate a grid of thumbnails from video."""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            num_thumbs = grid_size[0] * grid_size[1]
            indices = np.linspace(0, total_frames - 1, num_thumbs, dtype=int)
            
            frames = []
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    resized = cv2.resize(frame, thumb_size)
                    frames.append(resized)
            
            cap.release()
            
            if len(frames) < num_thumbs:
                return {"error": "Not enough frames extracted"}
            
            # Create grid
            rows = []
            for i in range(grid_size[1]):
                row = np.hstack(frames[i * grid_size[0]:(i + 1) * grid_size[0]])
                rows.append(row)
            
            grid = np.vstack(rows)
            cv2.imwrite(output_path, grid)
            
            return {
                "success": True,
                "grid_size": grid_size,
                "thumbnails_count": len(frames)
            }
            
        except Exception as e:
            logger.error(f"Thumbnail grid error: {e}")
            return {"error": str(e)}


class VideoQualityService:
    """Main service for video quality and duplicate detection."""
    
    def __init__(self):
        self.hasher = VideoHasher()
        self.scene_detector = SceneDetector()
        self.quality_analyzer = VideoQualityAnalyzer()
        self.thumbnail_gen = ThumbnailGenerator()
    
    async def compute_video_hash(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Compute and store perceptual hash for a video item."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "video":
            return {"error": "Video item not found"}
        
        if not item.file_path:
            return {"error": "No video file"}
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Download video
            video_data = storage_service.download_file(item.file_path)
            ext = item.file_path.rsplit('.', 1)[-1]
            temp_file = os.path.join(temp_dir, f"video.{ext}")
            
            with open(temp_file, 'wb') as f:
                f.write(video_data)
            
            # Compute hash
            hash_result = self.hasher.compute_video_hash(temp_file)
            
            if "error" not in hash_result:
                # Store in metadata
                metadata = item.item_metadata or {}
                metadata["video_hash"] = hash_result["video_hash"]
                metadata["frame_hashes"] = hash_result["frame_hashes"]
                metadata["hash_computed_at"] = datetime.utcnow().isoformat()
                item.item_metadata = metadata
                await db.commit()
            
            return hash_result
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def find_duplicate_videos(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """Find duplicate videos in a project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == "video"
            )
        )
        items = result.scalars().all()
        
        # Compute hashes for items without them
        items_with_hash = []
        for item in items:
            metadata = item.item_metadata or {}
            if "video_hash" not in metadata:
                # Compute hash
                hash_result = await self.compute_video_hash(db, item.id)
                if "video_hash" in hash_result:
                    items_with_hash.append((item, hash_result["frame_hashes"]))
            else:
                items_with_hash.append((item, metadata.get("frame_hashes", [])))
        
        # Find duplicates
        duplicates = []
        checked = set()
        
        for i, (item1, hashes1) in enumerate(items_with_hash):
            if not hashes1:
                continue
            
            for j, (item2, hashes2) in enumerate(items_with_hash[i+1:], i+1):
                if not hashes2:
                    continue
                
                pair_key = tuple(sorted([str(item1.id), str(item2.id)]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)
                
                # Compare hashes
                similarities = []
                for h1, h2 in zip(hashes1, hashes2):
                    sim = self.hasher.compute_hash_similarity(h1, h2)
                    similarities.append(sim)
                
                avg_similarity = sum(similarities) / len(similarities) if similarities else 0
                
                if avg_similarity >= similarity_threshold:
                    duplicates.append({
                        "item1_id": str(item1.id),
                        "item2_id": str(item2.id),
                        "similarity": round(avg_similarity, 4),
                        "is_exact": avg_similarity > 0.99
                    })
        
        return {
            "total_videos": len(items),
            "analyzed": len(items_with_hash),
            "duplicate_pairs": len(duplicates),
            "duplicates": duplicates
        }
    
    async def detect_scenes(
        self,
        db: AsyncSession,
        item_id: UUID,
        threshold: float = 0.3,
        min_scene_length: float = 1.0
    ) -> Dict[str, Any]:
        """Detect scenes in a video."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "video":
            return {"error": "Video item not found"}
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            video_data = storage_service.download_file(item.file_path)
            ext = item.file_path.rsplit('.', 1)[-1]
            temp_file = os.path.join(temp_dir, f"video.{ext}")
            
            with open(temp_file, 'wb') as f:
                f.write(video_data)
            
            # Try OpenCV first, fallback to FFmpeg
            scenes = self.scene_detector.detect_scenes_opencv(
                temp_file, threshold * 100, min_scene_length
            )
            
            if not scenes:
                scenes = self.scene_detector.detect_scenes_ffmpeg(temp_file, threshold)
            
            # Store in metadata
            metadata = item.item_metadata or {}
            metadata["scenes"] = scenes
            metadata["scene_count"] = len(scenes)
            item.item_metadata = metadata
            await db.commit()
            
            return {
                "scene_count": len(scenes),
                "scenes": scenes,
                "total_duration": scenes[-1].get("end_time", 0) if scenes else 0
            }
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def analyze_video_quality(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Analyze video quality metrics."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "video":
            return {"error": "Video item not found"}
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            video_data = storage_service.download_file(item.file_path)
            ext = item.file_path.rsplit('.', 1)[-1]
            temp_file = os.path.join(temp_dir, f"video.{ext}")
            
            with open(temp_file, 'wb') as f:
                f.write(video_data)
            
            quality = self.quality_analyzer.analyze_quality(temp_file)
            
            # Store in metadata
            metadata = item.item_metadata or {}
            metadata["quality_analysis"] = quality
            item.item_metadata = metadata
            await db.commit()
            
            return quality
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def generate_smart_thumbnail(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Generate a smart thumbnail for a video."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "video":
            return {"error": "Video item not found"}
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            video_data = storage_service.download_file(item.file_path)
            ext = item.file_path.rsplit('.', 1)[-1]
            temp_file = os.path.join(temp_dir, f"video.{ext}")
            thumb_path = os.path.join(temp_dir, "thumbnail.jpg")
            
            with open(temp_file, 'wb') as f:
                f.write(video_data)
            
            result = await self.thumbnail_gen.generate_smart_thumbnail(
                temp_file, thumb_path
            )
            
            if result.get("success"):
                # Upload thumbnail
                with open(thumb_path, 'rb') as f:
                    thumb_data = f.read()
                
                import io
                storage_path = storage_service.upload_file(
                    io.BytesIO(thumb_data),
                    f"smart_thumb_{item.id}.jpg",
                    "image/jpeg",
                    f"projects/{item.project_id}/thumbnails"
                )
                
                metadata = item.item_metadata or {}
                metadata["smart_thumbnail_path"] = storage_path
                metadata["thumbnail_time_offset"] = result.get("time_offset")
                item.item_metadata = metadata
                await db.commit()
                
                result["thumbnail_path"] = storage_path
            
            return result
            
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def batch_analyze_project(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Batch analyze all videos in a project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == "video"
            )
        )
        items = result.scalars().all()
        
        results = {
            "total": len(items),
            "analyzed": 0,
            "quality_summary": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0
            },
            "issues": []
        }
        
        for item in items:
            try:
                quality = await self.analyze_video_quality(db, item.id)
                
                grade = quality.get("quality_grade", "unknown")
                if grade in results["quality_summary"]:
                    results["quality_summary"][grade] += 1
                
                if quality.get("is_blurry"):
                    results["issues"].append({
                        "item_id": str(item.id),
                        "issue": "blurry"
                    })
                
                if quality.get("camera_shake"):
                    results["issues"].append({
                        "item_id": str(item.id),
                        "issue": "camera_shake"
                    })
                
                results["analyzed"] += 1
                
            except Exception as e:
                logger.warning(f"Analysis failed for {item.id}: {e}")
        
        return results


# Global instance
video_quality_service = VideoQualityService()
