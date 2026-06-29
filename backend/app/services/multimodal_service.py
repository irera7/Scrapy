"""Multimodal Alignment Service for cross-modal data management."""
import os
import tempfile
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import structlog
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class VideoFrameExtractor:
    """Extract frames and audio from video for alignment."""
    
    def __init__(self):
        self._cv2_available = False
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            logger.info("OpenCV not available for video frame extraction")
    
    def extract_keyframes(self, video_path: str, num_frames: int = 5) -> List[bytes]:
        """Extract key frames from video."""
        if not self._cv2_available:
            return []
        
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                return []
            
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
            frames = []
            
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    _, buffer = cv2.imencode('.jpg', frame)
                    frames.append(buffer.tobytes())
            
            cap.release()
            return frames
            
        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            return []
    
    def extract_audio_track(self, video_path: str, output_path: str) -> bool:
        """Extract audio track from video."""
        try:
            import subprocess
            result = subprocess.run([
                'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', output_path, '-y'
            ], capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Audio extraction failed: {e}")
            return False


class MultimodalAligner:
    """Align and score multimodal data pairs."""
    
    def __init__(self):
        self._clip_available = False
        self._sentence_transformer_available = False
        self.video_extractor = VideoFrameExtractor()
        
        # Try to load CLIP for image-text alignment
        try:
            import torch
            import clip
            self._clip_model, self._clip_preprocess = clip.load("ViT-B/32")
            self._clip_available = True
            logger.info("CLIP model loaded for multimodal alignment")
        except ImportError:
            logger.info("CLIP not available, using fallback methods")
        
        # Try sentence transformers for text embeddings
        try:
            from sentence_transformers import SentenceTransformer
            self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._sentence_transformer_available = True
        except ImportError:
            logger.info("SentenceTransformer not available")
    
    async def compute_video_text_similarity(
        self,
        video_path: str,
        text: str
    ) -> Dict[str, Any]:
        """Compute similarity between video and text using key frames."""
        frames = self.video_extractor.extract_keyframes(video_path, num_frames=5)
        
        if not frames:
            return {"error": "Could not extract video frames", "similarity_score": 0.0}
        
        scores = []
        for frame_data in frames:
            result = await self.compute_image_text_similarity(frame_data, text)
            if "similarity_score" in result:
                scores.append(result["similarity_score"])
        
        if not scores:
            return {"error": "No valid frame scores", "similarity_score": 0.0}
        
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        
        return {
            "similarity_score": round(avg_score, 4),
            "max_frame_score": round(max_score, 4),
            "frames_analyzed": len(scores),
            "method": "video_clip" if self._clip_available else "video_heuristic",
            "is_aligned": avg_score > 0.2,
            "confidence": "high" if max_score > 0.3 else "medium" if max_score > 0.2 else "low"
        }
    
    async def compute_image_audio_similarity(
        self,
        image_data: bytes,
        audio_transcription: str
    ) -> Dict[str, Any]:
        """Compute similarity between image and audio via transcription."""
        if not audio_transcription:
            return {"error": "No transcription available", "similarity_score": 0.0}
        
        # Use image-text similarity with transcription
        return await self.compute_image_text_similarity(image_data, audio_transcription)
    
    async def compute_video_audio_similarity(
        self,
        video_path: str,
        audio_transcription: str
    ) -> Dict[str, Any]:
        """Compute similarity between video frames and audio transcription."""
        if not audio_transcription:
            return {"error": "No transcription available", "similarity_score": 0.0}
        
        return await self.compute_video_text_similarity(video_path, audio_transcription)
    
    async def compute_image_text_similarity(
        self,
        image_data: bytes,
        text: str
    ) -> Dict[str, Any]:
        """
        Compute similarity between image and text using CLIP.
        """
        if self._clip_available:
            return await self._clip_similarity(image_data, text)
        else:
            return await self._fallback_similarity(image_data, text)
    
    async def _clip_similarity(
        self,
        image_data: bytes,
        text: str
    ) -> Dict[str, Any]:
        """Compute CLIP-based similarity."""
        try:
            import torch
            import clip
            from PIL import Image
            import io
            
            # Process image
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            image_input = self._clip_preprocess(image).unsqueeze(0)
            
            # Process text
            text_input = clip.tokenize([text], truncate=True)
            
            # Get embeddings
            with torch.no_grad():
                image_features = self._clip_model.encode_image(image_input)
                text_features = self._clip_model.encode_text(text_input)
                
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Compute similarity
                similarity = (image_features @ text_features.T).item()
            
            return {
                "similarity_score": round(float(similarity), 4),
                "method": "clip",
                "is_aligned": similarity > 0.2,
                "confidence": "high" if similarity > 0.3 else "medium" if similarity > 0.2 else "low"
            }
            
        except Exception as e:
            logger.error(f"CLIP similarity error: {e}")
            return {"error": str(e)}
    
    async def _fallback_similarity(
        self,
        image_data: bytes,
        text: str
    ) -> Dict[str, Any]:
        """Fallback similarity using basic heuristics."""
        try:
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_data))
            
            # Basic heuristics
            score = 0.5  # Base score
            
            # Check if text mentions image properties
            width, height = image.size
            text_lower = text.lower()
            
            if "image" in text_lower or "picture" in text_lower or "photo" in text_lower:
                score += 0.1
            
            if "horizontal" in text_lower and width > height:
                score += 0.1
            elif "vertical" in text_lower and height > width:
                score += 0.1
            
            # Check format mention
            format_name = image.format.lower() if image.format else ""
            if format_name and format_name in text_lower:
                score += 0.1
            
            return {
                "similarity_score": round(score, 4),
                "method": "heuristic",
                "is_aligned": score > 0.5,
                "note": "Using basic heuristics (CLIP not available)"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def compute_audio_text_similarity(
        self,
        transcription: str,
        reference_text: str
    ) -> Dict[str, Any]:
        """
        Compute similarity between audio transcription and reference text.
        """
        if not transcription or not reference_text:
            return {"error": "Empty text provided"}
        
        try:
            if self._sentence_transformer_available:
                # Use sentence transformers
                embeddings = self._sentence_model.encode([transcription, reference_text])
                
                import numpy as np
                similarity = float(np.dot(embeddings[0], embeddings[1]) / (
                    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
                ))
                
                method = "sentence_transformer"
            else:
                # Fallback to simple word overlap
                words1 = set(transcription.lower().split())
                words2 = set(reference_text.lower().split())
                
                intersection = len(words1 & words2)
                union = len(words1 | words2)
                
                similarity = intersection / union if union > 0 else 0.0
                method = "jaccard"
            
            return {
                "similarity_score": round(similarity, 4),
                "method": method,
                "is_aligned": similarity > 0.5,
                "confidence": "high" if similarity > 0.7 else "medium" if similarity > 0.5 else "low"
            }
            
        except Exception as e:
            logger.error(f"Text similarity error: {e}")
            return {"error": str(e)}


class MultimodalService:
    """Main service for multimodal data management."""
    
    def __init__(self):
        self.aligner = MultimodalAligner()
    
    async def create_multimodal_group(
        self,
        db: AsyncSession,
        project_id: UUID,
        item_ids: List[UUID],
        group_name: Optional[str] = None,
        alignment_type: str = "parallel"  # parallel, sequential, hierarchical
    ) -> Dict[str, Any]:
        """
        Create a multimodal group linking multiple data items.
        
        Args:
            project_id: Project ID
            item_ids: List of item IDs to group
            group_name: Optional name for the group
            alignment_type: Type of alignment relationship
        """
        if len(item_ids) < 2:
            return {"error": "At least 2 items required for multimodal group"}
        
        # Get items
        result = await db.execute(
            select(DataItem).where(DataItem.id.in_(item_ids))
        )
        items = result.scalars().all()
        
        if len(items) != len(item_ids):
            return {"error": "Some items not found"}
        
        # Verify all items belong to same project
        if not all(item.project_id == project_id for item in items):
            return {"error": "All items must belong to the same project"}
        
        # Generate group ID
        import uuid
        group_id = str(uuid.uuid4())
        
        if not group_name:
            data_types = sorted(set(item.data_type for item in items))
            group_name = f"multimodal_{'-'.join(data_types)}_{group_id[:8]}"
        
        # Update items with group info
        group_info = {
            "multimodal_group_id": group_id,
            "multimodal_group_name": group_name,
            "multimodal_alignment_type": alignment_type,
            "multimodal_members": [str(i) for i in item_ids],
            "multimodal_created_at": datetime.utcnow().isoformat()
        }
        
        for item in items:
            metadata = item.item_metadata or {}
            metadata["multimodal"] = group_info
            item.item_metadata = metadata
        
        await db.commit()
        
        return {
            "group_id": group_id,
            "group_name": group_name,
            "item_count": len(items),
            "data_types": list(set(item.data_type for item in items)),
            "alignment_type": alignment_type,
            "success": True
        }
    
    async def compute_group_alignment(
        self,
        db: AsyncSession,
        group_id: str
    ) -> Dict[str, Any]:
        """
        Compute alignment scores for a multimodal group.
        """
        # Find items in group
        result = await db.execute(
            select(DataItem).where(
                DataItem.item_metadata.contains({"multimodal": {"multimodal_group_id": group_id}})
            )
        )
        items = result.scalars().all()
        
        if len(items) < 2:
            return {"error": "Group not found or incomplete"}
        
        # Categorize by type
        items_by_type = {}
        for item in items:
            items_by_type.setdefault(item.data_type, []).append(item)
        
        alignment_scores = []
        
        # Compute pairwise alignments
        data_types = list(items_by_type.keys())
        
        for i, type1 in enumerate(data_types):
            for type2 in data_types[i+1:]:
                pair_scores = await self._compute_pair_alignment(
                    items_by_type[type1],
                    items_by_type[type2],
                    type1,
                    type2
                )
                alignment_scores.append({
                    "pair": f"{type1}-{type2}",
                    "scores": pair_scores
                })
        
        # Compute overall score
        all_scores = [s for pair in alignment_scores for s in pair["scores"]]
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        return {
            "group_id": group_id,
            "item_count": len(items),
            "data_types": data_types,
            "pair_alignments": alignment_scores,
            "overall_alignment_score": round(overall_score, 4),
            "is_well_aligned": overall_score > 0.5
        }
    
    async def _compute_pair_alignment(
        self,
        items1: List[DataItem],
        items2: List[DataItem],
        type1: str,
        type2: str
    ) -> List[float]:
        """Compute alignment between two sets of items."""
        scores = []
        
        for item1 in items1[:5]:  # Limit for performance
            for item2 in items2[:5]:
                score = await self._compute_item_pair_alignment(item1, item2, type1, type2)
                if score is not None:
                    scores.append(score)
        
        return scores
    
    async def _compute_item_pair_alignment(
        self,
        item1: DataItem,
        item2: DataItem,
        type1: str,
        type2: str
    ) -> Optional[float]:
        """Compute alignment between two specific items."""
        try:
            if type1 == "image" and type2 == "text":
                if item1.file_path and item2.content:
                    image_data = storage_service.download_file(item1.file_path)
                    result = await self.aligner.compute_image_text_similarity(
                        image_data, item2.content
                    )
                    return result.get("similarity_score")
            
            elif type1 == "text" and type2 == "image":
                if item2.file_path and item1.content:
                    image_data = storage_service.download_file(item2.file_path)
                    result = await self.aligner.compute_image_text_similarity(
                        image_data, item1.content
                    )
                    return result.get("similarity_score")
            
            elif type1 == "audio" and type2 == "text":
                transcription = (item1.item_metadata or {}).get("transcription", "")
                if transcription and item2.content:
                    result = await self.aligner.compute_audio_text_similarity(
                        transcription, item2.content
                    )
                    return result.get("similarity_score")
            
            elif type1 == "text" and type2 == "audio":
                transcription = (item2.item_metadata or {}).get("transcription", "")
                if transcription and item1.content:
                    result = await self.aligner.compute_audio_text_similarity(
                        transcription, item1.content
                    )
                    return result.get("similarity_score")
            
        except Exception as e:
            logger.warning(f"Pair alignment error: {e}")
        
        return None
    
    async def find_unaligned_items(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Find items that are not part of any multimodal group.
        """
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        unaligned = []
        grouped = []
        
        for item in items:
            metadata = item.item_metadata or {}
            if "multimodal" in metadata:
                grouped.append(str(item.id))
            else:
                unaligned.append({
                    "id": str(item.id),
                    "data_type": item.data_type,
                    "created_at": item.created_at.isoformat() if item.created_at else None
                })
        
        return {
            "total_items": len(items),
            "grouped_count": len(grouped),
            "unaligned_count": len(unaligned),
            "unaligned_items": unaligned
        }
    
    async def auto_align_by_timestamp(
        self,
        db: AsyncSession,
        project_id: UUID,
        time_window_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Automatically create multimodal groups based on timestamp proximity.
        """
        result = await db.execute(
            select(DataItem)
            .where(DataItem.project_id == project_id)
            .order_by(DataItem.created_at)
        )
        items = result.scalars().all()
        
        if len(items) < 2:
            return {"error": "Not enough items"}
        
        groups_created = 0
        current_group = [items[0]]
        
        for item in items[1:]:
            if not current_group[-1].created_at or not item.created_at:
                continue
            
            time_diff = (item.created_at - current_group[-1].created_at).total_seconds()
            
            if time_diff <= time_window_seconds:
                current_group.append(item)
            else:
                # Create group if multiple items and different types
                if len(current_group) >= 2:
                    types = set(i.data_type for i in current_group)
                    if len(types) >= 2:
                        await self.create_multimodal_group(
                            db,
                            project_id,
                            [i.id for i in current_group],
                            alignment_type="temporal"
                        )
                        groups_created += 1
                
                current_group = [item]
        
        # Handle last group
        if len(current_group) >= 2:
            types = set(i.data_type for i in current_group)
            if len(types) >= 2:
                await self.create_multimodal_group(
                    db,
                    project_id,
                    [i.id for i in current_group],
                    alignment_type="temporal"
                )
                groups_created += 1
        
        return {
            "groups_created": groups_created,
            "time_window_seconds": time_window_seconds,
            "items_processed": len(items)
        }
    
    async def get_group_details(
        self,
        db: AsyncSession,
        group_id: str
    ) -> Dict[str, Any]:
        """Get details of a multimodal group."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.item_metadata.contains({"multimodal": {"multimodal_group_id": group_id}})
            )
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "Group not found"}
        
        group_info = (items[0].item_metadata or {}).get("multimodal", {})
        
        return {
            "group_id": group_id,
            "group_name": group_info.get("multimodal_group_name"),
            "alignment_type": group_info.get("multimodal_alignment_type"),
            "created_at": group_info.get("multimodal_created_at"),
            "items": [
                {
                    "id": str(item.id),
                    "data_type": item.data_type,
                    "has_content": bool(item.content),
                    "has_file": bool(item.file_path)
                }
                for item in items
            ]
        }
    
    async def list_groups(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """List all multimodal groups in a project."""
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        groups = {}
        for item in items:
            metadata = item.item_metadata or {}
            if "multimodal" in metadata:
                group_id = metadata["multimodal"].get("multimodal_group_id")
                if group_id:
                    if group_id not in groups:
                        groups[group_id] = {
                            "group_id": group_id,
                            "group_name": metadata["multimodal"].get("multimodal_group_name"),
                            "alignment_type": metadata["multimodal"].get("multimodal_alignment_type"),
                            "created_at": metadata["multimodal"].get("multimodal_created_at"),
                            "data_types": set(),
                            "item_count": 0
                        }
                    groups[group_id]["data_types"].add(item.data_type)
                    groups[group_id]["item_count"] += 1
        
        # Convert sets to lists
        for g in groups.values():
            g["data_types"] = list(g["data_types"])
        
        return {
            "total_groups": len(groups),
            "groups": list(groups.values())
        }
    
    async def delete_group(
        self,
        db: AsyncSession,
        group_id: str
    ) -> Dict[str, Any]:
        """Delete a multimodal group (removes group metadata from items)."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.item_metadata.contains({"multimodal": {"multimodal_group_id": group_id}})
            )
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "Group not found"}
        
        # Remove multimodal metadata from items
        for item in items:
            metadata = item.item_metadata or {}
            if "multimodal" in metadata:
                del metadata["multimodal"]
                item.item_metadata = metadata
        
        await db.commit()
        
        return {
            "success": True,
            "group_id": group_id,
            "items_updated": len(items)
        }
    
    async def cross_modal_search(
        self,
        db: AsyncSession,
        project_id: UUID,
        query_text: str,
        target_modality: str = "image",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for items using text query across modalities.
        
        Args:
            query_text: Text query
            target_modality: Type of items to search (image, audio, video)
            limit: Max results
        """
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id,
                DataItem.data_type == target_modality
            ).limit(limit * 2)  # Get more for scoring
        )
        items = result.scalars().all()
        
        if not items:
            return {"results": [], "total": 0}
        
        scored_items = []
        
        for item in items:
            score = 0.0
            
            if target_modality == "image" and item.file_path:
                try:
                    image_data = storage_service.download_file(item.file_path)
                    result = await self.aligner.compute_image_text_similarity(image_data, query_text)
                    score = result.get("similarity_score", 0.0)
                except Exception:
                    pass
            
            elif target_modality == "audio":
                transcription = (item.item_metadata or {}).get("transcription", "")
                if transcription:
                    result = await self.aligner.compute_audio_text_similarity(transcription, query_text)
                    score = result.get("similarity_score", 0.0)
            
            elif target_modality == "video" and item.file_path:
                # For video, search in metadata/transcription if available
                metadata = item.item_metadata or {}
                transcription = metadata.get("transcription", "")
                description = metadata.get("description", "")
                search_text = f"{transcription} {description}".strip()
                
                if search_text:
                    result = await self.aligner.compute_audio_text_similarity(search_text, query_text)
                    score = result.get("similarity_score", 0.0)
            
            if score > 0:
                scored_items.append({
                    "id": str(item.id),
                    "data_type": item.data_type,
                    "score": round(score, 4),
                    "has_file": bool(item.file_path)
                })
        
        # Sort by score
        scored_items.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "query": query_text,
            "target_modality": target_modality,
            "results": scored_items[:limit],
            "total": len(scored_items)
        }
    
    async def merge_groups(
        self,
        db: AsyncSession,
        group_ids: List[str],
        new_group_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Merge multiple groups into one."""
        all_items = []
        project_id = None
        
        for gid in group_ids:
            result = await db.execute(
                select(DataItem).where(
                    DataItem.item_metadata.contains({"multimodal": {"multimodal_group_id": gid}})
                )
            )
            items = result.scalars().all()
            if items:
                all_items.extend(items)
                if not project_id:
                    project_id = items[0].project_id
        
        if len(all_items) < 2:
            return {"error": "Not enough items to merge"}
        
        # Generate new group ID
        import uuid
        new_group_id = str(uuid.uuid4())
        
        if not new_group_name:
            new_group_name = f"merged_group_{new_group_id[:8]}"
        
        # Update all items with new group info
        group_info = {
            "multimodal_group_id": new_group_id,
            "multimodal_group_name": new_group_name,
            "multimodal_alignment_type": "merged",
            "multimodal_members": [str(item.id) for item in all_items],
            "multimodal_created_at": datetime.utcnow().isoformat(),
            "multimodal_merged_from": group_ids
        }
        
        for item in all_items:
            metadata = item.item_metadata or {}
            metadata["multimodal"] = group_info
            item.item_metadata = metadata
        
        await db.commit()
        
        return {
            "success": True,
            "new_group_id": new_group_id,
            "new_group_name": new_group_name,
            "merged_groups": group_ids,
            "total_items": len(all_items)
        }
    
    async def auto_align_by_content_similarity(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.3,
        max_group_size: int = 5
    ) -> Dict[str, Any]:
        """
        Automatically create groups based on content similarity.
        Groups items with high cross-modal similarity scores.
        """
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            )
        )
        items = result.scalars().all()
        
        # Separate by type
        text_items = [i for i in items if i.data_type == "text"]
        image_items = [i for i in items if i.data_type == "image"]
        audio_items = [i for i in items if i.data_type == "audio"]
        
        groups_created = 0
        
        # Try to match text with images
        for text_item in text_items[:20]:  # Limit for performance
            if not text_item.content:
                continue
            
            best_matches = []
            
            for img_item in image_items[:20]:
                if not img_item.file_path:
                    continue
                
                # Check if already in a group
                if (img_item.item_metadata or {}).get("multimodal"):
                    continue
                
                try:
                    image_data = storage_service.download_file(img_item.file_path)
                    result = await self.aligner.compute_image_text_similarity(
                        image_data, text_item.content
                    )
                    score = result.get("similarity_score", 0.0)
                    
                    if score >= similarity_threshold:
                        best_matches.append((img_item, score))
                except Exception:
                    continue
            
            # Create group with best matches
            if best_matches:
                best_matches.sort(key=lambda x: x[1], reverse=True)
                group_items = [text_item] + [m[0] for m in best_matches[:max_group_size-1]]
                
                if len(group_items) >= 2:
                    await self.create_multimodal_group(
                        db,
                        project_id,
                        [i.id for i in group_items],
                        alignment_type="content_similarity"
                    )
                    groups_created += 1
        
        return {
            "groups_created": groups_created,
            "similarity_threshold": similarity_threshold,
            "text_items_processed": len(text_items[:20]),
            "image_items_processed": len(image_items[:20])
        }
    
    async def get_alignment_statistics(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive alignment statistics for a project."""
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        # Count by type
        type_counts = {}
        grouped_counts = {}
        alignment_types = {}
        
        for item in items:
            data_type = item.data_type
            type_counts[data_type] = type_counts.get(data_type, 0) + 1
            
            metadata = item.item_metadata or {}
            if "multimodal" in metadata:
                grouped_counts[data_type] = grouped_counts.get(data_type, 0) + 1
                align_type = metadata["multimodal"].get("multimodal_alignment_type", "unknown")
                alignment_types[align_type] = alignment_types.get(align_type, 0) + 1
        
        # Calculate coverage
        coverage = {}
        for dtype, count in type_counts.items():
            grouped = grouped_counts.get(dtype, 0)
            coverage[dtype] = {
                "total": count,
                "grouped": grouped,
                "ungrouped": count - grouped,
                "percentage": round(grouped / count * 100, 1) if count > 0 else 0
            }
        
        # Get group list
        groups_result = await self.list_groups(db, project_id)
        
        return {
            "total_items": len(items),
            "grouped_items": sum(grouped_counts.values()),
            "ungrouped_items": len(items) - sum(grouped_counts.values()),
            "coverage_by_type": coverage,
            "alignment_types": alignment_types,
            "total_groups": groups_result["total_groups"],
            "modalities_present": list(type_counts.keys())
        }


# Global instance
multimodal_service = MultimodalService()
