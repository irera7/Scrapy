"""CAPTCHA solving integration for web scraping."""
import asyncio
import base64
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum
import httpx
import structlog

logger = structlog.get_logger()


class CaptchaType(str, Enum):
    """Types of CAPTCHAs."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    IMAGE_CAPTCHA = "image"
    FUNCAPTCHA = "funcaptcha"
    TURNSTILE = "turnstile"  # Cloudflare


class CaptchaSolverBase(ABC):
    """Base class for CAPTCHA solvers."""
    
    @abstractmethod
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False
    ) -> Optional[str]:
        """Solve reCAPTCHA v2."""
        pass
    
    @abstractmethod
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.3
    ) -> Optional[str]:
        """Solve reCAPTCHA v3."""
        pass
    
    @abstractmethod
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve hCaptcha."""
        pass
    
    @abstractmethod
    async def solve_image_captcha(
        self,
        image_data: bytes,
        case_sensitive: bool = False
    ) -> Optional[str]:
        """Solve image-based CAPTCHA."""
        pass
    
    @abstractmethod
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve Cloudflare Turnstile."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """Get account balance."""
        pass


class TwoCaptchaSolver(CaptchaSolverBase):
    """2Captcha service integration."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://2captcha.com"
        self.timeout = 120  # seconds
        self.polling_interval = 5  # seconds
    
    async def _submit_task(self, params: Dict[str, Any]) -> Optional[str]:
        """Submit a CAPTCHA task and get task ID."""
        params["key"] = self.api_key
        params["json"] = 1
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/in.php",
                data=params,
                timeout=30
            )
            
            result = response.json()
            if result.get("status") == 1:
                return result.get("request")
            else:
                logger.error(f"2Captcha submit failed: {result}")
                return None
    
    async def _get_result(self, task_id: str) -> Optional[str]:
        """Poll for CAPTCHA result."""
        params = {
            "key": self.api_key,
            "action": "get",
            "id": task_id,
            "json": 1
        }
        
        elapsed = 0
        
        async with httpx.AsyncClient() as client:
            while elapsed < self.timeout:
                await asyncio.sleep(self.polling_interval)
                elapsed += self.polling_interval
                
                response = await client.get(
                    f"{self.base_url}/res.php",
                    params=params,
                    timeout=30
                )
                
                result = response.json()
                
                if result.get("status") == 1:
                    return result.get("request")
                elif result.get("request") == "CAPCHA_NOT_READY":
                    continue
                else:
                    logger.error(f"2Captcha result failed: {result}")
                    return None
        
        logger.error("2Captcha timeout")
        return None
    
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False
    ) -> Optional[str]:
        """Solve reCAPTCHA v2."""
        params = {
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
        }
        
        if invisible:
            params["invisible"] = 1
        
        task_id = await self._submit_task(params)
        if not task_id:
            return None
        
        logger.info(f"2Captcha task submitted: {task_id}")
        return await self._get_result(task_id)
    
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.3
    ) -> Optional[str]:
        """Solve reCAPTCHA v3."""
        params = {
            "method": "userrecaptcha",
            "version": "v3",
            "googlekey": site_key,
            "pageurl": page_url,
            "action": action,
            "min_score": min_score
        }
        
        task_id = await self._submit_task(params)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve hCaptcha."""
        params = {
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl": page_url
        }
        
        task_id = await self._submit_task(params)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_image_captcha(
        self,
        image_data: bytes,
        case_sensitive: bool = False
    ) -> Optional[str]:
        """Solve image-based CAPTCHA."""
        params = {
            "method": "base64",
            "body": base64.b64encode(image_data).decode(),
        }
        
        if case_sensitive:
            params["regsense"] = 1
        
        task_id = await self._submit_task(params)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve Cloudflare Turnstile."""
        params = {
            "method": "turnstile",
            "sitekey": site_key,
            "pageurl": page_url
        }
        
        task_id = await self._submit_task(params)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def get_balance(self) -> float:
        """Get account balance."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/res.php",
                params={
                    "key": self.api_key,
                    "action": "getbalance",
                    "json": 1
                },
                timeout=30
            )
            
            result = response.json()
            if result.get("status") == 1:
                return float(result.get("request", 0))
            return 0.0


class AntiCaptchaSolver(CaptchaSolverBase):
    """Anti-Captcha service integration."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anti-captcha.com"
        self.timeout = 120
        self.polling_interval = 5
    
    async def _create_task(self, task: Dict[str, Any]) -> Optional[int]:
        """Create a task and get task ID."""
        payload = {
            "clientKey": self.api_key,
            "task": task
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/createTask",
                json=payload,
                timeout=30
            )
            
            result = response.json()
            if result.get("errorId") == 0:
                return result.get("taskId")
            else:
                logger.error(f"Anti-Captcha create failed: {result}")
                return None
    
    async def _get_result(self, task_id: int) -> Optional[str]:
        """Poll for task result."""
        payload = {
            "clientKey": self.api_key,
            "taskId": task_id
        }
        
        elapsed = 0
        
        async with httpx.AsyncClient() as client:
            while elapsed < self.timeout:
                await asyncio.sleep(self.polling_interval)
                elapsed += self.polling_interval
                
                response = await client.post(
                    f"{self.base_url}/getTaskResult",
                    json=payload,
                    timeout=30
                )
                
                result = response.json()
                
                if result.get("status") == "ready":
                    solution = result.get("solution", {})
                    return solution.get("gRecaptchaResponse") or solution.get("token") or solution.get("text")
                elif result.get("status") == "processing":
                    continue
                else:
                    logger.error(f"Anti-Captcha result failed: {result}")
                    return None
        
        return None
    
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False
    ) -> Optional[str]:
        """Solve reCAPTCHA v2."""
        task = {
            "type": "RecaptchaV2TaskProxyless" if not invisible else "RecaptchaV2TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
            "isInvisible": invisible
        }
        
        task_id = await self._create_task(task)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.3
    ) -> Optional[str]:
        """Solve reCAPTCHA v3."""
        task = {
            "type": "RecaptchaV3TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
            "pageAction": action,
            "minScore": min_score
        }
        
        task_id = await self._create_task(task)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve hCaptcha."""
        task = {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key
        }
        
        task_id = await self._create_task(task)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_image_captcha(
        self,
        image_data: bytes,
        case_sensitive: bool = False
    ) -> Optional[str]:
        """Solve image-based CAPTCHA."""
        task = {
            "type": "ImageToTextTask",
            "body": base64.b64encode(image_data).decode(),
            "case": case_sensitive
        }
        
        task_id = await self._create_task(task)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Solve Cloudflare Turnstile."""
        task = {
            "type": "TurnstileTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key
        }
        
        task_id = await self._create_task(task)
        if not task_id:
            return None
        
        return await self._get_result(task_id)
    
    async def get_balance(self) -> float:
        """Get account balance."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/getBalance",
                json={"clientKey": self.api_key},
                timeout=30
            )
            
            result = response.json()
            if result.get("errorId") == 0:
                return float(result.get("balance", 0))
            return 0.0


class CaptchaManager:
    """Manager for CAPTCHA solving with multiple providers."""
    
    def __init__(self):
        self.solvers: Dict[str, CaptchaSolverBase] = {}
        self.primary_solver: Optional[str] = None
    
    def add_solver(self, name: str, solver: CaptchaSolverBase, primary: bool = False):
        """Add a CAPTCHA solver."""
        self.solvers[name] = solver
        if primary or not self.primary_solver:
            self.primary_solver = name
    
    def get_solver(self, name: Optional[str] = None) -> Optional[CaptchaSolverBase]:
        """Get a solver by name or primary solver."""
        if name:
            return self.solvers.get(name)
        if self.primary_solver:
            return self.solvers.get(self.primary_solver)
        return None
    
    async def solve(
        self,
        captcha_type: CaptchaType,
        **kwargs
    ) -> Optional[str]:
        """Solve a CAPTCHA using the best available solver."""
        solver = self.get_solver()
        if not solver:
            logger.error("No CAPTCHA solver configured")
            return None
        
        try:
            if captcha_type == CaptchaType.RECAPTCHA_V2:
                return await solver.solve_recaptcha_v2(
                    kwargs["site_key"],
                    kwargs["page_url"],
                    kwargs.get("invisible", False)
                )
            elif captcha_type == CaptchaType.RECAPTCHA_V3:
                return await solver.solve_recaptcha_v3(
                    kwargs["site_key"],
                    kwargs["page_url"],
                    kwargs.get("action", "verify"),
                    kwargs.get("min_score", 0.3)
                )
            elif captcha_type == CaptchaType.HCAPTCHA:
                return await solver.solve_hcaptcha(
                    kwargs["site_key"],
                    kwargs["page_url"]
                )
            elif captcha_type == CaptchaType.IMAGE_CAPTCHA:
                return await solver.solve_image_captcha(
                    kwargs["image_data"],
                    kwargs.get("case_sensitive", False)
                )
            elif captcha_type == CaptchaType.TURNSTILE:
                return await solver.solve_turnstile(
                    kwargs["site_key"],
                    kwargs["page_url"]
                )
            else:
                logger.error(f"Unknown CAPTCHA type: {captcha_type}")
                return None
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return None
    
    async def detect_captcha(self, page_content: str, page_url: str) -> Optional[Dict[str, Any]]:
        """Detect CAPTCHA type from page content."""
        content_lower = page_content.lower()
        
        # Check for reCAPTCHA
        if "g-recaptcha" in content_lower or "grecaptcha" in content_lower:
            # Try to extract site key
            import re
            
            # v2 detection
            v2_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
            if v2_match:
                return {
                    "type": CaptchaType.RECAPTCHA_V2,
                    "site_key": v2_match.group(1),
                    "page_url": page_url,
                    "invisible": "invisible" in content_lower
                }
            
            # v3 detection
            v3_match = re.search(r'grecaptcha\.execute\(["\']([^"\']+)["\']', page_content)
            if v3_match:
                return {
                    "type": CaptchaType.RECAPTCHA_V3,
                    "site_key": v3_match.group(1),
                    "page_url": page_url
                }
        
        # Check for hCaptcha
        if "h-captcha" in content_lower or "hcaptcha" in content_lower:
            import re
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
            if match:
                return {
                    "type": CaptchaType.HCAPTCHA,
                    "site_key": match.group(1),
                    "page_url": page_url
                }
        
        # Check for Cloudflare Turnstile
        if "cf-turnstile" in content_lower or "challenges.cloudflare.com/turnstile" in content_lower:
            import re
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_content)
            if match:
                return {
                    "type": CaptchaType.TURNSTILE,
                    "site_key": match.group(1),
                    "page_url": page_url
                }
        
        # Check for Cloudflare challenge
        if "checking your browser" in content_lower or "_cf_chl" in content_lower:
            return {
                "type": CaptchaType.TURNSTILE,
                "cloudflare_challenge": True,
                "page_url": page_url
            }
        
        return None


# Global instance
captcha_manager = CaptchaManager()

