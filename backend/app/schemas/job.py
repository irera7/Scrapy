from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class JobProvider(str, Enum):
    SERPAPI = "serpapi"
    APIFY = "apify"
    CUSTOM = "custom"
    TWITTER = "twitter"
    REDDIT = "reddit"
    BROWSERLESS = "browserless"
    YOUTUBE = "youtube"
    GITHUB = "github"
    NEWSAPI = "newsapi"
    GOOGLE_NEWS = "google_news"
    HACKERNEWS = "hackernews"
    ARXIV = "arxiv"
    WIKIPEDIA = "wikipedia"
    SITEMAP = "sitemap"
    RSS = "rss"
    WEBCRAWLER = "webcrawler"
    IMAGE_SCRAPER = "image_scraper"
    AUDIO_SCRAPER = "audio_scraper"
    VIDEO_SCRAPER = "video_scraper"


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    """Schema for creating a scraping job."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    provider: JobProvider
    config: Dict[str, Any]
    schedule: Optional[str] = None  # cron expression
    priority: Optional[int] = 0
    max_retries: Optional[int] = 3


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    priority: Optional[int] = None
    max_retries: Optional[int] = None
    status: Optional[JobStatus] = None


class JobResponse(BaseModel):
    """Schema for job response."""
    id: UUID
    project_id: UUID
    name: str
    provider: str
    config: Dict[str, Any]
    schedule: Optional[str]
    status: str
    priority: int
    retry_count: int
    max_retries: int
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Stats
    items_collected: Optional[int] = 0
    
    class Config:
        from_attributes = True


class JobLogResponse(BaseModel):
    """Schema for job log response."""
    id: UUID
    job_id: UUID
    level: str
    message: str
    details: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobRunRequest(BaseModel):
    """Schema for running a job manually."""
    force: bool = False  # Force run even if recently ran


# Provider-specific config schemas
class SerpAPIConfig(BaseModel):
    """Config for SerpAPI scraping."""
    query: str
    engine: str = "google"  # google, bing, youtube, etc.
    num_results: int = 10
    search_type: Optional[str] = None  # images, news, videos


class ApifyConfig(BaseModel):
    """Config for Apify actor."""
    actor_id: str
    input: Dict[str, Any] = {}


class CustomScraperConfig(BaseModel):
    """Config for custom scraping."""
    urls: List[str]
    selector: Optional[str] = None
    wait_for: Optional[str] = None
    extract_type: str = "text"  # text, html, images, links


class TwitterConfig(BaseModel):
    """Config for Twitter scraping."""
    query: str
    max_tweets: int = 100
    include_replies: bool = False


class RedditConfig(BaseModel):
    """Config for Reddit scraping."""
    subreddit: str
    sort: str = "hot"  # hot, new, top, rising
    limit: int = 100
    time_filter: str = "all"  # hour, day, week, month, year, all


class BrowserlessConfig(BaseModel):
    """Config for Browserless scraping."""
    urls: List[str]
    selector: Optional[str] = None
    wait_for: Optional[str] = None
    extract_type: str = "text"  # text, html, links, images, screenshot
    take_screenshot: bool = False
    extract_pdf: bool = False
    full_page: bool = True
    viewport: Optional[Dict[str, int]] = None  # {"width": 1920, "height": 1080}
    download_media: bool = False


class ProxyConfig(BaseModel):
    """Proxy configuration."""
    url: str
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None


class AdvancedScraperConfig(BaseModel):
    """Advanced scraping options."""
    use_proxy: bool = False
    proxy_strategy: str = "round_robin"  # round_robin, random, best_performance
    proxies: Optional[List[ProxyConfig]] = None
    download_media: bool = False
    max_retries: int = 3
    timeout: int = 30
    user_agent: Optional[str] = None

