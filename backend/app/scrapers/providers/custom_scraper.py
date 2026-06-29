from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import httpx
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class CustomScraper(BaseScraper):
    """Custom scraper using Playwright for dynamic pages."""
    
    def __init__(self):
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate custom scraper config."""
        required = ["urls"]
        return all(key in config for key in required)
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute custom scraping."""
        
        urls = config.get("urls", [])
        selector = config.get("selector")
        wait_for = config.get("wait_for")
        extract_type = config.get("extract_type", "text")
        download_images = config.get("download_images", False)
        
        logger.info(f"Custom scraper: {len(urls)} URLs, type: {extract_type}")
        
        items = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            for url in urls:
                try:
                    page = await context.new_page()
                    
                    # Navigate to page
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for specific element if specified
                    if wait_for:
                        await page.wait_for_selector(wait_for, timeout=10000)
                    
                    if extract_type == "text":
                        # Extract text content
                        if selector:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                text = await element.inner_text()
                                if text.strip():
                                    item = DataItem(
                                        project_id=project_id,
                                        job_id=job_id,
                                        data_type="text",
                                        source_url=url,
                                        content=text.strip(),
                                        item_metadata={"selector": selector}
                                    )
                                    db.add(item)
                                    items.append(item)
                        else:
                            # Get full page text
                            content = await page.content()
                            soup = BeautifulSoup(content, 'lxml')
                            
                            # Remove script and style elements
                            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                                element.decompose()
                            
                            text = soup.get_text(separator='\n', strip=True)
                            
                            item = DataItem(
                                project_id=project_id,
                                job_id=job_id,
                                data_type="text",
                                source_url=url,
                                content=text,
                                item_metadata={"title": await page.title()}
                            )
                            db.add(item)
                            items.append(item)
                    
                    elif extract_type == "html":
                        # Extract HTML content
                        if selector:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                html = await element.inner_html()
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="text",
                                    source_url=url,
                                    content=html,
                                    item_metadata={"selector": selector, "format": "html"}
                                )
                                db.add(item)
                                items.append(item)
                        else:
                            content = await page.content()
                            item = DataItem(
                                project_id=project_id,
                                job_id=job_id,
                                data_type="text",
                                source_url=url,
                                content=content,
                                item_metadata={"format": "html"}
                            )
                            db.add(item)
                            items.append(item)
                    
                    elif extract_type == "images":
                        # Extract image URLs
                        img_selector = selector or "img"
                        images = await page.query_selector_all(img_selector)
                        
                        for img in images:
                            src = await img.get_attribute("src")
                            alt = await img.get_attribute("alt") or ""
                            
                            if src and src.startswith("http"):
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="image",
                                    source_url=src,
                                    content=alt,
                                    item_metadata={"page_url": url}
                                )
                                
                                # Optionally download the image
                                if download_images:
                                    try:
                                        async with httpx.AsyncClient() as client:
                                            img_response = await client.get(src, timeout=30)
                                            if img_response.status_code == 200:
                                                content_type = img_response.headers.get("content-type", "image/jpeg")
                                                file_stream = io.BytesIO(img_response.content)
                                                file_path = storage_service.upload_file(
                                                    file_stream,
                                                    src.split("/")[-1].split("?")[0],
                                                    content_type,
                                                    f"projects/{project_id}/images"
                                                )
                                                item.file_path = file_path
                                                item.file_size = len(img_response.content)
                                                item.mime_type = content_type
                                    except Exception as e:
                                        logger.warning(f"Failed to download image: {src}, error: {e}")
                                
                                db.add(item)
                                items.append(item)
                    
                    elif extract_type == "links":
                        # Extract links
                        link_selector = selector or "a"
                        links = await page.query_selector_all(link_selector)
                        
                        for link in links:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            
                            if href:
                                item = DataItem(
                                    project_id=project_id,
                                    job_id=job_id,
                                    data_type="structured",
                                    source_url=url,
                                    content=text.strip() if text else "",
                                    item_metadata={
                                        "link": href,
                                        "page_url": url
                                    }
                                )
                                db.add(item)
                                items.append(item)
                    
                    await page.close()
                    
                except Exception as e:
                    logger.error(f"Error scraping {url}: {str(e)}")
                    continue
            
            await browser.close()
        
        await db.commit()
        
        logger.info(f"Custom scraper collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]

