"""Image Processing Service."""
import io
from typing import Dict, Any, Optional, Tuple, List
from uuid import UUID
import structlog
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class ImageProcessor:
    """Image processing utilities."""
    
    # Common image sizes for ML
    PRESET_SIZES = {
        "thumbnail": (128, 128),
        "small": (256, 256),
        "medium": (512, 512),
        "large": (1024, 1024),
        "imagenet": (224, 224),
        "yolo": (640, 640),
        "efficientnet": (300, 300),
    }
    
    def load_image(self, file_data: bytes) -> Image.Image:
        """Load image from bytes."""
        return Image.open(io.BytesIO(file_data))
    
    def save_image(
        self, 
        image: Image.Image, 
        format: str = "PNG",
        quality: int = 95
    ) -> bytes:
        """Save image to bytes."""
        buffer = io.BytesIO()
        
        # Convert RGBA to RGB for JPEG
        if format.upper() == "JPEG" and image.mode == "RGBA":
            image = image.convert("RGB")
        
        image.save(buffer, format=format, quality=quality)
        return buffer.getvalue()
    
    def get_image_info(self, image: Image.Image) -> Dict[str, Any]:
        """Get image metadata."""
        info = {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
            "is_animated": getattr(image, "is_animated", False),
        }
        
        # Calculate aspect ratio
        info["aspect_ratio"] = round(image.width / max(image.height, 1), 3)
        
        # Check if grayscale
        info["is_grayscale"] = image.mode in ("L", "LA", "1")
        
        # Check for transparency
        info["has_alpha"] = image.mode in ("RGBA", "LA", "PA")
        
        # EXIF data
        if hasattr(image, '_getexif') and image._getexif():
            try:
                exif = image._getexif()
                if exif:
                    info["has_exif"] = True
                    # Extract common EXIF tags
                    exif_tags = {}
                    for tag_id, value in exif.items():
                        from PIL.ExifTags import TAGS
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ('Make', 'Model', 'DateTime', 'Software'):
                            exif_tags[tag] = str(value)
                    if exif_tags:
                        info["exif"] = exif_tags
            except Exception:
                pass
        
        return info
    
    def resize(
        self, 
        image: Image.Image, 
        size: Tuple[int, int],
        method: str = "fit"
    ) -> Image.Image:
        """
        Resize image.
        
        Methods:
        - fit: Resize to fit within size, maintaining aspect ratio
        - fill: Resize to fill size, cropping if necessary
        - stretch: Stretch to exact size
        - pad: Resize to fit and pad with color
        """
        if method == "fit":
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return image
        
        elif method == "fill":
            # Resize and center crop
            target_ratio = size[0] / size[1]
            current_ratio = image.width / image.height
            
            if current_ratio > target_ratio:
                # Image is wider, resize by height
                new_height = size[1]
                new_width = int(new_height * current_ratio)
            else:
                # Image is taller, resize by width
                new_width = size[0]
                new_height = int(new_width / current_ratio)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (new_width - size[0]) // 2
            top = (new_height - size[1]) // 2
            return image.crop((left, top, left + size[0], top + size[1]))
        
        elif method == "stretch":
            return image.resize(size, Image.Resampling.LANCZOS)
        
        elif method == "pad":
            # Resize to fit and pad
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create new image with padding
            new_image = Image.new(image.mode, size, (0, 0, 0))
            paste_x = (size[0] - image.width) // 2
            paste_y = (size[1] - image.height) // 2
            new_image.paste(image, (paste_x, paste_y))
            return new_image
        
        return image
    
    def crop(
        self, 
        image: Image.Image, 
        box: Tuple[int, int, int, int]
    ) -> Image.Image:
        """Crop image. Box is (left, top, right, bottom)."""
        return image.crop(box)
    
    def center_crop(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Center crop to specified size."""
        left = (image.width - size[0]) // 2
        top = (image.height - size[1]) // 2
        return image.crop((left, top, left + size[0], top + size[1]))
    
    def rotate(self, image: Image.Image, angle: float, expand: bool = True) -> Image.Image:
        """Rotate image."""
        return image.rotate(angle, expand=expand, resample=Image.Resampling.BICUBIC)
    
    def flip(self, image: Image.Image, direction: str = "horizontal") -> Image.Image:
        """Flip image horizontally or vertically."""
        if direction == "horizontal":
            return ImageOps.mirror(image)
        elif direction == "vertical":
            return ImageOps.flip(image)
        return image
    
    def convert_mode(self, image: Image.Image, mode: str) -> Image.Image:
        """Convert image mode (RGB, L, RGBA, etc.)."""
        return image.convert(mode)
    
    def to_grayscale(self, image: Image.Image) -> Image.Image:
        """Convert to grayscale."""
        return image.convert("L")
    
    def normalize(self, image: Image.Image) -> Image.Image:
        """Normalize image (auto-contrast)."""
        return ImageOps.autocontrast(image)
    
    def enhance(
        self, 
        image: Image.Image, 
        brightness: float = 1.0,
        contrast: float = 1.0,
        sharpness: float = 1.0,
        color: float = 1.0
    ) -> Image.Image:
        """Enhance image properties."""
        if brightness != 1.0:
            image = ImageEnhance.Brightness(image).enhance(brightness)
        if contrast != 1.0:
            image = ImageEnhance.Contrast(image).enhance(contrast)
        if sharpness != 1.0:
            image = ImageEnhance.Sharpness(image).enhance(sharpness)
        if color != 1.0:
            image = ImageEnhance.Color(image).enhance(color)
        return image
    
    def apply_filter(self, image: Image.Image, filter_name: str) -> Image.Image:
        """Apply a filter to the image."""
        filters = {
            "blur": ImageFilter.BLUR,
            "sharpen": ImageFilter.SHARPEN,
            "edge_enhance": ImageFilter.EDGE_ENHANCE,
            "emboss": ImageFilter.EMBOSS,
            "contour": ImageFilter.CONTOUR,
            "detail": ImageFilter.DETAIL,
            "smooth": ImageFilter.SMOOTH,
        }
        
        if filter_name in filters:
            return image.filter(filters[filter_name])
        return image
    
    def compute_hash(self, image: Image.Image, hash_type: str = "md5") -> str:
        """Compute image hash for deduplication."""
        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        data = buffer.getvalue()
        
        if hash_type == "md5":
            return hashlib.md5(data).hexdigest()
        elif hash_type == "sha256":
            return hashlib.sha256(data).hexdigest()
        
        # Perceptual hash (simple version)
        elif hash_type == "phash":
            # Resize to 8x8
            small = image.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(small.getdata())
            avg = sum(pixels) / len(pixels)
            # Create binary hash
            bits = ''.join('1' if p > avg else '0' for p in pixels)
            return hex(int(bits, 2))[2:]
        
        return hashlib.md5(data).hexdigest()
    
    async def run_ocr(self, image: Image.Image, lang: str = "eng") -> str:
        """Run OCR on image using Tesseract."""
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except ImportError:
            logger.warning("pytesseract not installed")
            return ""
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""
    
    def generate_thumbnail(
        self, 
        image: Image.Image, 
        size: Tuple[int, int] = (256, 256)
    ) -> Image.Image:
        """Generate thumbnail."""
        thumb = image.copy()
        thumb.thumbnail(size, Image.Resampling.LANCZOS)
        return thumb


# Global instance
image_processor = ImageProcessor()


async def process_image_item(
    item: DataItem, 
    db: AsyncSession, 
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Process an image data item."""
    options = options or {}
    result = {}
    
    if not item.file_path:
        return {"error": "No file path"}
    
    try:
        # Download image
        image_data = storage_service.download_file(item.file_path)
        image = image_processor.load_image(image_data)
        
        # Get info
        info = image_processor.get_image_info(image)
        metadata = item.item_metadata or {}
        metadata.update(info)
        item.item_metadata = metadata
        result["info"] = info
        
        # Resize if requested
        if options.get("resize"):
            size = options["resize"]
            if isinstance(size, str) and size in image_processor.PRESET_SIZES:
                size = image_processor.PRESET_SIZES[size]
            method = options.get("resize_method", "fit")
            image = image_processor.resize(image, tuple(size), method)
            result["resized"] = True
        
        # Convert format
        if options.get("convert_format"):
            target_format = options["convert_format"].upper()
            image_data = image_processor.save_image(image, format=target_format)
            
            # Upload new version
            new_path = item.file_path.rsplit('.', 1)[0] + f".{target_format.lower()}"
            storage_service.upload_file(
                io.BytesIO(image_data),
                new_path.split('/')[-1],
                f"image/{target_format.lower()}",
                '/'.join(new_path.split('/')[:-1])
            )
            item.file_path = new_path
            item.mime_type = f"image/{target_format.lower()}"
            result["converted"] = target_format
        
        # Generate thumbnail
        if options.get("generate_thumbnail", True):
            thumb = image_processor.generate_thumbnail(image)
            thumb_data = image_processor.save_image(thumb, "JPEG", 85)
            
            thumb_folder = f"projects/{item.project_id}/thumbnails"
            thumb_name = f"thumb_{item.id}.jpg"
            thumb_path = storage_service.upload_file(
                io.BytesIO(thumb_data),
                thumb_name,
                "image/jpeg",
                thumb_folder
            )
            metadata = item.item_metadata or {}
            metadata["thumbnail_path"] = thumb_path
            item.item_metadata = metadata
            result["thumbnail"] = thumb_path
        
        # Compute hash
        if options.get("compute_hash", True):
            img_hash = image_processor.compute_hash(image, "phash")
            metadata = item.item_metadata or {}
            metadata["phash"] = img_hash
            item.item_metadata = metadata
            result["hash"] = img_hash
        
        # OCR
        if options.get("run_ocr", False):
            ocr_lang = options.get("ocr_language", "eng")
            text = await image_processor.run_ocr(image, ocr_lang)
            if text:
                metadata = item.item_metadata or {}
                metadata["ocr_text"] = text
                item.item_metadata = metadata
                result["ocr_text"] = text[:500]  # Limit for response
        
        # Enhancement
        if options.get("enhance"):
            enhance_opts = options["enhance"]
            image = image_processor.enhance(
                image,
                brightness=enhance_opts.get("brightness", 1.0),
                contrast=enhance_opts.get("contrast", 1.0),
                sharpness=enhance_opts.get("sharpness", 1.0),
            )
            result["enhanced"] = True
        
        # Save processed image if modified
        if any(key in options for key in ["resize", "enhance", "convert_format"]):
            processed_data = image_processor.save_image(
                image, 
                options.get("output_format", "PNG")
            )
            # Upload processed version
            processed_folder = f"projects/{item.project_id}/processed"
            processed_name = f"processed_{item.id}.{options.get('output_format', 'png').lower()}"
            processed_path = storage_service.upload_file(
                io.BytesIO(processed_data),
                processed_name,
                f"image/{options.get('output_format', 'png').lower()}",
                processed_folder
            )
            metadata = item.item_metadata or {}
            metadata["processed_path"] = processed_path
            item.item_metadata = metadata
            result["processed_path"] = processed_path
        
        item.is_processed = True
        await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return {"error": str(e)}

