"""Browserless.io scraper provider for headless Chrome scraping."""
from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
import structlog
from bs4 import BeautifulSoup
import base64
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.models.data_item import DataItem
from app.core.storage import storage_service

logger = structlog.get_logger()


class BrowserlessScraper(BaseScraper):
    """Scraper using Browserless.io API for headless Chrome."""
    
    BASE_URL = "https://chrome.browserless.io"
    
    def __init__(self, token: str):
        self.token = token
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Browserless config."""
        required = ["urls"]
        return all(key in config for key in required)
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute Browserless scraping."""
        
        urls = config.get("urls", [])
        selector = config.get("selector")
        wait_for = config.get("wait_for")
        extract_type = config.get("extract_type", "text")
        take_screenshot = config.get("take_screenshot", False)
        extract_pdf = config.get("extract_pdf", False)
        
        logger.info(f"Browserless scraping {len(urls)} URLs")
        
        items = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for url in urls:
                try:
                    if extract_type == "screenshot" or take_screenshot:
                        # Take screenshot
                        item = await self._take_screenshot(
                            client, url, project_id, config
                        )
                        if item:
                            db.add(item)
                            items.append(item)
                    
                    elif extract_pdf:
                        # Generate PDF
                        item = await self._generate_pdf(
                            client, url, project_id, config
                        )
                        if item:
                            db.add(item)
                            items.append(item)
                    
                    else:
                        # Extract content
                        extracted_items = await self._extract_content(
                            client, url, project_id, config, db
                        )
                        items.extend(extracted_items)
                
                except Exception as e:
                    logger.error(f"Error scraping {url}: {str(e)}")
                    continue
        
        await db.commit()
        
        logger.info(f"Browserless collected {len(items)} items")
        return [{"id": str(item.id)} for item in items]
    
    async def _take_screenshot(
        self,
        client: httpx.AsyncClient,
        url: str,
        project_id: UUID,
        config: Dict[str, Any]
    ) -> DataItem:
        """Take a screenshot of a page."""
        
        payload = {
            "url": url,
            "options": {
                "fullPage": config.get("full_page", True),
                "type": "png",
            },
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            }
        }
        
        if config.get("wait_for"):
            payload["waitForSelector"] = {
                "selector": config["wait_for"],
                "timeout": 10000,
            }
        
        if config.get("viewport"):
            payload["viewport"] = config["viewport"]
        
        response = await client.post(
            f"{self.BASE_URL}/screenshot?token={self.token}",
            json=payload,
        )
        response.raise_for_status()
        
        # Save screenshot to storage
        image_data = response.content
        file_stream = io.BytesIO(image_data)
        file_path = storage_service.upload_file(
            file_stream,
            f"screenshot_{url.replace('/', '_')[:50]}.png",
            "image/png",
            f"projects/{project_id}/screenshots"
        )
        
        return DataItem(
            project_id=project_id,
            data_type="image",
            source_url=url,
            file_path=file_path,
            file_size=len(image_data),
            mime_type="image/png",
            item_metadata={
                "type": "screenshot",
                "full_page": config.get("full_page", True),
            }
        )
    
    async def _generate_pdf(
        self,
        client: httpx.AsyncClient,
        url: str,
        project_id: UUID,
        config: Dict[str, Any]
    ) -> DataItem:
        """Generate PDF of a page."""
        
        payload = {
            "url": url,
            "options": {
                "printBackground": True,
                "format": "A4",
            },
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            }
        }
        
        response = await client.post(
            f"{self.BASE_URL}/pdf?token={self.token}",
            json=payload,
        )
        response.raise_for_status()
        
        # Save PDF to storage
        pdf_data = response.content
        file_stream = io.BytesIO(pdf_data)
        file_path = storage_service.upload_file(
            file_stream,
            f"page_{url.replace('/', '_')[:50]}.pdf",
            "application/pdf",
            f"projects/{project_id}/pdfs"
        )
        
        return DataItem(
            project_id=project_id,
            data_type="text",
            source_url=url,
            file_path=file_path,
            file_size=len(pdf_data),
            mime_type="application/pdf",
            item_metadata={"type": "pdf"}
        )
    
    async def _extract_content(
        self,
        client: httpx.AsyncClient,
        url: str,
        project_id: UUID,
        config: Dict[str, Any],
        db: AsyncSession
    ) -> List[DataItem]:
        """Extract content from a page."""
        
        items = []
        selector = config.get("selector")
        extract_type = config.get("extract_type", "text")
        
        # Use /content endpoint for HTML
        payload = {
            "url": url,
            "gotoOptions": {
                "waitUntil": "networkidle2",
                "timeout": 30000,
            }
        }
        
        if config.get("wait_for"):
            payload["waitForSelector"] = {
                "selector": config["wait_for"],
                "timeout": 10000,
            }
        
        response = await client.post(
            f"{self.BASE_URL}/content?token={self.token}",
            json=payload,
        )
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'lxml')
        
        if extract_type == "text":
            if selector:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text:
                        item = DataItem(
                            project_id=project_id,
                            data_type="text",
                            source_url=url,
                            content=text,
                            item_metadata={
                                "selector": selector,
                                "provider": "browserless"
                            }
                        )
                        db.add(item)
                        items.append(item)
            else:
                # Remove script and style
                for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                    element.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                item = DataItem(
                    project_id=project_id,
                    data_type="text",
                    source_url=url,
                    content=text,
                    item_metadata={
                        "title": soup.title.string if soup.title else None,
                        "provider": "browserless"
                    }
                )
                db.add(item)
                items.append(item)
        
        elif extract_type == "html":
            if selector:
                elements = soup.select(selector)
                for element in elements:
                    item = DataItem(
                        project_id=project_id,
                        data_type="text",
                        source_url=url,
                        content=str(element),
                        item_metadata={
                            "selector": selector,
                            "format": "html",
                            "provider": "browserless"
                        }
                    )
                    db.add(item)
                    items.append(item)
            else:
                item = DataItem(
                    project_id=project_id,
                    data_type="text",
                    source_url=url,
                    content=html_content,
                    item_metadata={
                        "format": "html",
                        "provider": "browserless"
                    }
                )
                db.add(item)
                items.append(item)
        
        elif extract_type == "links":
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                if href and href.startswith('http'):
                    item = DataItem(
                        project_id=project_id,
                        data_type="structured",
                        source_url=url,
                        content=text,
                        item_metadata={
                            "link": href,
                            "provider": "browserless"
                        }
                    )
                    db.add(item)
                    items.append(item)
        
        elif extract_type == "images":
            images = soup.find_all('img', src=True)
            for img in images:
                src = img.get('src')
                alt = img.get('alt', '')
                if src and src.startswith('http'):
                    item = DataItem(
                        project_id=project_id,
                        data_type="image",
                        source_url=src,
                        content=alt,
                        item_metadata={
                            "page_url": url,
                            "provider": "browserless"
                        }
                    )
                    db.add(item)
                    items.append(item)
        
        return items
    
    async def scrape_with_function(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Execute custom JavaScript function on page."""
        
        url = config.get("url")
        js_function = config.get("js_function")
        
        if not url or not js_function:
            raise ValueError("URL and js_function are required")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "code": f"""
                    module.exports = async ({{ page }}) => {{
                        await page.goto('{url}', {{ waitUntil: 'networkidle2' }});
                        {js_function}
                    }};
                """
            }
            
            response = await client.post(
                f"{self.BASE_URL}/function?token={self.token}",
                json=payload,
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Save result as data item
            item = DataItem(
                project_id=project_id,
                data_type="structured",
                source_url=url,
                content=str(result),
                item_metadata={
                    "type": "function_result",
                    "provider": "browserless"
                }
            )
            db.add(item)
            await db.commit()
            
            return [{"id": str(item.id), "result": result}]

