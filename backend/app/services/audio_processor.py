"""Audio Processing Service with Whisper transcription."""
import io
import os
import tempfile
from typing import Dict, Any, Optional, List
from uuid import UUID
import structlog
import subprocess

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class AudioProcessor:
    """Audio processing utilities."""
    
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.webm'}
    
    def __init__(self):
        self._whisper_model = None
        self._whisper_available = False
        
        try:
            import whisper
            self._whisper_available = True
        except ImportError:
            logger.warning("Whisper not installed, transcription will not be available")
    
    def load_whisper_model(self, model_size: str = "base"):
        """Load Whisper model."""
        if not self._whisper_available:
            raise ImportError("Whisper is not installed")
        
        if self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model(model_size)
        
        return self._whisper_model
    
    async def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get audio file metadata using ffprobe."""
        try:
            result = subprocess.run([
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                audio_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                format_info = data.get('format', {})
                
                info = {
                    "duration": float(format_info.get('duration', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "size": int(format_info.get('size', 0)),
                }
                
                if audio_stream:
                    info.update({
                        "codec": audio_stream.get('codec_name', ''),
                        "sample_rate": int(audio_stream.get('sample_rate', 0)),
                        "channels": int(audio_stream.get('channels', 0)),
                        "channel_layout": audio_stream.get('channel_layout', ''),
                    })
                
                return info
        except Exception as e:
            logger.warning(f"Could not get audio info: {e}")
        
        return {}
    
    async def convert_format(
        self, 
        input_path: str, 
        output_format: str = "wav",
        sample_rate: int = 16000
    ) -> str:
        """Convert audio to different format."""
        output_path = input_path.rsplit('.', 1)[0] + f".{output_format}"
        
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ar', str(sample_rate),
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                output_path
            ], check=True, capture_output=True)
            
            return output_path
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            raise
    
    async def transcribe(
        self, 
        audio_path: str,
        model_size: str = "base",
        language: Optional[str] = None,
        task: str = "transcribe"  # or "translate" for English translation
    ) -> Dict[str, Any]:
        """Transcribe audio using Whisper."""
        if not self._whisper_available:
            return {"error": "Whisper not installed"}
        
        try:
            model = self.load_whisper_model(model_size)
            
            result = model.transcribe(
                audio_path,
                language=language,
                task=task,
                verbose=False
            )
            
            return {
                "text": result["text"],
                "language": result.get("language"),
                "segments": [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                    }
                    for seg in result.get("segments", [])
                ]
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"error": str(e)}
    
    async def extract_features(self, audio_path: str) -> Dict[str, Any]:
        """Extract audio features for ML."""
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Duration
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Energy/RMS
            rms = librosa.feature.rms(y=y)[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            # Spectral centroid
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            
            # MFCC (commonly used for speech)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            
            return {
                "duration": round(duration, 2),
                "sample_rate": sr,
                "rms_mean": round(float(np.mean(rms)), 4),
                "rms_std": round(float(np.std(rms)), 4),
                "zcr_mean": round(float(np.mean(zcr)), 4),
                "spectral_centroid_mean": round(float(np.mean(spectral_centroid)), 2),
                "mfcc_mean": [round(float(x), 4) for x in np.mean(mfccs, axis=1)],
            }
        except ImportError:
            logger.warning("librosa not installed")
            return {}
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return {}
    
    async def split_audio(
        self, 
        input_path: str,
        output_dir: str,
        segment_length: float = 30.0
    ) -> List[str]:
        """Split audio into segments."""
        segments = []
        
        try:
            info = await self.get_audio_info(input_path)
            duration = info.get("duration", 0)
            
            if duration <= segment_length:
                return [input_path]
            
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]
            ext = input_path.rsplit('.', 1)[1]
            
            start = 0
            segment_num = 0
            
            while start < duration:
                output_path = os.path.join(output_dir, f"{base_name}_seg{segment_num:03d}.{ext}")
                
                subprocess.run([
                    'ffmpeg',
                    '-i', input_path,
                    '-ss', str(start),
                    '-t', str(segment_length),
                    '-c', 'copy',
                    '-y',
                    output_path
                ], check=True, capture_output=True)
                
                segments.append(output_path)
                start += segment_length
                segment_num += 1
            
            return segments
        except Exception as e:
            logger.error(f"Audio split error: {e}")
            return [input_path]
    
    async def normalize_audio(
        self, 
        input_path: str, 
        target_db: float = -20.0
    ) -> str:
        """Normalize audio volume."""
        output_path = input_path.rsplit('.', 1)[0] + "_normalized." + input_path.rsplit('.', 1)[1]
        
        try:
            # Get current loudness
            result = subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-af', 'volumedetect',
                '-f', 'null',
                '-'
            ], capture_output=True, text=True)
            
            # Parse mean volume
            import re
            match = re.search(r'mean_volume: ([-\d.]+) dB', result.stderr)
            if match:
                current_db = float(match.group(1))
                adjustment = target_db - current_db
                
                # Apply volume adjustment
                subprocess.run([
                    'ffmpeg',
                    '-i', input_path,
                    '-af', f'volume={adjustment}dB',
                    '-y',
                    output_path
                ], check=True, capture_output=True)
                
                return output_path
        except Exception as e:
            logger.error(f"Normalization error: {e}")
        
        return input_path
    
    async def reduce_noise(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        noise_reduction_amount: float = 1.0,
        stationary: bool = True
    ) -> Dict[str, Any]:
        """
        Reduce background noise from audio.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output file (auto-generated if None)
            noise_reduction_amount: Strength of noise reduction (0.0 to 1.0)
            stationary: True for stationary noise (fans, AC), False for non-stationary
            
        Returns:
            Dict with output_path and processing info
        """
        if output_path is None:
            output_path = input_path.rsplit('.', 1)[0] + "_denoised.wav"
        
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(input_path, sr=None)
            original_rms = float(np.sqrt(np.mean(y**2)))
            
            # Try noisereduce library first
            try:
                import noisereduce as nr
                
                # Reduce noise
                y_reduced = nr.reduce_noise(
                    y=y, 
                    sr=sr, 
                    prop_decrease=noise_reduction_amount,
                    stationary=stationary
                )
                
                method = "noisereduce"
                
            except ImportError:
                # Fallback: Simple spectral gating
                logger.info("noisereduce not installed, using spectral gating fallback")
                
                # Compute STFT
                stft = librosa.stft(y)
                magnitude = np.abs(stft)
                phase = np.angle(stft)
                
                # Estimate noise from first 0.5 seconds
                noise_frames = int(0.5 * sr / 512)  # 512 is default hop_length
                noise_profile = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
                
                # Spectral gating
                threshold = noise_profile * (2 - noise_reduction_amount)
                mask = magnitude > threshold
                magnitude_reduced = magnitude * mask
                
                # Reconstruct
                stft_reduced = magnitude_reduced * np.exp(1j * phase)
                y_reduced = librosa.istft(stft_reduced)
                
                method = "spectral_gating"
            
            # Save output
            import soundfile as sf
            sf.write(output_path, y_reduced, sr)
            
            # Compute metrics
            reduced_rms = float(np.sqrt(np.mean(y_reduced**2)))
            noise_removed_db = 20 * np.log10(original_rms / max(reduced_rms, 1e-10))
            
            return {
                "output_path": output_path,
                "method": method,
                "original_rms": round(original_rms, 6),
                "reduced_rms": round(reduced_rms, 6),
                "noise_removed_db": round(float(noise_removed_db), 2),
                "sample_rate": sr,
                "success": True
            }
            
        except ImportError as e:
            logger.error(f"Missing library for noise reduction: {e}")
            return {"error": f"Missing library: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Noise reduction error: {e}")
            return {"error": str(e), "success": False}
    
    async def detect_voice_activity(
        self,
        audio_path: str,
        energy_threshold: float = 0.02,
        min_speech_duration: float = 0.3
    ) -> Dict[str, Any]:
        """
        Detect voice activity regions in audio.
        
        Returns segments where speech is detected.
        """
        try:
            import librosa
            import numpy as np
            
            y, sr = librosa.load(audio_path, sr=None)
            
            # Compute RMS energy
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.010 * sr)    # 10ms hop
            
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Normalize RMS
            rms_normalized = rms / max(np.max(rms), 1e-10)
            
            # Detect speech frames
            is_speech = rms_normalized > energy_threshold
            
            # Convert frames to time segments
            segments = []
            in_speech = False
            start_time = 0
            
            for i, speech in enumerate(is_speech):
                time = i * hop_length / sr
                
                if speech and not in_speech:
                    start_time = time
                    in_speech = True
                elif not speech and in_speech:
                    if time - start_time >= min_speech_duration:
                        segments.append({
                            "start": round(start_time, 3),
                            "end": round(time, 3),
                            "duration": round(time - start_time, 3)
                        })
                    in_speech = False
            
            # Handle final segment
            if in_speech:
                end_time = len(y) / sr
                if end_time - start_time >= min_speech_duration:
                    segments.append({
                        "start": round(start_time, 3),
                        "end": round(end_time, 3),
                        "duration": round(end_time - start_time, 3)
                    })
            
            total_speech = sum(s["duration"] for s in segments)
            total_duration = len(y) / sr
            
            return {
                "segments": segments,
                "total_speech_duration": round(total_speech, 2),
                "total_duration": round(total_duration, 2),
                "speech_ratio": round(total_speech / total_duration, 3) if total_duration > 0 else 0,
                "segment_count": len(segments)
            }
            
        except ImportError:
            return {"error": "librosa not installed"}
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return {"error": str(e)}
    
    async def trim_silence(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        top_db: int = 30
    ) -> Dict[str, Any]:
        """
        Trim leading and trailing silence from audio.
        
        Args:
            input_path: Path to input audio
            output_path: Path for trimmed output
            top_db: Threshold in dB below reference to consider silence
        """
        if output_path is None:
            output_path = input_path.rsplit('.', 1)[0] + "_trimmed.wav"
        
        try:
            import librosa
            import soundfile as sf
            
            y, sr = librosa.load(input_path, sr=None)
            original_duration = len(y) / sr
            
            # Trim silence
            y_trimmed, index = librosa.effects.trim(y, top_db=top_db)
            trimmed_duration = len(y_trimmed) / sr
            
            # Save
            sf.write(output_path, y_trimmed, sr)
            
            return {
                "output_path": output_path,
                "original_duration": round(original_duration, 2),
                "trimmed_duration": round(trimmed_duration, 2),
                "removed_duration": round(original_duration - trimmed_duration, 2),
                "trim_start": round(index[0] / sr, 3),
                "trim_end": round(index[1] / sr, 3),
                "success": True
            }
            
        except ImportError:
            return {"error": "librosa not installed", "success": False}
        except Exception as e:
            logger.error(f"Trim silence error: {e}")
            return {"error": str(e), "success": False}


# Global instance
audio_processor = AudioProcessor()


async def process_audio_item(
    item: DataItem, 
    db: AsyncSession, 
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Process an audio data item."""
    options = options or {}
    result = {}
    
    if not item.file_path:
        return {"error": "No file path"}
    
    temp_dir = tempfile.mkdtemp()
    temp_file = None
    
    try:
        # Download audio
        audio_data = storage_service.download_file(item.file_path)
        ext = item.file_path.rsplit('.', 1)[-1]
        temp_file = os.path.join(temp_dir, f"audio.{ext}")
        
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        
        # Get info
        if options.get("get_info", True):
            info = await audio_processor.get_audio_info(temp_file)
            metadata = item.item_metadata or {}
            metadata.update(info)
            item.item_metadata = metadata
            result["info"] = info
        
        # Transcribe
        if options.get("transcribe", False):
            model_size = options.get("whisper_model", "base")
            language = options.get("language")
            task = options.get("transcribe_task", "transcribe")
            
            transcription = await audio_processor.transcribe(
                temp_file, model_size, language, task
            )
            
            if "error" not in transcription:
                metadata = item.item_metadata or {}
                metadata["transcription"] = transcription["text"]
                metadata["detected_language"] = transcription.get("language")
                if options.get("include_segments", False):
                    metadata["segments"] = transcription.get("segments", [])
                item.item_metadata = metadata
                
                # Also save as content for text processing
                item.content = transcription["text"]
                
                result["transcription"] = transcription["text"][:1000]  # Limit
                result["language"] = transcription.get("language")
        
        # Extract features
        if options.get("extract_features", False):
            features = await audio_processor.extract_features(temp_file)
            if features:
                metadata = item.item_metadata or {}
                metadata["audio_features"] = features
                item.item_metadata = metadata
                result["features"] = features
        
        # Convert format
        if options.get("convert_format"):
            target_format = options["convert_format"]
            sample_rate = options.get("sample_rate", 16000)
            
            converted_path = await audio_processor.convert_format(
                temp_file, target_format, sample_rate
            )
            
            # Upload converted file
            with open(converted_path, 'rb') as f:
                converted_data = f.read()
            
            new_path = storage_service.upload_file(
                io.BytesIO(converted_data),
                f"converted_{item.id}.{target_format}",
                f"audio/{target_format}",
                f"projects/{item.project_id}/audio"
            )
            
            metadata = item.item_metadata or {}
            metadata["converted_path"] = new_path
            item.item_metadata = metadata
            result["converted_path"] = new_path
        
        item.is_processed = True
        await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        return {"error": str(e)}
    
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

