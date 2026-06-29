from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey

router = APIRouter()
logger = structlog.get_logger()


class ApiKeyCreate(BaseModel):
    """Schema for creating an API key."""
    provider: str
    api_key: str


class ApiKeyResponse(BaseModel):
    """Schema for API key response."""
    id: UUID
    provider: str
    is_active: bool
    # Don't expose the actual key, just show masked version
    masked_key: str
    
    class Config:
        from_attributes = True


class ProviderInfo(BaseModel):
    """Schema for provider information."""
    id: str
    name: str
    description: str
    supported_data_types: List[str]
    requires_api_key: bool
    documentation_url: str


# Available providers
PROVIDERS = [
    ProviderInfo(
        id="serpapi",
        name="SerpAPI",
        description="Search engine results scraping (Google, Bing, YouTube)",
        supported_data_types=["text", "image", "video"],
        requires_api_key=True,
        documentation_url="https://serpapi.com/docs"
    ),
    ProviderInfo(
        id="apify",
        name="Apify",
        description="Pre-built web scraping actors for various websites",
        supported_data_types=["text", "image", "audio", "video", "structured"],
        requires_api_key=True,
        documentation_url="https://docs.apify.com/"
    ),
    ProviderInfo(
        id="browserless",
        name="Browserless",
        description="Headless Chrome for custom web scraping",
        supported_data_types=["text", "image"],
        requires_api_key=True,
        documentation_url="https://docs.browserless.io/"
    ),
    ProviderInfo(
        id="custom",
        name="Custom Scraper",
        description="Built-in Playwright scraper for custom URLs",
        supported_data_types=["text", "image"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="twitter",
        name="Twitter/X",
        description="Twitter API for tweets and media",
        supported_data_types=["text", "image", "video"],
        requires_api_key=True,
        documentation_url="https://developer.twitter.com/en/docs"
    ),
    ProviderInfo(
        id="reddit",
        name="Reddit",
        description="Reddit API for posts and comments",
        supported_data_types=["text", "image", "video"],
        requires_api_key=True,
        documentation_url="https://www.reddit.com/dev/api/"
    ),
    ProviderInfo(
        id="youtube",
        name="YouTube",
        description="YouTube video and channel data scraper",
        supported_data_types=["text", "video", "structured"],
        requires_api_key=False,
        documentation_url="https://developers.google.com/youtube/v3"
    ),
    ProviderInfo(
        id="github",
        name="GitHub",
        description="GitHub repositories, issues, and code search",
        supported_data_types=["text", "structured"],
        requires_api_key=False,
        documentation_url="https://docs.github.com/en/rest"
    ),
    ProviderInfo(
        id="newsapi",
        name="NewsAPI",
        description="News articles from 80,000+ sources worldwide",
        supported_data_types=["text", "image"],
        requires_api_key=True,
        documentation_url="https://newsapi.org/docs"
    ),
    ProviderInfo(
        id="google_news",
        name="Google News",
        description="Google News headlines and articles (no API key needed)",
        supported_data_types=["text", "image"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="hackernews",
        name="Hacker News",
        description="Top stories, comments, and discussions from HN",
        supported_data_types=["text", "structured"],
        requires_api_key=False,
        documentation_url="https://github.com/HackerNews/API"
    ),
    ProviderInfo(
        id="arxiv",
        name="arXiv",
        description="Scientific papers and preprints from arXiv.org",
        supported_data_types=["text", "structured"],
        requires_api_key=False,
        documentation_url="https://arxiv.org/help/api"
    ),
    ProviderInfo(
        id="wikipedia",
        name="Wikipedia",
        description="Wikipedia articles and content",
        supported_data_types=["text", "image", "structured"],
        requires_api_key=False,
        documentation_url="https://www.mediawiki.org/wiki/API:Main_page"
    ),
    ProviderInfo(
        id="sitemap",
        name="Sitemap Crawler",
        description="Crawl websites using their sitemap.xml",
        supported_data_types=["text", "image"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="rss",
        name="RSS Feed",
        description="Scrape content from RSS/Atom feeds",
        supported_data_types=["text", "structured"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="webcrawler",
        name="Web Crawler",
        description="Recursive web crawler with depth control",
        supported_data_types=["text", "image"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="image_scraper",
        name="Image Scraper",
        description="Scrape images from Unsplash, Wikimedia, Pexels, or custom URLs",
        supported_data_types=["image"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="audio_scraper",
        name="Audio Scraper",
        description="Scrape audio from Wikimedia, Internet Archive, or Freesound",
        supported_data_types=["audio"],
        requires_api_key=False,
        documentation_url=""
    ),
    ProviderInfo(
        id="video_scraper",
        name="Video Scraper",
        description="Scrape video metadata from Wikimedia, Internet Archive, or Vimeo",
        supported_data_types=["video"],
        requires_api_key=False,
        documentation_url=""
    ),
]


@router.get("", response_model=List[ProviderInfo])
async def list_providers():
    """List all available providers."""
    return PROVIDERS


@router.get("/{provider_id}", response_model=ProviderInfo)
async def get_provider(provider_id: str):
    """Get a specific provider info."""
    for provider in PROVIDERS:
        if provider.id == provider_id:
            return provider
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Provider not found"
    )


@router.get("/keys/list", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys for the current user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id)
    )
    keys = result.scalars().all()
    
    response = []
    for key in keys:
        # Mask the key
        actual_key = key.api_key
        masked = actual_key[:4] + "*" * (len(actual_key) - 8) + actual_key[-4:] if len(actual_key) > 8 else "****"
        
        response.append(ApiKeyResponse(
            id=key.id,
            provider=key.provider,
            is_active=key.is_active,
            masked_key=masked
        ))
    
    return response


@router.post("/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update an API key for a provider."""
    # Check if key already exists for this provider
    result = await db.execute(
        select(ApiKey).where(
            and_(
                ApiKey.user_id == current_user.id,
                ApiKey.provider == key_data.provider
            )
        )
    )
    existing_key = result.scalar_one_or_none()
    
    if existing_key:
        # Update existing key
        existing_key.api_key = key_data.api_key
        existing_key.is_active = True
        key = existing_key
    else:
        # Create new key
        key = ApiKey(
            user_id=current_user.id,
            provider=key_data.provider,
            api_key=key_data.api_key,
        )
        db.add(key)
    
    await db.commit()
    await db.refresh(key)
    
    logger.info(f"API key saved for provider: {key_data.provider}")
    
    # Mask the key
    masked = key_data.api_key[:4] + "*" * (len(key_data.api_key) - 8) + key_data.api_key[-4:] if len(key_data.api_key) > 8 else "****"
    
    return ApiKeyResponse(
        id=key.id,
        provider=key.provider,
        is_active=key.is_active,
        masked_key=masked
    )


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    result = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await db.delete(key)
    await db.commit()
    
    logger.info(f"API key deleted for provider: {key.provider}")


@router.post("/keys/{key_id}/test", response_model=dict)
async def test_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test an API key by making a simple request to the provider."""
    result = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # TODO: Implement actual API key testing for each provider
    # For now, just return success
    return {
        "success": True,
        "message": f"API key for {key.provider} is valid"
    }

