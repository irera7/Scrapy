"""Visual scraping API for no-code selector building."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import json
import structlog
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

from app.scrapers.anti_detection import anti_detection
from app.scrapers.stealth_browser import StealthBrowser, StealthPage

logger = structlog.get_logger()


@dataclass
class SelectorCandidate:
    """A potential CSS selector for an element."""
    selector: str
    specificity: int  # Higher is more specific
    matches_count: int  # Number of elements matched
    sample_text: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class ElementInfo:
    """Information about a DOM element."""
    tag: str
    id: Optional[str]
    classes: List[str]
    text: str
    html: str
    attributes: Dict[str, str]
    xpath: str
    css_selector: str
    suggested_selectors: List[SelectorCandidate]
    children_count: int
    parent_tag: Optional[str]
    siblings_count: int
    position: Dict[str, float]  # bounding box


@dataclass
class ExtractionRule:
    """A rule for extracting data from a page."""
    id: str
    name: str
    selector: str
    extract_type: str  # text, html, attribute, count
    attribute_name: Optional[str] = None  # for attribute extraction
    multiple: bool = False
    transform: Optional[str] = None  # regex, trim, lowercase, etc.


@dataclass
class ScrapingRecipe:
    """A complete scraping recipe with multiple extraction rules."""
    id: str
    name: str
    base_url: str
    rules: List[ExtractionRule]
    pagination: Optional[Dict[str, Any]] = None
    wait_for: Optional[str] = None
    scroll_to_bottom: bool = False
    created_at: str = ""
    updated_at: str = ""


class VisualScraperAPI:
    """API for visual/no-code scraping configuration."""
    
    def __init__(self):
        self.browser: Optional[StealthBrowser] = None
        self.page: Optional[StealthPage] = None
        self._current_url: Optional[str] = None
    
    async def start_session(self, headless: bool = True):
        """Start a browser session."""
        self.browser = StealthBrowser()
        await self.browser.start(headless=headless)
    
    async def end_session(self):
        """End the browser session."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.stop()
        self.page = None
        self.browser = None
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL and return page info."""
        if not self.browser:
            await self.start_session()
        
        self.page = await self.browser.new_page()
        await self.page.goto(url)
        self._current_url = url
        
        # Get page structure
        structure = await self._get_page_structure()
        
        return {
            "url": url,
            "title": await self.page.page.title(),
            "structure": structure
        }
    
    async def _get_page_structure(self) -> Dict[str, Any]:
        """Get a simplified structure of the page."""
        return await self.page.evaluate("""
            () => {
                function getStructure(element, depth = 0, maxDepth = 3) {
                    if (depth > maxDepth) return null;
                    
                    const children = Array.from(element.children)
                        .filter(el => !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName))
                        .slice(0, 10)
                        .map(el => getStructure(el, depth + 1, maxDepth))
                        .filter(el => el !== null);
                    
                    return {
                        tag: element.tagName.toLowerCase(),
                        id: element.id || null,
                        classes: Array.from(element.classList),
                        childCount: element.children.length,
                        textLength: element.innerText?.length || 0,
                        children: children
                    };
                }
                
                return getStructure(document.body);
            }
        """)
    
    async def get_element_at_point(self, x: int, y: int) -> ElementInfo:
        """Get element information at a specific point."""
        if not self.page:
            raise ValueError("No active page")
        
        element_data = await self.page.evaluate(f"""
            () => {{
                const element = document.elementFromPoint({x}, {y});
                if (!element) return null;
                
                const rect = element.getBoundingClientRect();
                
                // Generate XPath
                function getXPath(el) {{
                    if (el.id) return '//*[@id="' + el.id + '"]';
                    if (el === document.body) return '/html/body';
                    
                    let ix = 0;
                    const siblings = el.parentNode.childNodes;
                    for (let i = 0; i < siblings.length; i++) {{
                        const sibling = siblings[i];
                        if (sibling === el) {{
                            return getXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }}
                        if (sibling.nodeType === 1 && sibling.tagName === el.tagName) {{
                            ix++;
                        }}
                    }}
                }}
                
                // Generate CSS selector
                function getCSSSelector(el) {{
                    if (el.id) return '#' + el.id;
                    
                    let selector = el.tagName.toLowerCase();
                    if (el.className) {{
                        selector += '.' + Array.from(el.classList).join('.');
                    }}
                    
                    // Add nth-child if needed
                    const parent = el.parentNode;
                    if (parent) {{
                        const siblings = Array.from(parent.children).filter(
                            c => c.tagName === el.tagName
                        );
                        if (siblings.length > 1) {{
                            const index = siblings.indexOf(el) + 1;
                            selector += ':nth-of-type(' + index + ')';
                        }}
                    }}
                    
                    return selector;
                }}
                
                // Get attributes
                const attributes = {{}};
                for (const attr of element.attributes) {{
                    attributes[attr.name] = attr.value;
                }}
                
                return {{
                    tag: element.tagName.toLowerCase(),
                    id: element.id || null,
                    classes: Array.from(element.classList),
                    text: element.innerText?.substring(0, 500) || '',
                    html: element.outerHTML.substring(0, 1000),
                    attributes: attributes,
                    xpath: getXPath(element),
                    cssSelector: getCSSSelector(element),
                    childrenCount: element.children.length,
                    parentTag: element.parentNode?.tagName?.toLowerCase() || null,
                    siblingsCount: element.parentNode?.children?.length - 1 || 0,
                    position: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }}
                }};
            }}
        """)
        
        if not element_data:
            raise ValueError("No element at that point")
        
        # Generate suggested selectors
        suggested = await self._generate_selector_suggestions(element_data)
        
        return ElementInfo(
            tag=element_data["tag"],
            id=element_data.get("id"),
            classes=element_data.get("classes", []),
            text=element_data.get("text", ""),
            html=element_data.get("html", ""),
            attributes=element_data.get("attributes", {}),
            xpath=element_data.get("xpath", ""),
            css_selector=element_data.get("cssSelector", ""),
            suggested_selectors=suggested,
            children_count=element_data.get("childrenCount", 0),
            parent_tag=element_data.get("parentTag"),
            siblings_count=element_data.get("siblingsCount", 0),
            position=element_data.get("position", {})
        )
    
    async def _generate_selector_suggestions(self, element_data: Dict[str, Any]) -> List[SelectorCandidate]:
        """Generate multiple CSS selector options for an element."""
        suggestions = []
        
        # ID-based selector
        if element_data.get("id"):
            selector = f"#{element_data['id']}"
            count = await self._count_matches(selector)
            suggestions.append(SelectorCandidate(
                selector=selector,
                specificity=100,
                matches_count=count,
                sample_text=element_data.get("text", "")[:100]
            ))
        
        # Class-based selectors
        classes = element_data.get("classes", [])
        if classes:
            # All classes
            selector = element_data["tag"] + "." + ".".join(classes)
            count = await self._count_matches(selector)
            suggestions.append(SelectorCandidate(
                selector=selector,
                specificity=len(classes) * 10 + 1,
                matches_count=count,
                sample_text=element_data.get("text", "")[:100]
            ))
            
            # Each class individually
            for cls in classes[:3]:  # Limit to first 3
                selector = f".{cls}"
                count = await self._count_matches(selector)
                suggestions.append(SelectorCandidate(
                    selector=selector,
                    specificity=10,
                    matches_count=count,
                    sample_text=element_data.get("text", "")[:100]
                ))
        
        # Attribute-based selectors
        attrs = element_data.get("attributes", {})
        useful_attrs = ["data-testid", "data-id", "name", "role", "aria-label"]
        for attr in useful_attrs:
            if attr in attrs:
                selector = f'[{attr}="{attrs[attr]}"]'
                count = await self._count_matches(selector)
                suggestions.append(SelectorCandidate(
                    selector=selector,
                    specificity=40,
                    matches_count=count,
                    sample_text=element_data.get("text", "")[:100],
                    attributes={attr: attrs[attr]}
                ))
        
        # Tag + parent context
        if element_data.get("parentTag"):
            parent = element_data["parentTag"]
            tag = element_data["tag"]
            selector = f"{parent} > {tag}"
            count = await self._count_matches(selector)
            suggestions.append(SelectorCandidate(
                selector=selector,
                specificity=2,
                matches_count=count,
                sample_text=element_data.get("text", "")[:100]
            ))
        
        # Sort by specificity and match count
        suggestions.sort(key=lambda s: (-s.specificity if s.matches_count == 1 else s.matches_count))
        
        return suggestions[:10]  # Return top 10
    
    async def _count_matches(self, selector: str) -> int:
        """Count how many elements match a selector."""
        if not self.page:
            return 0
        
        try:
            return await self.page.evaluate(f"""
                () => document.querySelectorAll('{selector}').length
            """)
        except:
            return 0
    
    async def test_selector(self, selector: str) -> Dict[str, Any]:
        """Test a CSS selector and return matching elements."""
        if not self.page:
            raise ValueError("No active page")
        
        results = await self.page.evaluate(f"""
            () => {{
                const elements = document.querySelectorAll('{selector}');
                return Array.from(elements).slice(0, 20).map(el => ({{
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText?.substring(0, 200) || '',
                    html: el.outerHTML.substring(0, 500),
                    rect: el.getBoundingClientRect()
                }}));
            }}
        """)
        
        return {
            "selector": selector,
            "count": len(results),
            "matches": results
        }
    
    async def extract_data(self, rules: List[ExtractionRule]) -> Dict[str, Any]:
        """Extract data using a list of rules."""
        if not self.page:
            raise ValueError("No active page")
        
        results = {}
        
        for rule in rules:
            try:
                if rule.multiple:
                    elements = await self.page.page.query_selector_all(rule.selector)
                    values = []
                    for elem in elements:
                        value = await self._extract_value(elem, rule)
                        if value:
                            values.append(value)
                    results[rule.name] = values
                else:
                    element = await self.page.page.query_selector(rule.selector)
                    if element:
                        results[rule.name] = await self._extract_value(element, rule)
                    else:
                        results[rule.name] = None
            except Exception as e:
                logger.warning(f"Extraction failed for rule {rule.name}: {e}")
                results[rule.name] = None
        
        return results
    
    async def _extract_value(self, element, rule: ExtractionRule) -> Optional[str]:
        """Extract value from element based on rule type."""
        if rule.extract_type == "text":
            value = await element.inner_text()
        elif rule.extract_type == "html":
            value = await element.inner_html()
        elif rule.extract_type == "attribute" and rule.attribute_name:
            value = await element.get_attribute(rule.attribute_name)
        elif rule.extract_type == "count":
            # Count children matching selector
            return str(len(await element.query_selector_all("*")))
        else:
            value = await element.inner_text()
        
        # Apply transform
        if value and rule.transform:
            value = self._apply_transform(value, rule.transform)
        
        return value
    
    def _apply_transform(self, value: str, transform: str) -> str:
        """Apply a transformation to extracted value."""
        import re
        
        if transform == "trim":
            return value.strip()
        elif transform == "lowercase":
            return value.lower()
        elif transform == "uppercase":
            return value.upper()
        elif transform.startswith("regex:"):
            pattern = transform[6:]
            match = re.search(pattern, value)
            return match.group(1) if match else value
        elif transform.startswith("replace:"):
            parts = transform[8:].split("->")
            if len(parts) == 2:
                return value.replace(parts[0], parts[1])
        
        return value
    
    async def highlight_elements(self, selector: str, color: str = "red"):
        """Highlight elements matching selector on the page."""
        if not self.page:
            return
        
        await self.page.evaluate(f"""
            () => {{
                document.querySelectorAll('.visual-scraper-highlight').forEach(
                    el => el.classList.remove('visual-scraper-highlight')
                );
                
                const style = document.createElement('style');
                style.textContent = `
                    .visual-scraper-highlight {{
                        outline: 3px solid {color} !important;
                        background-color: rgba(255, 0, 0, 0.1) !important;
                    }}
                `;
                document.head.appendChild(style);
                
                document.querySelectorAll('{selector}').forEach(
                    el => el.classList.add('visual-scraper-highlight')
                );
            }}
        """)
    
    async def take_screenshot(self, full_page: bool = False) -> bytes:
        """Take a screenshot of the current page."""
        if not self.page:
            raise ValueError("No active page")
        
        return await self.page.screenshot(full_page=full_page)
    
    def create_recipe(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        pagination: Optional[Dict[str, Any]] = None
    ) -> ScrapingRecipe:
        """Create a scraping recipe from rules."""
        extraction_rules = [
            ExtractionRule(
                id=str(uuid4()),
                name=rule.get("name", f"field_{i}"),
                selector=rule.get("selector", ""),
                extract_type=rule.get("extract_type", "text"),
                attribute_name=rule.get("attribute_name"),
                multiple=rule.get("multiple", False),
                transform=rule.get("transform")
            )
            for i, rule in enumerate(rules)
        ]
        
        return ScrapingRecipe(
            id=str(uuid4()),
            name=name,
            base_url=self._current_url or "",
            rules=extraction_rules,
            pagination=pagination
        )
    
    def recipe_to_json(self, recipe: ScrapingRecipe) -> str:
        """Convert recipe to JSON string."""
        return json.dumps({
            "id": recipe.id,
            "name": recipe.name,
            "base_url": recipe.base_url,
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "selector": r.selector,
                    "extract_type": r.extract_type,
                    "attribute_name": r.attribute_name,
                    "multiple": r.multiple,
                    "transform": r.transform
                }
                for r in recipe.rules
            ],
            "pagination": recipe.pagination,
            "wait_for": recipe.wait_for,
            "scroll_to_bottom": recipe.scroll_to_bottom
        }, indent=2)
    
    @staticmethod
    def recipe_from_json(json_str: str) -> ScrapingRecipe:
        """Load recipe from JSON string."""
        data = json.loads(json_str)
        
        rules = [
            ExtractionRule(
                id=r.get("id", str(uuid4())),
                name=r.get("name", ""),
                selector=r.get("selector", ""),
                extract_type=r.get("extract_type", "text"),
                attribute_name=r.get("attribute_name"),
                multiple=r.get("multiple", False),
                transform=r.get("transform")
            )
            for r in data.get("rules", [])
        ]
        
        return ScrapingRecipe(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            base_url=data.get("base_url", ""),
            rules=rules,
            pagination=data.get("pagination"),
            wait_for=data.get("wait_for"),
            scroll_to_bottom=data.get("scroll_to_bottom", False)
        )


# API endpoints for visual scraper
class VisualScraperService:
    """Service for visual scraper API endpoints."""
    
    def __init__(self):
        self._sessions: Dict[str, VisualScraperAPI] = {}
    
    async def create_session(self, session_id: str) -> str:
        """Create a new visual scraper session."""
        api = VisualScraperAPI()
        await api.start_session(headless=True)
        self._sessions[session_id] = api
        return session_id
    
    async def end_session(self, session_id: str):
        """End a visual scraper session."""
        if session_id in self._sessions:
            await self._sessions[session_id].end_session()
            del self._sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[VisualScraperAPI]:
        """Get an existing session."""
        return self._sessions.get(session_id)
    
    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate to URL in session."""
        api = self.get_session(session_id)
        if not api:
            raise ValueError(f"Session not found: {session_id}")
        return await api.navigate(url)
    
    async def get_element(self, session_id: str, x: int, y: int) -> ElementInfo:
        """Get element at point."""
        api = self.get_session(session_id)
        if not api:
            raise ValueError(f"Session not found: {session_id}")
        return await api.get_element_at_point(x, y)
    
    async def test_selector(self, session_id: str, selector: str) -> Dict[str, Any]:
        """Test selector in session."""
        api = self.get_session(session_id)
        if not api:
            raise ValueError(f"Session not found: {session_id}")
        return await api.test_selector(selector)


# Global service instance
visual_scraper_service = VisualScraperService()

