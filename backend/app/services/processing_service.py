from uuid import UUID
import structlog
import re
from bs4 import BeautifulSoup
import chardet

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.storage import storage_service
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


async def process_item(item_id: str, processing_type: str) -> dict:
    """Process a data item."""
    engine, db = create_worker_session()
    
    try:
        result = await db.execute(
            select(DataItem).where(DataItem.id == UUID(item_id))
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError(f"Item not found: {item_id}")
        
        if processing_type == "clean_text":
            await process_text(item, db)
        elif processing_type == "extract_text_from_html":
            await extract_text_from_html(item, db)
        elif processing_type == "detect_language":
            await detect_language(item, db)
        elif processing_type == "compute_quality":
            await compute_quality_score(item, db)
        elif processing_type == "process_image":
            await process_image(item, db)
        
        item.is_processed = True
        await db.commit()
        
        return {"success": True, "item_id": item_id}
    
    finally:
        # Always clean up: close session and dispose engine
        await db.close()
        await engine.dispose()


async def process_text(item: DataItem, db: AsyncSession):
    """Clean and normalize text content."""
    if not item.content:
        return
    
    text = item.content
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize unicode
    import unicodedata
    text = unicodedata.normalize('NFKC', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    item.content = text
    
    # Update metadata
    metadata = item.item_metadata or {}
    metadata["processed"] = True
    metadata["char_count"] = len(text)
    metadata["word_count"] = len(text.split())
    item.item_metadata = metadata


async def extract_text_from_html(item: DataItem, db: AsyncSession):
    """Extract clean text from HTML content."""
    if not item.content:
        return
    
    soup = BeautifulSoup(item.content, 'lxml')
    
    # Remove script, style, and other non-content elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
        element.decompose()
    
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = '\n'.join(lines)
    
    item.content = text
    
    # Update metadata
    metadata = item.item_metadata or {}
    metadata["extracted_from_html"] = True
    item.item_metadata = metadata


async def detect_language(item: DataItem, db: AsyncSession):
    """Detect the language of text content."""
    if not item.content or len(item.content) < 20:
        return
    
    try:
        # Use a simple heuristic or external library
        # For production, use langdetect or fasttext
        from langdetect import detect, detect_langs
        
        lang = detect(item.content)
        langs = detect_langs(item.content)
        
        metadata = item.item_metadata or {}
        metadata["language"] = lang
        metadata["language_confidence"] = [
            {"lang": str(l.lang), "prob": l.prob}
            for l in langs[:3]
        ]
        item.item_metadata = metadata
    
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")


async def compute_quality_score(item: DataItem, db: AsyncSession):
    """Compute a quality score for the data item."""
    score = 1.0
    
    if item.data_type == "text":
        if not item.content:
            score = 0.0
        else:
            text = item.content
            
            # Penalize very short content
            if len(text) < 50:
                score *= 0.5
            elif len(text) < 100:
                score *= 0.7
            
            # Penalize excessive special characters
            special_ratio = len(re.findall(r'[^a-zA-Z0-9\s\u0600-\u06FF]', text)) / max(len(text), 1)
            if special_ratio > 0.3:
                score *= 0.6
            
            # Penalize repetitive content
            words = text.lower().split()
            if words:
                unique_ratio = len(set(words)) / len(words)
                if unique_ratio < 0.3:
                    score *= 0.5
            
            # Boost for having labels
            if item.labels and len(item.labels) > 0:
                score = min(score * 1.1, 1.0)
    
    elif item.data_type == "image":
        if not item.file_path and not item.source_url:
            score = 0.0
        else:
            # Check file size
            if item.file_size:
                if item.file_size < 1000:  # Less than 1KB
                    score *= 0.3
                elif item.file_size < 10000:  # Less than 10KB
                    score *= 0.7
            
            # Boost for having labels
            if item.labels and len(item.labels) > 0:
                score = min(score * 1.1, 1.0)
    
    item.quality_score = round(score, 2)


async def process_image(item: DataItem, db: AsyncSession):
    """Process an image file."""
    if not item.file_path:
        return
    
    try:
        from PIL import Image
        import io
        
        # Download image
        image_data = storage_service.download_file(item.file_path)
        image = Image.open(io.BytesIO(image_data))
        
        # Get metadata
        metadata = item.item_metadata or {}
        metadata["width"] = image.width
        metadata["height"] = image.height
        metadata["format"] = image.format
        metadata["mode"] = image.mode
        
        # Check for EXIF data
        if hasattr(image, '_getexif') and image._getexif():
            exif = image._getexif()
            if exif:
                metadata["has_exif"] = True
        
        item.item_metadata = metadata
        
    except Exception as e:
        logger.warning(f"Image processing failed: {e}")

