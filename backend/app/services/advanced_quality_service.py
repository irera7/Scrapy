"""Advanced Quality Metrics Service.

Provides advanced quality metrics for various data types:
- Image: Blur detection, brightness/contrast analysis
- Audio: SNR, clarity metrics
- Text: Readability scores, coherence
- General: Completeness, consistency
"""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import io
import structlog
import math
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class ImageQualityAnalyzer:
    """Advanced image quality analysis."""
    
    def __init__(self):
        try:
            from PIL import Image
            import numpy as np
            self.Image = Image
            self.np = np
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("PIL or numpy not available for image quality analysis")
    
    def analyze_blur(self, image_data: bytes) -> Dict[str, Any]:
        """
        Detect blur in image using Laplacian variance.
        Lower variance = more blur.
        """
        if not self.available:
            return {"error": "PIL/numpy not available"}
        
        try:
            image = self.Image.open(io.BytesIO(image_data)).convert('L')
            img_array = self.np.array(image, dtype=float)
            
            # Compute Laplacian
            laplacian = self.np.array([
                [0, 1, 0],
                [1, -4, 1],
                [0, 1, 0]
            ])
            
            from scipy import ndimage
            laplacian_response = ndimage.convolve(img_array, laplacian)
            variance = laplacian_response.var()
            
            # Thresholds (empirically determined)
            if variance < 100:
                blur_level = "high"
                is_blurry = True
            elif variance < 500:
                blur_level = "medium"
                is_blurry = True
            else:
                blur_level = "low"
                is_blurry = False
            
            return {
                "laplacian_variance": round(float(variance), 2),
                "blur_level": blur_level,
                "is_blurry": is_blurry,
                "threshold_used": {"high": 100, "medium": 500}
            }
        except ImportError:
            # Fallback without scipy
            return self._simple_blur_detection(image_data)
        except Exception as e:
            logger.error(f"Blur analysis error: {e}")
            return {"error": str(e)}
    
    def _simple_blur_detection(self, image_data: bytes) -> Dict[str, Any]:
        """Simple blur detection without scipy."""
        try:
            image = self.Image.open(io.BytesIO(image_data)).convert('L')
            img_array = self.np.array(image, dtype=float)
            
            # Use gradient-based approach
            gx = self.np.diff(img_array, axis=1)
            gy = self.np.diff(img_array, axis=0)
            
            sharpness = self.np.mean(gx**2) + self.np.mean(gy**2)
            
            if sharpness < 50:
                blur_level = "high"
                is_blurry = True
            elif sharpness < 200:
                blur_level = "medium"
                is_blurry = True
            else:
                blur_level = "low"
                is_blurry = False
            
            return {
                "sharpness_score": round(float(sharpness), 2),
                "blur_level": blur_level,
                "is_blurry": is_blurry
            }
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_brightness(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image brightness and contrast."""
        if not self.available:
            return {"error": "PIL/numpy not available"}
        
        try:
            image = self.Image.open(io.BytesIO(image_data)).convert('RGB')
            img_array = self.np.array(image)
            
            # Convert to grayscale for brightness
            gray = 0.299 * img_array[:,:,0] + 0.587 * img_array[:,:,1] + 0.114 * img_array[:,:,2]
            
            mean_brightness = self.np.mean(gray)
            std_brightness = self.np.std(gray)
            
            # Histogram for exposure analysis
            histogram, _ = self.np.histogram(gray.flatten(), bins=256, range=(0, 256))
            
            # Check for clipping
            underexposed = histogram[:10].sum() / gray.size
            overexposed = histogram[-10:].sum() / gray.size
            
            # Classify brightness
            if mean_brightness < 50:
                brightness_class = "too_dark"
                is_acceptable = False
            elif mean_brightness > 200:
                brightness_class = "too_bright"
                is_acceptable = False
            else:
                brightness_class = "normal"
                is_acceptable = True
            
            # Classify contrast
            if std_brightness < 30:
                contrast_class = "low"
            elif std_brightness > 80:
                contrast_class = "high"
            else:
                contrast_class = "normal"
            
            return {
                "mean_brightness": round(float(mean_brightness), 2),
                "std_brightness": round(float(std_brightness), 2),
                "brightness_class": brightness_class,
                "contrast_class": contrast_class,
                "underexposed_ratio": round(float(underexposed), 4),
                "overexposed_ratio": round(float(overexposed), 4),
                "is_acceptable": is_acceptable and underexposed < 0.3 and overexposed < 0.3
            }
        except Exception as e:
            logger.error(f"Brightness analysis error: {e}")
            return {"error": str(e)}
    
    def analyze_resolution(self, image_data: bytes, min_size: int = 224) -> Dict[str, Any]:
        """Check if image meets minimum resolution requirements."""
        if not self.available:
            return {"error": "PIL not available"}
        
        try:
            image = self.Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            meets_minimum = width >= min_size and height >= min_size
            
            # Classify resolution
            min_dim = min(width, height)
            if min_dim < 100:
                resolution_class = "very_low"
            elif min_dim < 224:
                resolution_class = "low"
            elif min_dim < 512:
                resolution_class = "medium"
            elif min_dim < 1024:
                resolution_class = "high"
            else:
                resolution_class = "very_high"
            
            return {
                "width": width,
                "height": height,
                "min_dimension": min_dim,
                "resolution_class": resolution_class,
                "meets_minimum": meets_minimum,
                "min_required": min_size,
                "megapixels": round(width * height / 1_000_000, 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def full_analysis(self, image_data: bytes) -> Dict[str, Any]:
        """Run full image quality analysis."""
        results = {
            "blur": self.analyze_blur(image_data),
            "brightness": self.analyze_brightness(image_data),
            "resolution": self.analyze_resolution(image_data)
        }
        
        # Compute overall score
        score = 1.0
        issues = []
        
        if results["blur"].get("is_blurry"):
            score -= 0.3
            issues.append("image_is_blurry")
        
        if not results["brightness"].get("is_acceptable", True):
            score -= 0.2
            issues.append(f"brightness_{results['brightness'].get('brightness_class', 'issue')}")
        
        if not results["resolution"].get("meets_minimum", True):
            score -= 0.3
            issues.append("resolution_too_low")
        
        results["overall_score"] = max(0, round(score, 2))
        results["issues"] = issues
        results["quality_acceptable"] = score >= 0.5
        
        return results


class AudioQualityAnalyzer:
    """Advanced audio quality analysis."""
    
    def __init__(self):
        self.available = False
        try:
            import numpy as np
            self.np = np
            self.available = True
        except ImportError:
            logger.warning("numpy not available for audio quality analysis")
    
    async def analyze_snr(self, audio_path: str) -> Dict[str, Any]:
        """
        Estimate Signal-to-Noise Ratio.
        Uses voice activity detection to separate signal from noise.
        """
        if not self.available:
            return {"error": "numpy not available"}
        
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Compute RMS energy in frames
            frame_length = int(sr * 0.025)  # 25ms frames
            hop_length = int(sr * 0.010)    # 10ms hop
            
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Simple VAD: top 30% RMS frames are signal, bottom 30% are noise
            sorted_rms = self.np.sort(rms)
            n_frames = len(sorted_rms)
            
            noise_rms = self.np.mean(sorted_rms[:int(n_frames * 0.3)])
            signal_rms = self.np.mean(sorted_rms[int(n_frames * 0.7):])
            
            # Calculate SNR in dB
            if noise_rms > 0:
                snr_db = 20 * self.np.log10(signal_rms / noise_rms)
            else:
                snr_db = float('inf')
            
            # Classify SNR
            if snr_db < 10:
                snr_class = "poor"
                is_acceptable = False
            elif snr_db < 20:
                snr_class = "fair"
                is_acceptable = True
            elif snr_db < 30:
                snr_class = "good"
                is_acceptable = True
            else:
                snr_class = "excellent"
                is_acceptable = True
            
            return {
                "snr_db": round(float(snr_db), 2),
                "snr_class": snr_class,
                "signal_rms": round(float(signal_rms), 6),
                "noise_rms": round(float(noise_rms), 6),
                "is_acceptable": is_acceptable,
                "threshold": {"poor": 10, "fair": 20, "good": 30}
            }
        except ImportError:
            return {"error": "librosa not installed"}
        except Exception as e:
            logger.error(f"SNR analysis error: {e}")
            return {"error": str(e)}
    
    async def analyze_clarity(self, audio_path: str) -> Dict[str, Any]:
        """Analyze audio clarity using spectral features."""
        if not self.available:
            return {"error": "numpy not available"}
        
        try:
            import librosa
            
            y, sr = librosa.load(audio_path, sr=None)
            
            # Spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            mean_centroid = self.np.mean(spectral_centroid)
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            mean_rolloff = self.np.mean(spectral_rolloff)
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
            mean_bandwidth = self.np.mean(spectral_bandwidth)
            
            # Zero crossing rate (high = noisy)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            mean_zcr = self.np.mean(zcr)
            
            # Compute clarity score (heuristic)
            # Good speech: moderate centroid, low ZCR
            clarity_score = min(1.0, max(0.0,
                0.5 + (mean_centroid / 4000) * 0.3 - mean_zcr * 0.5
            ))
            
            return {
                "spectral_centroid": round(float(mean_centroid), 2),
                "spectral_rolloff": round(float(mean_rolloff), 2),
                "spectral_bandwidth": round(float(mean_bandwidth), 2),
                "zero_crossing_rate": round(float(mean_zcr), 4),
                "clarity_score": round(float(clarity_score), 3),
                "is_clear": clarity_score > 0.4
            }
        except ImportError:
            return {"error": "librosa not installed"}
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_duration(
        self, 
        audio_path: str, 
        min_duration: float = 1.0,
        max_duration: float = 300.0
    ) -> Dict[str, Any]:
        """Check audio duration constraints."""
        try:
            import librosa
            
            duration = librosa.get_duration(path=audio_path)
            
            is_valid = min_duration <= duration <= max_duration
            
            if duration < min_duration:
                issue = "too_short"
            elif duration > max_duration:
                issue = "too_long"
            else:
                issue = None
            
            return {
                "duration_seconds": round(duration, 2),
                "is_valid": is_valid,
                "issue": issue,
                "min_required": min_duration,
                "max_allowed": max_duration
            }
        except ImportError:
            return {"error": "librosa not installed"}
        except Exception as e:
            return {"error": str(e)}


class TextQualityAnalyzer:
    """Advanced text quality analysis."""
    
    def compute_readability(self, text: str) -> Dict[str, Any]:
        """
        Compute readability scores.
        Includes Flesch Reading Ease and Flesch-Kincaid Grade Level.
        """
        if not text:
            return {"error": "Empty text"}
        
        # Count sentences, words, syllables
        sentences = self._count_sentences(text)
        words = self._count_words(text)
        syllables = self._count_syllables(text)
        
        if sentences == 0 or words == 0:
            return {"error": "Cannot compute readability for this text"}
        
        # Flesch Reading Ease
        # 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        fre = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        fre = max(0, min(100, fre))
        
        # Flesch-Kincaid Grade Level
        # 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
        fkgl = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        fkgl = max(0, fkgl)
        
        # Interpret FRE
        if fre >= 90:
            difficulty = "very_easy"
        elif fre >= 80:
            difficulty = "easy"
        elif fre >= 70:
            difficulty = "fairly_easy"
        elif fre >= 60:
            difficulty = "standard"
        elif fre >= 50:
            difficulty = "fairly_difficult"
        elif fre >= 30:
            difficulty = "difficult"
        else:
            difficulty = "very_difficult"
        
        return {
            "flesch_reading_ease": round(fre, 2),
            "flesch_kincaid_grade": round(fkgl, 1),
            "difficulty": difficulty,
            "statistics": {
                "sentences": sentences,
                "words": words,
                "syllables": syllables,
                "avg_words_per_sentence": round(words / sentences, 1),
                "avg_syllables_per_word": round(syllables / words, 2)
            }
        }
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        import re
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        import re
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    def _count_syllables(self, text: str) -> int:
        """Estimate syllable count (English)."""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        
        total = 0
        for word in words:
            # Simple syllable counting
            syllables = len(re.findall(r'[aeiouy]+', word))
            # Adjust for silent e
            if word.endswith('e') and syllables > 1:
                syllables -= 1
            total += max(1, syllables)
        
        return total
    
    def compute_coherence(self, text: str) -> Dict[str, Any]:
        """
        Compute text coherence metrics.
        Based on vocabulary richness and structure.
        """
        if not text:
            return {"error": "Empty text"}
        
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        
        if len(words) < 10:
            return {"error": "Text too short for coherence analysis"}
        
        # Type-Token Ratio (vocabulary richness)
        unique_words = set(words)
        ttr = len(unique_words) / len(words)
        
        # Hapax Legomena ratio (words appearing once)
        word_freq = Counter(words)
        hapax = sum(1 for count in word_freq.values() if count == 1)
        hapax_ratio = hapax / len(unique_words) if unique_words else 0
        
        # Average word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Coherence score (heuristic)
        coherence_score = (
            0.4 * min(1, ttr * 2) +  # Vocabulary richness
            0.3 * (1 - hapax_ratio) +  # Word reuse
            0.3 * min(1, avg_word_length / 6)  # Word complexity
        )
        
        return {
            "type_token_ratio": round(ttr, 4),
            "vocabulary_richness": "high" if ttr > 0.6 else "medium" if ttr > 0.4 else "low",
            "hapax_ratio": round(hapax_ratio, 4),
            "unique_words": len(unique_words),
            "total_words": len(words),
            "avg_word_length": round(avg_word_length, 2),
            "coherence_score": round(coherence_score, 3)
        }
    
    def detect_language_consistency(self, text: str) -> Dict[str, Any]:
        """Check if text maintains consistent language."""
        try:
            from langdetect import detect_langs
            
            # Split into sentences and detect language of each
            import re
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            if len(sentences) < 2:
                return {"consistent": True, "primary_language": "unknown"}
            
            languages = []
            for sent in sentences[:10]:  # Check first 10 sentences
                try:
                    langs = detect_langs(sent)
                    if langs:
                        languages.append(langs[0].lang)
                except:
                    pass
            
            if not languages:
                return {"consistent": True, "primary_language": "unknown"}
            
            primary_lang = Counter(languages).most_common(1)[0][0]
            consistency = sum(1 for l in languages if l == primary_lang) / len(languages)
            
            return {
                "consistent": consistency > 0.8,
                "consistency_ratio": round(consistency, 2),
                "primary_language": primary_lang,
                "detected_languages": list(set(languages))
            }
        except ImportError:
            return {"error": "langdetect not installed"}
        except Exception as e:
            return {"error": str(e)}


class VideoQualityAnalyzer:
    """Advanced video quality analysis."""
    
    def __init__(self):
        self.available = False
        try:
            import numpy as np
            self.np = np
            self.available = True
        except ImportError:
            logger.warning("numpy not available for video quality analysis")
    
    async def analyze_frame_quality(self, video_path: str, sample_frames: int = 10) -> Dict[str, Any]:
        """
        Analyze quality of video frames.
        Samples frames and checks for blur, brightness issues.
        """
        import subprocess
        import tempfile
        import os
        
        if not self.available:
            return {"error": "numpy not available"}
        
        try:
            from PIL import Image
            
            # Create temp directory for frames
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract sample frames using ffmpeg
                result = subprocess.run([
                    'ffmpeg', '-i', video_path,
                    '-vf', f'fps=1/{max(1, sample_frames)}',
                    '-frames:v', str(sample_frames),
                    os.path.join(temp_dir, 'frame_%04d.jpg')
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {"error": "Failed to extract frames"}
                
                # Analyze each frame
                frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
                
                blur_scores = []
                brightness_scores = []
                
                for frame_file in frame_files:
                    frame_path = os.path.join(temp_dir, frame_file)
                    
                    img = Image.open(frame_path).convert('L')
                    img_array = self.np.array(img, dtype=float)
                    
                    # Blur detection (gradient-based)
                    gx = self.np.diff(img_array, axis=1)
                    gy = self.np.diff(img_array, axis=0)
                    sharpness = self.np.mean(gx**2) + self.np.mean(gy**2)
                    blur_scores.append(sharpness)
                    
                    # Brightness
                    brightness = self.np.mean(img_array)
                    brightness_scores.append(brightness)
                
                if not blur_scores:
                    return {"error": "No frames analyzed"}
                
                avg_blur = sum(blur_scores) / len(blur_scores)
                avg_brightness = sum(brightness_scores) / len(brightness_scores)
                
                # Count problematic frames
                blurry_frames = sum(1 for s in blur_scores if s < 50)
                dark_frames = sum(1 for b in brightness_scores if b < 50)
                bright_frames = sum(1 for b in brightness_scores if b > 200)
                
                return {
                    "frames_analyzed": len(blur_scores),
                    "average_sharpness": round(float(avg_blur), 2),
                    "average_brightness": round(float(avg_brightness), 2),
                    "blurry_frames": blurry_frames,
                    "dark_frames": dark_frames,
                    "bright_frames": bright_frames,
                    "blurry_ratio": round(blurry_frames / len(blur_scores), 3),
                    "is_acceptable": blurry_frames < len(blur_scores) * 0.3
                }
                
        except Exception as e:
            logger.error(f"Video frame analysis error: {e}")
            return {"error": str(e)}
    
    async def compute_video_hash(self, video_path: str, num_keyframes: int = 5) -> Dict[str, Any]:
        """
        Compute perceptual hash for video based on keyframes.
        Useful for duplicate detection.
        """
        import subprocess
        import tempfile
        import os
        
        try:
            import imagehash
            from PIL import Image
        except ImportError:
            return {"error": "imagehash not installed"}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract keyframes
                result = subprocess.run([
                    'ffmpeg', '-i', video_path,
                    '-vf', 'select=eq(pict_type\\,I)',
                    '-vsync', 'vfr',
                    '-frames:v', str(num_keyframes),
                    os.path.join(temp_dir, 'keyframe_%04d.jpg')
                ], capture_output=True, text=True)
                
                frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
                
                if not frame_files:
                    # Fallback to regular frames
                    result = subprocess.run([
                        'ffmpeg', '-i', video_path,
                        '-frames:v', str(num_keyframes),
                        os.path.join(temp_dir, 'frame_%04d.jpg')
                    ], capture_output=True, text=True)
                    frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
                
                if not frame_files:
                    return {"error": "Could not extract frames"}
                
                # Compute hash for each frame
                frame_hashes = []
                for frame_file in frame_files:
                    frame_path = os.path.join(temp_dir, frame_file)
                    img = Image.open(frame_path)
                    phash = str(imagehash.phash(img))
                    frame_hashes.append(phash)
                
                # Combine hashes
                combined_hash = "_".join(frame_hashes)
                
                return {
                    "video_hash": combined_hash,
                    "keyframes_used": len(frame_hashes),
                    "frame_hashes": frame_hashes
                }
                
        except Exception as e:
            logger.error(f"Video hash computation error: {e}")
            return {"error": str(e)}
    
    async def check_stability(self, video_path: str) -> Dict[str, Any]:
        """
        Check video stability (detect camera shake).
        Uses frame-to-frame difference analysis.
        """
        import subprocess
        import tempfile
        import os
        
        if not self.available:
            return {"error": "numpy not available"}
        
        try:
            from PIL import Image
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract frames at 5 fps for stability check
                result = subprocess.run([
                    'ffmpeg', '-i', video_path,
                    '-vf', 'fps=5',
                    '-frames:v', '30',
                    os.path.join(temp_dir, 'frame_%04d.jpg')
                ], capture_output=True, text=True)
                
                frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
                
                if len(frame_files) < 2:
                    return {"error": "Not enough frames for stability analysis"}
                
                # Calculate frame-to-frame differences
                differences = []
                prev_array = None
                
                for frame_file in frame_files:
                    frame_path = os.path.join(temp_dir, frame_file)
                    img = Image.open(frame_path).convert('L').resize((160, 90))
                    img_array = self.np.array(img, dtype=float)
                    
                    if prev_array is not None:
                        diff = self.np.mean(self.np.abs(img_array - prev_array))
                        differences.append(diff)
                    
                    prev_array = img_array
                
                if not differences:
                    return {"error": "Could not compute differences"}
                
                avg_diff = sum(differences) / len(differences)
                max_diff = max(differences)
                std_diff = self.np.std(differences)
                
                # High variance in differences indicates shake
                is_stable = std_diff < 10 and max_diff < 50
                
                return {
                    "average_frame_difference": round(float(avg_diff), 2),
                    "max_frame_difference": round(float(max_diff), 2),
                    "std_frame_difference": round(float(std_diff), 2),
                    "is_stable": is_stable,
                    "stability_score": round(max(0, 1 - std_diff / 20), 3)
                }
                
        except Exception as e:
            logger.error(f"Video stability check error: {e}")
            return {"error": str(e)}
    
    async def full_analysis(self, video_path: str) -> Dict[str, Any]:
        """Run full video quality analysis."""
        results = {
            "frame_quality": await self.analyze_frame_quality(video_path),
            "stability": await self.check_stability(video_path)
        }
        
        # Compute overall score
        score = 1.0
        issues = []
        
        if results["frame_quality"].get("blurry_ratio", 0) > 0.3:
            score -= 0.3
            issues.append("too_many_blurry_frames")
        
        if not results["stability"].get("is_stable", True):
            score -= 0.2
            issues.append("camera_shake_detected")
        
        results["overall_score"] = max(0, round(score, 2))
        results["issues"] = issues
        results["quality_acceptable"] = score >= 0.5
        
        return results


class AdvancedQualityService:
    """Main service for advanced quality metrics."""
    
    def __init__(self):
        self.image_analyzer = ImageQualityAnalyzer()
        self.audio_analyzer = AudioQualityAnalyzer()
        self.text_analyzer = TextQualityAnalyzer()
        self.video_analyzer = VideoQualityAnalyzer()
    
    async def analyze_item(
        self,
        db: AsyncSession,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Run comprehensive quality analysis on a data item."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": "Item not found"}
        
        analysis_result = {
            "item_id": str(item_id),
            "data_type": item.data_type
        }
        
        if item.data_type == "text" and item.content:
            analysis_result["readability"] = self.text_analyzer.compute_readability(item.content)
            analysis_result["coherence"] = self.text_analyzer.compute_coherence(item.content)
            analysis_result["language_consistency"] = self.text_analyzer.detect_language_consistency(item.content)
            
        elif item.data_type == "image" and item.file_path:
            try:
                image_data = storage_service.download_file(item.file_path)
                analysis_result["image_quality"] = self.image_analyzer.full_analysis(image_data)
            except Exception as e:
                analysis_result["error"] = str(e)
        
        elif item.data_type == "video" and item.file_path:
            try:
                # Download video to temp file for analysis
                import tempfile
                import os
                video_data = storage_service.download_file(item.file_path)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_data)
                    tmp_path = tmp.name
                
                try:
                    analysis_result["video_quality"] = await self.video_analyzer.full_analysis(tmp_path)
                finally:
                    os.unlink(tmp_path)
            except Exception as e:
                analysis_result["error"] = str(e)
        
        # Update item metadata with quality analysis
        metadata = item.item_metadata or {}
        metadata["advanced_quality_analysis"] = analysis_result
        item.item_metadata = metadata
        
        await db.commit()
        
        return analysis_result
    
    async def batch_quality_check(
        self,
        db: AsyncSession,
        project_id: UUID,
        data_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Run quality check on multiple items."""
        query = select(DataItem).where(DataItem.project_id == project_id)
        
        if data_type:
            query = query.where(DataItem.data_type == data_type)
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        results = {
            "total_checked": len(items),
            "passed": 0,
            "failed": 0,
            "issues_summary": Counter()
        }
        
        for item in items:
            try:
                analysis = await self.analyze_item(db, item.id)
                
                # Check if passed
                passed = True
                if "image_quality" in analysis:
                    if not analysis["image_quality"].get("quality_acceptable", True):
                        passed = False
                        for issue in analysis["image_quality"].get("issues", []):
                            results["issues_summary"][issue] += 1
                
                if passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["issues_summary"]["analysis_error"] += 1
        
        results["issues_summary"] = dict(results["issues_summary"])
        results["pass_rate"] = round(results["passed"] / max(1, results["total_checked"]), 3)
        
        return results


# Global instance
advanced_quality_service = AdvancedQualityService()
