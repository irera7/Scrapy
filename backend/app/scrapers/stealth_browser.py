"""Stealth browser wrapper with advanced anti-detection."""
import asyncio
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
from datetime import datetime
import random
import structlog

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Response,
)

from app.scrapers.anti_detection import anti_detection, BrowserProfile
from app.scrapers.captcha_solver import captcha_manager, CaptchaType
from app.scrapers.proxy_manager import ProxyManager, ProxyInfo

logger = structlog.get_logger()


class StealthPage:
    """A stealth-enabled page wrapper."""
    
    def __init__(
        self,
        page: Page,
        profile: BrowserProfile,
        captcha_enabled: bool = False
    ):
        self.page = page
        self.profile = profile
        self.captcha_enabled = captcha_enabled
        self._intercepted_responses: List[Dict[str, Any]] = []
    
    async def goto(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: int = 30000,
        referer: Optional[str] = None,
        handle_captcha: bool = True
    ) -> Optional[Response]:
        """Navigate to URL with anti-detection measures."""
        
        # Add human-like delay before navigation
        await anti_detection.human_delay(0.5, 2.0)
        
        # Set extra headers
        headers = anti_detection.get_request_headers(self.profile, referer)
        await self.page.set_extra_http_headers({
            k: v for k, v in headers.items()
            if k.lower() not in ['user-agent', 'accept-encoding']
        })
        
        try:
            response = await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            
            # Check for CAPTCHA and handle if enabled
            if handle_captcha and self.captcha_enabled:
                await self._handle_captcha_if_present(url)
            
            return response
        
        except Exception as e:
            logger.error(f"Navigation failed: {url}, error: {e}")
            raise
    
    async def _handle_captcha_if_present(self, url: str):
        """Detect and solve CAPTCHA if present."""
        content = await self.page.content()
        
        captcha_info = await captcha_manager.detect_captcha(content, url)
        
        if captcha_info:
            logger.info(f"CAPTCHA detected: {captcha_info['type']}")
            
            token = await captcha_manager.solve(
                captcha_info["type"],
                **captcha_info
            )
            
            if token:
                # Inject token based on CAPTCHA type
                if captcha_info["type"] in [CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3]:
                    await self.page.evaluate(f"""
                        document.querySelector('[name="g-recaptcha-response"]').value = '{token}';
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {{
                            // Try to trigger callback
                            const callback = document.querySelector('[data-callback]')?.getAttribute('data-callback');
                            if (callback && window[callback]) {{
                                window[callback]('{token}');
                            }}
                        }}
                    """)
                
                elif captcha_info["type"] == CaptchaType.HCAPTCHA:
                    await self.page.evaluate(f"""
                        document.querySelector('[name="h-captcha-response"]').value = '{token}';
                        document.querySelector('[name="g-recaptcha-response"]').value = '{token}';
                    """)
                
                elif captcha_info["type"] == CaptchaType.TURNSTILE:
                    await self.page.evaluate(f"""
                        document.querySelector('[name="cf-turnstile-response"]').value = '{token}';
                    """)
                
                # Submit form or trigger verification
                await self.page.click('button[type="submit"], input[type="submit"]', timeout=5000)
                await self.page.wait_for_load_state("networkidle")
                
                logger.info("CAPTCHA solved successfully")
            else:
                logger.warning("CAPTCHA solving failed")
    
    async def wait_for_selector(
        self,
        selector: str,
        timeout: int = 10000,
        state: str = "visible"
    ):
        """Wait for selector with random delay."""
        await anti_detection.human_delay(0.2, 0.5)
        return await self.page.wait_for_selector(selector, timeout=timeout, state=state)
    
    async def click(
        self,
        selector: str,
        timeout: int = 5000,
        human_like: bool = True
    ):
        """Click with human-like behavior."""
        element = await self.page.wait_for_selector(selector, timeout=timeout)
        
        if human_like and element:
            # Get element position
            box = await element.bounding_box()
            if box:
                # Move mouse to element area with some randomness
                target_x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
                target_y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
                
                # Simulate mouse movement
                await self.page.mouse.move(target_x, target_y, steps=random.randint(5, 10))
                
                # Small delay before click
                await anti_detection.human_delay(0.1, 0.3)
                
                # Click with slight position randomness
                await self.page.mouse.click(target_x, target_y)
        else:
            await self.page.click(selector, timeout=timeout)
        
        await anti_detection.human_delay(0.3, 0.8)
    
    async def type(
        self,
        selector: str,
        text: str,
        delay: Optional[int] = None,
        clear_first: bool = True
    ):
        """Type with human-like delays."""
        element = await self.page.wait_for_selector(selector, timeout=5000)
        
        if clear_first:
            await element.click(click_count=3)  # Select all
            await self.page.keyboard.press("Backspace")
        
        # Human-like typing with variable delays
        for char in text:
            await self.page.keyboard.type(char)
            if delay:
                await asyncio.sleep(delay / 1000)
            else:
                # Random delay between keystrokes
                await asyncio.sleep(random.uniform(0.05, 0.15))
        
        await anti_detection.human_delay(0.2, 0.5)
    
    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        smooth: bool = True
    ):
        """Scroll with human-like behavior."""
        if smooth:
            # Smooth scroll in steps
            step_size = random.randint(50, 100)
            steps = amount // step_size
            
            for _ in range(steps):
                delta = step_size if direction == "down" else -step_size
                await self.page.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.05, 0.1))
        else:
            delta = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, delta)
        
        await anti_detection.human_delay(0.3, 0.8)
    
    async def scroll_to_bottom(self, max_scrolls: int = 10, wait_time: float = 1.0):
        """Scroll to bottom of page (for infinite scroll)."""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        
        for i in range(max_scrolls):
            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(wait_time)
            
            # Add some random intermediate scrolls
            if random.random() > 0.7:
                await self.scroll("up", random.randint(100, 300))
                await asyncio.sleep(0.5)
                await self.scroll("down", random.randint(200, 400))
            
            # Check if we've reached the bottom
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
            logger.info(f"Scroll {i+1}/{max_scrolls}, height: {new_height}")
    
    async def extract_text(self, selector: Optional[str] = None) -> str:
        """Extract text content."""
        if selector:
            elements = await self.page.query_selector_all(selector)
            texts = []
            for el in elements:
                text = await el.inner_text()
                texts.append(text.strip())
            return "\n".join(texts)
        else:
            return await self.page.inner_text("body")
    
    async def extract_html(self, selector: Optional[str] = None) -> str:
        """Extract HTML content."""
        if selector:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_html()
            return ""
        return await self.page.content()
    
    async def extract_links(self, selector: str = "a") -> List[Dict[str, str]]:
        """Extract all links."""
        links = []
        elements = await self.page.query_selector_all(selector)
        
        for el in elements:
            href = await el.get_attribute("href")
            text = await el.inner_text()
            if href:
                links.append({
                    "url": href,
                    "text": text.strip() if text else ""
                })
        
        return links
    
    async def extract_images(self, selector: str = "img") -> List[Dict[str, str]]:
        """Extract all images."""
        images = []
        elements = await self.page.query_selector_all(selector)
        
        for el in elements:
            src = await el.get_attribute("src")
            alt = await el.get_attribute("alt")
            if src:
                images.append({
                    "url": src,
                    "alt": alt or ""
                })
        
        return images
    
    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> bytes:
        """Take a screenshot."""
        return await self.page.screenshot(path=path, full_page=full_page)
    
    async def pdf(self, path: Optional[str] = None) -> bytes:
        """Generate PDF."""
        return await self.page.pdf(path=path)
    
    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression."""
        return await self.page.evaluate(expression)
    
    async def intercept_responses(
        self,
        url_pattern: str,
        callback: Optional[Callable] = None
    ):
        """Intercept network responses matching pattern."""
        async def handler(response: Response):
            if url_pattern in response.url:
                data = {
                    "url": response.url,
                    "status": response.status,
                    "headers": response.headers,
                }
                try:
                    data["body"] = await response.text()
                except:
                    pass
                
                self._intercepted_responses.append(data)
                
                if callback:
                    await callback(data)
        
        self.page.on("response", handler)
    
    def get_intercepted_responses(self) -> List[Dict[str, Any]]:
        """Get intercepted responses."""
        return self._intercepted_responses
    
    async def close(self):
        """Close the page."""
        await self.page.close()


class StealthBrowser:
    """Stealth browser manager with anti-detection features."""
    
    def __init__(
        self,
        proxy_manager: Optional[ProxyManager] = None,
        captcha_enabled: bool = False
    ):
        self.proxy_manager = proxy_manager
        self.captcha_enabled = captcha_enabled
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: List[BrowserContext] = []
    
    async def start(self, browser_type: str = "chromium", headless: bool = True):
        """Start the browser."""
        self._playwright = await async_playwright().start()
        
        launch_options = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-browser-side-navigation",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
            ]
        }
        
        if browser_type == "chromium":
            self._browser = await self._playwright.chromium.launch(**launch_options)
        elif browser_type == "firefox":
            self._browser = await self._playwright.firefox.launch(**launch_options)
        elif browser_type == "webkit":
            self._browser = await self._playwright.webkit.launch(**launch_options)
        else:
            raise ValueError(f"Unknown browser type: {browser_type}")
        
        logger.info(f"Started {browser_type} browser (headless={headless})")
    
    async def stop(self):
        """Stop the browser."""
        for context in self._contexts:
            try:
                await context.close()
            except:
                pass
        
        if self._browser:
            await self._browser.close()
        
        if self._playwright:
            await self._playwright.stop()
        
        logger.info("Browser stopped")
    
    async def new_page(
        self,
        profile: Optional[BrowserProfile] = None,
        proxy: Optional[ProxyInfo] = None
    ) -> StealthPage:
        """Create a new stealth page."""
        if not self._browser:
            await self.start()
        
        # Generate profile if not provided
        if not profile:
            profile = anti_detection.generate_profile()
        
        # Get context options
        context_options = anti_detection.get_playwright_context_options(profile)
        
        # Add proxy if provided
        if proxy:
            from app.scrapers.proxy_manager import proxy_manager as pm
            context_options["proxy"] = pm.get_playwright_proxy_dict(proxy)
        elif self.proxy_manager:
            proxy = await self.proxy_manager.get_proxy("round_robin")
            if proxy:
                from app.scrapers.proxy_manager import proxy_manager as pm
                context_options["proxy"] = pm.get_playwright_proxy_dict(proxy)
        
        # Create context
        context = await self._browser.new_context(**context_options)
        self._contexts.append(context)
        
        # Create page
        page = await context.new_page()
        
        # Inject stealth scripts
        await page.add_init_script(anti_detection.get_stealth_scripts(profile))
        
        # Remove webdriver property
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info(f"Created stealth page with profile: {profile.platform}")
        
        return StealthPage(page, profile, self.captcha_enabled)
    
    @asynccontextmanager
    async def page(
        self,
        profile: Optional[BrowserProfile] = None,
        proxy: Optional[ProxyInfo] = None
    ):
        """Context manager for stealth page."""
        page = await self.new_page(profile, proxy)
        try:
            yield page
        finally:
            await page.close()


class SmartWaiter:
    """Smart waiting strategies for dynamic content."""
    
    @staticmethod
    async def wait_for_content_stable(
        page: StealthPage,
        selector: str,
        timeout: int = 10000,
        stability_time: float = 0.5
    ):
        """Wait for content to stop changing."""
        start_time = datetime.now()
        last_content = ""
        stable_since = None
        
        while (datetime.now() - start_time).total_seconds() * 1000 < timeout:
            try:
                element = await page.page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    
                    if content == last_content:
                        if stable_since is None:
                            stable_since = datetime.now()
                        elif (datetime.now() - stable_since).total_seconds() >= stability_time:
                            return True
                    else:
                        last_content = content
                        stable_since = None
            except:
                pass
            
            await asyncio.sleep(0.1)
        
        return False
    
    @staticmethod
    async def wait_for_lazy_load(
        page: StealthPage,
        selector: str,
        expected_count: int,
        timeout: int = 30000
    ):
        """Wait for lazy-loaded elements."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() * 1000 < timeout:
            elements = await page.page.query_selector_all(selector)
            if len(elements) >= expected_count:
                return True
            
            # Scroll to trigger lazy loading
            await page.scroll("down", 500)
            await asyncio.sleep(0.5)
        
        return False
    
    @staticmethod
    async def wait_for_ajax(
        page: StealthPage,
        timeout: int = 10000
    ):
        """Wait for all AJAX requests to complete."""
        await page.page.wait_for_load_state("networkidle", timeout=timeout)
    
    @staticmethod
    async def wait_for_spa_navigation(
        page: StealthPage,
        url_pattern: str,
        timeout: int = 10000
    ):
        """Wait for SPA navigation to complete."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() * 1000 < timeout:
            current_url = page.page.url
            if url_pattern in current_url:
                await page.page.wait_for_load_state("networkidle")
                return True
            
            await asyncio.sleep(0.1)
        
        return False


# Global instance
stealth_browser = StealthBrowser()

