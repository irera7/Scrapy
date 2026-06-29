from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class SerpAPIScraper(BaseScraper):
    """Scraper using SerpAPI for search engine results."""
    
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate SerpAPI config."""
        required = ["query"]
        return all(key in config for key in required)
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute SerpAPI search and save results."""
        
        query = config.get("query")
        engine = config.get("engine", "google")
        num_results = config.get("num_results", 10)
        search_type = config.get("search_type")  # images, news, videos
        
        logger.info(f"SerpAPI search: {query} on {engine}")
        
        # Build API params
        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": engine,
            "num": num_results,
        }
        
        if search_type:
            params["tbm"] = search_type  # isch for images, nws for news, vid for videos
        
        items = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process results based on type
            if search_type == "isch" or search_type == "images":
                results = data.get("images_results", [])
                for result in results[:num_results]:
                    item = DataItem(
                        project_id=project_id,
                        data_type="image",
                        source_url=result.get("original") or result.get("link"),
                        content=result.get("title", ""),
                        item_metadata={
                            "thumbnail": result.get("thumbnail"),
                            "source": result.get("source"),
                            "width": result.get("original_width"),
                            "height": result.get("original_height"),
                            "query": query,
                            "engine": engine,
                        }
                    )
                    db.add(item)
                    items.append(item)
            
            elif search_type == "vid" or search_type == "videos":
                results = data.get("video_results", [])
                for result in results[:num_results]:
                    item = DataItem(
                        project_id=project_id,
                        data_type="video",
                        source_url=result.get("link"),
                        content=result.get("title", ""),
                        item_metadata={
                            "thumbnail": result.get("thumbnail"),
                            "channel": result.get("channel", {}).get("name"),
                            "duration": result.get("duration"),
                            "views": result.get("views"),
                            "date": result.get("date"),
                            "query": query,
                            "engine": engine,
                        }
                    )
                    db.add(item)
                    items.append(item)
            
            elif search_type == "nws" or search_type == "news":
                results = data.get("news_results", [])
                for result in results[:num_results]:
                    item = DataItem(
                        project_id=project_id,
                        data_type="text",
                        source_url=result.get("link"),
                        content=f"{result.get('title', '')}\n\n{result.get('snippet', '')}",
                        item_metadata={
                            "thumbnail": result.get("thumbnail"),
                            "source": result.get("source"),
                            "date": result.get("date"),
                            "query": query,
                            "engine": engine,
                        }
                    )
                    db.add(item)
                    items.append(item)
            
            else:
                # Regular organic results
                results = data.get("organic_results", [])
                for result in results[:num_results]:
                    item = DataItem(
                        project_id=project_id,
                        data_type="text",
                        source_url=result.get("link"),
                        content=f"{result.get('title', '')}\n\n{result.get('snippet', '')}",
                        item_metadata={
                            "position": result.get("position"),
                            "displayed_link": result.get("displayed_link"),
                            "query": query,
                            "engine": engine,
                        }
                    )
                    db.add(item)
                    items.append(item)
        
        await db.commit()
        
        logger.info(f"SerpAPI collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]

