"""Data Leakage Detection Service.

This service detects potential data leakage between train/validation/test splits
to ensure model evaluation integrity.
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from collections import defaultdict
import structlog
from datetime import datetime
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.data_item import DataItem

logger = structlog.get_logger()


class LeakageDetector:
    """Detect various types of data leakage."""
    
    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Compute hash of normalized text."""
        if not text:
            return ""
        # Normalize text
        normalized = text.lower().strip()
        normalized = " ".join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    @staticmethod
    def compute_text_shingles(text: str, k: int = 5) -> Set[str]:
        """Compute k-shingles (character n-grams) for near-duplicate detection."""
        if not text or len(text) < k:
            return set()
        text = text.lower().strip()
        return {text[i:i+k] for i in range(len(text) - k + 1)}
    
    @staticmethod
    def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0


class DataLeakageService:
    """Service for detecting data leakage in ML datasets."""
    
    def __init__(self):
        self.detector = LeakageDetector()
    
    async def detect_exact_duplicates(
        self,
        db: AsyncSession,
        project_id: UUID,
        splits: List[str] = None
    ) -> Dict[str, Any]:
        """
        Detect exact duplicates between splits.
        
        Args:
            db: Database session
            project_id: Project ID
            splits: Splits to check (default: train, val, test)
            
        Returns:
            Report of exact duplicates found
        """
        if splits is None:
            splits = ["train", "val", "test"]
        
        # Get items for each split
        split_items: Dict[str, List[DataItem]] = {}
        split_hashes: Dict[str, Dict[str, UUID]] = {}
        
        for split in splits:
            result = await db.execute(
                select(DataItem).where(
                    and_(
                        DataItem.project_id == project_id,
                        DataItem.dataset_split == split
                    )
                )
            )
            items = result.scalars().all()
            split_items[split] = items
            
            # Compute hashes
            split_hashes[split] = {}
            for item in items:
                if item.content:
                    hash_val = self.detector.compute_text_hash(item.content)
                    split_hashes[split][hash_val] = item.id
        
        # Find duplicates between splits
        duplicates = []
        checked_pairs = set()
        
        for i, split1 in enumerate(splits):
            for split2 in splits[i+1:]:
                pair_key = tuple(sorted([split1, split2]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # Find common hashes
                common_hashes = set(split_hashes[split1].keys()) & set(split_hashes[split2].keys())
                
                for hash_val in common_hashes:
                    if hash_val:  # Skip empty hashes
                        duplicates.append({
                            "type": "exact_duplicate",
                            "split_1": split1,
                            "split_2": split2,
                            "item_1_id": str(split_hashes[split1][hash_val]),
                            "item_2_id": str(split_hashes[split2][hash_val]),
                            "hash": hash_val,
                            "severity": "high"
                        })
        
        # Calculate statistics
        total_items = sum(len(items) for items in split_items.values())
        
        return {
            "project_id": str(project_id),
            "splits_checked": splits,
            "total_items": total_items,
            "items_per_split": {split: len(items) for split, items in split_items.items()},
            "exact_duplicates_found": len(duplicates),
            "duplicates": duplicates,
            "has_leakage": len(duplicates) > 0,
            "severity": "high" if duplicates else "none",
            "checked_at": datetime.now().isoformat()
        }
    
    async def detect_near_duplicates(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.8,
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Detect near-duplicates (similar content) between splits.
        Uses shingle-based similarity for efficiency.
        """
        splits = ["train", "val", "test"]
        
        # Get items for each split (sample if too many)
        split_items: Dict[str, List[DataItem]] = {}
        
        for split in splits:
            result = await db.execute(
                select(DataItem).where(
                    and_(
                        DataItem.project_id == project_id,
                        DataItem.dataset_split == split,
                        DataItem.content.isnot(None)
                    )
                ).limit(sample_size)
            )
            split_items[split] = result.scalars().all()
        
        # Compute shingles for all items
        item_shingles: Dict[str, Tuple[Set[str], str, str]] = {}
        
        for split, items in split_items.items():
            for item in items:
                if item.content:
                    shingles = self.detector.compute_text_shingles(item.content)
                    item_shingles[str(item.id)] = (shingles, split, item.content[:100])
        
        # Find near-duplicates between different splits
        near_duplicates = []
        
        # Compare test/val items against train items
        train_ids = [str(item.id) for item in split_items.get("train", [])]
        other_ids = [str(item.id) for item in split_items.get("val", []) + split_items.get("test", [])]
        
        for other_id in other_ids:
            if other_id not in item_shingles:
                continue
            
            other_shingles, other_split, other_preview = item_shingles[other_id]
            
            for train_id in train_ids:
                if train_id not in item_shingles:
                    continue
                
                train_shingles, _, train_preview = item_shingles[train_id]
                
                similarity = self.detector.jaccard_similarity(other_shingles, train_shingles)
                
                if similarity >= similarity_threshold:
                    near_duplicates.append({
                        "type": "near_duplicate",
                        "split_1": "train",
                        "split_2": other_split,
                        "item_1_id": train_id,
                        "item_2_id": other_id,
                        "similarity": round(similarity, 4),
                        "preview_1": train_preview,
                        "preview_2": other_preview,
                        "severity": "high" if similarity > 0.95 else "medium"
                    })
        
        # Sort by similarity (highest first)
        near_duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        
        return {
            "project_id": str(project_id),
            "similarity_threshold": similarity_threshold,
            "sample_size": sample_size,
            "items_checked": len(item_shingles),
            "near_duplicates_found": len(near_duplicates),
            "near_duplicates": near_duplicates[:100],  # Limit output
            "has_leakage": len(near_duplicates) > 0,
            "severity": "high" if any(d["similarity"] > 0.95 for d in near_duplicates) else "medium" if near_duplicates else "none",
            "checked_at": datetime.now().isoformat()
        }
    
    async def detect_embedding_leakage(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        Detect leakage using embedding similarity.
        Requires embeddings to be pre-computed.
        """
        splits = ["train", "val", "test"]
        
        # Get items with embeddings
        split_items: Dict[str, List[DataItem]] = {}
        
        for split in splits:
            result = await db.execute(
                select(DataItem).where(
                    and_(
                        DataItem.project_id == project_id,
                        DataItem.dataset_split == split,
                        DataItem.embedding.isnot(None)
                    )
                )
            )
            split_items[split] = result.scalars().all()
        
        embedding_leakages = []
        
        # Compare test/val embeddings against train
        train_items = split_items.get("train", [])
        
        if not train_items:
            return {
                "project_id": str(project_id),
                "error": "No items with embeddings in train split",
                "has_leakage": False
            }
        
        for split in ["val", "test"]:
            for item in split_items.get(split, []):
                if not item.embedding:
                    continue
                
                for train_item in train_items:
                    if not train_item.embedding:
                        continue
                    
                    # Compute cosine similarity
                    similarity = self._cosine_similarity(item.embedding, train_item.embedding)
                    
                    if similarity >= similarity_threshold:
                        embedding_leakages.append({
                            "type": "embedding_similarity",
                            "split_1": "train",
                            "split_2": split,
                            "item_1_id": str(train_item.id),
                            "item_2_id": str(item.id),
                            "similarity": round(similarity, 4),
                            "severity": "high" if similarity > 0.99 else "medium"
                        })
        
        return {
            "project_id": str(project_id),
            "similarity_threshold": similarity_threshold,
            "items_with_embeddings": {
                split: len(items) for split, items in split_items.items()
            },
            "embedding_leakages_found": len(embedding_leakages),
            "leakages": embedding_leakages[:100],
            "has_leakage": len(embedding_leakages) > 0,
            "checked_at": datetime.now().isoformat()
        }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def detect_source_leakage(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Detect leakage based on source URLs.
        Same source appearing in train and test indicates potential leakage.
        """
        splits = ["train", "val", "test"]
        
        # Get source URLs for each split
        split_sources: Dict[str, Dict[str, List[UUID]]] = {}
        
        for split in splits:
            result = await db.execute(
                select(DataItem).where(
                    and_(
                        DataItem.project_id == project_id,
                        DataItem.dataset_split == split,
                        DataItem.source_url.isnot(None)
                    )
                )
            )
            items = result.scalars().all()
            
            split_sources[split] = defaultdict(list)
            for item in items:
                if item.source_url:
                    # Extract domain from URL
                    domain = self._extract_domain(item.source_url)
                    split_sources[split][domain].append(item.id)
        
        # Find overlapping sources
        source_leakages = []
        
        train_domains = set(split_sources.get("train", {}).keys())
        
        for split in ["val", "test"]:
            split_domains = set(split_sources.get(split, {}).keys())
            common_domains = train_domains & split_domains
            
            for domain in common_domains:
                train_count = len(split_sources["train"][domain])
                other_count = len(split_sources[split][domain])
                
                source_leakages.append({
                    "type": "source_overlap",
                    "domain": domain,
                    "train_items": train_count,
                    f"{split}_items": other_count,
                    "severity": "medium" if train_count < 10 else "high"
                })
        
        return {
            "project_id": str(project_id),
            "unique_sources_per_split": {
                split: len(sources) for split, sources in split_sources.items()
            },
            "source_overlaps": source_leakages,
            "has_leakage": len(source_leakages) > 0,
            "severity": "high" if any(l["severity"] == "high" for l in source_leakages) else "medium" if source_leakages else "none",
            "checked_at": datetime.now().isoformat()
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or url
        except:
            return url
    
    async def detect_temporal_leakage(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Detect temporal leakage (future data in training set).
        Useful for time-series and news data.
        """
        splits = ["train", "val", "test"]
        
        # Get timestamps for each split
        split_timestamps: Dict[str, List[datetime]] = {}
        
        for split in splits:
            result = await db.execute(
                select(DataItem.created_at).where(
                    and_(
                        DataItem.project_id == project_id,
                        DataItem.dataset_split == split
                    )
                )
            )
            timestamps = [row[0] for row in result.fetchall() if row[0]]
            split_timestamps[split] = sorted(timestamps)
        
        issues = []
        
        # Check if train data is newer than val/test
        train_timestamps = split_timestamps.get("train", [])
        
        if train_timestamps:
            train_max = max(train_timestamps)
            train_min = min(train_timestamps)
            
            for split in ["val", "test"]:
                other_timestamps = split_timestamps.get(split, [])
                if other_timestamps:
                    other_min = min(other_timestamps)
                    other_max = max(other_timestamps)
                    
                    # Check if train contains data newer than val/test min
                    if train_max > other_min:
                        overlap_count = sum(1 for t in train_timestamps if t > other_min)
                        issues.append({
                            "type": "temporal_overlap",
                            "description": f"Train set contains {overlap_count} items newer than oldest {split} item",
                            "train_max_date": train_max.isoformat(),
                            f"{split}_min_date": other_min.isoformat(),
                            "overlapping_items": overlap_count,
                            "severity": "high" if overlap_count > 100 else "medium"
                        })
        
        return {
            "project_id": str(project_id),
            "date_ranges": {
                split: {
                    "min": min(ts).isoformat() if ts else None,
                    "max": max(ts).isoformat() if ts else None,
                    "count": len(ts)
                }
                for split, ts in split_timestamps.items()
            },
            "temporal_issues": issues,
            "has_leakage": len(issues) > 0,
            "recommendation": "Use temporal split for time-sensitive data" if issues else None,
            "checked_at": datetime.now().isoformat()
        }
    
    async def run_full_leakage_check(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Run comprehensive leakage detection.
        Combines all leakage detection methods.
        """
        results = {
            "project_id": str(project_id),
            "checks": {},
            "overall_status": "clean",
            "total_issues": 0,
            "recommendations": []
        }
        
        # Run all checks
        try:
            exact_check = await self.detect_exact_duplicates(db, project_id)
            results["checks"]["exact_duplicates"] = exact_check
            if exact_check.get("has_leakage"):
                results["total_issues"] += exact_check.get("exact_duplicates_found", 0)
                results["recommendations"].append("Remove exact duplicates from test/val that exist in train")
        except Exception as e:
            results["checks"]["exact_duplicates"] = {"error": str(e)}
        
        try:
            near_check = await self.detect_near_duplicates(db, project_id, sample_size=500)
            results["checks"]["near_duplicates"] = near_check
            if near_check.get("has_leakage"):
                results["total_issues"] += near_check.get("near_duplicates_found", 0)
                results["recommendations"].append("Review near-duplicates for potential data leakage")
        except Exception as e:
            results["checks"]["near_duplicates"] = {"error": str(e)}
        
        try:
            source_check = await self.detect_source_leakage(db, project_id)
            results["checks"]["source_overlap"] = source_check
            if source_check.get("has_leakage"):
                results["total_issues"] += len(source_check.get("source_overlaps", []))
                results["recommendations"].append("Consider splitting by source domain")
        except Exception as e:
            results["checks"]["source_overlap"] = {"error": str(e)}
        
        try:
            temporal_check = await self.detect_temporal_leakage(db, project_id)
            results["checks"]["temporal_leakage"] = temporal_check
            if temporal_check.get("has_leakage"):
                results["total_issues"] += len(temporal_check.get("temporal_issues", []))
                results["recommendations"].append("Use temporal split for time-ordered data")
        except Exception as e:
            results["checks"]["temporal_leakage"] = {"error": str(e)}
        
        # Determine overall status
        if results["total_issues"] > 10:
            results["overall_status"] = "critical"
        elif results["total_issues"] > 0:
            results["overall_status"] = "warning"
        else:
            results["overall_status"] = "clean"
        
        results["checked_at"] = datetime.now().isoformat()
        
        return results


# Global instance
data_leakage_service = DataLeakageService()
