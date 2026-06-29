"""YouTube scraper for video metadata, transcripts, and comments."""
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
import json
import structlog
import httpx
from bs4 import BeautifulSoup

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.scrapers.anti_detection import anti_detection
from app.scrapers.smart_retry import with_retry, SmartRetry, RetryConfig
from app.models.data_item import DataItem

logger = structlog.get_logger()


class YouTubeScraper(BaseScraper):
    """Scraper for YouTube content."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.retry_handler = SmartRetry(RetryConfig(max_retries=3))
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate YouTube scraper config."""
        valid_types = ["search", "video", "channel", "playlist", "comments", "transcript"]
        return config.get("type") in valid_types
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute YouTube scraping based on config type."""
        
        scrape_type = config.get("type", "search")
        items = []
        
        if scrape_type == "search":
            items = await self._search_videos(config, project_id, db, job_id)
        elif scrape_type == "video":
            items = await self._get_video_details(config, project_id, db, job_id)
        elif scrape_type == "channel":
            items = await self._get_channel_videos(config, project_id, db, job_id)
        elif scrape_type == "playlist":
            items = await self._get_playlist_videos(config, project_id, db, job_id)
        elif scrape_type == "comments":
            items = await self._get_video_comments(config, project_id, db, job_id)
        elif scrape_type == "transcript":
            items = await self._get_video_transcript(config, project_id, db, job_id)
        
        await db.commit()
        return items
    
    async def _api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make YouTube API request."""
        if not self.api_key:
            raise ValueError("YouTube API key required")
        
        params["key"] = self.api_key
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def _search_videos(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Search for videos."""
        query = config.get("query", "")
        max_results = min(config.get("max_results", 50), 50)
        order = config.get("order", "relevance")  # relevance, date, viewCount, rating
        
        logger.info(f"YouTube search: {query}")
        
        items = []
        
        if self.api_key:
            # Use official API
            data = await self._api_request("search", {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "order": order
            })
            
            for video in data.get("items", []):
                snippet = video.get("snippet", {})
                video_id = video.get("id", {}).get("videoId")
                
                if video_id:
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="video",
                        source_url=f"https://www.youtube.com/watch?v={video_id}",
                        content=snippet.get("description", ""),
                        item_metadata={
                            "platform": "youtube",
                            "video_id": video_id,
                            "title": snippet.get("title"),
                            "channel_id": snippet.get("channelId"),
                            "channel_title": snippet.get("channelTitle"),
                            "published_at": snippet.get("publishedAt"),
                            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                        }
                    )
                    db.add(item)
                    items.append(item)
        else:
            # Scrape without API
            items = await self._scrape_search_results(query, max_results, project_id, db, job_id)
        
        logger.info(f"Found {len(items)} YouTube videos")
        return [{"id": str(item.id)} for item in items]
    
    async def _scrape_search_results(
        self,
        query: str,
        max_results: int,
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Scrape search results without API."""
        items = []
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            # Search on YouTube
            response = await client.get(
                "https://www.youtube.com/results",
                params={"search_query": query},
                headers=headers,
                timeout=30
            )
            
            # Extract video data from initial data
            content = response.text
            
            # Find ytInitialData
            match = re.search(r'var ytInitialData = ({.*?});', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    
                    # Navigate to video results
                    contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                    
                    for section in contents:
                        item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                        for video_renderer in item_section:
                            video = video_renderer.get("videoRenderer", {})
                            if video:
                                video_id = video.get("videoId")
                                if video_id and len(items) < max_results:
                                    title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                                    
                                    item = DataItem(
                                        project_id=project_id,
                                        job_id=job_id,
                                        data_type="video",
                                        source_url=f"https://www.youtube.com/watch?v={video_id}",
                                        content=title,
                                        item_metadata={
                                            "platform": "youtube",
                                            "video_id": video_id,
                                            "title": title,
                                            "channel_title": video.get("ownerText", {}).get("runs", [{}])[0].get("text", ""),
                                            "view_count": video.get("viewCountText", {}).get("simpleText", ""),
                                            "published_time": video.get("publishedTimeText", {}).get("simpleText", ""),
                                            "duration": video.get("lengthText", {}).get("simpleText", ""),
                                        }
                                    )
                                    db.add(item)
                                    items.append(item)
                except json.JSONDecodeError:
                    logger.error("Failed to parse YouTube data")
        
        return items
    
    async def _get_video_details(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed video information."""
        video_ids = config.get("video_ids", [])
        if isinstance(video_ids, str):
            video_ids = [video_ids]
        
        items = []
        
        if self.api_key:
            # Batch request (up to 50 videos)
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                
                data = await self._api_request("videos", {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(batch)
                })
                
                for video in data.get("items", []):
                    snippet = video.get("snippet", {})
                    stats = video.get("statistics", {})
                    content_details = video.get("contentDetails", {})
                    
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="video",
                        source_url=f"https://www.youtube.com/watch?v={video['id']}",
                        content=snippet.get("description", ""),
                        item_metadata={
                            "platform": "youtube",
                            "video_id": video["id"],
                            "title": snippet.get("title"),
                            "channel_id": snippet.get("channelId"),
                            "channel_title": snippet.get("channelTitle"),
                            "published_at": snippet.get("publishedAt"),
                            "tags": snippet.get("tags", []),
                            "category_id": snippet.get("categoryId"),
                            "duration": content_details.get("duration"),
                            "view_count": int(stats.get("viewCount", 0)),
                            "like_count": int(stats.get("likeCount", 0)),
                            "comment_count": int(stats.get("commentCount", 0)),
                            "thumbnail": snippet.get("thumbnails", {}).get("maxres", snippet.get("thumbnails", {}).get("high", {})).get("url"),
                        }
                    )
                    db.add(item)
                    items.append(item)
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_video_comments(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get video comments."""
        video_id = config.get("video_id")
        max_results = config.get("max_results", 100)
        
        if not video_id:
            raise ValueError("video_id required for comments")
        
        items = []
        
        if self.api_key:
            page_token = None
            collected = 0
            
            while collected < max_results:
                params = {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(100, max_results - collected),
                    "order": "relevance"
                }
                
                if page_token:
                    params["pageToken"] = page_token
                
                data = await self._api_request("commentThreads", params)
                
                for thread in data.get("items", []):
                    snippet = thread.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    
                    item = DataItem(
                        project_id=project_id,
                        job_id=job_id,
                        data_type="text",
                        source_url=f"https://www.youtube.com/watch?v={video_id}",
                        content=snippet.get("textDisplay", ""),
                        item_metadata={
                            "platform": "youtube",
                            "type": "comment",
                            "video_id": video_id,
                            "comment_id": thread.get("id"),
                            "author": snippet.get("authorDisplayName"),
                            "author_channel_id": snippet.get("authorChannelId", {}).get("value"),
                            "like_count": snippet.get("likeCount", 0),
                            "published_at": snippet.get("publishedAt"),
                            "reply_count": thread.get("snippet", {}).get("totalReplyCount", 0),
                        }
                    )
                    db.add(item)
                    items.append(item)
                    collected += 1
                
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        
        logger.info(f"Collected {len(items)} comments from video {video_id}")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_video_transcript(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get video transcript/captions."""
        video_id = config.get("video_id")
        language = config.get("language", "en")
        
        if not video_id:
            raise ValueError("video_id required for transcript")
        
        items = []
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            # Get video page to find caption tracks
            response = await client.get(
                f"https://www.youtube.com/watch?v={video_id}",
                headers=headers,
                timeout=30
            )
            
            # Find caption tracks in player response
            content = response.text
            
            # Look for captions in ytInitialPlayerResponse
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', content, re.DOTALL)
            if match:
                try:
                    player_data = json.loads(match.group(1))
                    captions = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
                    
                    # Find the right language
                    caption_url = None
                    for track in captions:
                        if track.get("languageCode") == language:
                            caption_url = track.get("baseUrl")
                            break
                    
                    # Fallback to first track
                    if not caption_url and captions:
                        caption_url = captions[0].get("baseUrl")
                    
                    if caption_url:
                        # Fetch caption XML
                        caption_response = await client.get(caption_url, headers=headers, timeout=30)
                        
                        # Parse XML captions
                        soup = BeautifulSoup(caption_response.text, "lxml-xml")
                        texts = []
                        
                        for text_elem in soup.find_all("text"):
                            start = float(text_elem.get("start", 0))
                            dur = float(text_elem.get("dur", 0))
                            text = text_elem.get_text()
                            texts.append({
                                "start": start,
                                "duration": dur,
                                "text": text
                            })
                        
                        # Create data item with full transcript
                        full_transcript = " ".join([t["text"] for t in texts])
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="text",
                            source_url=f"https://www.youtube.com/watch?v={video_id}",
                            content=full_transcript,
                            item_metadata={
                                "platform": "youtube",
                                "type": "transcript",
                                "video_id": video_id,
                                "language": language,
                                "segments": texts,
                                "segment_count": len(texts),
                            }
                        )
                        db.add(item)
                        items.append(item)
                        
                        logger.info(f"Extracted transcript with {len(texts)} segments")
                
                except json.JSONDecodeError:
                    logger.error("Failed to parse player response")
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_channel_videos(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get videos from a channel."""
        channel_id = config.get("channel_id")
        max_results = config.get("max_results", 50)
        
        if not channel_id and config.get("channel_url"):
            # Extract channel ID from URL
            channel_id = await self._get_channel_id_from_url(config["channel_url"])
        
        if not channel_id:
            raise ValueError("channel_id or channel_url required")
        
        items = []
        
        if self.api_key:
            # Get uploads playlist ID
            channel_data = await self._api_request("channels", {
                "part": "contentDetails",
                "id": channel_id
            })
            
            if channel_data.get("items"):
                uploads_playlist = channel_data["items"][0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                
                if uploads_playlist:
                    config["playlist_id"] = uploads_playlist
                    config["max_results"] = max_results
                    return await self._get_playlist_videos(config, project_id, db, job_id)
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_playlist_videos(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get videos from a playlist."""
        playlist_id = config.get("playlist_id")
        max_results = config.get("max_results", 50)
        
        if not playlist_id:
            raise ValueError("playlist_id required")
        
        items = []
        
        if self.api_key:
            page_token = None
            collected = 0
            
            while collected < max_results:
                params = {
                    "part": "snippet,contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": min(50, max_results - collected)
                }
                
                if page_token:
                    params["pageToken"] = page_token
                
                data = await self._api_request("playlistItems", params)
                
                for playlist_item in data.get("items", []):
                    snippet = playlist_item.get("snippet", {})
                    video_id = snippet.get("resourceId", {}).get("videoId")
                    
                    if video_id:
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="video",
                            source_url=f"https://www.youtube.com/watch?v={video_id}",
                            content=snippet.get("description", ""),
                            item_metadata={
                                "platform": "youtube",
                                "video_id": video_id,
                                "title": snippet.get("title"),
                                "channel_id": snippet.get("channelId"),
                                "channel_title": snippet.get("channelTitle"),
                                "published_at": snippet.get("publishedAt"),
                                "playlist_id": playlist_id,
                                "position": snippet.get("position"),
                                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                            }
                        )
                        db.add(item)
                        items.append(item)
                        collected += 1
                
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        
        logger.info(f"Collected {len(items)} videos from playlist {playlist_id}")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_channel_id_from_url(self, url: str) -> Optional[str]:
        """Extract channel ID from YouTube URL."""
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=30)
            
            # Try to find channel ID in page
            match = re.search(r'"channelId":"([^"]+)"', response.text)
            if match:
                return match.group(1)
        
        return None

