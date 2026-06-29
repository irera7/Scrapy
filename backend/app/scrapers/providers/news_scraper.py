"""News scraper for multiple news sources."""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import structlog
import httpx
from bs4 import BeautifulSoup

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.scrapers.anti_detection import anti_detection
from app.models.data_item import DataItem

logger = structlog.get_logger()

# Helper to create DataItem with job_id
def create_data_item(project_id: UUID, job_id: Optional[UUID], **kwargs) -> DataItem:
    """Create a DataItem with optional job_id."""
    return DataItem(project_id=project_id, job_id=job_id, **kwargs)


class NewsAPIScraper(BaseScraper):
    """Scraper using NewsAPI.org."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("query") or config.get("sources") or config.get("category"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape news articles."""
        scrape_type = config.get("type", "everything")
        items = []
        
        if scrape_type == "everything":
            items = await self._search_everything(config, project_id, db, job_id)
        elif scrape_type == "top_headlines":
            items = await self._get_top_headlines(config, project_id, db, job_id)
        elif scrape_type == "sources":
            items = await self._get_sources(config, project_id, db, job_id)
        
        await db.commit()
        return items
    
    async def _api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make NewsAPI request."""
        params["apiKey"] = self.api_key
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def _search_everything(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Search all articles."""
        query = config.get("query", "")
        max_results = min(config.get("max_results", 100), 100)
        language = config.get("language", "en")
        sort_by = config.get("sort_by", "relevancy")  # relevancy, popularity, publishedAt
        from_date = config.get("from_date")
        to_date = config.get("to_date")
        sources = config.get("sources")
        domains = config.get("domains")
        
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": max_results,
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if sources:
            params["sources"] = sources if isinstance(sources, str) else ",".join(sources)
        if domains:
            params["domains"] = domains if isinstance(domains, str) else ",".join(domains)
        
        logger.info(f"NewsAPI search: {query}")
        
        data = await self._api_request("everything", params)
        
        items = []
        for article in data.get("articles", []):
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="text",
                source_url=article.get("url"),
                content=f"{article.get('title', '')}\n\n{article.get('description', '')}\n\n{article.get('content', '')}",
                item_metadata={
                    "platform": "news",
                    "source": article.get("source", {}).get("name"),
                    "source_id": article.get("source", {}).get("id"),
                    "author": article.get("author"),
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "image_url": article.get("urlToImage"),
                    "published_at": article.get("publishedAt"),
                }
            )
            db.add(item)
            items.append(item)
        
        logger.info(f"Found {len(items)} news articles")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_top_headlines(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get top headlines."""
        country = config.get("country", "us")
        category = config.get("category")  # business, entertainment, general, health, science, sports, technology
        query = config.get("query")
        max_results = min(config.get("max_results", 100), 100)
        sources = config.get("sources")
        
        params = {
            "pageSize": max_results,
        }
        
        if sources:
            params["sources"] = sources if isinstance(sources, str) else ",".join(sources)
        else:
            params["country"] = country
            if category:
                params["category"] = category
        
        if query:
            params["q"] = query
        
        data = await self._api_request("top-headlines", params)
        
        items = []
        for article in data.get("articles", []):
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="text",
                source_url=article.get("url"),
                content=f"{article.get('title', '')}\n\n{article.get('description', '')}\n\n{article.get('content', '')}",
                item_metadata={
                    "platform": "news",
                    "type": "headline",
                    "source": article.get("source", {}).get("name"),
                    "source_id": article.get("source", {}).get("id"),
                    "author": article.get("author"),
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "image_url": article.get("urlToImage"),
                    "published_at": article.get("publishedAt"),
                    "country": country,
                    "category": category,
                }
            )
            db.add(item)
            items.append(item)
        
        logger.info(f"Found {len(items)} headlines")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_sources(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get available news sources."""
        category = config.get("category")
        language = config.get("language")
        country = config.get("country")
        
        params = {}
        if category:
            params["category"] = category
        if language:
            params["language"] = language
        if country:
            params["country"] = country
        
        data = await self._api_request("top-headlines/sources", params)
        
        items = []
        for source in data.get("sources", []):
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="structured",
                source_url=source.get("url"),
                content=source.get("description", ""),
                item_metadata={
                    "platform": "news",
                    "type": "source",
                    "source_id": source.get("id"),
                    "name": source.get("name"),
                    "category": source.get("category"),
                    "language": source.get("language"),
                    "country": source.get("country"),
                }
            )
            db.add(item)
            items.append(item)
        
        return [{"id": str(item.id)} for item in items]


class GoogleNewsScraper(BaseScraper):
    """Scraper for Google News with JS rendering support."""
    
    def __init__(self):
        self.rss_base_url = "https://news.google.com/rss"
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("query") or config.get("topic"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape Google News using multiple methods."""
        use_js = config.get("use_js_rendering", True)
        
        items = []
        
        # Try JS rendering first if enabled
        if use_js:
            try:
                items = await self._scrape_with_playwright(config, project_id, db, job_id)
                if items:
                    await db.commit()
                    logger.info(f"Scraped {len(items)} articles from Google News (Playwright)")
                    return [{"id": str(item.id)} for item in items]
            except Exception as e:
                logger.warning(f"Playwright scraping failed, falling back to RSS: {e}")
        
        # Fall back to RSS feed (doesn't require JS)
        items = await self._scrape_rss(config, project_id, db, job_id)
        
        if not items:
            # Last resort: try static HTML parsing
            items = await self._scrape_static(config, project_id, db, job_id)
        
        await db.commit()
        logger.info(f"Scraped {len(items)} articles from Google News")
        return [{"id": str(item.id)} for item in items]
    
    async def _scrape_with_playwright(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Scrape Google News with Playwright JS rendering."""
        from playwright.async_api import async_playwright
        
        query = config.get("query", "")
        topic = config.get("topic")
        language = config.get("language", "en")
        country = config.get("country", "US")
        max_results = config.get("max_results", 50)
        
        items = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = await context.new_page()
            
            try:
                # Build URL
                if query:
                    url = f"https://news.google.com/search?q={query}&hl={language}&gl={country}&ceid={country}:{language}"
                elif topic:
                    url = f"https://news.google.com/topics/{topic}?hl={language}&gl={country}&ceid={country}:{language}"
                else:
                    url = f"https://news.google.com/?hl={language}&gl={country}&ceid={country}:{language}"
                
                logger.info(f"Google News Playwright: navigating to {url}")
                
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Wait for articles to load
                await page.wait_for_selector("article", timeout=10000)
                
                # Scroll to load more articles
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                
                # Extract articles
                articles = await page.query_selector_all("article")
                logger.info(f"Found {len(articles)} article elements")
                
                for article in articles[:max_results]:
                    try:
                        # Get title and link
                        title_elem = await article.query_selector("h3 a, h4 a, a[href*='/articles/']")
                        if not title_elem:
                            continue
                        
                        title = await title_elem.inner_text()
                        link = await title_elem.get_attribute("href")
                        
                        if not title or not link:
                            continue
                        
                        # Convert relative URL
                        if link.startswith("./"):
                            link = f"https://news.google.com{link[1:]}"
                        elif link.startswith("/"):
                            link = f"https://news.google.com{link}"
                        
                        # Get source info
                        source_elem = await article.query_selector("[data-n-tid], .wEwyrc, .vr1PYe")
                        source = await source_elem.inner_text() if source_elem else ""
                        
                        # Get time
                        time_elem = await article.query_selector("time")
                        published_time = await time_elem.get_attribute("datetime") if time_elem else None
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="text",
                            source_url=link,
                            content=title.strip(),
                            item_metadata={
                                "platform": "google_news",
                                "title": title.strip(),
                                "source": source.strip() if source else None,
                                "published_at": published_time,
                                "query": query,
                                "topic": topic,
                                "language": language,
                                "country": country,
                                "scrape_method": "playwright"
                            }
                        )
                        db.add(item)
                        items.append(item)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse article element: {e}")
                        continue
                
            finally:
                await browser.close()
        
        return items
    
    async def _scrape_rss(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Scrape Google News RSS feed (no JS required)."""
        query = config.get("query", "")
        topic = config.get("topic")
        language = config.get("language", "en")
        country = config.get("country", "US")
        max_results = config.get("max_results", 50)
        
        items = []
        
        # Build RSS URL
        if query:
            # Search RSS
            rss_url = f"{self.rss_base_url}/search?q={query}&hl={language}&gl={country}&ceid={country}:{language}"
        elif topic:
            # Topic RSS - map topic names to RSS paths
            topic_map = {
                "WORLD": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB",
                "NATION": "topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNRGxqTjNjd0VnSmxiaWdBUAE",
                "BUSINESS": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
                "TECHNOLOGY": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
                "ENTERTAINMENT": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pWVXlnQVAB",
                "SPORTS": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pWVXlnQVAB",
                "SCIENCE": "topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB",
                "HEALTH": "topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ",
            }
            topic_path = topic_map.get(topic.upper(), topic)
            rss_url = f"{self.rss_base_url}/{topic_path}?hl={language}&gl={country}&ceid={country}:{language}"
        else:
            # Top stories RSS
            rss_url = f"{self.rss_base_url}?hl={language}&gl={country}&ceid={country}:{language}"
        
        logger.info(f"Google News RSS: fetching {rss_url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(rss_url, timeout=30, follow_redirects=True)
                response.raise_for_status()
                
                # Parse RSS XML
                soup = BeautifulSoup(response.text, "lxml-xml")
                
                for item_elem in soup.find_all("item")[:max_results]:
                    try:
                        title = item_elem.find("title").get_text(strip=True) if item_elem.find("title") else ""
                        link = item_elem.find("link").get_text(strip=True) if item_elem.find("link") else ""
                        pub_date = item_elem.find("pubDate").get_text(strip=True) if item_elem.find("pubDate") else None
                        source = item_elem.find("source").get_text(strip=True) if item_elem.find("source") else ""
                        description = item_elem.find("description").get_text(strip=True) if item_elem.find("description") else ""
                        
                        if not title or not link:
                            continue
                        
                        # Clean up description (remove HTML)
                        if description:
                            desc_soup = BeautifulSoup(description, "lxml")
                            description = desc_soup.get_text(strip=True)
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="text",
                            source_url=link,
                            content=f"{title}\n\n{description}" if description else title,
                            item_metadata={
                                "platform": "google_news",
                                "title": title,
                                "source": source,
                                "published_at": pub_date,
                                "query": query,
                                "topic": topic,
                                "language": language,
                                "country": country,
                                "scrape_method": "rss"
                            }
                        )
                        db.add(item)
                        items.append(item)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse RSS item: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to fetch RSS feed: {e}")
        
        return items
    
    async def _scrape_static(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Scrape Google News with static HTML (fallback)."""
        query = config.get("query", "")
        topic = config.get("topic")
        language = config.get("language", "en")
        country = config.get("country", "US")
        max_results = config.get("max_results", 50)
        
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        items = []
        
        async with httpx.AsyncClient() as client:
            if query:
                url = f"https://news.google.com/search?q={query}&hl={language}&gl={country}&ceid={country}:{language}"
            elif topic:
                url = f"https://news.google.com/topics/{topic}?hl={language}&gl={country}&ceid={country}:{language}"
            else:
                url = f"https://news.google.com/?hl={language}&gl={country}&ceid={country}:{language}"
            
            try:
                response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Find article elements
                articles = soup.select("article")
                
                for article in articles[:max_results]:
                    try:
                        title_elem = article.select_one("h3 a, h4 a, a[href*='/articles/']")
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get("href", "")
                        
                        if link.startswith("./"):
                            link = f"https://news.google.com{link[1:]}"
                        
                        source_elem = article.select_one("time")
                        source_text = source_elem.parent.get_text(strip=True) if source_elem else ""
                        
                        time_elem = article.select_one("time")
                        published_time = time_elem.get("datetime") if time_elem else None
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="text",
                            source_url=link,
                            content=title,
                            item_metadata={
                                "platform": "google_news",
                                "title": title,
                                "source": source_text.split("·")[0].strip() if "·" in source_text else source_text,
                                "published_at": published_time,
                                "query": query,
                                "topic": topic,
                                "language": language,
                                "country": country,
                                "scrape_method": "static"
                            }
                        )
                        db.add(item)
                        items.append(item)
                    
                    except Exception as e:
                        logger.warning(f"Failed to parse article: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Failed to scrape static page: {e}")
        
        return items


class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News."""
    
    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        valid_types = ["top", "new", "best", "ask", "show", "job", "item", "user"]
        return config.get("type", "top") in valid_types
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape Hacker News."""
        scrape_type = config.get("type", "top")
        max_results = config.get("max_results", 100)
        include_comments = config.get("include_comments", False)
        
        items = []
        
        async with httpx.AsyncClient() as client:
            if scrape_type == "item":
                # Get specific item
                item_id = config.get("item_id")
                if item_id:
                    items = await self._get_item(client, item_id, project_id, db, include_comments, job_id)
            elif scrape_type == "user":
                # Get user submissions
                username = config.get("username")
                if username:
                    items = await self._get_user_items(client, username, max_results, project_id, db, job_id)
            else:
                # Get story list
                story_ids = await self._get_story_ids(client, scrape_type)
                
                for story_id in story_ids[:max_results]:
                    story_items = await self._get_item(client, story_id, project_id, db, include_comments, job_id)
                    items.extend(story_items)
        
        await db.commit()
        logger.info(f"Scraped {len(items)} items from Hacker News")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_story_ids(self, client: httpx.AsyncClient, story_type: str) -> List[int]:
        """Get story IDs for a given type."""
        endpoint_map = {
            "top": "topstories",
            "new": "newstories",
            "best": "beststories",
            "ask": "askstories",
            "show": "showstories",
            "job": "jobstories",
        }
        
        endpoint = endpoint_map.get(story_type, "topstories")
        response = await client.get(f"{self.base_url}/{endpoint}.json", timeout=30)
        return response.json()
    
    async def _get_item(
        self,
        client: httpx.AsyncClient,
        item_id: int,
        project_id: UUID,
        db: AsyncSession,
        include_comments: bool = False,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Get a specific item."""
        items = []
        
        response = await client.get(f"{self.base_url}/item/{item_id}.json", timeout=30)
        data = response.json()
        
        if not data:
            return items
        
        # Create main item
        item_type = data.get("type", "story")
        
        if item_type in ["story", "job", "poll"]:
            content = data.get("title", "")
            if data.get("text"):
                content += f"\n\n{data.get('text')}"
            
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="text",
                source_url=data.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
                content=content,
                item_metadata={
                    "platform": "hackernews",
                    "type": item_type,
                    "item_id": item_id,
                    "title": data.get("title"),
                    "author": data.get("by"),
                    "score": data.get("score"),
                    "descendants": data.get("descendants", 0),
                    "time": data.get("time"),
                    "kids": data.get("kids", [])[:10],  # First 10 comment IDs
                }
            )
            db.add(item)
            items.append(item)
            
            # Fetch comments if requested
            if include_comments and data.get("kids"):
                for kid_id in data.get("kids", [])[:20]:  # Limit to 20 comments
                    comment_items = await self._get_item(client, kid_id, project_id, db, False, job_id)
                    items.extend(comment_items)
        
        elif item_type == "comment":
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="text",
                source_url=f"https://news.ycombinator.com/item?id={item_id}",
                content=data.get("text", ""),
                item_metadata={
                    "platform": "hackernews",
                    "type": "comment",
                    "item_id": item_id,
                    "author": data.get("by"),
                    "parent": data.get("parent"),
                    "time": data.get("time"),
                }
            )
            db.add(item)
            items.append(item)
        
        return items
    
    async def _get_user_items(
        self,
        client: httpx.AsyncClient,
        username: str,
        max_results: int,
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Get user's submitted items."""
        items = []
        
        response = await client.get(f"{self.base_url}/user/{username}.json", timeout=30)
        user_data = response.json()
        
        if not user_data or not user_data.get("submitted"):
            return items
        
        for item_id in user_data["submitted"][:max_results]:
            item_data = await self._get_item(client, item_id, project_id, db, False, job_id)
            items.extend(item_data)
        
        return items


class ArxivScraper(BaseScraper):
    """Scraper for arXiv papers."""
    
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"  # Use HTTPS
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("query") or config.get("id_list") or config.get("category"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape arXiv papers."""
        query = config.get("query", "")
        id_list = config.get("id_list", [])
        category = config.get("category")  # e.g., cs.AI, cs.LG, stat.ML
        max_results = config.get("max_results", 100)
        sort_by = config.get("sort_by", "submittedDate")  # relevance, lastUpdatedDate, submittedDate
        sort_order = config.get("sort_order", "descending")
        
        # Build search query
        search_query = query
        if category:
            cat_query = f"cat:{category}"
            search_query = f"{search_query} AND {cat_query}" if search_query else cat_query
        
        params = {
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        
        if search_query:
            params["search_query"] = search_query
        if id_list:
            params["id_list"] = ",".join(id_list)
        
        logger.info(f"arXiv search: {search_query}")
        
        items = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, timeout=60)
            
            # Parse Atom feed
            soup = BeautifulSoup(response.text, "lxml-xml")
            
            for entry in soup.find_all("entry"):
                # Extract paper info
                arxiv_id = entry.find("id").get_text().split("/abs/")[-1] if entry.find("id") else ""
                title = entry.find("title").get_text(strip=True) if entry.find("title") else ""
                summary = entry.find("summary").get_text(strip=True) if entry.find("summary") else ""
                
                # Authors
                authors = []
                for author in entry.find_all("author"):
                    name = author.find("name").get_text(strip=True) if author.find("name") else ""
                    if name:
                        authors.append(name)
                
                # Categories
                categories = []
                for cat in entry.find_all("category"):
                    term = cat.get("term")
                    if term:
                        categories.append(term)
                
                # Links
                pdf_link = None
                abstract_link = None
                for link in entry.find_all("link"):
                    if link.get("title") == "pdf":
                        pdf_link = link.get("href")
                    elif link.get("rel") == "alternate":
                        abstract_link = link.get("href")
                
                # Dates
                published = entry.find("published").get_text() if entry.find("published") else None
                updated = entry.find("updated").get_text() if entry.find("updated") else None
                
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=abstract_link or f"https://arxiv.org/abs/{arxiv_id}",
                    content=f"{title}\n\n{summary}",
                    item_metadata={
                        "platform": "arxiv",
                        "arxiv_id": arxiv_id,
                        "title": title,
                        "authors": authors,
                        "categories": categories,
                        "primary_category": categories[0] if categories else None,
                        "pdf_url": pdf_link,
                        "published": published,
                        "updated": updated,
                    }
                )
                db.add(item)
                items.append(item)
        
        await db.commit()
        logger.info(f"Found {len(items)} arXiv papers")
        return [{"id": str(item.id)} for item in items]


class WikipediaScraper(BaseScraper):
    """Scraper for Wikipedia articles."""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        # Wikipedia requires a proper User-Agent header
        self.headers = {
            "User-Agent": "AIDataCollector/1.0 (https://github.com/ai-data-collector; contact@example.com) Python/httpx"
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("query") or config.get("titles") or config.get("category"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Scrape Wikipedia articles."""
        scrape_type = config.get("type", "search")
        items = []
        
        if scrape_type == "search":
            items = await self._search_articles(config, project_id, db, job_id)
        elif scrape_type == "article":
            items = await self._get_article(config, project_id, db, job_id=job_id)
        elif scrape_type == "category":
            items = await self._get_category_articles(config, project_id, db, job_id)
        elif scrape_type == "random":
            items = await self._get_random_articles(config, project_id, db, job_id)
        
        await db.commit()
        return items
    
    async def _search_articles(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Search Wikipedia articles."""
        query = config.get("query", "")
        # Support both 'max_results' and 'limit' field names (frontend uses 'limit')
        max_results = config.get("max_results") or config.get("limit") or 50
        language = config.get("language", "en")
        
        base_url = f"https://{language}.wikipedia.org/w/api.php"
        
        items = []
        
        async with httpx.AsyncClient(headers=self.headers) as client:
            # Search for articles
            response = await client.get(base_url, params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
            }, timeout=30)
            
            data = response.json()
            
            for result in data.get("query", {}).get("search", []):
                title = result.get("title")
                page_id = result.get("pageid")
                
                # Get full article content
                article_items = await self._get_article({
                    "titles": title,
                    "language": language,
                    "include_sections": config.get("include_sections", True),
                }, project_id, db, client, job_id=job_id)
                
                items.extend(article_items)
        
        logger.info(f"Found {len(items)} Wikipedia articles")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_article(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        client: Optional[httpx.AsyncClient] = None,
        job_id: Optional[UUID] = None
    ) -> List[DataItem]:
        """Get specific Wikipedia article(s)."""
        titles = config.get("titles", "")
        if isinstance(titles, list):
            titles = "|".join(titles)
        
        language = config.get("language", "en")
        include_sections = config.get("include_sections", True)
        
        base_url = f"https://{language}.wikipedia.org/w/api.php"
        
        items = []
        
        should_close = False
        if client is None:
            client = httpx.AsyncClient(headers=self.headers)
            should_close = True
        
        try:
            # Get article content
            response = await client.get(base_url, params={
                "action": "query",
                "titles": titles,
                "prop": "extracts|info|categories|links",
                "exintro": "" if not include_sections else None,
                "explaintext": "",
                "inprop": "url",
                "format": "json",
            }, timeout=60)
            
            data = response.json()
            
            for page_id, page in data.get("query", {}).get("pages", {}).items():
                if page_id == "-1":  # Page not found
                    continue
                
                content = page.get("extract", "")
                
                # Get categories
                categories = [c.get("title", "").replace("Category:", "") 
                            for c in page.get("categories", [])]
                
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=page.get("fullurl") or f"https://{language}.wikipedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
                    content=content,
                    item_metadata={
                        "platform": "wikipedia",
                        "page_id": int(page_id),
                        "title": page.get("title"),
                        "language": language,
                        "categories": categories[:20],  # Limit categories
                        "content_length": len(content),
                    }
                )
                db.add(item)
                items.append(item)
        
        finally:
            if should_close:
                await client.aclose()
        
        return items
    
    async def _get_category_articles(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get articles from a category."""
        category = config.get("category", "")
        # Support both 'max_results' and 'limit' field names
        max_results = config.get("max_results") or config.get("limit") or 100
        language = config.get("language", "en")
        
        if not category.startswith("Category:"):
            category = f"Category:{category}"
        
        base_url = f"https://{language}.wikipedia.org/w/api.php"
        
        items = []
        
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(base_url, params={
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": max_results,
                "cmtype": "page",
                "format": "json",
            }, timeout=30)
            
            data = response.json()
            
            for member in data.get("query", {}).get("categorymembers", []):
                title = member.get("title")
                
                article_items = await self._get_article({
                    "titles": title,
                    "language": language,
                    "include_sections": config.get("include_sections", True),
                }, project_id, db, client, job_id=job_id)
                
                items.extend(article_items)
                
                if len(items) >= max_results:
                    break
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_random_articles(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get random Wikipedia articles."""
        # Support multiple field names
        count = config.get("count") or config.get("max_results") or config.get("limit") or 10
        language = config.get("language", "en")
        
        base_url = f"https://{language}.wikipedia.org/w/api.php"
        
        items = []
        
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(base_url, params={
                "action": "query",
                "list": "random",
                "rnlimit": count,
                "rnnamespace": 0,  # Main namespace only
                "format": "json",
            }, timeout=30)
            
            data = response.json()
            
            titles = [r.get("title") for r in data.get("query", {}).get("random", [])]
            
            if titles:
                article_items = await self._get_article({
                    "titles": titles,
                    "language": language,
                    "include_sections": config.get("include_sections", True),
                }, project_id, db, client, job_id=job_id)
                
                items.extend(article_items)
        
        return [{"id": str(item.id)} for item in items]

