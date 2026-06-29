"""Embedding Generation Service for similarity search."""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import structlog
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating and managing embeddings."""
    
    def __init__(self):
        self._text_model = None
        self._image_model = None
        self._text_model_name = "all-MiniLM-L6-v2"
        self._available = False
        
    def _load_text_model(self):
        """Lazy load text embedding model."""
        if self._text_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._text_model = SentenceTransformer(self._text_model_name)
                self._available = True
                logger.info(f"Loaded text embedding model: {self._text_model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed. Using simple TF-IDF.")
                self._available = False
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
                self._available = False
        return self._text_model
    
    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if not texts:
            return []
        
        model = self._load_text_model()
        
        if model is not None:
            # Use SentenceTransformer
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Fallback to simple TF-IDF based embedding
            return self._simple_text_embedding(texts)
    
    def _simple_text_embedding(self, texts: List[str], dim: int = 384) -> List[List[float]]:
        """Simple text embedding using hashing and TF-IDF-like approach."""
        embeddings = []
        
        for text in texts:
            # Create a simple embedding using character n-grams
            words = text.lower().split()
            embedding = [0.0] * dim
            
            for i, word in enumerate(words):
                # Hash word to get indices
                for j in range(len(word) - 2):
                    trigram = word[j:j+3]
                    idx = hash(trigram) % dim
                    # Use TF-like weighting
                    embedding[idx] += 1.0 / (1 + np.log1p(i))
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            embeddings.append(embedding)
        
        return embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = self.embed_text([text])
        return embeddings[0] if embeddings else []
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def find_similar(
        self, 
        query_embedding: List[float], 
        embeddings: List[Tuple[str, List[float]]], 
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Find most similar items based on embeddings."""
        similarities = []
        
        for item_id, embedding in embeddings:
            if embedding:
                sim = self.cosine_similarity(query_embedding, embedding)
                similarities.append((item_id, sim))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: -x[1])
        
        return similarities[:top_k]


# Global instance
embedding_service = EmbeddingService()


async def generate_embeddings_for_project(
    db: AsyncSession,
    project_id: UUID,
    recompute: bool = False,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """Generate embeddings for all text items in a project."""
    
    # Get items that need embeddings
    query = select(DataItem).where(
        DataItem.project_id == project_id,
        DataItem.data_type == "text",
        DataItem.content.isnot(None),
    )
    
    if not recompute:
        query = query.where(DataItem.embedding.is_(None))
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    if not items:
        return {"processed": 0, "total": 0}
    
    # Process in batches
    processed = 0
    total = len(items)
    
    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        texts = [item.content for item in batch]
        
        embeddings = embedding_service.embed_text(texts)
        
        for item, embedding in zip(batch, embeddings):
            item.embedding = embedding
            processed += 1
        
        await db.commit()
        logger.info(f"Generated embeddings: {processed}/{total}")
    
    return {"processed": processed, "total": total}


async def find_similar_items(
    db: AsyncSession,
    item_id: UUID,
    project_id: UUID,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Find items similar to a given item."""
    
    # Get the source item
    result = await db.execute(
        select(DataItem).where(DataItem.id == item_id)
    )
    source_item = result.scalar_one_or_none()
    
    if not source_item:
        return []
    
    # Generate embedding if not exists
    if source_item.embedding is None:
        if source_item.content:
            source_item.embedding = embedding_service.embed_single(source_item.content)
            await db.commit()
        else:
            return []
    
    # Get all items with embeddings in the project
    result = await db.execute(
        select(DataItem).where(
            DataItem.project_id == project_id,
            DataItem.id != item_id,
            DataItem.embedding.isnot(None),
        )
    )
    items = result.scalars().all()
    
    # Find similar
    embeddings = [(str(item.id), item.embedding) for item in items]
    similar = embedding_service.find_similar(source_item.embedding, embeddings, top_k)
    
    # Get item details
    similar_ids = [UUID(sid) for sid, _ in similar]
    similarity_map = {sid: score for sid, score in similar}
    
    result = await db.execute(
        select(DataItem).where(DataItem.id.in_(similar_ids))
    )
    similar_items = result.scalars().all()
    
    return [
        {
            "id": str(item.id),
            "similarity": similarity_map[str(item.id)],
            "content_preview": item.content[:200] if item.content else None,
            "data_type": item.data_type,
            "labels": item.labels,
        }
        for item in sorted(similar_items, key=lambda x: -similarity_map[str(x.id)])
    ]


async def find_duplicates_by_embedding(
    db: AsyncSession,
    project_id: UUID,
    threshold: float = 0.95,
) -> List[Dict[str, Any]]:
    """Find potential duplicates using embedding similarity."""
    
    # Get all items with embeddings
    result = await db.execute(
        select(DataItem).where(
            DataItem.project_id == project_id,
            DataItem.embedding.isnot(None),
        )
    )
    items = result.scalars().all()
    
    if len(items) < 2:
        return []
    
    duplicates = []
    checked = set()
    
    for i, item1 in enumerate(items):
        for item2 in items[i + 1:]:
            pair_key = (str(item1.id), str(item2.id))
            if pair_key in checked:
                continue
            
            similarity = embedding_service.cosine_similarity(item1.embedding, item2.embedding)
            
            if similarity >= threshold:
                duplicates.append({
                    "item1_id": str(item1.id),
                    "item2_id": str(item2.id),
                    "similarity": similarity,
                })
            
            checked.add(pair_key)
    
    return sorted(duplicates, key=lambda x: -x["similarity"])
