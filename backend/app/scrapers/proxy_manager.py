"""Proxy rotation manager for web scraping."""
import random
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class ProxyInfo:
    """Information about a proxy."""
    url: str
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    avg_response_time: float = 0.0
    
    @property
    def full_url(self) -> str:
        """Get full proxy URL with credentials."""
        if self.username and self.password:
            # Parse URL and add auth
            protocol = self.protocol
            host_port = self.url.replace(f"{protocol}://", "")
            return f"{protocol}://{self.username}:{self.password}@{host_port}"
        return self.url
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
    
    def record_success(self, response_time: float):
        """Record a successful request."""
        self.success_count += 1
        self.last_used = datetime.now()
        # Update average response time
        total = self.success_count + self.failure_count
        self.avg_response_time = (
            (self.avg_response_time * (total - 1) + response_time) / total
        )
    
    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_used = datetime.now()
        # Deactivate if too many failures
        if self.success_rate < 0.3 and self.failure_count > 5:
            self.is_active = False


class ProxyManager:
    """Manages proxy rotation for scraping."""
    
    def __init__(self, proxies: Optional[List[Dict[str, Any]]] = None):
        self.proxies: List[ProxyInfo] = []
        self.current_index = 0
        self._lock = asyncio.Lock()
        
        if proxies:
            for proxy_config in proxies:
                self.add_proxy(proxy_config)
    
    def add_proxy(self, config: Dict[str, Any]) -> ProxyInfo:
        """Add a proxy to the pool."""
        proxy = ProxyInfo(
            url=config["url"],
            protocol=config.get("protocol", "http"),
            username=config.get("username"),
            password=config.get("password"),
            country=config.get("country"),
        )
        self.proxies.append(proxy)
        return proxy
    
    def remove_proxy(self, url: str):
        """Remove a proxy from the pool."""
        self.proxies = [p for p in self.proxies if p.url != url]
    
    @property
    def active_proxies(self) -> List[ProxyInfo]:
        """Get list of active proxies."""
        return [p for p in self.proxies if p.is_active]
    
    async def get_proxy(self, strategy: str = "round_robin") -> Optional[ProxyInfo]:
        """Get next proxy based on strategy."""
        async with self._lock:
            active = self.active_proxies
            if not active:
                return None
            
            if strategy == "round_robin":
                proxy = active[self.current_index % len(active)]
                self.current_index += 1
                return proxy
            
            elif strategy == "random":
                return random.choice(active)
            
            elif strategy == "least_used":
                # Sort by last used time, prefer ones not used recently
                sorted_proxies = sorted(
                    active,
                    key=lambda p: p.last_used or datetime.min
                )
                return sorted_proxies[0]
            
            elif strategy == "best_performance":
                # Sort by success rate and response time
                sorted_proxies = sorted(
                    active,
                    key=lambda p: (-p.success_rate, p.avg_response_time)
                )
                return sorted_proxies[0]
            
            elif strategy == "weighted_random":
                # Weighted random based on success rate
                weights = [p.success_rate for p in active]
                total_weight = sum(weights)
                if total_weight == 0:
                    return random.choice(active)
                
                r = random.uniform(0, total_weight)
                cumulative = 0
                for proxy, weight in zip(active, weights):
                    cumulative += weight
                    if r <= cumulative:
                        return proxy
                return active[-1]
            
            return active[0]
    
    async def test_proxy(self, proxy: ProxyInfo, test_url: str = "https://httpbin.org/ip") -> bool:
        """Test if a proxy is working."""
        try:
            async with httpx.AsyncClient(
                proxies={proxy.protocol: proxy.full_url},
                timeout=10.0
            ) as client:
                start = datetime.now()
                response = await client.get(test_url)
                response_time = (datetime.now() - start).total_seconds()
                
                if response.status_code == 200:
                    proxy.record_success(response_time)
                    logger.info(f"Proxy test passed: {proxy.url}")
                    return True
                else:
                    proxy.record_failure()
                    return False
        
        except Exception as e:
            proxy.record_failure()
            logger.warning(f"Proxy test failed: {proxy.url}, error: {e}")
            return False
    
    async def test_all_proxies(self, test_url: str = "https://httpbin.org/ip"):
        """Test all proxies in the pool."""
        tasks = [self.test_proxy(proxy, test_url) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working = sum(1 for r in results if r is True)
        logger.info(f"Proxy test complete: {working}/{len(self.proxies)} working")
        
        return working
    
    def get_httpx_proxy_dict(self, proxy: ProxyInfo) -> Dict[str, str]:
        """Get proxy dict for httpx client."""
        return {
            "http://": proxy.full_url,
            "https://": proxy.full_url,
        }
    
    def get_playwright_proxy_dict(self, proxy: ProxyInfo) -> Dict[str, Any]:
        """Get proxy dict for Playwright."""
        result = {
            "server": proxy.url,
        }
        if proxy.username and proxy.password:
            result["username"] = proxy.username
            result["password"] = proxy.password
        return result
    
    def reactivate_proxies(self, min_failures: int = 10, hours: int = 1):
        """Reactivate proxies that have been inactive for a while."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        for proxy in self.proxies:
            if not proxy.is_active:
                if proxy.last_used and proxy.last_used < cutoff:
                    if proxy.failure_count >= min_failures:
                        # Reset and reactivate
                        proxy.is_active = True
                        proxy.success_count = 0
                        proxy.failure_count = 0
                        logger.info(f"Reactivated proxy: {proxy.url}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy pool statistics."""
        total = len(self.proxies)
        active = len(self.active_proxies)
        
        total_success = sum(p.success_count for p in self.proxies)
        total_failure = sum(p.failure_count for p in self.proxies)
        
        return {
            "total_proxies": total,
            "active_proxies": active,
            "inactive_proxies": total - active,
            "total_requests": total_success + total_failure,
            "success_count": total_success,
            "failure_count": total_failure,
            "overall_success_rate": total_success / max(total_success + total_failure, 1),
        }


class ProxyProvider:
    """Base class for proxy providers."""
    
    async def fetch_proxies(self) -> List[Dict[str, Any]]:
        """Fetch proxies from provider."""
        raise NotImplementedError


class FreeProxyListProvider(ProxyProvider):
    """Fetch free proxies from free-proxy-list.net."""
    
    async def fetch_proxies(self) -> List[Dict[str, Any]]:
        """Fetch free proxies."""
        proxies = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.free-proxy-list.net/",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'lxml')
                
                table = soup.find('table', {'id': 'proxylisttable'})
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows[:50]:  # Limit to 50
                        cols = row.find_all('td')
                        if len(cols) >= 7:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            https = cols[6].text.strip() == 'yes'
                            
                            protocol = "https" if https else "http"
                            proxies.append({
                                "url": f"{protocol}://{ip}:{port}",
                                "protocol": protocol,
                            })
        
        except Exception as e:
            logger.error(f"Error fetching free proxies: {e}")
        
        return proxies


# Global proxy manager instance
proxy_manager = ProxyManager()

