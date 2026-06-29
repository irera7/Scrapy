"""Media scrapers for images, audio, and video - no Playwright required."""
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
import structlog
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.scrapers.anti_detection import anti_detection
from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class ImageScraper(BaseScraper):
    """Scraper for images from various sources - uses httpx (no Playwright)."""
    
    def __init__(self):
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("urls") or config.get("source"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape images from URLs or specific sources."""
        source = config.get("source", "urls")
        max_results = config.get("max_results", 50)
        download_images = config.get("download_images", False)
        min_width = config.get("min_width", 100)
        min_height = config.get("min_height", 100)
        
        items = []
        
        if source == "unsplash":
            items = await self._scrape_unsplash(config, project_id, db, job_id, max_results, download_images)
        elif source == "pexels":
            items = await self._scrape_pexels(config, project_id, db, job_id, max_results, download_images)
        elif source == "wikimedia":
            items = await self._scrape_wikimedia(config, project_id, db, job_id, max_results, download_images)
        elif source == "urls":
            urls = config.get("urls", [])
            for url in urls:
                page_items = await self._scrape_page_images(
                    url, project_id, db, job_id, max_results, download_images, min_width, min_height
                )
                items.extend(page_items)
        
        await db.commit()
        logger.info(f"Image scraper collected {len(items)} images")
        return [{"id": str(item.id)} for item in items]
    
    async def _scrape_page_images(
        self,
        url: str,
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int,
        download_images: bool,
        min_width: int,
        min_height: int
    ) -> List[DataItem]:
        """Scrape images from a single page."""
        items = []
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Find all images
                for img in soup.find_all("img")[:max_results]:
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if not src:
                        continue
                    
                    # Make absolute URL
                    if not src.startswith("http"):
                        src = urljoin(url, src)
                    
                    # Skip data URIs and small images
                    if src.startswith("data:"):
                        continue
                    
                    # Check dimensions if specified
                    width = img.get("width", "0")
                    height = img.get("height", "0")
                    try:
                        w = int(re.sub(r'\D', '', str(width)) or 0)
                        h = int(re.sub(r'\D', '', str(height)) or 0)
                        if (w > 0 and w < min_width) or (h > 0 and h < min_height):
                            continue
                    except:
                        pass
                    
                    alt = img.get("alt", "")
                    title = img.get("title", "")
                    
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="image",
                        source_url=src,
                        content=alt or title or src.split("/")[-1],
                        item_metadata={
                            "page_url": url,
                            "alt": alt,
                            "title": title,
                            "width": width,
                            "height": height
                        }
                    )
                    
                    # Optionally download the image
                    if download_images:
                        await self._download_image(client, src, item, project_id)
                    
                    db.add(item)
                    items.append(item)
                    
            except Exception as e:
                logger.error(f"Error scraping images from {url}: {e}")
        
        return items
    
    async def _download_image(self, client: httpx.AsyncClient, src: str, item: DataItem, project_id: UUID):
        """Download and store an image."""
        try:
            img_response = await client.get(src, timeout=30, follow_redirects=True)
            if img_response.status_code == 200:
                content_type = img_response.headers.get("content-type", "image/jpeg")
                file_stream = io.BytesIO(img_response.content)
                filename = src.split("/")[-1].split("?")[0] or "image.jpg"
                file_path = storage_service.upload_file(
                    file_stream,
                    filename,
                    content_type,
                    f"projects/{project_id}/images"
                )
                item.file_path = file_path
                item.file_size = len(img_response.content)
                item.mime_type = content_type
        except Exception as e:
            logger.warning(f"Failed to download image: {src}, error: {e}")
    
    async def _scrape_unsplash(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int,
        download_images: bool
    ) -> List[DataItem]:
        """Scrape from Unsplash Source (free image API)."""
        query = config.get("query", "nature")
        items = []
        
        # Unsplash Source API for random images
        for i in range(min(max_results, 30)):
            # Unsplash Source URL pattern
            img_url = f"https://source.unsplash.com/800x600/?{query}&sig={i}"
            
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="image",
                source_url=img_url,
                content=f"Unsplash image: {query}",
                item_metadata={
                    "platform": "unsplash",
                    "query": query,
                    "index": i
                }
            )
            
            if download_images:
                async with httpx.AsyncClient() as client:
                    await self._download_image(client, img_url, item, project_id)
            
            db.add(item)
            items.append(item)
        
        return items
    
    async def _scrape_pexels(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int,
        download_images: bool
    ) -> List[DataItem]:
        """Scrape from Pexels (requires API key for full access)."""
        api_key = config.get("api_key")
        query = config.get("query", "nature")
        
        if not api_key:
            logger.warning("Pexels requires API key, using page scraping instead")
            return await self._scrape_page_images(
                f"https://www.pexels.com/search/{query}/",
                project_id, db, job_id, max_results, download_images, 100, 100
            )
        
        items = []
        headers = {"Authorization": api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": min(max_results, 80)},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for photo in data.get("photos", []):
                    img_url = photo.get("src", {}).get("large", photo.get("src", {}).get("original"))
                    
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="image",
                        source_url=img_url,
                        content=photo.get("alt", "Pexels photo"),
                        item_metadata={
                            "platform": "pexels",
                            "photographer": photo.get("photographer"),
                            "photographer_url": photo.get("photographer_url"),
                            "width": photo.get("width"),
                            "height": photo.get("height")
                        }
                    )
                    
                    if download_images:
                        await self._download_image(client, img_url, item, project_id)
                    
                    db.add(item)
                    items.append(item)
        
        return items
    
    async def _scrape_wikimedia(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int,
        download_images: bool
    ) -> List[DataItem]:
        """Scrape from Wikimedia Commons using their API."""
        query = config.get("query", "nature")
        items = []
        
        headers = {
            "User-Agent": "AI-DataCollector/1.0 (https://github.com/ai-collector; contact@example.com) httpx/0.25"
        }
        
        async with httpx.AsyncClient(headers=headers) as client:
            # Use Wikimedia Commons API
            response = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{query} filetype:bitmap",
                    "srnamespace": "6",  # File namespace
                    "srlimit": min(max_results, 50),
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                titles = [r["title"] for r in data.get("query", {}).get("search", [])]
                
                if titles:
                    # Get image info for each file
                    info_response = await client.get(
                        "https://commons.wikimedia.org/w/api.php",
                        params={
                            "action": "query",
                            "titles": "|".join(titles[:50]),
                            "prop": "imageinfo",
                            "iiprop": "url|size|mime|extmetadata",
                            "format": "json"
                        },
                        timeout=30
                    )
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        pages = info_data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if page_id == "-1":
                                continue
                            
                            imageinfo = page.get("imageinfo", [{}])[0]
                            img_url = imageinfo.get("url")
                            
                            if img_url:
                                extmeta = imageinfo.get("extmetadata", {})
                                
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="image",
                                    source_url=img_url,
                                    content=page.get("title", "").replace("File:", ""),
                                    item_metadata={
                                        "platform": "wikimedia",
                                        "width": imageinfo.get("width"),
                                        "height": imageinfo.get("height"),
                                        "mime": imageinfo.get("mime"),
                                        "description": extmeta.get("ImageDescription", {}).get("value", ""),
                                        "license": extmeta.get("LicenseShortName", {}).get("value", "")
                                    }
                                )
                                
                                if download_images:
                                    await self._download_image(client, img_url, item, project_id)
                                
                                db.add(item)
                                items.append(item)
        
        return items


class AudioScraper(BaseScraper):
    """Scraper for audio files from various sources."""
    
    def __init__(self):
        self.audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("source") or config.get("urls"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape audio from various sources."""
        source = config.get("source", "freesound")
        max_results = config.get("max_results", 50)
        
        items = []
        
        if source == "freesound":
            items = await self._scrape_freesound(config, project_id, db, job_id, max_results)
        elif source == "archive":
            items = await self._scrape_internet_archive_audio(config, project_id, db, job_id, max_results)
        elif source == "wikimedia":
            items = await self._scrape_wikimedia_audio(config, project_id, db, job_id, max_results)
        
        await db.commit()
        logger.info(f"Audio scraper collected {len(items)} audio files")
        return [{"id": str(item.id)} for item in items]
    
    async def _scrape_freesound(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape from Freesound API (requires API key)."""
        api_key = config.get("api_key")
        query = config.get("query", "music")
        
        if not api_key:
            logger.warning("Freesound requires API key")
            return []
        
        items = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query": query,
                    "page_size": min(max_results, 150),
                    "fields": "id,name,description,duration,url,previews,tags",
                    "token": api_key
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for sound in data.get("results", []):
                    preview_url = sound.get("previews", {}).get("preview-hq-mp3")
                    
                    if preview_url:
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="audio",
                            source_url=preview_url,
                            content=sound.get("name", "Audio file"),
                            item_metadata={
                                "platform": "freesound",
                                "description": sound.get("description"),
                                "duration": sound.get("duration"),
                                "tags": sound.get("tags", []),
                                "freesound_url": sound.get("url")
                            }
                        )
                        db.add(item)
                        items.append(item)
        
        return items
    
    async def _scrape_internet_archive_audio(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape from Internet Archive audio collection."""
        query = config.get("query", "music")
        items = []
        
        async with httpx.AsyncClient() as client:
            # Search Internet Archive
            response = await client.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": f"{query} AND mediatype:audio",
                    "fl[]": ["identifier", "title", "description", "creator"],
                    "rows": min(max_results, 100),
                    "output": "json"
                },
                timeout=30,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                data = response.json()
                for doc in data.get("response", {}).get("docs", []):
                    identifier = doc.get("identifier")
                    
                    if identifier:
                        # Get item metadata
                        details_url = f"https://archive.org/details/{identifier}"
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="audio",
                            source_url=details_url,
                            content=doc.get("title", identifier),
                            item_metadata={
                                "platform": "internet_archive",
                                "identifier": identifier,
                                "creator": doc.get("creator"),
                                "description": doc.get("description")
                            }
                        )
                        db.add(item)
                        items.append(item)
        
        return items
    
    async def _scrape_wikimedia_audio(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape audio from Wikimedia Commons."""
        query = config.get("query", "music")
        items = []
        
        headers = {
            "User-Agent": "AI-DataCollector/1.0 (https://github.com/ai-collector; contact@example.com) httpx/0.25"
        }
        
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{query} filetype:audio",
                    "srnamespace": "6",
                    "srlimit": min(max_results, 50),
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                titles = [r["title"] for r in data.get("query", {}).get("search", [])]
                
                if titles:
                    info_response = await client.get(
                        "https://commons.wikimedia.org/w/api.php",
                        params={
                            "action": "query",
                            "titles": "|".join(titles[:50]),
                            "prop": "imageinfo",
                            "iiprop": "url|size|mime",
                            "format": "json"
                        },
                        timeout=30
                    )
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        pages = info_data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if page_id == "-1":
                                continue
                            
                            imageinfo = page.get("imageinfo", [{}])[0]
                            audio_url = imageinfo.get("url")
                            
                            if audio_url:
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="audio",
                                    source_url=audio_url,
                                    content=page.get("title", "").replace("File:", ""),
                                    item_metadata={
                                        "platform": "wikimedia",
                                        "mime": imageinfo.get("mime"),
                                        "size": imageinfo.get("size")
                                    }
                                )
                                db.add(item)
                                items.append(item)
        
        return items


class VideoScraper(BaseScraper):
    """Scraper for video metadata from various sources."""
    
    def __init__(self):
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("source") or config.get("query"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape video metadata from various sources."""
        source = config.get("source", "archive")
        max_results = config.get("max_results", 50)
        
        items = []
        
        if source == "archive":
            items = await self._scrape_internet_archive_video(config, project_id, db, job_id, max_results)
        elif source == "wikimedia":
            items = await self._scrape_wikimedia_video(config, project_id, db, job_id, max_results)
        elif source == "vimeo":
            items = await self._scrape_vimeo(config, project_id, db, job_id, max_results)
        
        await db.commit()
        logger.info(f"Video scraper collected {len(items)} videos")
        return [{"id": str(item.id)} for item in items]
    
    async def _scrape_internet_archive_video(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape from Internet Archive video collection."""
        query = config.get("query", "documentary")
        items = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": f"{query} AND mediatype:movies",
                    "fl[]": ["identifier", "title", "description", "creator", "year"],
                    "rows": min(max_results, 100),
                    "output": "json"
                },
                timeout=30,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                data = response.json()
                for doc in data.get("response", {}).get("docs", []):
                    identifier = doc.get("identifier")
                    
                    if identifier:
                        embed_url = f"https://archive.org/embed/{identifier}"
                        details_url = f"https://archive.org/details/{identifier}"
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="video",
                            source_url=details_url,
                            content=doc.get("title", identifier),
                            item_metadata={
                                "platform": "internet_archive",
                                "identifier": identifier,
                                "embed_url": embed_url,
                                "creator": doc.get("creator"),
                                "year": doc.get("year"),
                                "description": doc.get("description")
                            }
                        )
                        db.add(item)
                        items.append(item)
        
        return items
    
    async def _scrape_wikimedia_video(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape video from Wikimedia Commons."""
        query = config.get("query", "nature")
        items = []
        
        headers = {
            "User-Agent": "AI-DataCollector/1.0 (https://github.com/ai-collector; contact@example.com) httpx/0.25"
        }
        
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{query} filetype:video",
                    "srnamespace": "6",
                    "srlimit": min(max_results, 50),
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                titles = [r["title"] for r in data.get("query", {}).get("search", [])]
                
                if titles:
                    info_response = await client.get(
                        "https://commons.wikimedia.org/w/api.php",
                        params={
                            "action": "query",
                            "titles": "|".join(titles[:50]),
                            "prop": "imageinfo",
                            "iiprop": "url|size|mime",
                            "format": "json"
                        },
                        timeout=30
                    )
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        pages = info_data.get("query", {}).get("pages", {})
                        
                        for page_id, page in pages.items():
                            if page_id == "-1":
                                continue
                            
                            imageinfo = page.get("imageinfo", [{}])[0]
                            video_url = imageinfo.get("url")
                            
                            if video_url:
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="video",
                                    source_url=video_url,
                                    content=page.get("title", "").replace("File:", ""),
                                    item_metadata={
                                        "platform": "wikimedia",
                                        "mime": imageinfo.get("mime"),
                                        "size": imageinfo.get("size")
                                    }
                                )
                                db.add(item)
                                items.append(item)
        
        return items
    
    async def _scrape_vimeo(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID],
        max_results: int
    ) -> List[DataItem]:
        """Scrape from Vimeo (requires API key for full access)."""
        api_key = config.get("api_key")
        query = config.get("query", "nature")
        
        if not api_key:
            logger.warning("Vimeo API requires access token")
            return []
        
        items = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.vimeo.com/videos",
                params={"query": query, "per_page": min(max_results, 100)},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for video in data.get("data", []):
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="video",
                        source_url=video.get("link"),
                        content=video.get("name", "Vimeo video"),
                        item_metadata={
                            "platform": "vimeo",
                            "description": video.get("description"),
                            "duration": video.get("duration"),
                            "width": video.get("width"),
                            "height": video.get("height")
                        }
                    )
                    db.add(item)
                    items.append(item)
        
        return items

