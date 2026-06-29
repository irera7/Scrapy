"""Media downloader for images, audio, and video files."""
import asyncio
import hashlib
import io
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
import structlog

from app.core.storage import storage_service
from app.core.config import settings

logger = structlog.get_logger()


class MediaDownloader:
    """Downloads and processes media files."""
    
    # Supported formats
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma'}
    VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
    
    # Max file sizes (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024   # 50MB
    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    
    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: float = 60.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    def _get_file_extension(self, url: str, content_type: Optional[str] = None) -> str:
        """Extract file extension from URL or content type."""
        # Try from URL first
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = Path(path).suffix.lower()
        
        if ext and ext in (self.IMAGE_EXTENSIONS | self.AUDIO_EXTENSIONS | self.VIDEO_EXTENSIONS):
            return ext
        
        # Try from content type
        if content_type:
            guessed = mimetypes.guess_extension(content_type.split(';')[0])
            if guessed:
                return guessed
        
        return '.bin'
    
    def _get_media_type(self, extension: str) -> str:
        """Determine media type from extension."""
        ext = extension.lower()
        if ext in self.IMAGE_EXTENSIONS:
            return "image"
        elif ext in self.AUDIO_EXTENSIONS:
            return "audio"
        elif ext in self.VIDEO_EXTENSIONS:
            return "video"
        return "file"
    
    def _get_max_size(self, media_type: str) -> int:
        """Get max file size for media type."""
        if media_type == "image":
            return self.MAX_IMAGE_SIZE
        elif media_type == "audio":
            return self.MAX_AUDIO_SIZE
        elif media_type == "video":
            return self.MAX_VIDEO_SIZE
        return self.MAX_IMAGE_SIZE
    
    def _generate_filename(self, url: str, extension: str) -> str:
        """Generate unique filename based on URL hash."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{url_hash}{extension}"
    
    async def download_file(
        self,
        url: str,
        project_id: UUID,
        proxy: Optional[str] = None,
        verify_ssl: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Download a single media file using requests library.
        
        Returns dict with file info or None if failed.
        """
        async with self._semaphore:
            try:
                # Setup session with browser-like headers
                session = requests.Session()
                session.headers.update(self.headers)
                
                # Setup proxies if provided
                proxies = None
                if proxy:
                    proxies = {"http": proxy, "https": proxy}
                
                # Run requests in thread pool to avoid blocking
                def _download():
                    # First, do a HEAD request to check file size
                    try:
                        head_response = session.head(
                            url,
                            timeout=self.timeout,
                            allow_redirects=True,
                            verify=verify_ssl,
                            proxies=proxies
                        )
                        content_length = int(head_response.headers.get('content-length', 0))
                        content_type = head_response.headers.get('content-type', '')
                    except Exception:
                        content_length = 0
                        content_type = ''
                    
                    # Get extension and media type
                    extension = self._get_file_extension(url, content_type)
                    media_type = self._get_media_type(extension)
                    max_size = self._get_max_size(media_type)
                    
                    # Check size before downloading
                    if content_length > max_size:
                        logger.warning(f"File too large: {url} ({content_length} bytes)")
                        return None
                    
                    # Download file
                    response = session.get(
                        url,
                        timeout=self.timeout,
                        allow_redirects=True,
                        verify=verify_ssl,
                        proxies=proxies
                    )
                    response.raise_for_status()
                    
                    file_data = response.content
                    file_size = len(file_data)
                    
                    # Double check size
                    if file_size > max_size:
                        logger.warning(f"Downloaded file too large: {url} ({file_size} bytes)")
                        return None
                    
                    # Get actual content type
                    actual_content_type = response.headers.get('content-type', content_type)
                    if not actual_content_type:
                        actual_content_type = mimetypes.guess_type(url)[0] or 'application/octet-stream'
                    
                    # Generate filename and upload
                    filename = self._generate_filename(url, extension)
                    folder = f"projects/{project_id}/{media_type}s"
                    
                    file_stream = io.BytesIO(file_data)
                    file_path = storage_service.upload_file(
                        file_stream,
                        filename,
                        actual_content_type.split(';')[0],
                        folder
                    )
                    
                    logger.info(f"Downloaded: {url} -> {file_path}")
                    
                    return {
                        "url": url,
                        "file_path": file_path,
                        "file_size": file_size,
                        "mime_type": actual_content_type.split(';')[0],
                        "media_type": media_type,
                        "extension": extension,
                    }
                
                # Run download in thread pool
                result = await asyncio.to_thread(_download)
                return result
            
            except requests.HTTPError as e:
                logger.warning(f"HTTP error downloading {url}: {e.response.status_code if e.response else 'unknown'}")
                return None
            
            except Exception as e:
                logger.error(f"Error downloading {url}: {str(e)}")
                return None
    
    async def download_batch(
        self,
        urls: List[str],
        project_id: UUID,
        proxy: Optional[str] = None,
        on_progress: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Download multiple files concurrently.
        
        Args:
            urls: List of URLs to download
            project_id: Project ID for storage
            proxy: Optional proxy URL
            on_progress: Optional callback(completed, total)
        
        Returns:
            List of successful download results
        """
        results = []
        total = len(urls)
        completed = 0
        
        async def download_with_progress(url: str):
            nonlocal completed
            result = await self.download_file(url, project_id, proxy)
            completed += 1
            if on_progress:
                on_progress(completed, total)
            return result
        
        # Create tasks
        tasks = [download_with_progress(url) for url in urls]
        
        # Execute concurrently
        download_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        for result in download_results:
            if isinstance(result, dict):
                results.append(result)
        
        logger.info(f"Batch download complete: {len(results)}/{total} successful")
        return results
    
    async def download_images_from_html(
        self,
        html: str,
        base_url: str,
        project_id: UUID,
        min_size: int = 1000,  # Minimum 1KB
        proxy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract and download images from HTML content."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        soup = BeautifulSoup(html, 'lxml')
        image_urls = set()
        
        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Handle relative URLs
                full_url = urljoin(base_url, src)
                if full_url.startswith('http'):
                    image_urls.add(full_url)
        
        # Find background images in style attributes
        import re
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            urls = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for url in urls:
                full_url = urljoin(base_url, url)
                if full_url.startswith('http'):
                    image_urls.add(full_url)
        
        logger.info(f"Found {len(image_urls)} images in HTML")
        
        # Download all images
        return await self.download_batch(list(image_urls), project_id, proxy)


# Global downloader instance
media_downloader = MediaDownloader()

