"""ML Integration Service for Scraping Pipeline.

This service integrates ML features into the scraping process:
1. Auto-labeling during scraping
2. Smart deduplication with embeddings
3. Quality filtering before saving
"""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import re
import structlog
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.data_item import DataItem
from app.models.project import Project

logger = structlog.get_logger()


class AutoLabeler:
    """Auto-labeling system for scraped data."""
    
    # Keyword-based classification rules
    KEYWORD_RULES = {
        # Sentiment
        "positive": ["excellent", "amazing", "great", "wonderful", "fantastic", "love", "perfect", "best", "عالی", "فوق‌العاده", "بهترین"],
        "negative": ["terrible", "awful", "horrible", "worst", "hate", "bad", "poor", "افتضاح", "بد", "ضعیف"],
        
        # Topics
        "technology": ["software", "hardware", "ai", "machine learning", "programming", "tech", "computer", "نرم‌افزار", "هوش مصنوعی"],
        "business": ["company", "market", "stock", "finance", "investment", "economy", "شرکت", "بازار", "سرمایه"],
        "health": ["medical", "health", "doctor", "hospital", "medicine", "treatment", "پزشکی", "سلامت", "درمان"],
        "sports": ["game", "team", "player", "championship", "football", "basketball", "ورزش", "بازی", "تیم"],
        "education": ["university", "school", "student", "learning", "course", "teacher", "دانشگاه", "مدرسه", "آموزش"],
        "entertainment": ["movie", "music", "celebrity", "show", "actor", "singer", "فیلم", "موسیقی", "سینما"],
        "science": ["research", "study", "experiment", "scientist", "discovery", "تحقیق", "علم", "کشف"],
        "politics": ["government", "election", "president", "minister", "policy", "دولت", "انتخابات", "سیاست"],
    }
    
    # Data type specific patterns
    IMAGE_PATTERNS = {
        "portrait": ["face", "person", "portrait", "headshot", "selfie"],
        "landscape": ["nature", "mountain", "ocean", "forest", "sunset", "sunrise"],
        "product": ["product", "item", "merchandise", "goods"],
        "document": ["document", "paper", "text", "scan"],
        "chart": ["chart", "graph", "diagram", "infographic"],
        "screenshot": ["screenshot", "screen", "capture", "ui"],
    }
    
    @classmethod
    def extract_labels_from_text(cls, text: str) -> List[str]:
        """Extract labels from text content using keyword matching."""
        if not text:
            return []
        
        text_lower = text.lower()
        labels = []
        
        for label, keywords in cls.KEYWORD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    labels.append(label)
                    break
        
        return list(set(labels))
    
    @classmethod
    def extract_labels_from_url(cls, url: str) -> List[str]:
        """Extract labels from URL patterns."""
        if not url:
            return []
        
        url_lower = url.lower()
        labels = []
        
        # URL path patterns
        path_patterns = {
            "news": ["/news/", "/article/", "/post/", "/blog/"],
            "product": ["/product/", "/item/", "/shop/", "/buy/"],
            "video": ["/video/", "/watch/", "youtube.com", "vimeo.com"],
            "image": ["/image/", "/photo/", "/gallery/", "imgur.com", "flickr.com"],
            "social": ["twitter.com", "facebook.com", "instagram.com", "linkedin.com"],
            "forum": ["/forum/", "/discussion/", "reddit.com", "/thread/"],
            "documentation": ["/docs/", "/documentation/", "/api/", "/reference/"],
        }
        
        for label, patterns in path_patterns.items():
            for pattern in patterns:
                if pattern in url_lower:
                    labels.append(label)
                    break
        
        return list(set(labels))
    
    @classmethod
    def extract_labels_from_metadata(cls, metadata: Dict[str, Any]) -> List[str]:
        """Extract labels from metadata fields."""
        if not metadata:
            return []
        
        labels = []
        
        # Check common metadata fields
        label_fields = ['labels', 'tags', 'categories', 'keywords', 'topics', 'genre', 'type']
        
        for field in label_fields:
            if field in metadata:
                value = metadata[field]
                if isinstance(value, list):
                    labels.extend([str(v) for v in value if v])
                elif isinstance(value, str) and value:
                    # Handle comma-separated values
                    if ',' in value:
                        labels.extend([v.strip() for v in value.split(',') if v.strip()])
                    else:
                        labels.append(value)
        
        # Check for primary_category (e.g., from arxiv)
        if 'primary_category' in metadata and metadata['primary_category']:
            labels.append(str(metadata['primary_category']))
        
        # Check for content type
        if 'content_type' in metadata:
            labels.append(metadata['content_type'])
        
        return list(set(labels))
    
    @classmethod
    def extract_labels_from_image(cls, metadata: Dict[str, Any], source_url: str = None) -> List[str]:
        """Extract labels for image data from metadata and URL."""
        labels = []
        
        # Check metadata for image-specific fields
        if metadata:
            if 'alt_text' in metadata:
                alt_labels = cls.extract_labels_from_text(metadata['alt_text'])
                labels.extend(alt_labels)
            
            if 'title' in metadata:
                title_labels = cls.extract_labels_from_text(metadata['title'])
                labels.extend(title_labels)
            
            if 'description' in metadata:
                desc_labels = cls.extract_labels_from_text(metadata['description'])
                labels.extend(desc_labels)
        
        # Check URL for image type patterns
        if source_url:
            url_lower = source_url.lower()
            for label, patterns in cls.IMAGE_PATTERNS.items():
                for pattern in patterns:
                    if pattern in url_lower:
                        labels.append(f"image_{label}")
                        break
        
        return list(set(labels))
    
    @classmethod
    def auto_label(
        cls,
        content: str = None,
        source_url: str = None,
        metadata: Dict[str, Any] = None,
        data_type: str = "text"
    ) -> Tuple[List[str], float]:
        """
        Auto-label data and return labels with confidence score.
        
        Returns:
            Tuple of (labels, confidence_score)
        """
        all_labels = []
        
        # Extract from metadata (highest priority)
        if metadata:
            meta_labels = cls.extract_labels_from_metadata(metadata)
            all_labels.extend(meta_labels)
        
        # Extract from content
        if content:
            content_labels = cls.extract_labels_from_text(content)
            all_labels.extend(content_labels)
        
        # Extract from URL
        if source_url:
            url_labels = cls.extract_labels_from_url(source_url)
            all_labels.extend(url_labels)
        
        # Data type specific extraction
        if data_type == "image":
            image_labels = cls.extract_labels_from_image(metadata, source_url)
            all_labels.extend(image_labels)
        
        # Remove duplicates while preserving order
        unique_labels = list(dict.fromkeys(all_labels))
        
        # Calculate confidence based on number of sources that agree
        confidence = min(len(unique_labels) * 0.2, 1.0) if unique_labels else 0.0
        
        return unique_labels, confidence


class QualityFilter:
    """Quality filtering for scraped data before saving."""
    
    # Minimum thresholds
    MIN_TEXT_LENGTH = 20
    MIN_WORDS = 3
    MAX_DUPLICATE_RATIO = 0.5
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'buy now',
        r'click here',
        r'free money',
        r'winner',
        r'congratulations.*won',
        r'limited time offer',
        r'act now',
        r'100% free',
        r'make money fast',
        r'work from home',
        r'no experience needed',
    ]
    
    # Low quality patterns
    LOW_QUALITY_PATTERNS = [
        r'^[\s\n]*$',  # Empty or whitespace only
        r'^[^\w]*$',  # No alphanumeric characters
        r'^(.)\1{10,}',  # Repeated characters
        r'^(lorem ipsum|test|asdf|qwerty)',  # Placeholder text
    ]
    
    @classmethod
    def check_text_quality(cls, text: str) -> Tuple[bool, str, float]:
        """
        Check text quality.
        
        Returns:
            Tuple of (is_valid, reason, quality_score)
        """
        if not text:
            return False, "empty_content", 0.0
        
        text_stripped = text.strip()
        
        # Check minimum length
        if len(text_stripped) < cls.MIN_TEXT_LENGTH:
            return False, "too_short", 0.1
        
        # Check minimum words
        words = text_stripped.split()
        if len(words) < cls.MIN_WORDS:
            return False, "too_few_words", 0.1
        
        # Check for low quality patterns
        for pattern in cls.LOW_QUALITY_PATTERNS:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                return False, "low_quality_pattern", 0.2
        
        # Check for spam patterns
        spam_count = 0
        for pattern in cls.SPAM_PATTERNS:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                spam_count += 1
        
        if spam_count >= 2:
            return False, "spam_detected", 0.1
        
        # Calculate quality score
        quality_score = cls.calculate_text_quality_score(text_stripped)
        
        if quality_score < 0.3:
            return False, "low_quality_score", quality_score
        
        return True, "passed", quality_score
    
    @classmethod
    def calculate_text_quality_score(cls, text: str) -> float:
        """Calculate quality score for text (0-1)."""
        score = 0.0
        
        # Length score (up to 0.3)
        length_score = min(len(text) / 500, 0.3)
        score += length_score
        
        # Word diversity score (up to 0.3)
        words = text.lower().split()
        if words:
            unique_ratio = len(set(words)) / len(words)
            score += unique_ratio * 0.3
        
        # Sentence structure score (up to 0.2)
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_length = len(words) / len(sentences)
            # Good sentences are between 5-30 words
            if 5 <= avg_sentence_length <= 30:
                score += 0.2
            elif avg_sentence_length > 0:
                score += 0.1
        
        # Punctuation score (up to 0.1)
        punctuation_count = len(re.findall(r'[.,!?;:،؛]', text))
        punctuation_ratio = punctuation_count / max(len(words), 1)
        if 0.05 <= punctuation_ratio <= 0.3:
            score += 0.1
        
        # No spam patterns (up to 0.1)
        has_spam = any(re.search(p, text, re.IGNORECASE) for p in cls.SPAM_PATTERNS)
        if not has_spam:
            score += 0.1
        
        return min(score, 1.0)
    
    @classmethod
    def check_image_quality(cls, metadata: Dict[str, Any]) -> Tuple[bool, str, float]:
        """
        Check image quality based on metadata.
        
        Returns:
            Tuple of (is_valid, reason, quality_score)
        """
        if not metadata:
            return True, "no_metadata", 0.5
        
        score = 0.5  # Base score
        
        # Check dimensions
        width = metadata.get('width', 0) or metadata.get('image_width', 0)
        height = metadata.get('height', 0) or metadata.get('image_height', 0)
        
        try:
            width = int(str(width).replace('px', '').strip() or 0)
            height = int(str(height).replace('px', '').strip() or 0)
        except (ValueError, TypeError):
            width, height = 0, 0
        
        # Reject very small images (likely icons/placeholders)
        if width > 0 and height > 0:
            if width < 50 or height < 50:
                return False, "too_small", 0.1
            
            if width < 100 or height < 100:
                score = 0.3
            elif width >= 500 and height >= 500:
                score = 0.8
            else:
                score = 0.6
        
        # Check file size
        file_size = metadata.get('file_size', 0)
        if file_size:
            if file_size < 1000:  # Less than 1KB
                return False, "file_too_small", 0.1
            elif file_size > 100000:  # More than 100KB
                score = min(score + 0.1, 1.0)
        
        # Check for alt text (indicates meaningful image)
        if metadata.get('alt_text'):
            score = min(score + 0.1, 1.0)
        
        return True, "passed", score
    
    @classmethod
    def filter_item(
        cls,
        content: str = None,
        data_type: str = "text",
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, str, float]:
        """
        Filter a data item based on quality.
        
        Returns:
            Tuple of (should_keep, reason, quality_score)
        """
        if data_type == "text":
            return cls.check_text_quality(content or "")
        elif data_type == "image":
            return cls.check_image_quality(metadata or {})
        else:
            # For other types, pass through with medium score
            return True, "unsupported_type", 0.5


class SmartDeduplicator:
    """Smart deduplication using embeddings for semantic similarity."""
    
    def __init__(self, similarity_threshold: float = 0.92):
        self.similarity_threshold = similarity_threshold
        self._embeddings_cache: Dict[str, List[float]] = {}
    
    async def check_duplicate_with_embedding(
        self,
        db: AsyncSession,
        project_id: UUID,
        content: str,
        data_type: str = "text"
    ) -> Tuple[bool, Optional[UUID], float]:
        """
        Check for duplicates using embedding similarity.
        
        Returns:
            Tuple of (is_duplicate, original_id, similarity_score)
        """
        if data_type != "text" or not content:
            return False, None, 0.0
        
        try:
            from app.services.embedding_service import EmbeddingService
            
            # Generate embedding for new content
            new_embedding = EmbeddingService.generate_text_embedding(content)
            
            if not new_embedding:
                return False, None, 0.0
            
            # Query items with embeddings from same project
            result = await db.execute(
                select(DataItem.id, DataItem.embedding)
                .where(
                    DataItem.project_id == project_id,
                    DataItem.embedding.isnot(None)
                )
            )
            existing_items = result.all()
            
            if not existing_items:
                return False, None, 0.0
            
            # Find most similar item
            best_match_id = None
            best_similarity = 0.0
            
            for item_id, item_embedding in existing_items:
                if item_embedding:
                    similarity = EmbeddingService.cosine_similarity(new_embedding, item_embedding)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_id = item_id
            
            is_duplicate = best_similarity >= self.similarity_threshold
            
            return is_duplicate, best_match_id if is_duplicate else None, best_similarity
            
        except Exception as e:
            logger.warning(f"Embedding deduplication failed: {e}")
            return False, None, 0.0
    
    async def deduplicate_batch(
        self,
        db: AsyncSession,
        project_id: UUID,
        items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Deduplicate a batch of items.
        
        Returns:
            Tuple of (unique_items, duplicate_items)
        """
        unique_items = []
        duplicate_items = []
        
        for item in items:
            content = item.get('content', '')
            data_type = item.get('data_type', 'text')
            
            is_dup, original_id, similarity = await self.check_duplicate_with_embedding(
                db, project_id, content, data_type
            )
            
            if is_dup:
                item['_duplicate_of'] = str(original_id)
                item['_similarity'] = similarity
                duplicate_items.append(item)
            else:
                unique_items.append(item)
        
        return unique_items, duplicate_items


class ScrapingMLIntegration:
    """Main integration class for ML features in scraping pipeline."""
    
    def __init__(
        self,
        enable_auto_labeling: bool = True,
        enable_quality_filter: bool = True,
        enable_smart_dedup: bool = True,
        min_quality_score: float = 0.3,
        dedup_threshold: float = 0.92
    ):
        self.enable_auto_labeling = enable_auto_labeling
        self.enable_quality_filter = enable_quality_filter
        self.enable_smart_dedup = enable_smart_dedup
        self.min_quality_score = min_quality_score
        self.deduplicator = SmartDeduplicator(dedup_threshold)
    
    async def process_item(
        self,
        db: AsyncSession,
        project_id: UUID,
        content: str = None,
        source_url: str = None,
        metadata: Dict[str, Any] = None,
        data_type: str = "text"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a single item through ML pipeline.
        
        Returns:
            Tuple of (should_save, processed_data)
        """
        result = {
            'labels': [],
            'quality_score': None,
            'is_duplicate': False,
            'duplicate_of': None,
            'filter_reason': None,
        }
        
        # Step 1: Quality filtering
        if self.enable_quality_filter:
            is_valid, reason, quality_score = QualityFilter.filter_item(
                content, data_type, metadata
            )
            result['quality_score'] = quality_score
            
            if not is_valid:
                result['filter_reason'] = reason
                logger.info(f"Item filtered: {reason}, score: {quality_score}")
                return False, result
        
        # Step 2: Smart deduplication
        if self.enable_smart_dedup:
            is_dup, original_id, similarity = await self.deduplicator.check_duplicate_with_embedding(
                db, project_id, content, data_type
            )
            result['is_duplicate'] = is_dup
            
            if is_dup:
                result['duplicate_of'] = str(original_id)
                result['filter_reason'] = f"duplicate (similarity: {similarity:.2f})"
                logger.info(f"Duplicate detected: {similarity:.2f} similar to {original_id}")
                return False, result
        
        # Step 3: Auto-labeling
        if self.enable_auto_labeling:
            labels, confidence = AutoLabeler.auto_label(
                content, source_url, metadata, data_type
            )
            result['labels'] = labels
            result['label_confidence'] = confidence
            
            if labels:
                logger.info(f"Auto-labeled with {len(labels)} labels: {labels[:5]}")
        
        return True, result
    
    async def process_batch(
        self,
        db: AsyncSession,
        project_id: UUID,
        items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Process a batch of items through ML pipeline.
        
        Returns:
            Tuple of (valid_items, stats)
        """
        valid_items = []
        stats = {
            'total': len(items),
            'passed': 0,
            'filtered_quality': 0,
            'filtered_duplicate': 0,
            'labeled': 0,
        }
        
        for item in items:
            should_save, result = await self.process_item(
                db=db,
                project_id=project_id,
                content=item.get('content'),
                source_url=item.get('source_url'),
                metadata=item.get('metadata', {}),
                data_type=item.get('data_type', 'text')
            )
            
            if should_save:
                # Apply results to item
                if result['labels']:
                    item['labels'] = result['labels']
                    item['is_labeled'] = True
                    stats['labeled'] += 1
                
                if result['quality_score']:
                    item['quality_score'] = result['quality_score']
                
                valid_items.append(item)
                stats['passed'] += 1
            else:
                if result.get('is_duplicate'):
                    stats['filtered_duplicate'] += 1
                else:
                    stats['filtered_quality'] += 1
        
        logger.info(f"ML Processing: {stats['passed']}/{stats['total']} passed, "
                   f"{stats['filtered_quality']} quality filtered, "
                   f"{stats['filtered_duplicate']} duplicates, "
                   f"{stats['labeled']} labeled")
        
        return valid_items, stats


# Global instance
scraping_ml = ScrapingMLIntegration()
