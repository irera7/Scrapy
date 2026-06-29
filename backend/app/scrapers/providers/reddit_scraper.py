from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem

logger = structlog.get_logger()


class RedditScraper(BaseScraper):
    """Scraper for Reddit API."""
    
    BASE_URL = "https://oauth.reddit.com"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Reddit config."""
        required = ["subreddit"]
        return all(key in config for key in required)
    
    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        """Get OAuth access token."""
        if self.access_token:
            return self.access_token
        
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "client_credentials"
        }
        headers = {
            "User-Agent": "AI-Data-Collector/1.0"
        }
        
        response = await client.post(
            self.AUTH_URL,
            auth=auth,
            data=data,
            headers=headers
        )
        response.raise_for_status()
        
        self.access_token = response.json()["access_token"]
        return self.access_token
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute Reddit scraping and save results."""
        
        subreddit = config.get("subreddit")
        sort = config.get("sort", "hot")
        limit = config.get("limit", 100)
        time_filter = config.get("time_filter", "all")
        include_comments = config.get("include_comments", False)
        
        logger.info(f"Reddit scraping r/{subreddit}, sort: {sort}")
        
        items = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            token = await self._get_access_token(client)
            
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "AI-Data-Collector/1.0"
            }
            
            # Get posts
            params = {
                "limit": min(limit, 100),
                "t": time_filter
            }
            
            url = f"{self.BASE_URL}/r/{subreddit}/{sort}"
            collected = 0
            after = None
            
            while collected < limit:
                if after:
                    params["after"] = after
                
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    
                    # Determine content type
                    data_type = "text"
                    source_url = post_data.get("url")
                    
                    if post_data.get("is_video"):
                        data_type = "video"
                    elif post_data.get("post_hint") == "image" or source_url and any(
                        ext in source_url.lower() for ext in [".jpg", ".jpeg", ".png", ".gif"]
                    ):
                        data_type = "image"
                    
                    # Combine title and selftext
                    content = post_data.get("title", "")
                    if post_data.get("selftext"):
                        content += "\n\n" + post_data.get("selftext")
                    
                    item = DataItem(
                        project_id=project_id,
                        data_type=data_type,
                        source_url=f"https://reddit.com{post_data.get('permalink')}",
                        content=content,
                        item_metadata={
                            "post_id": post_data.get("id"),
                            "subreddit": subreddit,
                            "author": post_data.get("author"),
                            "score": post_data.get("score"),
                            "upvote_ratio": post_data.get("upvote_ratio"),
                            "num_comments": post_data.get("num_comments"),
                            "created_utc": post_data.get("created_utc"),
                            "flair": post_data.get("link_flair_text"),
                            "is_video": post_data.get("is_video"),
                            "media_url": source_url if data_type != "text" else None,
                        }
                    )
                    db.add(item)
                    items.append(item)
                    
                    collected += 1
                    
                    # Get comments if requested
                    if include_comments and post_data.get("num_comments", 0) > 0:
                        comments = await self._get_comments(
                            client, headers, subreddit, post_data.get("id")
                        )
                        
                        for comment in comments[:10]:  # Limit comments per post
                            comment_item = DataItem(
                                project_id=project_id,
                                data_type="text",
                                source_url=f"https://reddit.com{post_data.get('permalink')}",
                                content=comment.get("body", ""),
                                item_metadata={
                                    "parent_post_id": post_data.get("id"),
                                    "comment_id": comment.get("id"),
                                    "author": comment.get("author"),
                                    "score": comment.get("score"),
                                    "is_comment": True,
                                }
                            )
                            db.add(comment_item)
                            items.append(comment_item)
                
                # Check for next page
                after = data.get("data", {}).get("after")
                if not after or collected >= limit:
                    break
        
        await db.commit()
        
        logger.info(f"Reddit collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_comments(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        subreddit: str,
        post_id: str
    ) -> List[dict]:
        """Get comments for a post."""
        try:
            url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}"
            response = await client.get(url, headers=headers, params={"limit": 10})
            response.raise_for_status()
            data = response.json()
            
            comments = []
            if len(data) > 1:
                for child in data[1].get("data", {}).get("children", []):
                    if child.get("kind") == "t1":  # Comment
                        comments.append(child.get("data", {}))
            
            return comments
        except Exception as e:
            logger.warning(f"Failed to get comments for {post_id}: {e}")
            return []

