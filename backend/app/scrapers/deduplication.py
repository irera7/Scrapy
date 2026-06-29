"""Data deduplication system for scraped content."""
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import re
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class DeduplicationStrategy(str, Enum):
    """Strategies for detecting duplicates."""
    EXACT_MATCH = "exact"  # Exact content match
    URL_MATCH = "url"  # Same URL
    HASH_MATCH = "hash"  # Same content hash
    SIMILARITY = "similarity"  # Similar content (fuzzy)
    COMBINED = "combined"  # Multiple strategies


@dataclass
class DuplicateInfo:
    """Information about a detected duplicate."""
    original_id: str
    duplicate_id: str
    strategy: DeduplicationStrategy
    similarity_score: float
    detected_at: datetime


class ContentHasher:
    """Generate various hashes for content."""
    
    @staticmethod
    def md5_hash(content: str) -> str:
        """Generate MD5 hash."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def sha256_hash(content: str) -> str:
        """Generate SHA256 hash."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def normalized_hash(content: str) -> str:
        """Generate hash after normalizing content."""
        # Normalize whitespace and case
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def simhash(content: str, hash_bits: int = 64) -> int:
        """
        Generate SimHash for similarity detection.
        SimHash is locality-sensitive - similar content has similar hashes.
        """
        # Tokenize
        tokens = re.findall(r'\w+', content.lower())
        
        if not tokens:
            return 0
        
        # Generate feature hashes
        v = [0] * hash_bits
        
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
            
            for i in range(hash_bits):
                if token_hash & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Generate final hash
        fingerprint = 0
        for i in range(hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int, bits: int = 64) -> int:
        """Calculate Hamming distance between two hashes."""
        xor = hash1 ^ hash2
        distance = bin(xor).count('1')
        return distance
    
    @staticmethod
    def simhash_similarity(hash1: int, hash2: int, bits: int = 64) -> float:
        """Calculate similarity based on SimHash (0-1)."""
        distance = ContentHasher.hamming_distance(hash1, hash2, bits)
        return 1 - (distance / bits)


class SimilarityCalculator:
    """Calculate similarity between content."""
    
    @staticmethod
    def jaccard_similarity(text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def cosine_similarity(text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        # Tokenize
        words1 = re.findall(r'\w+', text1.lower())
        words2 = re.findall(r'\w+', text2.lower())
        
        if not words1 or not words2:
            return 0.0
        
        # Count word frequencies
        freq1 = defaultdict(int)
        freq2 = defaultdict(int)
        
        for word in words1:
            freq1[word] += 1
        for word in words2:
            freq2[word] += 1
        
        # Get all unique words
        all_words = set(freq1.keys()) | set(freq2.keys())
        
        # Calculate dot product and magnitudes
        dot_product = sum(freq1.get(word, 0) * freq2.get(word, 0) for word in all_words)
        magnitude1 = sum(v ** 2 for v in freq1.values()) ** 0.5
        magnitude2 = sum(v ** 2 for v in freq2.values()) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    @staticmethod
    def levenshtein_similarity(text1: str, text2: str, max_len: int = 1000) -> float:
        """Calculate similarity based on Levenshtein distance."""
        # Truncate for performance
        text1 = text1[:max_len]
        text2 = text2[:max_len]
        
        if text1 == text2:
            return 1.0
        
        len1, len2 = len(text1), len(text2)
        
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Dynamic programming approach
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if text1[i-1] == text2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,
                    matrix[i][j-1] + 1,
                    matrix[i-1][j-1] + cost
                )
        
        distance = matrix[len1][len2]
        max_len = max(len1, len2)
        
        return 1 - (distance / max_len)
    
    @staticmethod
    def ngram_similarity(text1: str, text2: str, n: int = 3) -> float:
        """Calculate similarity using n-grams."""
        def get_ngrams(text: str, n: int) -> Set[str]:
            text = text.lower()
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0


class DeduplicationManager:
    """Manager for data deduplication."""
    
    def __init__(
        self,
        strategy: DeduplicationStrategy = DeduplicationStrategy.COMBINED,
        similarity_threshold: float = 0.9
    ):
        self.strategy = strategy
        self.similarity_threshold = similarity_threshold
        
        # Storage for seen content
        self._url_index: Dict[str, str] = {}  # URL -> item_id
        self._hash_index: Dict[str, str] = {}  # Content hash -> item_id
        self._simhash_index: Dict[str, Tuple[int, str]] = {}  # Normalized hash -> (simhash, item_id)
        self._content_store: Dict[str, str] = {}  # item_id -> content (for similarity checking)
    
    def add_item(
        self,
        item_id: str,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DuplicateInfo]:
        """
        Add an item and check for duplicates.
        Returns DuplicateInfo if duplicate found, None otherwise.
        """
        # Check URL match
        if url and self.strategy in [DeduplicationStrategy.URL_MATCH, DeduplicationStrategy.COMBINED]:
            if url in self._url_index:
                return DuplicateInfo(
                    original_id=self._url_index[url],
                    duplicate_id=item_id,
                    strategy=DeduplicationStrategy.URL_MATCH,
                    similarity_score=1.0,
                    detected_at=datetime.now()
                )
        
        # Check exact hash match
        if self.strategy in [DeduplicationStrategy.EXACT_MATCH, DeduplicationStrategy.HASH_MATCH, DeduplicationStrategy.COMBINED]:
            content_hash = ContentHasher.md5_hash(content)
            if content_hash in self._hash_index:
                return DuplicateInfo(
                    original_id=self._hash_index[content_hash],
                    duplicate_id=item_id,
                    strategy=DeduplicationStrategy.HASH_MATCH,
                    similarity_score=1.0,
                    detected_at=datetime.now()
                )
        
        # Check similarity
        if self.strategy in [DeduplicationStrategy.SIMILARITY, DeduplicationStrategy.COMBINED]:
            duplicate_info = self._check_similarity(item_id, content)
            if duplicate_info:
                return duplicate_info
        
        # No duplicate found, add to indexes
        if url:
            self._url_index[url] = item_id
        
        content_hash = ContentHasher.md5_hash(content)
        self._hash_index[content_hash] = item_id
        
        # Add to simhash index
        normalized_hash = ContentHasher.normalized_hash(content)
        simhash = ContentHasher.simhash(content)
        self._simhash_index[normalized_hash] = (simhash, item_id)
        
        # Store content for future similarity checks
        self._content_store[item_id] = content
        
        return None
    
    def _check_similarity(self, item_id: str, content: str) -> Optional[DuplicateInfo]:
        """Check for similar content using various methods."""
        # First, quick check using SimHash
        new_simhash = ContentHasher.simhash(content)
        
        for normalized_hash, (existing_simhash, existing_id) in self._simhash_index.items():
            # Calculate SimHash similarity
            simhash_sim = ContentHasher.simhash_similarity(new_simhash, existing_simhash)
            
            # If SimHash suggests similarity, do deeper check
            if simhash_sim >= self.similarity_threshold - 0.1:
                existing_content = self._content_store.get(existing_id)
                
                if existing_content:
                    # Use multiple similarity measures
                    jaccard_sim = SimilarityCalculator.jaccard_similarity(content, existing_content)
                    cosine_sim = SimilarityCalculator.cosine_similarity(content, existing_content)
                    
                    # Average of similarities
                    avg_similarity = (jaccard_sim + cosine_sim + simhash_sim) / 3
                    
                    if avg_similarity >= self.similarity_threshold:
                        return DuplicateInfo(
                            original_id=existing_id,
                            duplicate_id=item_id,
                            strategy=DeduplicationStrategy.SIMILARITY,
                            similarity_score=avg_similarity,
                            detected_at=datetime.now()
                        )
        
        return None
    
    def check_duplicate(
        self,
        content: str,
        url: Optional[str] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if content is a duplicate without adding it.
        Returns (is_duplicate, original_id, similarity_score).
        """
        # Check URL
        if url and url in self._url_index:
            return True, self._url_index[url], 1.0
        
        # Check exact hash
        content_hash = ContentHasher.md5_hash(content)
        if content_hash in self._hash_index:
            return True, self._hash_index[content_hash], 1.0
        
        # Check similarity
        new_simhash = ContentHasher.simhash(content)
        
        best_match_id = None
        best_similarity = 0.0
        
        for normalized_hash, (existing_simhash, existing_id) in self._simhash_index.items():
            simhash_sim = ContentHasher.simhash_similarity(new_simhash, existing_simhash)
            
            if simhash_sim > best_similarity:
                existing_content = self._content_store.get(existing_id)
                if existing_content:
                    jaccard_sim = SimilarityCalculator.jaccard_similarity(content, existing_content)
                    cosine_sim = SimilarityCalculator.cosine_similarity(content, existing_content)
                    avg_similarity = (jaccard_sim + cosine_sim + simhash_sim) / 3
                    
                    if avg_similarity > best_similarity:
                        best_similarity = avg_similarity
                        best_match_id = existing_id
        
        is_duplicate = best_similarity >= self.similarity_threshold
        return is_duplicate, best_match_id, best_similarity
    
    def find_duplicates_in_batch(
        self,
        items: List[Dict[str, Any]],
        content_key: str = "content",
        id_key: str = "id",
        url_key: str = "url"
    ) -> List[DuplicateInfo]:
        """Find all duplicates within a batch of items."""
        duplicates = []
        
        for item in items:
            content = item.get(content_key, "")
            item_id = item.get(id_key, "")
            url = item.get(url_key)
            
            duplicate_info = self.add_item(item_id, content, url)
            if duplicate_info:
                duplicates.append(duplicate_info)
        
        return duplicates
    
    def clear(self):
        """Clear all indexes."""
        self._url_index.clear()
        self._hash_index.clear()
        self._simhash_index.clear()
        self._content_store.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return {
            "total_items": len(self._content_store),
            "unique_urls": len(self._url_index),
            "unique_hashes": len(self._hash_index),
        }


class CrossProjectDeduplication:
    """Deduplication across multiple projects."""
    
    def __init__(self):
        self._global_hashes: Dict[str, List[str]] = defaultdict(list)  # hash -> [project_id:item_id, ...]
    
    def register_item(
        self,
        project_id: str,
        item_id: str,
        content: str
    ) -> List[Tuple[str, str]]:
        """
        Register an item and return list of duplicates in other projects.
        Returns list of (project_id, item_id) tuples for duplicates.
        """
        content_hash = ContentHasher.normalized_hash(content)
        
        duplicates = []
        
        # Check for existing items with same hash
        for existing in self._global_hashes.get(content_hash, []):
            existing_project, existing_item = existing.split(":", 1)
            if existing_project != project_id:
                duplicates.append((existing_project, existing_item))
        
        # Register this item
        key = f"{project_id}:{item_id}"
        self._global_hashes[content_hash].append(key)
        
        return duplicates
    
    def find_cross_project_duplicates(
        self,
        project_id: str,
        items: List[Dict[str, Any]]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        Find duplicates across projects for a list of items.
        Returns dict of item_id -> [(other_project_id, other_item_id), ...]
        """
        results = {}
        
        for item in items:
            content = item.get("content", "")
            item_id = item.get("id", "")
            
            duplicates = self.register_item(project_id, item_id, content)
            if duplicates:
                results[item_id] = duplicates
        
        return results


# Global instances
dedup_manager = DeduplicationManager()
cross_project_dedup = CrossProjectDeduplication()

