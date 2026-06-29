"""Smart content extraction with readability algorithms."""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import re
import math
from urllib.parse import urljoin, urlparse
import structlog
from bs4 import BeautifulSoup, Tag, NavigableString

logger = structlog.get_logger()


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    title: str
    content: str
    html_content: str
    excerpt: str
    author: Optional[str]
    published_date: Optional[str]
    featured_image: Optional[str]
    images: List[Dict[str, str]]
    links: List[Dict[str, str]]
    word_count: int
    language: Optional[str]
    metadata: Dict[str, Any]


class ReadabilityExtractor:
    """Extracts main content from web pages using readability algorithms."""
    
    # Elements that are unlikely to contain main content
    UNLIKELY_CANDIDATES = re.compile(
        r'combx|comment|community|disqus|extra|foot|header|menu|remark|rss|'
        r'shoutbox|sidebar|sponsor|ad-break|agegate|pagination|pager|popup|'
        r'tweet|twitter|share|social|related|recommend|promo|banner|advertisement|'
        r'nav|navigation|breadcrumb|cookie|modal|overlay',
        re.IGNORECASE
    )
    
    # Elements that might contain main content
    POSITIVE_CANDIDATES = re.compile(
        r'article|body|content|entry|hentry|main|page|pagination|post|text|'
        r'blog|story|prose',
        re.IGNORECASE
    )
    
    # Elements to remove
    REMOVE_ELEMENTS = [
        'script', 'style', 'noscript', 'iframe', 'form', 'button',
        'input', 'textarea', 'select', 'nav', 'header', 'footer',
        'aside', 'figure', 'figcaption'
    ]
    
    # Block-level elements
    BLOCK_ELEMENTS = [
        'p', 'div', 'article', 'section', 'main', 'header', 'footer',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th'
    ]
    
    def __init__(
        self,
        min_text_length: int = 25,
        min_content_length: int = 100,
        remove_empty_elements: bool = True
    ):
        self.min_text_length = min_text_length
        self.min_content_length = min_content_length
        self.remove_empty_elements = remove_empty_elements
    
    def extract(self, html: str, url: Optional[str] = None) -> ExtractedContent:
        """Extract main content from HTML."""
        soup = BeautifulSoup(html, "lxml")
        
        # Extract metadata first
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        published_date = self._extract_date(soup)
        featured_image = self._extract_featured_image(soup, url)
        language = self._extract_language(soup)
        
        # Clean the document
        self._clean_document(soup)
        
        # Find and score content blocks
        candidates = self._find_candidates(soup)
        
        if not candidates:
            # Fallback to body content
            body = soup.find("body")
            if body:
                content_element = body
            else:
                content_element = soup
        else:
            # Get best candidate
            content_element = max(candidates, key=lambda x: x[1])[0]
        
        # Clean the content element
        self._clean_content(content_element)
        
        # Extract text content
        text_content = self._extract_text(content_element)
        html_content = str(content_element)
        
        # Extract images and links
        images = self._extract_images(content_element, url)
        links = self._extract_links(content_element, url)
        
        # Generate excerpt
        excerpt = self._generate_excerpt(text_content)
        
        # Word count
        word_count = len(text_content.split())
        
        # Additional metadata
        metadata = self._extract_metadata(soup)
        
        return ExtractedContent(
            title=title,
            content=text_content,
            html_content=html_content,
            excerpt=excerpt,
            author=author,
            published_date=published_date,
            featured_image=featured_image,
            images=images,
            links=links,
            word_count=word_count,
            language=language,
            metadata=metadata
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        
        # Try twitter:title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            return twitter_title["content"].strip()
        
        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        # Fall back to title tag
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name."""
        # Try meta tags
        for meta_name in ["author", "article:author", "og:article:author"]:
            meta = soup.find("meta", attrs={"name": meta_name}) or soup.find("meta", property=meta_name)
            if meta and meta.get("content"):
                return meta["content"].strip()
        
        # Try structured data
        for attr in ["itemprop", "rel"]:
            author_elem = soup.find(attrs={attr: "author"})
            if author_elem:
                return author_elem.get_text(strip=True)
        
        # Try common class names
        for class_name in ["author", "byline", "by-author", "article-author"]:
            author_elem = soup.find(class_=re.compile(class_name, re.I))
            if author_elem:
                text = author_elem.get_text(strip=True)
                # Clean up "By Author Name" format
                text = re.sub(r'^[Bb]y\s+', '', text)
                return text
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date."""
        # Try meta tags
        for meta_name in ["article:published_time", "og:article:published_time", "date", "pubdate"]:
            meta = soup.find("meta", attrs={"name": meta_name}) or soup.find("meta", property=meta_name)
            if meta and meta.get("content"):
                return meta["content"].strip()
        
        # Try time element
        time_elem = soup.find("time")
        if time_elem:
            if time_elem.get("datetime"):
                return time_elem["datetime"]
            return time_elem.get_text(strip=True)
        
        # Try structured data
        date_elem = soup.find(attrs={"itemprop": "datePublished"})
        if date_elem:
            if date_elem.get("datetime"):
                return date_elem["datetime"]
            if date_elem.get("content"):
                return date_elem["content"]
            return date_elem.get_text(strip=True)
        
        return None
    
    def _extract_featured_image(self, soup: BeautifulSoup, base_url: Optional[str]) -> Optional[str]:
        """Extract featured/hero image."""
        # Try og:image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            url = og_image["content"]
            if base_url:
                url = urljoin(base_url, url)
            return url
        
        # Try twitter:image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            url = twitter_image["content"]
            if base_url:
                url = urljoin(base_url, url)
            return url
        
        return None
    
    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page language."""
        html = soup.find("html")
        if html and html.get("lang"):
            return html["lang"]
        
        meta_lang = soup.find("meta", attrs={"http-equiv": "Content-Language"})
        if meta_lang and meta_lang.get("content"):
            return meta_lang["content"]
        
        return None
    
    def _clean_document(self, soup: BeautifulSoup):
        """Clean the document by removing unwanted elements."""
        # Remove script, style, etc.
        for tag_name in self.REMOVE_ELEMENTS:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, NavigableString) and text.strip().startswith('<!--')):
            comment.extract()
        
        # Remove hidden elements
        for elem in soup.find_all(style=re.compile(r'display:\s*none|visibility:\s*hidden', re.I)):
            elem.decompose()
        
        # Remove elements with unlikely class/id
        for elem in soup.find_all(True):
            if isinstance(elem, Tag):
                class_id = ' '.join([
                    ' '.join(elem.get('class', [])),
                    elem.get('id', '')
                ])
                
                if self.UNLIKELY_CANDIDATES.search(class_id):
                    if not self.POSITIVE_CANDIDATES.search(class_id):
                        elem.decompose()
    
    def _find_candidates(self, soup: BeautifulSoup) -> List[Tuple[Tag, float]]:
        """Find and score content candidates."""
        candidates = []
        
        # Look for article, main, or div elements
        for elem in soup.find_all(['article', 'main', 'div', 'section']):
            if not isinstance(elem, Tag):
                continue
            
            score = self._score_element(elem)
            
            if score > 0:
                candidates.append((elem, score))
        
        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:5]  # Return top 5 candidates
    
    def _score_element(self, elem: Tag) -> float:
        """Score an element based on content quality."""
        score = 0.0
        
        # Get text content
        text = elem.get_text(strip=True)
        
        if len(text) < self.min_content_length:
            return 0
        
        # Base score on text length
        score += min(len(text) / 100, 10)
        
        # Score based on class/id
        class_id = ' '.join([
            ' '.join(elem.get('class', [])),
            elem.get('id', '')
        ])
        
        if self.POSITIVE_CANDIDATES.search(class_id):
            score += 25
        
        if self.UNLIKELY_CANDIDATES.search(class_id):
            score -= 25
        
        # Score based on tag name
        tag_scores = {
            'article': 30,
            'main': 25,
            'section': 10,
            'div': 5
        }
        score += tag_scores.get(elem.name, 0)
        
        # Count paragraphs
        paragraphs = elem.find_all('p')
        good_paragraphs = sum(1 for p in paragraphs if len(p.get_text(strip=True)) > self.min_text_length)
        score += good_paragraphs * 3
        
        # Penalize too many links
        links = elem.find_all('a')
        text_length = len(text)
        if text_length > 0:
            link_density = len(links) / (text_length / 100)
            if link_density > 1:
                score -= link_density * 5
        
        # Bonus for having images
        images = elem.find_all('img')
        score += min(len(images) * 2, 10)
        
        return score
    
    def _clean_content(self, elem: Tag):
        """Clean the content element."""
        if not isinstance(elem, Tag):
            return
        
        # Remove empty elements
        if self.remove_empty_elements:
            for child in elem.find_all(True):
                if isinstance(child, Tag) and not child.get_text(strip=True):
                    child.decompose()
        
        # Remove remaining unwanted elements
        for tag_name in ['form', 'input', 'button', 'select', 'textarea']:
            for tag in elem.find_all(tag_name):
                tag.decompose()
    
    def _extract_text(self, elem: Tag) -> str:
        """Extract clean text from element."""
        if not isinstance(elem, Tag):
            return ""
        
        # Process text with proper spacing
        lines = []
        
        for child in elem.descendants:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    lines.append(text)
            elif isinstance(child, Tag) and child.name in self.BLOCK_ELEMENTS:
                lines.append("\n")
        
        # Join and clean up
        text = ' '.join(lines)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _extract_images(self, elem: Tag, base_url: Optional[str]) -> List[Dict[str, str]]:
        """Extract images from content."""
        images = []
        
        for img in elem.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            
            if base_url:
                src = urljoin(base_url, src)
            
            images.append({
                'url': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        
        return images
    
    def _extract_links(self, elem: Tag, base_url: Optional[str]) -> List[Dict[str, str]]:
        """Extract links from content."""
        links = []
        
        for a in elem.find_all('a', href=True):
            href = a['href']
            
            if base_url:
                href = urljoin(base_url, href)
            
            # Skip anchor links and javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            links.append({
                'url': href,
                'text': a.get_text(strip=True)
            })
        
        return links
    
    def _generate_excerpt(self, text: str, max_length: int = 300) -> str:
        """Generate a short excerpt from content."""
        # Get first paragraph or sentences
        paragraphs = text.split('\n\n')
        
        if paragraphs:
            excerpt = paragraphs[0]
        else:
            excerpt = text
        
        # Trim to max length
        if len(excerpt) > max_length:
            excerpt = excerpt[:max_length]
            # Try to end at a sentence
            last_period = excerpt.rfind('.')
            if last_period > max_length * 0.5:
                excerpt = excerpt[:last_period + 1]
            else:
                excerpt = excerpt.rsplit(' ', 1)[0] + '...'
        
        return excerpt
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract additional metadata."""
        metadata = {}
        
        # Description
        desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if desc and desc.get("content"):
            metadata["description"] = desc["content"]
        
        # Keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        if keywords and keywords.get("content"):
            metadata["keywords"] = [k.strip() for k in keywords["content"].split(",")]
        
        # Site name
        site_name = soup.find("meta", property="og:site_name")
        if site_name and site_name.get("content"):
            metadata["site_name"] = site_name["content"]
        
        # Type
        og_type = soup.find("meta", property="og:type")
        if og_type and og_type.get("content"):
            metadata["type"] = og_type["content"]
        
        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            metadata["canonical_url"] = canonical["href"]
        
        return metadata


class StructuredDataExtractor:
    """Extract structured data (JSON-LD, Microdata, RDFa) from web pages."""
    
    def extract(self, html: str) -> Dict[str, Any]:
        """Extract all structured data."""
        soup = BeautifulSoup(html, "lxml")
        
        data = {
            "json_ld": self._extract_json_ld(soup),
            "microdata": self._extract_microdata(soup),
            "opengraph": self._extract_opengraph(soup),
            "twitter_cards": self._extract_twitter_cards(soup),
        }
        
        return data
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract JSON-LD data."""
        import json
        
        results = []
        
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
            except:
                continue
        
        return results
    
    def _extract_microdata(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract Microdata."""
        results = []
        
        for item in soup.find_all(attrs={"itemscope": True}):
            item_data = {
                "type": item.get("itemtype", ""),
                "properties": {}
            }
            
            for prop in item.find_all(attrs={"itemprop": True}):
                prop_name = prop.get("itemprop")
                
                # Get value based on element type
                if prop.name == "meta":
                    value = prop.get("content")
                elif prop.name == "link":
                    value = prop.get("href")
                elif prop.name == "img":
                    value = prop.get("src")
                elif prop.name == "time":
                    value = prop.get("datetime") or prop.get_text(strip=True)
                else:
                    value = prop.get_text(strip=True)
                
                if prop_name and value:
                    if prop_name in item_data["properties"]:
                        if not isinstance(item_data["properties"][prop_name], list):
                            item_data["properties"][prop_name] = [item_data["properties"][prop_name]]
                        item_data["properties"][prop_name].append(value)
                    else:
                        item_data["properties"][prop_name] = value
            
            if item_data["properties"]:
                results.append(item_data)
        
        return results
    
    def _extract_opengraph(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Open Graph metadata."""
        og_data = {}
        
        for meta in soup.find_all("meta", property=re.compile(r"^og:")):
            prop = meta.get("property", "").replace("og:", "")
            content = meta.get("content")
            if prop and content:
                og_data[prop] = content
        
        return og_data
    
    def _extract_twitter_cards(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Twitter Cards metadata."""
        twitter_data = {}
        
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = meta.get("name", "").replace("twitter:", "")
            content = meta.get("content")
            if name and content:
                twitter_data[name] = content
        
        return twitter_data


class TableExtractor:
    """Extract tables from HTML and convert to structured data."""
    
    def extract_tables(self, html: str) -> List[Dict[str, Any]]:
        """Extract all tables as structured data."""
        soup = BeautifulSoup(html, "lxml")
        tables = []
        
        for table in soup.find_all("table"):
            table_data = self._parse_table(table)
            if table_data:
                tables.append(table_data)
        
        return tables
    
    def _parse_table(self, table: Tag) -> Optional[Dict[str, Any]]:
        """Parse a single table."""
        headers = []
        rows = []
        
        # Get caption if exists
        caption = table.find("caption")
        title = caption.get_text(strip=True) if caption else ""
        
        # Try to find headers
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        
        # Get rows
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            
            # If no headers yet and first row has th elements, use as headers
            if not headers and all(cell.name == "th" for cell in cells):
                headers = [cell.get_text(strip=True) for cell in cells]
                continue
            
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                rows.append(row_data)
        
        if not rows:
            return None
        
        # Create structured output
        if headers:
            # Create list of dicts
            structured_rows = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    key = headers[i] if i < len(headers) else f"column_{i}"
                    row_dict[key] = value
                structured_rows.append(row_dict)
            
            return {
                "title": title,
                "headers": headers,
                "rows": structured_rows,
                "raw_rows": rows
            }
        else:
            return {
                "title": title,
                "headers": [],
                "rows": rows,
                "raw_rows": rows
            }
    
    def to_csv(self, table_data: Dict[str, Any]) -> str:
        """Convert table data to CSV string."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if table_data["headers"]:
            writer.writerow(table_data["headers"])
        
        for row in table_data["raw_rows"]:
            writer.writerow(row)
        
        return output.getvalue()


# Global instances
readability_extractor = ReadabilityExtractor()
structured_data_extractor = StructuredDataExtractor()
table_extractor = TableExtractor()

