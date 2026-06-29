"""Video Processing Service."""
import io
import os
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
import structlog
import subprocess
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class VideoProcessor:
    """Video processing utilities."""
    
    SUPPORTED_FORMATS = {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
    
    def __init__(self):
        self._whisper_model = None
        self._whisper_available = False
        
        try:
            import whisper
            self._whisper_available = True
        except ImportError:
            logger.warning("Whisper not installed, video transcription will not be available")
    
    def load_whisper_model(self, model_size: str = "base"):
        """Load Whisper model for transcription."""
        if not self._whisper_available:
            raise ImportError("Whisper is not installed")
        
        if self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model(model_size)
        
        return self._whisper_model
    
    async def get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get video file metadata using ffprobe."""
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
                data = json.loads(result.stdout)
                
                video_stream = None
                audio_stream = None
                
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video' and not video_stream:
                        video_stream = stream
                    elif stream.get('codec_type') == 'audio' and not audio_stream:
                        audio_stream = stream
                
                format_info = data.get('format', {})
                
                info = {
                    "duration": float(format_info.get('duration', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "size": int(format_info.get('size', 0)),
                }
                
                if video_stream:
                    info.update({
                        "width": int(video_stream.get('width', 0)),
                        "height": int(video_stream.get('height', 0)),
                        "video_codec": video_stream.get('codec_name', ''),
                        "fps": eval(video_stream.get('r_frame_rate', '0/1')) if '/' in video_stream.get('r_frame_rate', '') else 0,
                        "pixel_format": video_stream.get('pix_fmt', ''),
                    })
                    
                    # Calculate aspect ratio
                    if info.get("height", 0) > 0:
                        info["aspect_ratio"] = round(info["width"] / info["height"], 3)
                
                if audio_stream:
                    info.update({
                        "audio_codec": audio_stream.get('codec_name', ''),
                        "audio_sample_rate": int(audio_stream.get('sample_rate', 0)),
                        "audio_channels": int(audio_stream.get('channels', 0)),
                    })
                
                return info
        except Exception as e:
            logger.warning(f"Could not get video info: {e}")
        
        return {}
    
    async def extract_frames(
        self, 
        input_path: str,
        output_dir: str,
        fps: float = 1.0,
        max_frames: int = 100
    ) -> List[str]:
        """Extract frames from video at specified FPS."""
        frames = []
        
        try:
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]
            
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-vf', f'fps={fps}',
                '-frames:v', str(max_frames),
                '-y',
                os.path.join(output_dir, f'{base_name}_frame_%04d.jpg')
            ], check=True, capture_output=True)
            
            # List generated frames
            for f in sorted(os.listdir(output_dir)):
                if f.startswith(base_name) and f.endswith('.jpg'):
                    frames.append(os.path.join(output_dir, f))
            
            return frames[:max_frames]
        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            return []
    
    async def extract_keyframes(
        self, 
        input_path: str,
        output_dir: str,
        max_frames: int = 50
    ) -> List[str]:
        """Extract keyframes (I-frames) from video."""
        frames = []
        
        try:
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]
            
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-vf', 'select=eq(pict_type\\,I)',
                '-vsync', 'vfr',
                '-frames:v', str(max_frames),
                '-y',
                os.path.join(output_dir, f'{base_name}_keyframe_%04d.jpg')
            ], check=True, capture_output=True)
            
            for f in sorted(os.listdir(output_dir)):
                if f.startswith(base_name) and 'keyframe' in f:
                    frames.append(os.path.join(output_dir, f))
            
            return frames[:max_frames]
        except Exception as e:
            logger.error(f"Keyframe extraction error: {e}")
            return []
    
    async def extract_audio(
        self, 
        input_path: str,
        output_format: str = "mp3"
    ) -> Optional[str]:
        """Extract audio track from video."""
        output_path = input_path.rsplit('.', 1)[0] + f"_audio.{output_format}"
        
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame' if output_format == 'mp3' else 'copy',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return output_path
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return None
    
    async def generate_thumbnail(
        self, 
        input_path: str,
        output_path: str,
        time_offset: float = 1.0,
        size: Tuple[int, int] = (320, 180)
    ) -> bool:
        """Generate video thumbnail."""
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ss', str(time_offset),
                '-vframes', '1',
                '-vf', f'scale={size[0]}:{size[1]}',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return True
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")
            return False
    
    async def generate_gif(
        self, 
        input_path: str,
        output_path: str,
        start_time: float = 0,
        duration: float = 5.0,
        fps: int = 10,
        width: int = 320
    ) -> bool:
        """Generate GIF from video segment."""
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return True
        except Exception as e:
            logger.error(f"GIF generation error: {e}")
            return False
    
    async def clip_video(
        self, 
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float
    ) -> bool:
        """Extract a clip from video."""
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return True
        except Exception as e:
            logger.error(f"Video clip error: {e}")
            return False
    
    async def resize_video(
        self, 
        input_path: str,
        output_path: str,
        width: int,
        height: int = -1
    ) -> bool:
        """Resize video."""
        try:
            scale = f'scale={width}:{height}'
            
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-vf', scale,
                '-c:a', 'copy',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return True
        except Exception as e:
            logger.error(f"Video resize error: {e}")
            return False
    
    async def convert_format(
        self, 
        input_path: str,
        output_format: str = "mp4"
    ) -> Optional[str]:
        """Convert video to different format."""
        output_path = input_path.rsplit('.', 1)[0] + f".{output_format}"
        
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                output_path
            ], check=True, capture_output=True)
            
            return output_path
        except Exception as e:
            logger.error(f"Video conversion error: {e}")
            return None
    
    async def detect_scenes(
        self, 
        input_path: str,
        threshold: float = 0.3
    ) -> List[float]:
        """Detect scene changes in video."""
        scenes = []
        
        try:
            result = subprocess.run([
                'ffprobe',
                '-v', 'quiet',
                '-show_frames',
                '-of', 'json',
                '-f', 'lavfi',
                f'movie={input_path},select=gt(scene\\,{threshold})'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for frame in data.get('frames', []):
                    if 'pkt_pts_time' in frame:
                        scenes.append(float(frame['pkt_pts_time']))
            
            return scenes
        except Exception as e:
            logger.warning(f"Scene detection error: {e}")
            return []
    
    async def transcribe_video(
        self, 
        input_path: str,
        model_size: str = "base",
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe video audio using Whisper.
        
        Args:
            input_path: Path to video file
            model_size: Whisper model size (tiny, base, small, medium, large)
            language: Language code (e.g., 'en', 'fa') or None for auto-detect
            task: 'transcribe' or 'translate' (to English)
            
        Returns:
            Dictionary with transcription text, detected language, and segments
        """
        if not self._whisper_available:
            return {"error": "Whisper not installed"}
        
        temp_audio_path = None
        
        try:
            # Extract audio from video
            temp_audio_path = input_path.rsplit('.', 1)[0] + "_audio_temp.wav"
            
            # Use ffmpeg to extract audio as WAV (16kHz, mono - optimal for Whisper)
            extract_result = subprocess.run([
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', input_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                temp_audio_path
            ], capture_output=True, text=True)
            
            if extract_result.returncode != 0:
                logger.warning(f"Audio extraction failed: {extract_result.stderr}")
                return {"error": "Failed to extract audio from video"}
            
            # Load Whisper model and transcribe
            model = self.load_whisper_model(model_size)
            
            result = model.transcribe(
                temp_audio_path,
                language=language,
                task=task,
                verbose=False
            )
            
            return {
                "text": result["text"],
                "language": result.get("language"),
                "segments": [
                    {
                        "id": seg["id"],
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                    }
                    for seg in result.get("segments", [])
                ],
                "duration": result.get("segments", [{}])[-1].get("end", 0) if result.get("segments") else 0
            }
            
        except Exception as e:
            logger.error(f"Video transcription error: {e}")
            return {"error": str(e)}
        
        finally:
            # Cleanup temp audio file
            if temp_audio_path:
                import os
                try:
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
                except:
                    pass
    
    async def transcribe_with_timestamps(
        self, 
        input_path: str,
        model_size: str = "base",
        language: Optional[str] = None,
        output_format: str = "srt"
    ) -> str:
        """
        Transcribe video and generate subtitles.
        
        Args:
            input_path: Path to video file
            model_size: Whisper model size
            language: Language code or None for auto-detect
            output_format: 'srt', 'vtt', or 'txt'
            
        Returns:
            Formatted subtitle string
        """
        transcription = await self.transcribe_video(input_path, model_size, language)
        
        if "error" in transcription:
            return ""
        
        segments = transcription.get("segments", [])
        
        if output_format == "srt":
            lines = []
            for i, seg in enumerate(segments, 1):
                start = self._format_timestamp_srt(seg["start"])
                end = self._format_timestamp_srt(seg["end"])
                lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")
            return "\n".join(lines)
        
        elif output_format == "vtt":
            lines = ["WEBVTT\n"]
            for seg in segments:
                start = self._format_timestamp_vtt(seg["start"])
                end = self._format_timestamp_vtt(seg["end"])
                lines.append(f"\n{start} --> {end}\n{seg['text'].strip()}")
            return "\n".join(lines)
        
        else:  # txt
            return transcription.get("text", "")
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# Global instance
video_processor = VideoProcessor()


async def process_video_item(
    item: DataItem, 
    db: AsyncSession, 
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Process a video data item."""
    options = options or {}
    result = {}
    
    if not item.file_path:
        return {"error": "No file path"}
    
    temp_dir = tempfile.mkdtemp()
    temp_file = None
    
    try:
        # Download video
        video_data = storage_service.download_file(item.file_path)
        ext = item.file_path.rsplit('.', 1)[-1]
        temp_file = os.path.join(temp_dir, f"video.{ext}")
        
        with open(temp_file, 'wb') as f:
            f.write(video_data)
        
        # Get info
        if options.get("get_info", True):
            info = await video_processor.get_video_info(temp_file)
            metadata = item.item_metadata or {}
            metadata.update(info)
            item.item_metadata = metadata
            result["info"] = info
        
        # Generate thumbnail
        if options.get("generate_thumbnail", True):
            thumb_path = os.path.join(temp_dir, "thumbnail.jpg")
            success = await video_processor.generate_thumbnail(
                temp_file, 
                thumb_path,
                time_offset=options.get("thumbnail_offset", 1.0)
            )
            
            if success:
                with open(thumb_path, 'rb') as f:
                    thumb_data = f.read()
                
                storage_thumb_path = storage_service.upload_file(
                    io.BytesIO(thumb_data),
                    f"thumb_{item.id}.jpg",
                    "image/jpeg",
                    f"projects/{item.project_id}/thumbnails"
                )
                
                metadata = item.item_metadata or {}
                metadata["thumbnail_path"] = storage_thumb_path
                item.item_metadata = metadata
                result["thumbnail"] = storage_thumb_path
        
        # Transcribe video with Whisper
        if options.get("transcribe", False):
            model_size = options.get("whisper_model", "base")
            language = options.get("language")
            task = options.get("transcribe_task", "transcribe")
            include_segments = options.get("include_segments", True)
            generate_subtitles = options.get("generate_subtitles", False)
            subtitle_format = options.get("subtitle_format", "srt")
            
            transcription = await video_processor.transcribe_video(
                temp_file, model_size, language, task
            )
            
            if "error" not in transcription:
                metadata = item.item_metadata or {}
                metadata["transcription"] = transcription["text"]
                metadata["detected_language"] = transcription.get("language")
                metadata["transcription_duration"] = transcription.get("duration")
                
                if include_segments:
                    metadata["transcription_segments"] = transcription.get("segments", [])
                
                item.item_metadata = metadata
                
                # Save transcription as content for text-based operations
                item.content = transcription["text"]
                
                result["transcription"] = transcription["text"][:1000]  # Limit for response
                result["language"] = transcription.get("language")
                result["transcription_duration"] = transcription.get("duration")
                
                # Generate subtitle file if requested
                if generate_subtitles:
                    subtitle_content = await video_processor.transcribe_with_timestamps(
                        temp_file, model_size, language, subtitle_format
                    )
                    
                    if subtitle_content:
                        subtitle_ext = subtitle_format
                        subtitle_data = subtitle_content.encode('utf-8')
                        
                        storage_subtitle_path = storage_service.upload_file(
                            io.BytesIO(subtitle_data),
                            f"subtitles_{item.id}.{subtitle_ext}",
                            f"text/{subtitle_format}",
                            f"projects/{item.project_id}/subtitles"
                        )
                        
                        metadata = item.item_metadata or {}
                        metadata["subtitles_path"] = storage_subtitle_path
                        metadata["subtitles_format"] = subtitle_format
                        item.item_metadata = metadata
                        result["subtitles_path"] = storage_subtitle_path
            else:
                result["transcription_error"] = transcription.get("error")
        
        # Extract frames
        if options.get("extract_frames", False):
            fps = options.get("frame_fps", 1.0)
            max_frames = options.get("max_frames", 10)
            
            frames_dir = os.path.join(temp_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)
            
            frame_paths = await video_processor.extract_frames(
                temp_file, frames_dir, fps, max_frames
            )
            
            # Upload frames
            uploaded_frames = []
            for frame_path in frame_paths[:max_frames]:
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()
                
                frame_name = os.path.basename(frame_path)
                storage_path = storage_service.upload_file(
                    io.BytesIO(frame_data),
                    f"{item.id}_{frame_name}",
                    "image/jpeg",
                    f"projects/{item.project_id}/frames"
                )
                uploaded_frames.append(storage_path)
            
            metadata = item.item_metadata or {}
            metadata["extracted_frames"] = uploaded_frames
            item.item_metadata = metadata
            result["frames"] = len(uploaded_frames)
        
        # Extract audio
        if options.get("extract_audio", False):
            audio_path = await video_processor.extract_audio(
                temp_file,
                options.get("audio_format", "mp3")
            )
            
            if audio_path:
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                storage_audio_path = storage_service.upload_file(
                    io.BytesIO(audio_data),
                    f"audio_{item.id}.{options.get('audio_format', 'mp3')}",
                    f"audio/{options.get('audio_format', 'mp3')}",
                    f"projects/{item.project_id}/audio"
                )
                
                metadata = item.item_metadata or {}
                metadata["extracted_audio_path"] = storage_audio_path
                item.item_metadata = metadata
                result["audio_path"] = storage_audio_path
        
        # Generate GIF preview
        if options.get("generate_gif", False):
            gif_path = os.path.join(temp_dir, "preview.gif")
            success = await video_processor.generate_gif(
                temp_file,
                gif_path,
                start_time=options.get("gif_start", 0),
                duration=options.get("gif_duration", 3.0),
                fps=options.get("gif_fps", 10),
                width=options.get("gif_width", 320)
            )
            
            if success:
                with open(gif_path, 'rb') as f:
                    gif_data = f.read()
                
                storage_gif_path = storage_service.upload_file(
                    io.BytesIO(gif_data),
                    f"preview_{item.id}.gif",
                    "image/gif",
                    f"projects/{item.project_id}/previews"
                )
                
                metadata = item.item_metadata or {}
                metadata["gif_preview_path"] = storage_gif_path
                item.item_metadata = metadata
                result["gif_preview"] = storage_gif_path
        
        # Detect scenes
        if options.get("detect_scenes", False):
            scenes = await video_processor.detect_scenes(
                temp_file,
                options.get("scene_threshold", 0.3)
            )
            
            metadata = item.item_metadata or {}
            metadata["scene_changes"] = scenes
            item.item_metadata = metadata
            result["scenes"] = len(scenes)
        
        item.is_processed = True
        await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Video processing error: {e}")
        return {"error": str(e)}
    
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

