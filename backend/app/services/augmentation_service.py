"""Data Augmentation Service for ML training."""
import random
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import structlog
import io

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem
from app.models.dataset import AugmentationRule
from app.core.storage import storage_service

logger = structlog.get_logger()


class TextAugmenter:
    """Text data augmentation methods."""
    
    # Simple synonym dictionary (in production, use WordNet or similar)
    SYNONYMS = {
        "good": ["great", "excellent", "fine", "nice"],
        "bad": ["poor", "terrible", "awful", "horrible"],
        "big": ["large", "huge", "enormous", "massive"],
        "small": ["tiny", "little", "miniature", "compact"],
        "happy": ["joyful", "pleased", "glad", "delighted"],
        "sad": ["unhappy", "sorrowful", "melancholy", "depressed"],
        "fast": ["quick", "rapid", "swift", "speedy"],
        "slow": ["sluggish", "gradual", "unhurried", "leisurely"],
    }
    
    def synonym_replacement(self, text: str, n: int = 2) -> str:
        """Replace n words with their synonyms."""
        words = text.split()
        new_words = words.copy()
        
        replaceable_indices = [
            i for i, word in enumerate(words) 
            if word.lower() in self.SYNONYMS
        ]
        
        if not replaceable_indices:
            return text
        
        num_replacements = min(n, len(replaceable_indices))
        indices_to_replace = random.sample(replaceable_indices, num_replacements)
        
        for idx in indices_to_replace:
            word = words[idx].lower()
            synonyms = self.SYNONYMS.get(word, [])
            if synonyms:
                new_word = random.choice(synonyms)
                # Preserve original case
                if words[idx][0].isupper():
                    new_word = new_word.capitalize()
                new_words[idx] = new_word
        
        return ' '.join(new_words)
    
    def random_swap(self, text: str, n: int = 2) -> str:
        """Randomly swap n pairs of words."""
        words = text.split()
        if len(words) < 2:
            return text
        
        new_words = words.copy()
        for _ in range(n):
            if len(new_words) >= 2:
                idx1, idx2 = random.sample(range(len(new_words)), 2)
                new_words[idx1], new_words[idx2] = new_words[idx2], new_words[idx1]
        
        return ' '.join(new_words)
    
    def random_deletion(self, text: str, p: float = 0.1) -> str:
        """Randomly delete words with probability p."""
        words = text.split()
        if len(words) <= 1:
            return text
        
        new_words = [word for word in words if random.random() > p]
        
        if not new_words:
            return random.choice(words)
        
        return ' '.join(new_words)
    
    def random_insertion(self, text: str, n: int = 1) -> str:
        """Randomly insert n words from the text."""
        words = text.split()
        if not words:
            return text
        
        new_words = words.copy()
        for _ in range(n):
            word_to_insert = random.choice(words)
            insert_pos = random.randint(0, len(new_words))
            new_words.insert(insert_pos, word_to_insert)
        
        return ' '.join(new_words)
    
    def add_noise(self, text: str, noise_prob: float = 0.05) -> str:
        """Add character-level noise (typos)."""
        chars = list(text)
        keyboard_neighbors = {
            'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs',
            'e': 'wrsdf', 'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg',
            'i': 'uojkl', 'j': 'uikmnh', 'k': 'iolmj', 'l': 'opk',
            'm': 'njk', 'n': 'bhjm', 'o': 'iplk', 'p': 'ol',
            'q': 'wa', 'r': 'etdf', 's': 'wedxza', 't': 'ryfg',
            'u': 'yihj', 'v': 'cfgb', 'w': 'qesa', 'x': 'zsdc',
            'y': 'tugh', 'z': 'asx',
        }
        
        for i, char in enumerate(chars):
            if random.random() < noise_prob and char.lower() in keyboard_neighbors:
                neighbors = keyboard_neighbors[char.lower()]
                new_char = random.choice(neighbors)
                chars[i] = new_char.upper() if char.isupper() else new_char
        
        return ''.join(chars)
    
    def augment(self, text: str, augmentation_type: str, params: Dict[str, Any] = None) -> str:
        """Apply augmentation based on type."""
        params = params or {}
        
        if augmentation_type == "text_synonym":
            return self.synonym_replacement(text, params.get("n", 2))
        elif augmentation_type == "text_random_swap":
            return self.random_swap(text, params.get("n", 2))
        elif augmentation_type == "text_random_delete":
            return self.random_deletion(text, params.get("probability", 0.1))
        elif augmentation_type == "text_random_insert":
            return self.random_insertion(text, params.get("n", 1))
        elif augmentation_type == "text_noise":
            return self.add_noise(text, params.get("noise_prob", 0.05))
        
        return text


class ImageAugmenter:
    """Image data augmentation methods."""
    
    def __init__(self):
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
            self.Image = Image
            self.ImageEnhance = ImageEnhance
            self.ImageFilter = ImageFilter
            self.ImageOps = ImageOps
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("PIL not available for image augmentation")
    
    def load_image(self, data: bytes):
        """Load image from bytes."""
        return self.Image.open(io.BytesIO(data))
    
    def save_image(self, image, format: str = "PNG") -> bytes:
        """Save image to bytes."""
        buffer = io.BytesIO()
        if format.upper() == "JPEG" and image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(buffer, format=format)
        return buffer.getvalue()
    
    def flip_horizontal(self, image):
        """Flip image horizontally."""
        return self.ImageOps.mirror(image)
    
    def flip_vertical(self, image):
        """Flip image vertically."""
        return self.ImageOps.flip(image)
    
    def rotate(self, image, angle: float = None, max_angle: float = 30):
        """Rotate image by angle or random angle."""
        if angle is None:
            angle = random.uniform(-max_angle, max_angle)
        return image.rotate(angle, expand=True, fillcolor=(0, 0, 0))
    
    def adjust_brightness(self, image, factor: float = None, range_: Tuple[float, float] = (0.7, 1.3)):
        """Adjust image brightness."""
        if factor is None:
            factor = random.uniform(*range_)
        enhancer = self.ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    
    def adjust_contrast(self, image, factor: float = None, range_: Tuple[float, float] = (0.7, 1.3)):
        """Adjust image contrast."""
        if factor is None:
            factor = random.uniform(*range_)
        enhancer = self.ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    def random_crop(self, image, crop_ratio: float = 0.8):
        """Randomly crop image."""
        width, height = image.size
        new_width = int(width * crop_ratio)
        new_height = int(height * crop_ratio)
        
        left = random.randint(0, width - new_width)
        top = random.randint(0, height - new_height)
        
        return image.crop((left, top, left + new_width, top + new_height))
    
    def add_gaussian_noise(self, image, std: float = 25):
        """Add Gaussian noise to image."""
        import numpy as np
        
        img_array = np.array(image).astype(np.float32)
        noise = np.random.normal(0, std, img_array.shape)
        noisy = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        
        return self.Image.fromarray(noisy)
    
    def apply_blur(self, image, radius: float = 2):
        """Apply Gaussian blur."""
        return image.filter(self.ImageFilter.GaussianBlur(radius=radius))
    
    def to_grayscale(self, image):
        """Convert to grayscale."""
        return image.convert("L").convert("RGB")
    
    def color_jitter(self, image, brightness: float = 0.2, contrast: float = 0.2, saturation: float = 0.2):
        """Apply random color jitter."""
        # Brightness
        b_factor = 1 + random.uniform(-brightness, brightness)
        image = self.ImageEnhance.Brightness(image).enhance(b_factor)
        
        # Contrast
        c_factor = 1 + random.uniform(-contrast, contrast)
        image = self.ImageEnhance.Contrast(image).enhance(c_factor)
        
        # Saturation (Color)
        s_factor = 1 + random.uniform(-saturation, saturation)
        image = self.ImageEnhance.Color(image).enhance(s_factor)
        
        return image
    
    def augment(self, image_data: bytes, augmentation_type: str, params: Dict[str, Any] = None) -> bytes:
        """Apply augmentation based on type."""
        if not self.available:
            return image_data
        
        params = params or {}
        image = self.load_image(image_data)
        
        if augmentation_type == "image_flip_horizontal":
            image = self.flip_horizontal(image)
        elif augmentation_type == "image_flip_vertical":
            image = self.flip_vertical(image)
        elif augmentation_type == "image_rotate":
            image = self.rotate(image, params.get("angle"), params.get("max_angle", 30))
        elif augmentation_type == "image_brightness":
            image = self.adjust_brightness(image, params.get("factor"))
        elif augmentation_type == "image_contrast":
            image = self.adjust_contrast(image, params.get("factor"))
        elif augmentation_type == "image_crop":
            image = self.random_crop(image, params.get("crop_ratio", 0.8))
        elif augmentation_type == "image_noise":
            image = self.add_gaussian_noise(image, params.get("std", 25))
        elif augmentation_type == "image_blur":
            image = self.apply_blur(image, params.get("radius", 2))
        elif augmentation_type == "image_grayscale":
            image = self.to_grayscale(image)
        elif augmentation_type == "image_color_jitter":
            image = self.color_jitter(
                image, 
                params.get("brightness", 0.2),
                params.get("contrast", 0.2),
                params.get("saturation", 0.2)
            )
        
        return self.save_image(image, params.get("format", "PNG"))


class AudioAugmenter:
    """Audio data augmentation methods using librosa."""
    
    def __init__(self):
        self.available = False
        self.np = None
        self.librosa = None
        self.sf = None
        
        try:
            import numpy as np
            self.np = np
            self.available = True
        except ImportError:
            logger.warning("NumPy not available for audio augmentation")
            return
        
        try:
            import librosa
            import soundfile as sf
            self.librosa = librosa
            self.sf = sf
            logger.info("Audio augmentation with librosa is available")
        except ImportError:
            logger.warning("librosa/soundfile not installed, audio augmentation will be limited")
    
    def _load_audio(self, audio_data: bytes, sr: int = None) -> tuple:
        """Load audio from bytes."""
        if not self.librosa:
            return None, None
        
        import io
        audio_file = io.BytesIO(audio_data)
        y, sample_rate = self.librosa.load(audio_file, sr=sr)
        return y, sample_rate
    
    def _save_audio(self, y, sr: int, format: str = 'wav') -> bytes:
        """Save audio to bytes."""
        if not self.sf:
            return None
        
        import io
        buffer = io.BytesIO()
        self.sf.write(buffer, y, sr, format=format)
        buffer.seek(0)
        return buffer.read()
    
    def change_speed(self, audio_data: bytes, speed_factor: float = None, 
                     speed_range: tuple = (0.8, 1.2)) -> bytes:
        """
        Change audio speed without changing pitch.
        
        Args:
            audio_data: Input audio bytes
            speed_factor: Speed multiplier (>1 = faster, <1 = slower)
            speed_range: Range for random speed if factor not specified
        """
        if not self.librosa or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if speed_factor is None:
                speed_factor = random.uniform(*speed_range)
            
            # Time stretch (changes speed without changing pitch)
            y_stretched = self.librosa.effects.time_stretch(y, rate=speed_factor)
            
            return self._save_audio(y_stretched, sr)
        except Exception as e:
            logger.warning(f"Speed change failed: {e}")
            return audio_data
    
    def change_pitch(self, audio_data: bytes, pitch_shift: float = None,
                     pitch_range: tuple = (-4, 4)) -> bytes:
        """
        Change audio pitch without changing speed.
        
        Args:
            audio_data: Input audio bytes
            pitch_shift: Semitones to shift (positive = higher, negative = lower)
            pitch_range: Range for random pitch shift if not specified
        """
        if not self.librosa or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if pitch_shift is None:
                pitch_shift = random.uniform(*pitch_range)
            
            # Pitch shift in semitones
            y_shifted = self.librosa.effects.pitch_shift(y, sr=sr, n_steps=pitch_shift)
            
            return self._save_audio(y_shifted, sr)
        except Exception as e:
            logger.warning(f"Pitch shift failed: {e}")
            return audio_data
    
    def add_noise(self, audio_data: bytes, noise_level: float = None,
                  noise_range: tuple = (0.001, 0.01)) -> bytes:
        """
        Add Gaussian noise to audio.
        
        Args:
            audio_data: Input audio bytes
            noise_level: Standard deviation of noise
            noise_range: Range for random noise level
        """
        if not self.np or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if noise_level is None:
                noise_level = random.uniform(*noise_range)
            
            # Add Gaussian noise
            noise = self.np.random.normal(0, noise_level, len(y))
            y_noisy = y + noise.astype(y.dtype)
            
            # Clip to valid range
            y_noisy = self.np.clip(y_noisy, -1.0, 1.0)
            
            return self._save_audio(y_noisy, sr)
        except Exception as e:
            logger.warning(f"Add noise failed: {e}")
            return audio_data
    
    def time_stretch(self, audio_data: bytes, stretch_factor: float = None,
                     stretch_range: tuple = (0.8, 1.2)) -> bytes:
        """
        Time stretch audio (changes both speed and pitch proportionally).
        
        Args:
            audio_data: Input audio bytes
            stretch_factor: Stretch multiplier
            stretch_range: Range for random stretch
        """
        if not self.librosa or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if stretch_factor is None:
                stretch_factor = random.uniform(*stretch_range)
            
            # Simple resampling for time stretch
            y_stretched = self.librosa.effects.time_stretch(y, rate=stretch_factor)
            
            return self._save_audio(y_stretched, sr)
        except Exception as e:
            logger.warning(f"Time stretch failed: {e}")
            return audio_data
    
    def add_reverb(self, audio_data: bytes, reverb_amount: float = None,
                   reverb_range: tuple = (0.1, 0.5)) -> bytes:
        """
        Add reverb effect to audio.
        
        Args:
            audio_data: Input audio bytes
            reverb_amount: Amount of reverb (0-1)
            reverb_range: Range for random reverb amount
        """
        if not self.np or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if reverb_amount is None:
                reverb_amount = random.uniform(*reverb_range)
            
            # Simple reverb using delay and decay
            delay_samples = int(sr * 0.03)  # 30ms delay
            decay = reverb_amount
            
            # Create reverb by adding delayed copies
            y_reverb = y.copy()
            for i in range(3):
                delay = delay_samples * (i + 1)
                decay_factor = decay ** (i + 1)
                if len(y) > delay:
                    y_reverb[delay:] += y[:-delay] * decay_factor
            
            # Normalize
            y_reverb = y_reverb / self.np.max(self.np.abs(y_reverb))
            
            return self._save_audio(y_reverb, sr)
        except Exception as e:
            logger.warning(f"Add reverb failed: {e}")
            return audio_data
    
    def shift_time(self, audio_data: bytes, shift_ms: float = None,
                   shift_range: tuple = (-500, 500)) -> bytes:
        """
        Shift audio in time (add silence at beginning or trim).
        
        Args:
            audio_data: Input audio bytes
            shift_ms: Milliseconds to shift (positive = add silence, negative = trim)
            shift_range: Range for random shift
        """
        if not self.np or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if shift_ms is None:
                shift_ms = random.uniform(*shift_range)
            
            shift_samples = int(sr * shift_ms / 1000)
            
            if shift_samples > 0:
                # Add silence at beginning
                silence = self.np.zeros(shift_samples)
                y_shifted = self.np.concatenate([silence, y])
            else:
                # Trim from beginning
                y_shifted = y[abs(shift_samples):]
            
            return self._save_audio(y_shifted, sr)
        except Exception as e:
            logger.warning(f"Time shift failed: {e}")
            return audio_data
    
    def change_volume(self, audio_data: bytes, volume_factor: float = None,
                      volume_range: tuple = (0.5, 1.5)) -> bytes:
        """
        Change audio volume.
        
        Args:
            audio_data: Input audio bytes
            volume_factor: Volume multiplier
            volume_range: Range for random volume change
        """
        if not self.np or not self.available:
            return audio_data
        
        try:
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if volume_factor is None:
                volume_factor = random.uniform(*volume_range)
            
            y_adjusted = y * volume_factor
            
            # Clip to valid range
            y_adjusted = self.np.clip(y_adjusted, -1.0, 1.0)
            
            return self._save_audio(y_adjusted, sr)
        except Exception as e:
            logger.warning(f"Volume change failed: {e}")
            return audio_data
    
    def low_pass_filter(self, audio_data: bytes, cutoff_hz: float = None,
                        cutoff_range: tuple = (2000, 8000)) -> bytes:
        """
        Apply low-pass filter to audio.
        
        Args:
            audio_data: Input audio bytes
            cutoff_hz: Cutoff frequency in Hz
            cutoff_range: Range for random cutoff
        """
        if not self.librosa or not self.available:
            return audio_data
        
        try:
            from scipy import signal
            
            y, sr = self._load_audio(audio_data)
            if y is None:
                return audio_data
            
            if cutoff_hz is None:
                cutoff_hz = random.uniform(*cutoff_range)
            
            # Design lowpass filter
            nyquist = sr / 2
            normalized_cutoff = cutoff_hz / nyquist
            b, a = signal.butter(4, normalized_cutoff, btype='low')
            
            y_filtered = signal.filtfilt(b, a, y)
            
            return self._save_audio(y_filtered, sr)
        except Exception as e:
            logger.warning(f"Low-pass filter failed: {e}")
            return audio_data
    
    def augment(self, audio_data: bytes, augmentation_type: str, params: Dict[str, Any] = None) -> bytes:
        """Apply augmentation based on type."""
        if not self.available:
            logger.warning("Audio augmentation not available")
            return audio_data
        
        params = params or {}
        
        if augmentation_type == "audio_speed":
            return self.change_speed(audio_data, params.get("speed_factor"), 
                                     params.get("speed_range", (0.8, 1.2)))
        elif augmentation_type == "audio_pitch":
            return self.change_pitch(audio_data, params.get("pitch_shift"),
                                     params.get("pitch_range", (-4, 4)))
        elif augmentation_type == "audio_noise":
            return self.add_noise(audio_data, params.get("noise_level"),
                                  params.get("noise_range", (0.001, 0.01)))
        elif augmentation_type == "audio_time_stretch":
            return self.time_stretch(audio_data, params.get("stretch_factor"),
                                     params.get("stretch_range", (0.8, 1.2)))
        elif augmentation_type == "audio_reverb":
            return self.add_reverb(audio_data, params.get("reverb_amount"),
                                   params.get("reverb_range", (0.1, 0.5)))
        elif augmentation_type == "audio_time_shift":
            return self.shift_time(audio_data, params.get("shift_ms"),
                                   params.get("shift_range", (-500, 500)))
        elif augmentation_type == "audio_volume":
            return self.change_volume(audio_data, params.get("volume_factor"),
                                      params.get("volume_range", (0.5, 1.5)))
        elif augmentation_type == "audio_low_pass":
            return self.low_pass_filter(audio_data, params.get("cutoff_hz"),
                                        params.get("cutoff_range", (2000, 8000)))
        
        return audio_data


class VideoAugmenter:
    """Video data augmentation methods using ffmpeg."""
    
    def __init__(self):
        self.available = False
        self.temp_dir = None
        
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.available = True
                logger.info("Video augmentation with ffmpeg is available")
            else:
                logger.warning("ffmpeg not properly installed")
        except Exception as e:
            logger.warning(f"ffmpeg not available: {e}")
    
    def _get_temp_dir(self):
        """Get or create temporary directory."""
        import tempfile
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir
    
    def _run_ffmpeg(self, input_path: str, output_path: str, filters: list) -> bool:
        """Run ffmpeg with given filters."""
        import subprocess
        
        try:
            filter_str = ','.join(filters) if filters else None
            
            cmd = ['ffmpeg', '-y', '-i', input_path]
            if filter_str:
                cmd.extend(['-vf', filter_str])
            cmd.extend(['-c:a', 'copy', output_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"FFmpeg command failed: {e}")
            return False
    
    def _save_temp_video(self, video_data: bytes, ext: str = 'mp4') -> str:
        """Save video data to temporary file."""
        import os
        temp_dir = self._get_temp_dir()
        import uuid as uuid_lib
        temp_path = os.path.join(temp_dir, f"input_{uuid_lib.uuid4()}.{ext}")
        with open(temp_path, 'wb') as f:
            f.write(video_data)
        return temp_path
    
    def _load_output_video(self, output_path: str) -> bytes:
        """Load video from output file."""
        with open(output_path, 'rb') as f:
            return f.read()
    
    def _cleanup_temp_files(self, *paths):
        """Remove temporary files."""
        import os
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except:
                pass
    
    def flip_horizontal(self, video_data: bytes, ext: str = 'mp4') -> bytes:
        """Flip video horizontally."""
        if not self.available:
            return video_data
        
        import os
        input_path = None
        output_path = None
        
        try:
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            if self._run_ffmpeg(input_path, output_path, ['hflip']):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Horizontal flip failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def flip_vertical(self, video_data: bytes, ext: str = 'mp4') -> bytes:
        """Flip video vertically."""
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            if self._run_ffmpeg(input_path, output_path, ['vflip']):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Vertical flip failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def rotate(self, video_data: bytes, angle: float = None, 
               angle_range: tuple = (-15, 15), ext: str = 'mp4') -> bytes:
        """
        Rotate video by angle.
        
        Args:
            video_data: Input video bytes
            angle: Rotation angle in degrees
            angle_range: Range for random rotation
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if angle is None:
                angle = random.uniform(*angle_range)
            
            # Convert to radians for ffmpeg
            import math
            radians = angle * math.pi / 180
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"rotate={radians}:c=black:ow=rotw({radians}):oh=roth({radians})"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Rotation failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def change_speed(self, video_data: bytes, speed_factor: float = None,
                     speed_range: tuple = (0.5, 2.0), ext: str = 'mp4') -> bytes:
        """
        Change video playback speed.
        
        Args:
            video_data: Input video bytes
            speed_factor: Speed multiplier (>1 = faster, <1 = slower)
            speed_range: Range for random speed
        """
        if not self.available:
            return video_data
        
        import subprocess
        input_path = None
        output_path = None
        
        try:
            if speed_factor is None:
                speed_factor = random.uniform(*speed_range)
            
            # Clamp speed factor
            speed_factor = max(0.25, min(4.0, speed_factor))
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            # PTS = Presentation Timestamp, dividing speeds up, multiplying slows down
            video_filter = f"setpts={1/speed_factor}*PTS"
            audio_filter = f"atempo={speed_factor}"
            
            # For extreme speed changes, chain atempo filters (max 2x per filter)
            if speed_factor > 2:
                audio_filter = "atempo=2.0,atempo=" + str(speed_factor / 2)
            elif speed_factor < 0.5:
                audio_filter = "atempo=0.5,atempo=" + str(speed_factor * 2)
            
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-filter_complex', f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
                '-map', '[v]', '-map', '[a]',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Speed change failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def adjust_brightness(self, video_data: bytes, brightness: float = None,
                          brightness_range: tuple = (-0.3, 0.3), ext: str = 'mp4') -> bytes:
        """
        Adjust video brightness.
        
        Args:
            video_data: Input video bytes
            brightness: Brightness adjustment (-1 to 1)
            brightness_range: Range for random adjustment
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if brightness is None:
                brightness = random.uniform(*brightness_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"eq=brightness={brightness}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Brightness adjustment failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def adjust_contrast(self, video_data: bytes, contrast: float = None,
                        contrast_range: tuple = (0.8, 1.2), ext: str = 'mp4') -> bytes:
        """
        Adjust video contrast.
        
        Args:
            video_data: Input video bytes
            contrast: Contrast multiplier
            contrast_range: Range for random adjustment
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if contrast is None:
                contrast = random.uniform(*contrast_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"eq=contrast={contrast}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Contrast adjustment failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def adjust_saturation(self, video_data: bytes, saturation: float = None,
                          saturation_range: tuple = (0.5, 1.5), ext: str = 'mp4') -> bytes:
        """
        Adjust video saturation.
        
        Args:
            video_data: Input video bytes
            saturation: Saturation multiplier
            saturation_range: Range for random adjustment
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if saturation is None:
                saturation = random.uniform(*saturation_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"eq=saturation={saturation}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Saturation adjustment failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def random_crop(self, video_data: bytes, crop_ratio: float = None,
                    crop_range: tuple = (0.7, 0.9), ext: str = 'mp4') -> bytes:
        """
        Randomly crop video.
        
        Args:
            video_data: Input video bytes
            crop_ratio: Ratio of area to keep
            crop_range: Range for random crop ratio
        """
        if not self.available:
            return video_data
        
        import subprocess
        import json
        input_path = None
        output_path = None
        
        try:
            if crop_ratio is None:
                crop_ratio = random.uniform(*crop_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            # Get video dimensions
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', input_path
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return video_data
            
            data = json.loads(result.stdout)
            width = height = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    break
            
            if not width or not height:
                return video_data
            
            # Calculate crop dimensions
            new_width = int(width * crop_ratio)
            new_height = int(height * crop_ratio)
            
            # Random position
            x_offset = random.randint(0, width - new_width)
            y_offset = random.randint(0, height - new_height)
            
            filter_str = f"crop={new_width}:{new_height}:{x_offset}:{y_offset}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Random crop failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def add_noise(self, video_data: bytes, noise_strength: float = None,
                  noise_range: tuple = (5, 20), ext: str = 'mp4') -> bytes:
        """
        Add noise to video.
        
        Args:
            video_data: Input video bytes
            noise_strength: Noise strength (0-100)
            noise_range: Range for random noise strength
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if noise_strength is None:
                noise_strength = random.uniform(*noise_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"noise=c0s={noise_strength}:allf=t"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Add noise failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def blur(self, video_data: bytes, blur_strength: float = None,
             blur_range: tuple = (1, 5), ext: str = 'mp4') -> bytes:
        """
        Apply blur to video.
        
        Args:
            video_data: Input video bytes
            blur_strength: Blur kernel size
            blur_range: Range for random blur
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if blur_strength is None:
                blur_strength = random.uniform(*blur_range)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"boxblur={blur_strength}:{blur_strength}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Blur failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def color_jitter(self, video_data: bytes, brightness: float = None,
                     contrast: float = None, saturation: float = None,
                     ext: str = 'mp4') -> bytes:
        """
        Apply random color jitter to video.
        
        Args:
            video_data: Input video bytes
            brightness: Brightness adjustment
            contrast: Contrast adjustment
            saturation: Saturation adjustment
        """
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            if brightness is None:
                brightness = random.uniform(-0.2, 0.2)
            if contrast is None:
                contrast = random.uniform(0.8, 1.2)
            if saturation is None:
                saturation = random.uniform(0.8, 1.2)
            
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            filter_str = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
            
            if self._run_ffmpeg(input_path, output_path, [filter_str]):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Color jitter failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def to_grayscale(self, video_data: bytes, ext: str = 'mp4') -> bytes:
        """Convert video to grayscale."""
        if not self.available:
            return video_data
        
        input_path = None
        output_path = None
        
        try:
            input_path = self._save_temp_video(video_data, ext)
            output_path = input_path.replace('input_', 'output_')
            
            if self._run_ffmpeg(input_path, output_path, ['format=gray']):
                return self._load_output_video(output_path)
            return video_data
        except Exception as e:
            logger.warning(f"Grayscale conversion failed: {e}")
            return video_data
        finally:
            self._cleanup_temp_files(input_path, output_path)
    
    def augment(self, video_data: bytes, augmentation_type: str, 
                params: Dict[str, Any] = None) -> bytes:
        """Apply augmentation based on type."""
        if not self.available:
            logger.warning("Video augmentation not available")
            return video_data
        
        params = params or {}
        ext = params.get('format', 'mp4')
        
        if augmentation_type == "video_flip_horizontal":
            return self.flip_horizontal(video_data, ext)
        elif augmentation_type == "video_flip_vertical":
            return self.flip_vertical(video_data, ext)
        elif augmentation_type == "video_rotate":
            return self.rotate(video_data, params.get("angle"), 
                             params.get("angle_range", (-15, 15)), ext)
        elif augmentation_type == "video_speed":
            return self.change_speed(video_data, params.get("speed_factor"),
                                    params.get("speed_range", (0.5, 2.0)), ext)
        elif augmentation_type == "video_brightness":
            return self.adjust_brightness(video_data, params.get("brightness"),
                                         params.get("brightness_range", (-0.3, 0.3)), ext)
        elif augmentation_type == "video_contrast":
            return self.adjust_contrast(video_data, params.get("contrast"),
                                       params.get("contrast_range", (0.8, 1.2)), ext)
        elif augmentation_type == "video_saturation":
            return self.adjust_saturation(video_data, params.get("saturation"),
                                         params.get("saturation_range", (0.5, 1.5)), ext)
        elif augmentation_type == "video_crop":
            return self.random_crop(video_data, params.get("crop_ratio"),
                                   params.get("crop_range", (0.7, 0.9)), ext)
        elif augmentation_type == "video_noise":
            return self.add_noise(video_data, params.get("noise_strength"),
                                 params.get("noise_range", (5, 20)), ext)
        elif augmentation_type == "video_blur":
            return self.blur(video_data, params.get("blur_strength"),
                           params.get("blur_range", (1, 5)), ext)
        elif augmentation_type == "video_color_jitter":
            return self.color_jitter(video_data, params.get("brightness"),
                                    params.get("contrast"), params.get("saturation"), ext)
        elif augmentation_type == "video_grayscale":
            return self.to_grayscale(video_data, ext)
        
        return video_data


# Global instances
text_augmenter = TextAugmenter()
image_augmenter = ImageAugmenter()
audio_augmenter = AudioAugmenter()
video_augmenter = VideoAugmenter()


async def run_augmentation(
    db: AsyncSession,
    project_id: UUID,
    rule_ids: Optional[List[UUID]] = None,
    item_ids: Optional[List[UUID]] = None,
    max_per_item: int = 1,
    only_labeled: bool = True,
) -> Dict[str, Any]:
    """Run augmentation on items."""
    
    # Get rules
    if rule_ids:
        rules_result = await db.execute(
            select(AugmentationRule).where(
                AugmentationRule.id.in_(rule_ids),
                AugmentationRule.is_active == True
            )
        )
    else:
        rules_result = await db.execute(
            select(AugmentationRule).where(
                AugmentationRule.project_id == project_id,
                AugmentationRule.is_active == True
            )
        )
    rules = rules_result.scalars().all()
    
    if not rules:
        return {"original_count": 0, "augmented_count": 0, "items_created": [], "errors": ["No active rules found"]}
    
    # Get items
    query = select(DataItem).where(DataItem.project_id == project_id)
    if item_ids:
        query = query.where(DataItem.id.in_(item_ids))
    if only_labeled:
        query = query.where(DataItem.is_labeled == True)
    
    items_result = await db.execute(query)
    items = items_result.scalars().all()
    
    original_count = len(items)
    augmented_count = 0
    items_created = []
    errors = []
    
    for item in items:
        # Find applicable rules for this item's data type
        applicable_rules = [r for r in rules if r.data_type == item.data_type]
        
        if not applicable_rules:
            continue
        
        for _ in range(max_per_item):
            # Pick a random rule based on probability
            rule = random.choices(
                applicable_rules,
                weights=[r.probability for r in applicable_rules]
            )[0]
            
            try:
                if item.data_type == "text" and item.content:
                    augmented_content = text_augmenter.augment(
                        item.content, 
                        rule.augmentation_type,
                        rule.parameters
                    )
                    
                    # Create new item
                    new_item = DataItem(
                        project_id=project_id,
                        job_id=item.job_id,
                        data_type=item.data_type,
                        source_url=item.source_url,
                        content=augmented_content,
                        item_metadata=item.item_metadata.copy() if item.item_metadata else {},
                        labels=item.labels.copy() if item.labels else [],
                        is_labeled=item.is_labeled,
                        dataset_split=item.dataset_split,
                        augmented_from=item.id,
                        augmentation_type=rule.augmentation_type,
                    )
                    
                    db.add(new_item)
                    items_created.append(new_item.id)
                    augmented_count += 1
                
                elif item.data_type == "image" and item.file_path:
                    # Download original image
                    try:
                        image_data = storage_service.download_file(item.file_path)
                        augmented_data = image_augmenter.augment(
                            image_data,
                            rule.augmentation_type,
                            rule.parameters
                        )
                        
                        # Upload augmented image
                        import uuid as uuid_lib
                        new_id = uuid_lib.uuid4()
                        ext = item.file_path.rsplit('.', 1)[-1] if '.' in item.file_path else 'png'
                        new_path = f"projects/{project_id}/augmented/{new_id}.{ext}"
                        
                        storage_service.upload_bytes(
                            augmented_data, 
                            new_path, 
                            item.mime_type or f"image/{ext}"
                        )
                        
                        # Create new item
                        new_item = DataItem(
                            id=new_id,
                            project_id=project_id,
                            job_id=item.job_id,
                            data_type=item.data_type,
                            source_url=item.source_url,
                            file_path=new_path,
                            file_size=len(augmented_data),
                            mime_type=item.mime_type,
                            item_metadata=item.item_metadata.copy() if item.item_metadata else {},
                            labels=item.labels.copy() if item.labels else [],
                            annotations=item.annotations.copy() if item.annotations else {},
                            is_labeled=item.is_labeled,
                            dataset_split=item.dataset_split,
                            augmented_from=item.id,
                            augmentation_type=rule.augmentation_type,
                        )
                        
                        db.add(new_item)
                        items_created.append(new_id)
                        augmented_count += 1
                    except Exception as e:
                        errors.append(f"Image augmentation failed for {item.id}: {str(e)}")
                
                elif item.data_type == "audio" and item.file_path:
                    # Download original audio
                    try:
                        audio_data = storage_service.download_file(item.file_path)
                        augmented_data = audio_augmenter.augment(
                            audio_data,
                            rule.augmentation_type,
                            rule.parameters
                        )
                        
                        if augmented_data and augmented_data != audio_data:
                            # Upload augmented audio
                            import uuid as uuid_lib
                            new_id = uuid_lib.uuid4()
                            ext = item.file_path.rsplit('.', 1)[-1] if '.' in item.file_path else 'wav'
                            new_path = f"projects/{project_id}/augmented/{new_id}.{ext}"
                            
                            storage_service.upload_bytes(
                                augmented_data, 
                                new_path, 
                                item.mime_type or f"audio/{ext}"
                            )
                            
                            # Create new item
                            new_item = DataItem(
                                id=new_id,
                                project_id=project_id,
                                job_id=item.job_id,
                                data_type=item.data_type,
                                source_url=item.source_url,
                                file_path=new_path,
                                file_size=len(augmented_data),
                                mime_type=item.mime_type,
                                content=item.content,  # Keep transcription if exists
                                item_metadata=item.item_metadata.copy() if item.item_metadata else {},
                                labels=item.labels.copy() if item.labels else [],
                                annotations=item.annotations.copy() if item.annotations else {},
                                is_labeled=item.is_labeled,
                                dataset_split=item.dataset_split,
                                augmented_from=item.id,
                                augmentation_type=rule.augmentation_type,
                            )
                            
                            db.add(new_item)
                            items_created.append(new_id)
                            augmented_count += 1
                        else:
                            errors.append(f"Audio augmentation returned no data for {item.id}")
                    except Exception as e:
                        errors.append(f"Audio augmentation failed for {item.id}: {str(e)}")
                
                elif item.data_type == "video" and item.file_path:
                    # Download original video
                    try:
                        video_data = storage_service.download_file(item.file_path)
                        
                        # Get file extension for proper handling
                        ext = item.file_path.rsplit('.', 1)[-1] if '.' in item.file_path else 'mp4'
                        params = rule.parameters.copy() if rule.parameters else {}
                        params['format'] = ext
                        
                        augmented_data = video_augmenter.augment(
                            video_data,
                            rule.augmentation_type,
                            params
                        )
                        
                        if augmented_data and augmented_data != video_data:
                            # Upload augmented video
                            import uuid as uuid_lib
                            new_id = uuid_lib.uuid4()
                            new_path = f"projects/{project_id}/augmented/{new_id}.{ext}"
                            
                            storage_service.upload_bytes(
                                augmented_data, 
                                new_path, 
                                item.mime_type or f"video/{ext}"
                            )
                            
                            # Create new item
                            new_item = DataItem(
                                id=new_id,
                                project_id=project_id,
                                job_id=item.job_id,
                                data_type=item.data_type,
                                source_url=item.source_url,
                                file_path=new_path,
                                file_size=len(augmented_data),
                                mime_type=item.mime_type,
                                content=item.content,  # Keep transcription if exists
                                item_metadata=item.item_metadata.copy() if item.item_metadata else {},
                                labels=item.labels.copy() if item.labels else [],
                                annotations=item.annotations.copy() if item.annotations else {},
                                is_labeled=item.is_labeled,
                                dataset_split=item.dataset_split,
                                augmented_from=item.id,
                                augmentation_type=rule.augmentation_type,
                            )
                            
                            db.add(new_item)
                            items_created.append(new_id)
                            augmented_count += 1
                        else:
                            errors.append(f"Video augmentation returned no data for {item.id}")
                    except Exception as e:
                        errors.append(f"Video augmentation failed for {item.id}: {str(e)}")
                
            except Exception as e:
                errors.append(f"Augmentation failed for {item.id}: {str(e)}")
    
    await db.commit()
    
    return {
        "original_count": original_count,
        "augmented_count": augmented_count,
        "items_created": [str(i) for i in items_created],
        "errors": errors[:10],  # Limit errors
    }
