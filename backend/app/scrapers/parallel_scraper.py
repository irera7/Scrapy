"""Parallel scraping with worker pools and domain-based rate limiting."""
import asyncio
from typing import List, Dict, Any, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse
import structlog
import httpx

from app.scrapers.anti_detection import anti_detection
from app.scrapers.smart_retry import SmartRetry, RetryConfig

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class ScrapingTask:
    """A single scraping task."""
    id: str
    url: str
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    
    @property
    def domain(self) -> str:
        """Get the domain of the URL."""
        parsed = urlparse(self.url)
        return parsed.netloc


@dataclass
class DomainConfig:
    """Configuration for a specific domain."""
    requests_per_second: float = 1.0
    max_concurrent: int = 3
    delay_between_requests: float = 1.0
    last_request_time: Optional[datetime] = None
    active_requests: int = 0


class RateLimiter:
    """Rate limiter with per-domain limits."""
    
    def __init__(self, default_rps: float = 1.0, default_delay: float = 1.0):
        self.default_rps = default_rps
        self.default_delay = default_delay
        self.domain_configs: Dict[str, DomainConfig] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    def configure_domain(
        self,
        domain: str,
        requests_per_second: Optional[float] = None,
        max_concurrent: Optional[int] = None,
        delay: Optional[float] = None
    ):
        """Configure rate limits for a specific domain."""
        if domain not in self.domain_configs:
            self.domain_configs[domain] = DomainConfig(
                requests_per_second=self.default_rps,
                delay_between_requests=self.default_delay
            )
        
        config = self.domain_configs[domain]
        
        if requests_per_second is not None:
            config.requests_per_second = requests_per_second
        if max_concurrent is not None:
            config.max_concurrent = max_concurrent
        if delay is not None:
            config.delay_between_requests = delay
    
    def _get_config(self, domain: str) -> DomainConfig:
        """Get or create config for domain."""
        if domain not in self.domain_configs:
            self.domain_configs[domain] = DomainConfig(
                requests_per_second=self.default_rps,
                delay_between_requests=self.default_delay
            )
        return self.domain_configs[domain]
    
    async def acquire(self, domain: str):
        """Acquire permission to make a request to domain."""
        async with self._locks[domain]:
            config = self._get_config(domain)
            
            # Wait if at max concurrent requests
            while config.active_requests >= config.max_concurrent:
                await asyncio.sleep(0.1)
            
            # Check time since last request
            if config.last_request_time:
                elapsed = (datetime.now() - config.last_request_time).total_seconds()
                min_interval = 1.0 / config.requests_per_second
                
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
            
            # Apply delay
            if config.delay_between_requests > 0:
                await asyncio.sleep(config.delay_between_requests)
            
            config.active_requests += 1
            config.last_request_time = datetime.now()
    
    async def release(self, domain: str):
        """Release a request slot for domain."""
        async with self._locks[domain]:
            config = self._get_config(domain)
            config.active_requests = max(0, config.active_requests - 1)


class PriorityQueue:
    """Priority queue for scraping tasks."""
    
    def __init__(self):
        self._queue: List[ScrapingTask] = []
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
    
    async def put(self, task: ScrapingTask):
        """Add task to queue."""
        async with self._lock:
            self._queue.append(task)
            self._queue.sort(key=lambda t: (-t.priority, t.created_at))
            self._not_empty.set()
    
    async def get(self) -> ScrapingTask:
        """Get highest priority task."""
        while True:
            async with self._lock:
                if self._queue:
                    return self._queue.pop(0)
                self._not_empty.clear()
            
            await self._not_empty.wait()
    
    async def put_many(self, tasks: List[ScrapingTask]):
        """Add multiple tasks to queue."""
        async with self._lock:
            self._queue.extend(tasks)
            self._queue.sort(key=lambda t: (-t.priority, t.created_at))
            self._not_empty.set()
    
    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)
    
    @property
    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0


class ParallelScraper:
    """Parallel scraper with worker pool and domain-based rate limiting."""
    
    def __init__(
        self,
        max_workers: int = 10,
        default_rps: float = 1.0,
        default_delay: float = 1.0,
        max_retries: int = 3
    ):
        self.max_workers = max_workers
        self.rate_limiter = RateLimiter(default_rps, default_delay)
        self.retry_handler = SmartRetry(RetryConfig(max_retries=max_retries))
        
        self._queue = PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._completed_tasks: List[ScrapingTask] = []
        self._failed_tasks: List[ScrapingTask] = []
        self._lock = asyncio.Lock()
        
        # Callbacks
        self._on_task_complete: Optional[Callable[[ScrapingTask], None]] = None
        self._on_task_error: Optional[Callable[[ScrapingTask, Exception], None]] = None
        self._scrape_function: Optional[Callable[[str, Dict[str, Any]], Any]] = None
    
    def set_scrape_function(self, func: Callable[[str, Dict[str, Any]], Any]):
        """Set the function to use for scraping."""
        self._scrape_function = func
    
    def on_complete(self, callback: Callable[[ScrapingTask], None]):
        """Set callback for completed tasks."""
        self._on_task_complete = callback
    
    def on_error(self, callback: Callable[[ScrapingTask, Exception], None]):
        """Set callback for failed tasks."""
        self._on_task_error = callback
    
    def configure_domain(
        self,
        domain: str,
        requests_per_second: Optional[float] = None,
        max_concurrent: Optional[int] = None,
        delay: Optional[float] = None
    ):
        """Configure rate limits for a domain."""
        self.rate_limiter.configure_domain(
            domain,
            requests_per_second,
            max_concurrent,
            delay
        )
    
    async def add_task(self, task: ScrapingTask):
        """Add a task to the queue."""
        await self._queue.put(task)
    
    async def add_tasks(self, tasks: List[ScrapingTask]):
        """Add multiple tasks to the queue."""
        await self._queue.put_many(tasks)
    
    async def add_urls(
        self,
        urls: List[str],
        config: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ):
        """Add URLs as tasks."""
        tasks = [
            ScrapingTask(
                id=f"task_{i}",
                url=url,
                config=config or {},
                priority=priority
            )
            for i, url in enumerate(urls)
        ]
        await self.add_tasks(tasks)
    
    async def start(self):
        """Start the worker pool."""
        if self._running:
            return
        
        self._running = True
        
        # Create workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker_{i}"))
            self._workers.append(worker)
        
        logger.info(f"Started {self.max_workers} workers")
    
    async def stop(self, graceful: bool = True):
        """Stop the worker pool."""
        self._running = False
        
        if graceful:
            # Wait for workers to finish current tasks
            for worker in self._workers:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
        else:
            # Cancel immediately
            for worker in self._workers:
                worker.cancel()
        
        self._workers.clear()
        logger.info("Stopped all workers")
    
    async def wait_until_complete(self, timeout: Optional[float] = None):
        """Wait until all tasks are processed."""
        start_time = datetime.now()
        
        while not self._queue.empty or any(w.done() == False for w in self._workers):
            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise TimeoutError("Scraping did not complete within timeout")
            
            await asyncio.sleep(0.5)
    
    async def _worker(self, worker_id: str):
        """Worker coroutine that processes tasks."""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Get task from queue
                task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            # Process task
            domain = task.domain
            
            try:
                # Acquire rate limit
                await self.rate_limiter.acquire(domain)
                
                task.started_at = datetime.now()
                
                # Execute scraping
                if self._scrape_function:
                    result = await self._scrape_function(task.url, task.config)
                else:
                    result = await self._default_scrape(task.url, task.config)
                
                task.result = result
                task.completed_at = datetime.now()
                
                async with self._lock:
                    self._completed_tasks.append(task)
                
                if self._on_task_complete:
                    self._on_task_complete(task)
                
                logger.debug(f"Worker {worker_id} completed task: {task.url}")
            
            except Exception as e:
                task.error = str(e)
                task.retries += 1
                
                # Retry if possible
                if task.retries < self.retry_handler.config.max_retries:
                    await self._queue.put(task)
                    logger.warning(f"Worker {worker_id} retrying task: {task.url}")
                else:
                    async with self._lock:
                        self._failed_tasks.append(task)
                    
                    if self._on_task_error:
                        self._on_task_error(task, e)
                    
                    logger.error(f"Worker {worker_id} failed task: {task.url}, error: {e}")
            
            finally:
                await self.rate_limiter.release(domain)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _default_scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Default scraping function using httpx."""
        profile = anti_detection.generate_profile()
        headers = anti_detection.get_request_headers(profile)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=config.get("timeout", 30),
                follow_redirects=True
            )
            
            response.raise_for_status()
            
            return {
                "url": str(response.url),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "content_length": len(response.content)
            }
    
    @property
    def completed_count(self) -> int:
        """Get number of completed tasks."""
        return len(self._completed_tasks)
    
    @property
    def failed_count(self) -> int:
        """Get number of failed tasks."""
        return len(self._failed_tasks)
    
    @property
    def pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._queue.size
    
    def get_results(self) -> List[ScrapingTask]:
        """Get all completed tasks."""
        return self._completed_tasks.copy()
    
    def get_failed(self) -> List[ScrapingTask]:
        """Get all failed tasks."""
        return self._failed_tasks.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "workers": len(self._workers),
            "running": self._running
        }


async def scrape_urls_parallel(
    urls: List[str],
    scrape_func: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    max_workers: int = 10,
    rate_limit: float = 1.0,
    config: Optional[Dict[str, Any]] = None,
    domain_configs: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Convenience function for parallel scraping of URLs.
    
    Args:
        urls: List of URLs to scrape
        scrape_func: Custom scraping function
        max_workers: Maximum number of concurrent workers
        rate_limit: Default requests per second per domain
        config: Config to pass to scrape function
        domain_configs: Per-domain rate limit configurations
    
    Returns:
        Dict with results, failed tasks, and stats
    """
    scraper = ParallelScraper(
        max_workers=max_workers,
        default_rps=rate_limit
    )
    
    if scrape_func:
        scraper.set_scrape_function(scrape_func)
    
    # Apply domain configs
    if domain_configs:
        for domain, conf in domain_configs.items():
            scraper.configure_domain(domain, **conf)
    
    # Add URLs
    await scraper.add_urls(urls, config)
    
    # Start and wait
    await scraper.start()
    await scraper.wait_until_complete()
    await scraper.stop()
    
    return {
        "results": scraper.get_results(),
        "failed": scraper.get_failed(),
        "stats": scraper.get_stats()
    }


class BatchProcessor:
    """Process items in batches with parallel execution."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_concurrent_batches: int = 3
    ):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
    
    async def process(
        self,
        items: List[T],
        processor: Callable[[List[T]], Any]
    ) -> List[Any]:
        """Process items in batches."""
        results = []
        
        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def process_batch(batch: List[T]) -> Any:
            async with semaphore:
                return await processor(batch)
        
        # Run all batches
        tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
            elif isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
        
        return results


# Utility functions

async def parallel_map(
    items: List[T],
    func: Callable[[T], Any],
    max_concurrent: int = 10
) -> List[Any]:
    """Apply a function to items in parallel with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process(item: T) -> Any:
        async with semaphore:
            if asyncio.iscoroutinefunction(func):
                return await func(item)
            else:
                return func(item)
    
    tasks = [process(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def parallel_filter(
    items: List[T],
    predicate: Callable[[T], bool],
    max_concurrent: int = 10
) -> List[T]:
    """Filter items in parallel."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check(item: T) -> Optional[T]:
        async with semaphore:
            if asyncio.iscoroutinefunction(predicate):
                result = await predicate(item)
            else:
                result = predicate(item)
            return item if result else None
    
    tasks = [check(item) for item in items]
    results = await asyncio.gather(*tasks)
    
    return [r for r in results if r is not None]

