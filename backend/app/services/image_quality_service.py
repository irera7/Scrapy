"""Image Quality and Analysis Service."""
import io
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import structlog
import numpy as np

from PIL import Image, ExifTags
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class ExifExtractor:
    """Extract and parse EXIF metadata from images."""
    
    EXIF_TAGS = {
        'Make': 'camera_make',
        'Model': 'camera_model',
        'DateTime': 'date_time',
        'DateTimeOriginal': 'date_original',
        'ExposureTime': 'exposure_time',
        'FNumber': 'f_number',
        'ISOSpeedRatings': 'iso',
        'FocalLength': 'focal_length',
        'Flash': 'flash',
        'WhiteBalance': 'white_balance',
        'ExposureMode': 'exposure_mode',
        'MeteringMode': 'metering_mode',
        'Software': 'software',
        'Artist': 'artist',
        'Copyright': 'copyright',
        'ImageDescription': 'description',
        'Orientation': 'orientation',
        'XResolution': 'x_resolution',
        'YResolution': 'y_resolution',
        'ResolutionUnit': 'resolution_unit',
    }
    
    GPS_TAGS = {
        'GPSLatitude': 'latitude',
        'GPSLongitude': 'longitude',
        'GPSAltitude': 'altitude',
        'GPSLatitudeRef': 'latitude_ref',
        'GPSLongitudeRef': 'longitude_ref',
    }
    
    def extract_exif(self, image: Image.Image) -> Dict[str, Any]:
        """Extract all EXIF data from image."""
        result = {
            "has_exif": False,
            "camera": {},
            "settings": {},
            "gps": {},
            "other": {}
        }
        
        try:
            exif_data = image._getexif()
            if not exif_data:
                return result
            
            result["has_exif"] = True
            
            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                
                # Process value
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        continue
                
                # Camera info
                if tag_name in ('Make', 'Model', 'Software'):
                    result["camera"][tag_name.lower()] = str(value)
                
                # Settings
                elif tag_name in ('ExposureTime', 'FNumber', 'ISOSpeedRatings', 
                                  'FocalLength', 'Flash', 'WhiteBalance'):
                    if tag_name == 'ExposureTime' and hasattr(value, 'numerator'):
                        value = f"{value.numerator}/{value.denominator}s"
                    elif tag_name == 'FNumber' and hasattr(value, 'numerator'):
                        value = round(value.numerator / value.denominator, 1)
                    elif tag_name == 'FocalLength' and hasattr(value, 'numerator'):
                        value = f"{round(value.numerator / value.denominator)}mm"
                    result["settings"][tag_name.lower()] = value
                
                # Date/Time
                elif 'DateTime' in tag_name or 'Date' in tag_name:
                    result["other"][tag_name.lower()] = str(value)
                
                # GPS
                elif tag_name.startswith('GPS'):
                    result["gps"][tag_name] = value
            
            # Parse GPS coordinates if available
            if result["gps"]:
                coords = self._parse_gps(result["gps"])
                if coords:
                    result["gps"] = coords
            
        except Exception as e:
            logger.warning(f"EXIF extraction error: {e}")
        
        return result
    
    def _parse_gps(self, gps_data: Dict) -> Optional[Dict[str, float]]:
        """Parse GPS coordinates from EXIF."""
        try:
            lat = gps_data.get('GPSLatitude')
            lat_ref = gps_data.get('GPSLatitudeRef', 'N')
            lon = gps_data.get('GPSLongitude')
            lon_ref = gps_data.get('GPSLongitudeRef', 'E')
            
            if lat and lon:
                lat_deg = self._dms_to_decimal(lat)
                lon_deg = self._dms_to_decimal(lon)
                
                if lat_ref == 'S':
                    lat_deg = -lat_deg
                if lon_ref == 'W':
                    lon_deg = -lon_deg
                
                return {
                    "latitude": round(lat_deg, 6),
                    "longitude": round(lon_deg, 6),
                    "altitude": gps_data.get('GPSAltitude')
                }
        except Exception:
            pass
        
        return None
    
    def _dms_to_decimal(self, dms) -> float:
        """Convert degrees, minutes, seconds to decimal."""
        if hasattr(dms[0], 'numerator'):
            d = dms[0].numerator / dms[0].denominator
            m = dms[1].numerator / dms[1].denominator
            s = dms[2].numerator / dms[2].denominator
        else:
            d, m, s = float(dms[0]), float(dms[1]), float(dms[2])
        
        return d + m / 60 + s / 3600


class ColorAnalyzer:
    """Analyze color properties of images."""
    
    def compute_histogram(
        self, 
        image: Image.Image,
        bins: int = 256
    ) -> Dict[str, Any]:
        """Compute color histogram."""
        result = {}
        
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            # Compute histograms for each channel
            for i, channel in enumerate(['red', 'green', 'blue']):
                hist, _ = np.histogram(img_array[:, :, i], bins=bins, range=(0, 256))
                result[channel] = {
                    "histogram": hist.tolist(),
                    "mean": float(np.mean(img_array[:, :, i])),
                    "std": float(np.std(img_array[:, :, i])),
                    "min": int(np.min(img_array[:, :, i])),
                    "max": int(np.max(img_array[:, :, i]))
                }
            
            # Overall statistics
            result["brightness"] = float(np.mean(img_array))
            result["contrast"] = float(np.std(img_array))
            
            # Dominant colors (simple clustering)
            result["dominant_colors"] = self._find_dominant_colors(img_array, n_colors=5)
            
        except Exception as e:
            logger.warning(f"Histogram computation error: {e}")
        
        return result
    
    def _find_dominant_colors(
        self, 
        img_array: np.ndarray, 
        n_colors: int = 5
    ) -> List[Dict[str, Any]]:
        """Find dominant colors using simple clustering."""
        try:
            # Reshape to pixel list
            pixels = img_array.reshape(-1, 3)
            
            # Sample for performance
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            
            # Simple k-means clustering
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = []
            for i, center in enumerate(kmeans.cluster_centers_):
                count = np.sum(kmeans.labels_ == i)
                percentage = count / len(pixels) * 100
                
                r, g, b = int(center[0]), int(center[1]), int(center[2])
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                
                colors.append({
                    "rgb": [r, g, b],
                    "hex": hex_color,
                    "percentage": round(percentage, 1)
                })
            
            # Sort by percentage
            colors.sort(key=lambda x: x["percentage"], reverse=True)
            return colors
            
        except ImportError:
            # Fallback without sklearn
            return []
        except Exception as e:
            logger.warning(f"Dominant color error: {e}")
            return []
    
    def analyze_color_palette(
        self, 
        image: Image.Image
    ) -> Dict[str, Any]:
        """Analyze overall color palette characteristics."""
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            # Calculate color statistics
            r_mean = np.mean(img_array[:, :, 0])
            g_mean = np.mean(img_array[:, :, 1])
            b_mean = np.mean(img_array[:, :, 2])
            
            # Determine color temperature
            if r_mean > b_mean * 1.2:
                temperature = "warm"
            elif b_mean > r_mean * 1.2:
                temperature = "cool"
            else:
                temperature = "neutral"
            
            # Saturation (simple estimation)
            hsv = self._rgb_to_hsv_array(img_array)
            saturation = float(np.mean(hsv[:, :, 1]))
            
            # Brightness
            brightness = float(np.mean(hsv[:, :, 2]))
            
            return {
                "temperature": temperature,
                "saturation": round(saturation, 3),
                "brightness": round(brightness, 3),
                "is_grayscale": saturation < 0.1,
                "is_dark": brightness < 0.3,
                "is_bright": brightness > 0.7,
                "channel_means": {
                    "red": round(r_mean, 1),
                    "green": round(g_mean, 1),
                    "blue": round(b_mean, 1)
                }
            }
            
        except Exception as e:
            logger.warning(f"Palette analysis error: {e}")
            return {}
    
    def _rgb_to_hsv_array(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB array to HSV."""
        rgb = rgb.astype(float) / 255.0
        
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        
        v = np.maximum(np.maximum(r, g), b)
        c = v - np.minimum(np.minimum(r, g), b)
        
        s = np.where(v != 0, c / v, 0)
        
        h = np.zeros_like(v)
        
        return np.stack([h, s, v], axis=2)


class ImageSimilarityFinder:
    """Find similar images using perceptual hashing."""
    
    def __init__(self):
        self._imagehash_available = False
        try:
            import imagehash
            self._imagehash_available = True
        except ImportError:
            logger.info("imagehash not available, using fallback")
    
    def compute_hashes(self, image: Image.Image) -> Dict[str, str]:
        """Compute multiple perceptual hashes for an image."""
        if not self._imagehash_available:
            # Fallback to simple hash
            img_bytes = image.tobytes()
            return {
                "md5": hashlib.md5(img_bytes).hexdigest(),
                "sha256": hashlib.sha256(img_bytes).hexdigest()[:32]
            }
        
        try:
            import imagehash
            
            # Resize for consistent hashing
            img_resized = image.copy()
            img_resized.thumbnail((256, 256))
            
            if img_resized.mode != 'RGB':
                img_resized = img_resized.convert('RGB')
            
            return {
                "phash": str(imagehash.phash(img_resized)),
                "dhash": str(imagehash.dhash(img_resized)),
                "whash": str(imagehash.whash(img_resized)),
                "colorhash": str(imagehash.colorhash(img_resized))
            }
            
        except Exception as e:
            logger.warning(f"Hash computation error: {e}")
            return {}
    
    def compute_similarity(
        self, 
        hash1: Dict[str, str], 
        hash2: Dict[str, str]
    ) -> float:
        """Compute similarity between two hash sets."""
        if not self._imagehash_available:
            # Simple exact match
            return 1.0 if hash1 == hash2 else 0.0
        
        try:
            import imagehash
            
            similarities = []
            
            for hash_type in ['phash', 'dhash', 'whash']:
                if hash_type in hash1 and hash_type in hash2:
                    h1 = imagehash.hex_to_hash(hash1[hash_type])
                    h2 = imagehash.hex_to_hash(hash2[hash_type])
                    
                    # Hamming distance to similarity
                    distance = h1 - h2
                    max_distance = 64  # For 8x8 hash
                    sim = 1 - (distance / max_distance)
                    similarities.append(sim)
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception:
            return 0.0


class ImageQualityService:
    """Main service for image quality analysis."""
    
    def __init__(self):
        self.exif_extractor = ExifExtractor()
        self.color_analyzer = ColorAnalyzer()
        self.similarity_finder = ImageSimilarityFinder()
    
    async def extract_full_exif(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Extract and store full EXIF data for an image."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "image":
            return {"error": "Image item not found"}
        
        if not item.file_path:
            return {"error": "No image file"}
        
        try:
            image_data = storage_service.download_file(item.file_path)
            image = Image.open(io.BytesIO(image_data))
            
            exif = self.exif_extractor.extract_exif(image)
            
            # Store in metadata
            metadata = item.item_metadata or {}
            metadata["exif"] = exif
            item.item_metadata = metadata
            await db.commit()
            
            return exif
            
        except Exception as e:
            logger.error(f"EXIF extraction error: {e}")
            return {"error": str(e)}
    
    async def analyze_colors(
        self,
        db: AsyncSession,
        item_id: UUID,
        include_histogram: bool = True
    ) -> Dict[str, Any]:
        """Analyze colors in an image."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "image":
            return {"error": "Image item not found"}
        
        try:
            image_data = storage_service.download_file(item.file_path)
            image = Image.open(io.BytesIO(image_data))
            
            result = {}
            
            # Palette analysis
            result["palette"] = self.color_analyzer.analyze_color_palette(image)
            
            # Histogram (optional, can be large)
            if include_histogram:
                hist = self.color_analyzer.compute_histogram(image)
                result["dominant_colors"] = hist.get("dominant_colors", [])
                result["brightness"] = hist.get("brightness")
                result["contrast"] = hist.get("contrast")
            
            # Store in metadata
            metadata = item.item_metadata or {}
            metadata["color_analysis"] = result
            item.item_metadata = metadata
            await db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Color analysis error: {e}")
            return {"error": str(e)}
    
    async def compute_image_hash(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Compute and store perceptual hashes for an image."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.data_type != "image":
            return {"error": "Image item not found"}
        
        try:
            image_data = storage_service.download_file(item.file_path)
            image = Image.open(io.BytesIO(image_data))
            
            hashes = self.similarity_finder.compute_hashes(image)
            
            # Store in metadata
            metadata = item.item_metadata or {}
            metadata["image_hashes"] = hashes
            metadata["hash_computed_at"] = datetime.utcnow().isoformat()
            item.item_metadata = metadata
            await db.commit()
            
            return {"hashes": hashes}
            
        except Exception as e:
            logger.error(f"Hash computation error: {e}")
            return {"error": str(e)}
    
    async def find_similar_images(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.9
    ) -> Dict[str, Any]:
        """Find similar images in a project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == "image"
            )
        )
        items = result.scalars().all()
        
        # Compute hashes for items without them
        items_with_hash = []
        for item in items:
            metadata = item.item_metadata or {}
            if "image_hashes" not in metadata:
                hash_result = await self.compute_image_hash(db, item.id)
                if "hashes" in hash_result:
                    items_with_hash.append((item, hash_result["hashes"]))
            else:
                items_with_hash.append((item, metadata["image_hashes"]))
        
        # Find similar pairs
        similar_pairs = []
        checked = set()
        
        for i, (item1, hashes1) in enumerate(items_with_hash):
            for j, (item2, hashes2) in enumerate(items_with_hash[i+1:], i+1):
                pair_key = tuple(sorted([str(item1.id), str(item2.id)]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)
                
                similarity = self.similarity_finder.compute_similarity(hashes1, hashes2)
                
                if similarity >= similarity_threshold:
                    similar_pairs.append({
                        "item1_id": str(item1.id),
                        "item2_id": str(item2.id),
                        "similarity": round(similarity, 4),
                        "is_duplicate": similarity > 0.98
                    })
        
        return {
            "total_images": len(items),
            "analyzed": len(items_with_hash),
            "similar_pairs": len(similar_pairs),
            "pairs": similar_pairs
        }
    
    async def batch_analyze_project(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Batch analyze all images in a project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == "image"
            )
        )
        items = result.scalars().all()
        
        results = {
            "total": len(items),
            "analyzed": 0,
            "with_exif": 0,
            "with_gps": 0,
            "color_summary": {
                "warm": 0,
                "cool": 0,
                "neutral": 0
            },
            "issues": []
        }
        
        for item in items:
            try:
                # Extract EXIF
                exif = await self.extract_full_exif(db, item.id)
                if exif.get("has_exif"):
                    results["with_exif"] += 1
                if exif.get("gps"):
                    results["with_gps"] += 1
                
                # Analyze colors
                colors = await self.analyze_colors(db, item.id, include_histogram=False)
                temp = colors.get("palette", {}).get("temperature")
                if temp in results["color_summary"]:
                    results["color_summary"][temp] += 1
                
                results["analyzed"] += 1
                
            except Exception as e:
                logger.warning(f"Analysis failed for {item.id}: {e}")
        
        return results


# Global instance
image_quality_service = ImageQualityService()
