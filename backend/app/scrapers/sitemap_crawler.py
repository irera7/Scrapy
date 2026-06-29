"""Sitemap and RSS crawler for discovering and collecting URLs."""
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
from datetime import datetime
from urllib.parse import urlparse, urljoin
import asyncio
import gzip
import io
import structlog
import httpx
from bs4 import BeautifulSoup

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.scrapers.anti_detection import anti_detection
from app.models.data_item import DataItem

logger = structlog.get_logger()


class SitemapCrawler(BaseScraper):
    """Crawler for sitemaps and discovering all URLs on a website."""
    
    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.visited_sitemaps: Set[str] = set()
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("base_url") or config.get("sitemap_url"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Crawl sitemap and discover URLs."""
        base_url = config.get("base_url")
        sitemap_url = config.get("sitemap_url")
        respect_robots = config.get("respect_robots", True)
        max_urls = config.get("max_urls", 1000)
        follow_sitemap_index = config.get("follow_sitemap_index", True)
        filter_patterns = config.get("filter_patterns", [])  # URL patterns to include
        exclude_patterns = config.get("exclude_patterns", [])  # URL patterns to exclude
        
        self.discovered_urls.clear()
        self.visited_sitemaps.clear()
        
        items = []
        
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            # Find sitemap URL if not provided
            if not sitemap_url:
                sitemap_url = await self._find_sitemap(client, base_url, headers, respect_robots)
            
            if sitemap_url:
                # Parse sitemap
                await self._parse_sitemap(
                    client, 
                    sitemap_url, 
                    headers, 
                    follow_sitemap_index,
                    max_urls
                )
            else:
                # Try common sitemap locations
                common_paths = [
                    "/sitemap.xml",
                    "/sitemap_index.xml",
                    "/sitemap/sitemap.xml",
                    "/sitemaps/sitemap.xml",
                ]
                
                for path in common_paths:
                    test_url = urljoin(base_url, path)
                    try:
                        response = await client.get(test_url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            sitemap_url = test_url
                            await self._parse_sitemap(
                                client,
                                sitemap_url,
                                headers,
                                follow_sitemap_index,
                                max_urls
                            )
                            break
                    except:
                        continue
            
            # Apply filters
            filtered_urls = self._filter_urls(
                list(self.discovered_urls),
                filter_patterns,
                exclude_patterns
            )
            
            # Create data items
            for url in filtered_urls[:max_urls]:
                item = DataItem(
                    project_id=project_id,
                    data_type="structured",
                    source_url=url,
                    content="",
                    item_metadata={
                        "type": "discovered_url",
                        "source": "sitemap",
                        "sitemap_url": sitemap_url,
                        "base_url": base_url,
                    }
                )
                db.add(item)
                items.append(item)
        
        await db.commit()
        logger.info(f"Discovered {len(items)} URLs from sitemap")
        return [{"id": str(item.id)} for item in items]
    
    async def _find_sitemap(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict[str, str],
        respect_robots: bool
    ) -> Optional[str]:
        """Find sitemap URL from robots.txt."""
        if not respect_robots:
            return None
        
        robots_url = urljoin(base_url, "/robots.txt")
        
        try:
            response = await client.get(robots_url, headers=headers, timeout=10)
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    line = line.strip().lower()
                    if line.startswith("sitemap:"):
                        return line.split(":", 1)[1].strip()
        except:
            pass
        
        return None
    
    async def _parse_sitemap(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        follow_index: bool,
        max_urls: int
    ):
        """Parse a sitemap file."""
        if url in self.visited_sitemaps:
            return
        
        self.visited_sitemaps.add(url)
        
        try:
            response = await client.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return
            
            content = response.content
            
            # Handle gzipped sitemaps
            if url.endswith(".gz") or response.headers.get("content-encoding") == "gzip":
                try:
                    content = gzip.decompress(content)
                except:
                    pass
            
            soup = BeautifulSoup(content, "lxml-xml")
            
            # Check if it's a sitemap index
            sitemap_tags = soup.find_all("sitemap")
            if sitemap_tags and follow_index:
                # It's a sitemap index
                for sitemap in sitemap_tags:
                    loc = sitemap.find("loc")
                    if loc:
                        sitemap_url = loc.get_text(strip=True)
                        await self._parse_sitemap(
                            client,
                            sitemap_url,
                            headers,
                            follow_index,
                            max_urls
                        )
                        
                        if len(self.discovered_urls) >= max_urls:
                            return
            
            # Parse URL entries
            url_tags = soup.find_all("url")
            for url_tag in url_tags:
                loc = url_tag.find("loc")
                if loc:
                    discovered_url = loc.get_text(strip=True)
                    self.discovered_urls.add(discovered_url)
                    
                    if len(self.discovered_urls) >= max_urls:
                        return
            
            logger.info(f"Parsed sitemap {url}: found {len(url_tags)} URLs")
        
        except Exception as e:
            logger.warning(f"Failed to parse sitemap {url}: {e}")
    
    def _filter_urls(
        self,
        urls: List[str],
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> List[str]:
        """Filter URLs based on patterns."""
        import re
        
        filtered = urls
        
        # Apply include patterns (if any)
        if include_patterns:
            filtered = [
                url for url in filtered
                if any(re.search(pattern, url) for pattern in include_patterns)
            ]
        
        # Apply exclude patterns
        if exclude_patterns:
            filtered = [
                url for url in filtered
                if not any(re.search(pattern, url) for pattern in exclude_patterns)
            ]
        
        return filtered


class RSSCrawler(BaseScraper):
    """Crawler for RSS and Atom feeds."""
    
    def __init__(self):
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("feed_url") or config.get("feed_urls"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Parse RSS/Atom feeds."""
        feed_urls = config.get("feed_urls", [])
        if config.get("feed_url"):
            feed_urls.append(config["feed_url"])
        
        max_items = config.get("max_items", 100)
        fetch_content = config.get("fetch_content", False)
        
        items = []
        
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            for feed_url in feed_urls:
                try:
                    feed_items = await self._parse_feed(
                        client,
                        feed_url,
                        headers,
                        project_id,
                        db,
                        max_items - len(items),
                        fetch_content
                    )
                    items.extend(feed_items)
                    
                    if len(items) >= max_items:
                        break
                
                except Exception as e:
                    logger.warning(f"Failed to parse feed {feed_url}: {e}")
        
        await db.commit()
        logger.info(f"Collected {len(items)} items from RSS feeds")
        return [{"id": str(item.id)} for item in items]
    
    async def _parse_feed(
        self,
        client: httpx.AsyncClient,
        feed_url: str,
        headers: Dict[str, str],
        project_id: UUID,
        db: AsyncSession,
        max_items: int,
        fetch_content: bool
    ) -> List[DataItem]:
        """Parse a single feed."""
        items = []
        
        response = await client.get(feed_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return items
        
        soup = BeautifulSoup(response.content, "lxml-xml")
        
        # Determine feed type and parse
        feed_type = self._detect_feed_type(soup)
        
        if feed_type == "rss":
            items = await self._parse_rss(soup, feed_url, project_id, db, max_items, fetch_content, client, headers)
        elif feed_type == "atom":
            items = await self._parse_atom(soup, feed_url, project_id, db, max_items, fetch_content, client, headers)
        
        return items
    
    def _detect_feed_type(self, soup: BeautifulSoup) -> str:
        """Detect if feed is RSS or Atom."""
        if soup.find("feed"):
            return "atom"
        elif soup.find("rss") or soup.find("channel"):
            return "rss"
        return "unknown"
    
    async def _parse_rss(
        self,
        soup: BeautifulSoup,
        feed_url: str,
        project_id: UUID,
        db: AsyncSession,
        max_items: int,
        fetch_content: bool,
        client: httpx.AsyncClient,
        headers: Dict[str, str]
    ) -> List[DataItem]:
        """Parse RSS 2.0 feed."""
        items = []
        
        # Get feed info
        channel = soup.find("channel")
        feed_title = channel.find("title").get_text(strip=True) if channel and channel.find("title") else ""
        feed_description = channel.find("description").get_text(strip=True) if channel and channel.find("description") else ""
        
        for item_elem in soup.find_all("item")[:max_items]:
            title = item_elem.find("title").get_text(strip=True) if item_elem.find("title") else ""
            link = item_elem.find("link").get_text(strip=True) if item_elem.find("link") else ""
            description = item_elem.find("description").get_text(strip=True) if item_elem.find("description") else ""
            pub_date = item_elem.find("pubDate").get_text(strip=True) if item_elem.find("pubDate") else None
            guid = item_elem.find("guid").get_text(strip=True) if item_elem.find("guid") else None
            author = item_elem.find("author").get_text(strip=True) if item_elem.find("author") else None
            
            # Categories
            categories = [cat.get_text(strip=True) for cat in item_elem.find_all("category")]
            
            # Enclosure (media)
            enclosure = item_elem.find("enclosure")
            media_url = enclosure.get("url") if enclosure else None
            media_type = enclosure.get("type") if enclosure else None
            
            content = f"{title}\n\n{description}"
            
            # Fetch full content if requested
            if fetch_content and link:
                try:
                    full_content = await self._fetch_article_content(client, link, headers)
                    if full_content:
                        content = f"{title}\n\n{full_content}"
                except:
                    pass
            
            item = DataItem(
                project_id=project_id,
                data_type="text",
                source_url=link,
                content=content,
                item_metadata={
                    "platform": "rss",
                    "feed_url": feed_url,
                    "feed_title": feed_title,
                    "title": title,
                    "guid": guid,
                    "author": author,
                    "categories": categories,
                    "published_at": pub_date,
                    "media_url": media_url,
                    "media_type": media_type,
                }
            )
            db.add(item)
            items.append(item)
        
        return items
    
    async def _parse_atom(
        self,
        soup: BeautifulSoup,
        feed_url: str,
        project_id: UUID,
        db: AsyncSession,
        max_items: int,
        fetch_content: bool,
        client: httpx.AsyncClient,
        headers: Dict[str, str]
    ) -> List[DataItem]:
        """Parse Atom feed."""
        items = []
        
        # Get feed info
        feed = soup.find("feed")
        feed_title = feed.find("title").get_text(strip=True) if feed and feed.find("title") else ""
        
        for entry in soup.find_all("entry")[:max_items]:
            title = entry.find("title").get_text(strip=True) if entry.find("title") else ""
            
            # Get link
            link = ""
            link_elem = entry.find("link", rel="alternate") or entry.find("link")
            if link_elem:
                link = link_elem.get("href", "")
            
            # Get content
            content_elem = entry.find("content") or entry.find("summary")
            description = content_elem.get_text(strip=True) if content_elem else ""
            
            # Get other metadata
            published = entry.find("published").get_text(strip=True) if entry.find("published") else None
            updated = entry.find("updated").get_text(strip=True) if entry.find("updated") else None
            entry_id = entry.find("id").get_text(strip=True) if entry.find("id") else None
            
            # Author
            author_elem = entry.find("author")
            author = author_elem.find("name").get_text(strip=True) if author_elem and author_elem.find("name") else None
            
            # Categories
            categories = [cat.get("term", "") for cat in entry.find_all("category")]
            
            content = f"{title}\n\n{description}"
            
            # Fetch full content if requested
            if fetch_content and link:
                try:
                    full_content = await self._fetch_article_content(client, link, headers)
                    if full_content:
                        content = f"{title}\n\n{full_content}"
                except:
                    pass
            
            item = DataItem(
                project_id=project_id,
                data_type="text",
                source_url=link,
                content=content,
                item_metadata={
                    "platform": "atom",
                    "feed_url": feed_url,
                    "feed_title": feed_title,
                    "title": title,
                    "entry_id": entry_id,
                    "author": author,
                    "categories": categories,
                    "published_at": published,
                    "updated_at": updated,
                }
            )
            db.add(item)
            items.append(item)
        
        return items
    
    async def _fetch_article_content(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str]
    ) -> Optional[str]:
        """Fetch full article content."""
        try:
            response = await client.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Try common article containers
            article = (
                soup.find("article") or
                soup.find("div", class_=["post-content", "article-content", "entry-content", "content"]) or
                soup.find("main")
            )
            
            if article:
                # Remove unwanted elements
                for elem in article.find_all(["script", "style", "nav", "aside", "footer", "header"]):
                    elem.decompose()
                
                return article.get_text(separator="\n", strip=True)
            
            return None
        
        except:
            return None


class RobotsTxtParser:
    """Parser for robots.txt files."""
    
    def __init__(self, content: str, user_agent: str = "*"):
        self.rules: Dict[str, List[Dict[str, Any]]] = {}
        self.sitemaps: List[str] = []
        self.crawl_delay: Optional[float] = None
        self.user_agent = user_agent
        self._parse(content)
    
    def _parse(self, content: str):
        """Parse robots.txt content."""
        current_agents = []
        current_rules = []
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Split directive
            if ":" not in line:
                continue
            
            directive, value = line.split(":", 1)
            directive = directive.strip().lower()
            value = value.strip()
            
            if directive == "user-agent":
                # Save previous rules
                if current_agents and current_rules:
                    for agent in current_agents:
                        self.rules[agent] = current_rules.copy()
                
                current_agents = [value.lower()]
                current_rules = []
            
            elif directive == "disallow":
                current_rules.append({"type": "disallow", "path": value})
            
            elif directive == "allow":
                current_rules.append({"type": "allow", "path": value})
            
            elif directive == "sitemap":
                self.sitemaps.append(value)
            
            elif directive == "crawl-delay":
                try:
                    self.crawl_delay = float(value)
                except:
                    pass
        
        # Save final rules
        if current_agents and current_rules:
            for agent in current_agents:
                self.rules[agent] = current_rules.copy()
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched."""
        path = urlparse(url).path
        
        # Find applicable rules
        rules = self.rules.get(self.user_agent.lower()) or self.rules.get("*", [])
        
        # Check rules in order
        for rule in rules:
            if path.startswith(rule["path"]):
                return rule["type"] == "allow"
        
        return True  # Default allow
    
    def get_crawl_delay(self) -> Optional[float]:
        """Get crawl delay."""
        return self.crawl_delay
    
    def get_sitemaps(self) -> List[str]:
        """Get sitemap URLs."""
        return self.sitemaps


class WebCrawler(BaseScraper):
    """General purpose web crawler with link following."""
    
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.url_queue: List[str] = []
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return bool(config.get("start_urls") or config.get("start_url"))
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Crawl website following links."""
        start_urls = config.get("start_urls", [])
        if config.get("start_url"):
            start_urls.append(config["start_url"])
        
        max_depth = config.get("max_depth", 2)
        max_pages = config.get("max_pages", 100)
        same_domain = config.get("same_domain", True)
        respect_robots = config.get("respect_robots", True)
        delay = config.get("delay", 1.0)  # Seconds between requests
        
        self.visited_urls.clear()
        
        items = []
        
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        # Get base domains
        base_domains = set()
        for url in start_urls:
            parsed = urlparse(url)
            base_domains.add(parsed.netloc)
        
        # Parse robots.txt for each domain
        robots_parsers: Dict[str, RobotsTxtParser] = {}
        
        async with httpx.AsyncClient() as client:
            if respect_robots:
                for domain in base_domains:
                    try:
                        robots_url = f"https://{domain}/robots.txt"
                        response = await client.get(robots_url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            robots_parsers[domain] = RobotsTxtParser(response.text)
                    except:
                        pass
            
            # BFS crawl
            queue = [(url, 0) for url in start_urls]  # (url, depth)
            
            while queue and len(items) < max_pages:
                url, depth = queue.pop(0)
                
                if url in self.visited_urls:
                    continue
                
                # Check domain restriction
                parsed = urlparse(url)
                if same_domain and parsed.netloc not in base_domains:
                    continue
                
                # Check robots.txt
                if respect_robots and parsed.netloc in robots_parsers:
                    if not robots_parsers[parsed.netloc].can_fetch(url):
                        continue
                
                self.visited_urls.add(url)
                
                try:
                    # Apply delay
                    await asyncio.sleep(delay)
                    
                    # Fetch page
                    response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
                    
                    if response.status_code != 200:
                        continue
                    
                    # Check content type
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        continue
                    
                    soup = BeautifulSoup(response.text, "lxml")
                    
                    # Extract content
                    title = soup.find("title").get_text(strip=True) if soup.find("title") else ""
                    
                    # Get main content
                    main_content = soup.find("article") or soup.find("main") or soup.find("body")
                    if main_content:
                        for elem in main_content.find_all(["script", "style", "nav", "footer", "header"]):
                            elem.decompose()
                        text_content = main_content.get_text(separator="\n", strip=True)
                    else:
                        text_content = ""
                    
                    # Create data item
                    item = DataItem(
                        project_id=project_id,
                        data_type="text",
                        source_url=str(response.url),
                        content=f"{title}\n\n{text_content}",
                        item_metadata={
                            "platform": "web",
                            "type": "crawled_page",
                            "title": title,
                            "depth": depth,
                            "content_length": len(text_content),
                        }
                    )
                    db.add(item)
                    items.append(item)
                    
                    # Extract links if not at max depth
                    if depth < max_depth:
                        for link in soup.find_all("a", href=True):
                            href = link.get("href")
                            if href:
                                # Resolve relative URLs
                                full_url = urljoin(str(response.url), href)
                                
                                # Clean URL
                                parsed_link = urlparse(full_url)
                                clean_url = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                                
                                if clean_url not in self.visited_urls:
                                    queue.append((clean_url, depth + 1))
                
                except Exception as e:
                    logger.warning(f"Failed to crawl {url}: {e}")
                    continue
        
        await db.commit()
        logger.info(f"Crawled {len(items)} pages")
        return [{"id": str(item.id)} for item in items]

