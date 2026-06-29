"""Anti-detection and fingerprint evasion module for web scraping."""
import random
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()


# Comprehensive User-Agent list (updated 2024)
USER_AGENTS = {
    "chrome_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ],
    "chrome_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ],
    "chrome_linux": [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ],
    "firefox_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    ],
    "firefox_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:121.0) Gecko/20100101 Firefox/121.0",
    ],
    "safari_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ],
    "edge_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ],
    "mobile_android": [
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ],
    "mobile_ios": [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ],
}

# Common screen resolutions
SCREEN_RESOLUTIONS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 2560, "height": 1440},
    {"width": 3840, "height": 2160},
    {"width": 1680, "height": 1050},
]

# Mobile screen resolutions
MOBILE_RESOLUTIONS = [
    {"width": 390, "height": 844},   # iPhone 14
    {"width": 393, "height": 873},   # Pixel 7
    {"width": 412, "height": 915},   # Samsung S23
    {"width": 375, "height": 812},   # iPhone X
    {"width": 414, "height": 896},   # iPhone 11
]

# Common languages
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fa;q=0.8",
    "en-US,en;q=0.9,de;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,es;q=0.8",
]

# WebGL vendors and renderers
WEBGL_VENDORS = [
    "Google Inc. (NVIDIA)",
    "Google Inc. (Intel)",
    "Google Inc. (AMD)",
    "Intel Inc.",
    "NVIDIA Corporation",
]

WEBGL_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)",
    "Mali-G78",
    "Adreno (TM) 740",
]

# Timezone offsets (minutes from UTC)
TIMEZONE_OFFSETS = [
    -480,  # PST
    -420,  # MST
    -360,  # CST
    -300,  # EST
    0,     # UTC/GMT
    60,    # CET
    120,   # EET
    210,   # Iran
    330,   # India
    480,   # China/Singapore
    540,   # Japan/Korea
]


@dataclass
class BrowserProfile:
    """A complete browser fingerprint profile."""
    user_agent: str
    platform: str
    vendor: str
    language: str
    languages: List[str]
    screen_width: int
    screen_height: int
    color_depth: int
    pixel_ratio: float
    timezone_offset: int
    webgl_vendor: str
    webgl_renderer: str
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    do_not_track: Optional[str]
    
    # Canvas and Audio fingerprint seeds
    canvas_seed: str = field(default_factory=lambda: hashlib.md5(str(random.random()).encode()).hexdigest()[:8])
    audio_seed: str = field(default_factory=lambda: hashlib.md5(str(random.random()).encode()).hexdigest()[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_agent": self.user_agent,
            "platform": self.platform,
            "vendor": self.vendor,
            "language": self.language,
            "languages": self.languages,
            "screen": {
                "width": self.screen_width,
                "height": self.screen_height,
                "colorDepth": self.color_depth,
                "pixelRatio": self.pixel_ratio,
            },
            "timezone_offset": self.timezone_offset,
            "webgl": {
                "vendor": self.webgl_vendor,
                "renderer": self.webgl_renderer,
            },
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "max_touch_points": self.max_touch_points,
            "do_not_track": self.do_not_track,
        }


class AntiDetection:
    """Anti-detection manager for web scraping."""
    
    def __init__(self):
        self.profiles: Dict[str, BrowserProfile] = {}
        self.used_user_agents: List[str] = []
        self._request_times: Dict[str, List[datetime]] = {}
    
    def get_random_user_agent(
        self, 
        browser_type: Optional[str] = None,
        mobile: bool = False
    ) -> str:
        """Get a random user agent."""
        if mobile:
            agents = USER_AGENTS["mobile_android"] + USER_AGENTS["mobile_ios"]
        elif browser_type:
            agents = []
            for key, value in USER_AGENTS.items():
                if browser_type.lower() in key:
                    agents.extend(value)
            if not agents:
                agents = self._get_all_desktop_agents()
        else:
            agents = self._get_all_desktop_agents()
        
        # Avoid recently used agents
        available = [a for a in agents if a not in self.used_user_agents[-10:]]
        if not available:
            available = agents
        
        selected = random.choice(available)
        self.used_user_agents.append(selected)
        
        return selected
    
    def _get_all_desktop_agents(self) -> List[str]:
        """Get all desktop user agents."""
        agents = []
        for key, value in USER_AGENTS.items():
            if "mobile" not in key:
                agents.extend(value)
        return agents
    
    def generate_profile(
        self,
        profile_id: Optional[str] = None,
        mobile: bool = False,
        browser_type: Optional[str] = None
    ) -> BrowserProfile:
        """Generate a consistent browser profile."""
        
        user_agent = self.get_random_user_agent(browser_type, mobile)
        
        # Determine platform from user agent
        if "Windows" in user_agent:
            platform = "Win32"
            vendor = "Google Inc."
        elif "Macintosh" in user_agent:
            platform = "MacIntel"
            vendor = "Apple Computer, Inc."
        elif "Linux" in user_agent and not mobile:
            platform = "Linux x86_64"
            vendor = "Google Inc."
        elif "Android" in user_agent:
            platform = "Linux armv8l"
            vendor = "Google Inc."
        elif "iPhone" in user_agent:
            platform = "iPhone"
            vendor = "Apple Computer, Inc."
        else:
            platform = "Win32"
            vendor = "Google Inc."
        
        # Screen resolution
        if mobile:
            screen = random.choice(MOBILE_RESOLUTIONS)
            pixel_ratio = random.choice([2.0, 2.5, 3.0])
            max_touch_points = random.randint(5, 10)
        else:
            screen = random.choice(SCREEN_RESOLUTIONS)
            pixel_ratio = random.choice([1.0, 1.25, 1.5, 2.0])
            max_touch_points = 0
        
        # Language
        accept_lang = random.choice(ACCEPT_LANGUAGES)
        primary_lang = accept_lang.split(",")[0].split("-")[0]
        
        profile = BrowserProfile(
            user_agent=user_agent,
            platform=platform,
            vendor=vendor,
            language=primary_lang,
            languages=accept_lang.split(","),
            screen_width=screen["width"],
            screen_height=screen["height"],
            color_depth=24,
            pixel_ratio=pixel_ratio,
            timezone_offset=random.choice(TIMEZONE_OFFSETS),
            webgl_vendor=random.choice(WEBGL_VENDORS),
            webgl_renderer=random.choice(WEBGL_RENDERERS),
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            max_touch_points=max_touch_points,
            do_not_track=random.choice([None, "1"]),
        )
        
        if profile_id:
            self.profiles[profile_id] = profile
        
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get an existing profile by ID."""
        return self.profiles.get(profile_id)
    
    def get_request_headers(
        self,
        profile: Optional[BrowserProfile] = None,
        referer: Optional[str] = None,
        origin: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate realistic request headers."""
        
        if not profile:
            profile = self.generate_profile()
        
        headers = {
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": ",".join(profile.languages),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none" if not referer else "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # Add Chrome-specific headers
        if "Chrome" in profile.user_agent:
            headers["sec-ch-ua"] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            headers["sec-ch-ua-mobile"] = "?0" if profile.max_touch_points == 0 else "?1"
            headers["sec-ch-ua-platform"] = f'"{profile.platform.split()[0]}"'
        
        if referer:
            headers["Referer"] = referer
        
        if origin:
            headers["Origin"] = origin
        
        if profile.do_not_track:
            headers["DNT"] = profile.do_not_track
        
        return headers
    
    def get_playwright_context_options(
        self,
        profile: Optional[BrowserProfile] = None
    ) -> Dict[str, Any]:
        """Get Playwright browser context options."""
        
        if not profile:
            profile = self.generate_profile()
        
        return {
            "user_agent": profile.user_agent,
            "viewport": {
                "width": profile.screen_width,
                "height": profile.screen_height,
            },
            "screen": {
                "width": profile.screen_width,
                "height": profile.screen_height,
            },
            "device_scale_factor": profile.pixel_ratio,
            "locale": profile.language,
            "timezone_id": self._get_timezone_from_offset(profile.timezone_offset),
            "color_scheme": random.choice(["light", "dark"]),
            "has_touch": profile.max_touch_points > 0,
        }
    
    def _get_timezone_from_offset(self, offset: int) -> str:
        """Get timezone string from offset."""
        timezone_map = {
            -480: "America/Los_Angeles",
            -420: "America/Denver",
            -360: "America/Chicago",
            -300: "America/New_York",
            0: "Europe/London",
            60: "Europe/Paris",
            120: "Europe/Helsinki",
            210: "Asia/Tehran",
            330: "Asia/Kolkata",
            480: "Asia/Shanghai",
            540: "Asia/Tokyo",
        }
        return timezone_map.get(offset, "UTC")
    
    def get_stealth_scripts(self, profile: BrowserProfile) -> str:
        """Get JavaScript to inject for stealth mode."""
        return f"""
        // Override navigator properties
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => {profile.languages}
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{profile.platform}'
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {profile.hardware_concurrency}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {profile.device_memory}
        }});
        
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => {profile.max_touch_points}
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => {profile.screen_width}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {profile.screen_height}
        }});
        
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {profile.color_depth}
        }});
        
        // Override WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return '{profile.webgl_vendor}';
            }}
            if (parameter === 37446) {{
                return '{profile.webgl_renderer}';
            }}
            return getParameter.call(this, parameter);
        }};
        
        // WebGL2
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) {{
                    return '{profile.webgl_vendor}';
                }}
                if (parameter === 37446) {{
                    return '{profile.webgl_renderer}';
                }}
                return getParameter2.call(this, parameter);
            }};
        }}
        
        // Override Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        
        // Remove Chrome automation flags
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Override chrome object
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};
        
        // Add plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' }},
                {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }},
                {{ name: 'Native Client', filename: 'internal-nacl-plugin' }}
            ]
        }});
        
        // Console log detection prevention
        const _log = console.log;
        console.log = function() {{
            if (arguments[0] && arguments[0].includes && arguments[0].includes('devtools')) {{
                return;
            }}
            return _log.apply(console, arguments);
        }};
        """
    
    async def human_delay(
        self,
        min_seconds: float = 0.5,
        max_seconds: float = 3.0,
        typing: bool = False
    ):
        """Add human-like delay."""
        if typing:
            # Typing delays are shorter
            delay = random.uniform(0.05, 0.2)
        else:
            # Use a distribution that favors shorter delays
            delay = random.triangular(min_seconds, max_seconds, min_seconds + 0.3)
        
        await asyncio.sleep(delay)
    
    async def rate_limit(
        self,
        domain: str,
        requests_per_minute: int = 10,
        requests_per_hour: int = 200
    ):
        """Apply rate limiting per domain."""
        now = datetime.now()
        
        if domain not in self._request_times:
            self._request_times[domain] = []
        
        # Clean old entries
        minute_ago = now.timestamp() - 60
        hour_ago = now.timestamp() - 3600
        
        self._request_times[domain] = [
            t for t in self._request_times[domain]
            if t.timestamp() > hour_ago
        ]
        
        # Count recent requests
        recent_minute = sum(1 for t in self._request_times[domain] if t.timestamp() > minute_ago)
        recent_hour = len(self._request_times[domain])
        
        # Apply rate limiting
        if recent_minute >= requests_per_minute:
            wait_time = 60 - (now.timestamp() - minute_ago)
            logger.info(f"Rate limit reached for {domain}, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        if recent_hour >= requests_per_hour:
            wait_time = 3600 - (now.timestamp() - hour_ago)
            logger.info(f"Hourly limit reached for {domain}, waiting {wait_time:.1f}s")
            await asyncio.sleep(min(wait_time, 300))  # Max 5 min wait
        
        self._request_times[domain].append(now)
    
    def get_mouse_movements(self, target_x: int, target_y: int) -> List[Dict[str, int]]:
        """Generate human-like mouse movements to a target."""
        movements = []
        
        # Start from random position
        current_x = random.randint(0, 500)
        current_y = random.randint(0, 500)
        
        # Number of steps
        steps = random.randint(5, 15)
        
        for i in range(steps):
            progress = (i + 1) / steps
            
            # Add some randomness to the path
            noise_x = random.randint(-10, 10) * (1 - progress)
            noise_y = random.randint(-10, 10) * (1 - progress)
            
            # Ease-out interpolation
            eased = 1 - (1 - progress) ** 3
            
            x = int(current_x + (target_x - current_x) * eased + noise_x)
            y = int(current_y + (target_y - current_y) * eased + noise_y)
            
            movements.append({"x": x, "y": y})
        
        # Final position
        movements.append({"x": target_x, "y": target_y})
        
        return movements


# Global instance
anti_detection = AntiDetection()

