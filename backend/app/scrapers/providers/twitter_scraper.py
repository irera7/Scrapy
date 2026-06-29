from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem

logger = structlog.get_logger()


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X API."""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Twitter config."""
        required = ["query"]
        return all(key in config for key in required)
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute Twitter search and save results."""
        
        query = config.get("query")
        max_tweets = config.get("max_tweets", 100)
        include_replies = config.get("include_replies", False)
        
        logger.info(f"Twitter search: {query}")
        
        items = []
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Modify query to exclude replies if needed
        if not include_replies:
            query = f"{query} -is:reply"
        
        params = {
            "query": query,
            "max_results": min(max_tweets, 100),  # API limit
            "tweet.fields": "created_at,author_id,public_metrics,entities,attachments",
            "expansions": "author_id,attachments.media_keys",
            "media.fields": "url,preview_image_url,type",
            "user.fields": "name,username"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            collected = 0
            next_token = None
            
            while collected < max_tweets:
                if next_token:
                    params["next_token"] = next_token
                
                response = await client.get(
                    f"{self.BASE_URL}/tweets/search/recent",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 429:
                    logger.warning("Twitter rate limit reached")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                tweets = data.get("data", [])
                includes = data.get("includes", {})
                users = {u["id"]: u for u in includes.get("users", [])}
                media = {m["media_key"]: m for m in includes.get("media", [])}
                
                for tweet in tweets:
                    author = users.get(tweet.get("author_id"), {})
                    
                    # Get media if available
                    tweet_media = []
                    if "attachments" in tweet:
                        for media_key in tweet.get("attachments", {}).get("media_keys", []):
                            if media_key in media:
                                tweet_media.append(media[media_key])
                    
                    # Create text item
                    item = DataItem(
                        project_id=project_id,
                        data_type="text",
                        source_url=f"https://twitter.com/{author.get('username')}/status/{tweet['id']}",
                        content=tweet.get("text", ""),
                        item_metadata={
                            "tweet_id": tweet["id"],
                            "author_id": tweet.get("author_id"),
                            "author_name": author.get("name"),
                            "author_username": author.get("username"),
                            "created_at": tweet.get("created_at"),
                            "retweet_count": tweet.get("public_metrics", {}).get("retweet_count"),
                            "like_count": tweet.get("public_metrics", {}).get("like_count"),
                            "reply_count": tweet.get("public_metrics", {}).get("reply_count"),
                            "query": query,
                        }
                    )
                    db.add(item)
                    items.append(item)
                    
                    # Create image items for media
                    for m in tweet_media:
                        if m.get("type") in ["photo", "animated_gif"]:
                            media_item = DataItem(
                                project_id=project_id,
                                data_type="image",
                                source_url=m.get("url") or m.get("preview_image_url"),
                                content=tweet.get("text", ""),
                                item_metadata={
                                    "tweet_id": tweet["id"],
                                    "media_type": m.get("type"),
                                    "author_username": author.get("username"),
                                }
                            )
                            db.add(media_item)
                            items.append(media_item)
                        elif m.get("type") == "video":
                            media_item = DataItem(
                                project_id=project_id,
                                data_type="video",
                                source_url=m.get("preview_image_url"),
                                content=tweet.get("text", ""),
                                item_metadata={
                                    "tweet_id": tweet["id"],
                                    "media_type": m.get("type"),
                                    "author_username": author.get("username"),
                                }
                            )
                            db.add(media_item)
                            items.append(media_item)
                    
                    collected += 1
                
                # Check for next page
                next_token = data.get("meta", {}).get("next_token")
                if not next_token or collected >= max_tweets:
                    break
        
        await db.commit()
        
        logger.info(f"Twitter collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]

