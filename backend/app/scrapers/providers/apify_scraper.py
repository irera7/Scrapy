from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import asyncio
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem

logger = structlog.get_logger()


class ApifyScraper(BaseScraper):
    """Scraper using Apify actors."""
    
    BASE_URL = "https://api.apify.com/v2"
    
    def __init__(self, token: str):
        self.token = token
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Apify config."""
        required = ["actor_id"]
        return all(key in config for key in required)
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute Apify actor and save results."""
        
        actor_id = config.get("actor_id")
        actor_input = config.get("input", {})
        
        logger.info(f"Apify running actor: {actor_id}")
        
        items = []
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Start actor run
            run_url = f"{self.BASE_URL}/acts/{actor_id}/runs"
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = await client.post(
                run_url,
                headers=headers,
                json=actor_input
            )
            response.raise_for_status()
            run_data = response.json()
            
            run_id = run_data["data"]["id"]
            
            # Poll for completion
            status_url = f"{self.BASE_URL}/actor-runs/{run_id}"
            max_wait = 600  # 10 minutes max
            waited = 0
            
            while waited < max_wait:
                await asyncio.sleep(5)
                waited += 5
                
                status_response = await client.get(status_url, headers=headers)
                status_data = status_response.json()
                status = status_data["data"]["status"]
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise Exception(f"Actor run failed with status: {status}")
            
            if waited >= max_wait:
                raise Exception("Actor run timed out")
            
            # Get results
            dataset_id = status_data["data"]["defaultDatasetId"]
            dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
            
            results_response = await client.get(dataset_url, headers=headers)
            results = results_response.json()
            
            # Process results
            for result in results:
                # Determine data type based on result content
                data_type = "structured"
                content = None
                source_url = None
                
                if isinstance(result, dict):
                    source_url = result.get("url") or result.get("link") or result.get("pageUrl")
                    
                    # Check for text content
                    text_fields = ["text", "content", "body", "description", "title"]
                    for field in text_fields:
                        if field in result and result[field]:
                            content = str(result[field])
                            data_type = "text"
                            break
                    
                    # Check for image
                    if result.get("imageUrl") or result.get("image"):
                        data_type = "image"
                        source_url = result.get("imageUrl") or result.get("image")
                
                item = DataItem(
                    project_id=project_id,
                    data_type=data_type,
                    source_url=source_url,
                    content=content,
                    item_metadata=result if isinstance(result, dict) else {"value": result}
                )
                db.add(item)
                items.append(item)
        
        await db.commit()
        
        logger.info(f"Apify collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]

