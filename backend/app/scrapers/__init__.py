"""Scraping modules for AI Data Collector."""

# Anti-detection and stealth
from app.scrapers.anti_detection import anti_detection, BrowserProfile
from app.scrapers.stealth_browser import StealthBrowser, StealthPage, SmartWaiter

# CAPTCHA handling
from app.scrapers.captcha_solver import (
    captcha_manager, 
    CaptchaType, 
    TwoCaptchaSolver, 
    AntiCaptchaSolver
)

# Proxy management
from app.scrapers.proxy_manager import proxy_manager, ProxyInfo, ProxyManager

# Smart retry
from app.scrapers.smart_retry import (
    SmartRetry, 
    RetryConfig, 
    RetryStrategy, 
    with_retry,
    CircuitBreaker
)

# Content extraction
from app.scrapers.content_extractor import (
    readability_extractor,
    structured_data_extractor,
    table_extractor,
    ExtractedContent
)

# Parallel scraping
from app.scrapers.parallel_scraper import (
    ParallelScraper, 
    ScrapingTask, 
    scrape_urls_parallel,
    BatchProcessor
)

# Visual scraping
from app.scrapers.visual_scraper import (
    VisualScraperAPI,
    visual_scraper_service,
    ScrapingRecipe,
    ExtractionRule
)

# Scheduling
from app.scrapers.scheduler import (
    advanced_scheduler,
    ScheduledJob,
    ScheduleConfig,
    ScheduleType,
    COMMON_SCHEDULES
)

# Deduplication
from app.scrapers.deduplication import (
    dedup_manager,
    DeduplicationManager,
    DeduplicationStrategy,
    ContentHasher,
    SimilarityCalculator
)

# Templates
from app.scrapers.templates import (
    template_manager,
    ScrapingTemplate,
    TemplateCategory,
    ExtractionField
)

# Sitemap and RSS
from app.scrapers.sitemap_crawler import (
    SitemapCrawler,
    RSSCrawler,
    WebCrawler,
    RobotsTxtParser
)

# Media downloading
from app.scrapers.media_downloader import media_downloader

# Execution
from app.scrapers.executor import execute_scraping_job, retry_failed_job

__all__ = [
    # Anti-detection
    "anti_detection",
    "BrowserProfile",
    "StealthBrowser",
    "StealthPage",
    "SmartWaiter",
    
    # CAPTCHA
    "captcha_manager",
    "CaptchaType",
    "TwoCaptchaSolver",
    "AntiCaptchaSolver",
    
    # Proxy
    "proxy_manager",
    "ProxyInfo",
    "ProxyManager",
    
    # Retry
    "SmartRetry",
    "RetryConfig",
    "RetryStrategy",
    "with_retry",
    "CircuitBreaker",
    
    # Content extraction
    "readability_extractor",
    "structured_data_extractor",
    "table_extractor",
    "ExtractedContent",
    
    # Parallel
    "ParallelScraper",
    "ScrapingTask",
    "scrape_urls_parallel",
    "BatchProcessor",
    
    # Visual
    "VisualScraperAPI",
    "visual_scraper_service",
    "ScrapingRecipe",
    "ExtractionRule",
    
    # Scheduling
    "advanced_scheduler",
    "ScheduledJob",
    "ScheduleConfig",
    "ScheduleType",
    "COMMON_SCHEDULES",
    
    # Deduplication
    "dedup_manager",
    "DeduplicationManager",
    "DeduplicationStrategy",
    "ContentHasher",
    "SimilarityCalculator",
    
    # Templates
    "template_manager",
    "ScrapingTemplate",
    "TemplateCategory",
    "ExtractionField",
    
    # Crawlers
    "SitemapCrawler",
    "RSSCrawler",
    "WebCrawler",
    "RobotsTxtParser",
    
    # Media
    "media_downloader",
    
    # Execution
    "execute_scraping_job",
    "retry_failed_job",
]
