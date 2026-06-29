"""Job executor for scraping tasks."""
from datetime import datetime, timezone
from uuid import UUID
import structlog
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.job import ScrapingJob, JobLog
from app.models.project import Project
from app.models.api_key import ApiKey
from app.models.data_item import DataItem
from app.scrapers.providers.serpapi_scraper import SerpAPIScraper
from app.scrapers.providers.apify_scraper import ApifyScraper
from app.scrapers.providers.custom_scraper import CustomScraper
from app.scrapers.providers.twitter_scraper import TwitterScraper
from app.scrapers.providers.reddit_scraper import RedditScraper
from app.scrapers.providers.browserless_scraper import BrowserlessScraper
from app.scrapers.providers.youtube_scraper import YouTubeScraper
from app.scrapers.providers.github_scraper import GitHubScraper
from app.scrapers.providers.news_scraper import NewsAPIScraper, GoogleNewsScraper, HackerNewsScraper, ArxivScraper, WikipediaScraper
from app.scrapers.providers.media_scraper import ImageScraper, AudioScraper, VideoScraper
from app.scrapers.sitemap_crawler import SitemapCrawler, RSSCrawler, WebCrawler
from app.scrapers.proxy_manager import proxy_manager, ProxyInfo
from app.scrapers.media_downloader import media_downloader
from app.scrapers.deduplication import dedup_manager
from app.services.scraping_ml_service import ScrapingMLIntegration, AutoLabeler, QualityFilter

logger = structlog.get_logger()


@asynccontextmanager
async def get_db_session():
    """Create a fresh database session for the current event loop.
    
    This is needed because Celery tasks run in different event loops than
    the main application. Each task needs its own engine and session.
    """
    # Create a new engine for this event loop
    engine = create_async_engine(
        settings.DATABASE_URL, 
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
    
    # Dispose the engine when done
    await engine.dispose()


async def get_api_key(db: AsyncSession, user_id: UUID, provider: str) -> str:
    """Get API key for a provider."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.provider == provider,
            ApiKey.is_active == True
        )
    )
    key = result.scalar_one_or_none()
    return key.api_key if key else None


async def add_job_log(
    db: AsyncSession,
    job_id: UUID,
    level: str,
    message: str,
    details: dict = None
):
    """Add a log entry for a job."""
    log = JobLog(
        job_id=job_id,
        level=level,
        message=message,
        details=details or {}
    )
    db.add(log)
    await db.commit()


async def extract_labels_from_metadata(db: AsyncSession, job_id: UUID) -> int:
    """Auto-extract labels from metadata fields like categories, tags, labels."""
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id
        )
    )
    items = result.scalars().all()
    
    if not items:
        return 0
    
    labeled_count = 0
    
    for item in items:
        metadata = item.item_metadata or {}
        extracted_labels = []
        
        # Extract from common metadata fields that contain label-like data
        label_fields = ['labels', 'tags', 'categories', 'keywords', 'topics']
        
        for field in label_fields:
            if field in metadata:
                value = metadata[field]
                if isinstance(value, list):
                    extracted_labels.extend([str(v) for v in value if v])
                elif isinstance(value, str) and value:
                    extracted_labels.append(value)
        
        # Also check for primary_category (e.g., from arxiv)
        if 'primary_category' in metadata and metadata['primary_category']:
            extracted_labels.append(str(metadata['primary_category']))
        
        # Remove duplicates and update if we found labels
        if extracted_labels:
            unique_labels = list(dict.fromkeys(extracted_labels))  # Preserve order, remove dupes
            item.labels = unique_labels
            item.is_labeled = True
            labeled_count += 1
    
    if labeled_count > 0:
        await db.commit()
        logger.info(f"Extracted labels for {labeled_count} items")
    
    return labeled_count


async def compute_quality_scores_for_job(db: AsyncSession, job_id: UUID) -> int:
    """Compute quality scores for all items in a job."""
    from app.services.processing_service import compute_quality_score
    
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id,
            DataItem.quality_score.is_(None)
        )
    )
    items = result.scalars().all()
    
    if not items:
        return 0
    
    logger.info(f"Computing quality scores for {len(items)} items")
    
    for item in items:
        await compute_quality_score(item, db)
    
    await db.commit()
    
    return len(items)


async def ml_auto_label_items(db: AsyncSession, job_id: UUID) -> int:
    """Auto-label items using ML-based keyword extraction and classification."""
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id,
            DataItem.is_labeled == False
        )
    )
    items = result.scalars().all()
    
    if not items:
        return 0
    
    labeled_count = 0
    
    for item in items:
        labels, confidence = AutoLabeler.auto_label(
            content=item.content,
            source_url=item.source_url,
            metadata=item.item_metadata,
            data_type=item.data_type
        )
        
        if labels:
            # Merge with existing labels if any
            existing_labels = item.labels or []
            all_labels = list(dict.fromkeys(existing_labels + labels))
            item.labels = all_labels
            item.is_labeled = True
            labeled_count += 1
    
    if labeled_count > 0:
        await db.commit()
        logger.info(f"ML auto-labeled {labeled_count} items")
    
    return labeled_count


async def smart_dedup_for_job(db: AsyncSession, project_id: UUID, job_id: UUID) -> int:
    """Smart deduplication using embeddings for newly scraped items."""
    try:
        from app.services.embedding_service import EmbeddingService
    except ImportError:
        logger.warning("Embedding service not available for smart deduplication")
        return 0
    
    # Get items from this job that don't have embeddings
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id,
            DataItem.data_type == "text",
            DataItem.embedding.is_(None)
        )
    )
    new_items = result.scalars().all()
    
    if not new_items:
        return 0
    
    # Get existing items with embeddings
    existing_result = await db.execute(
        select(DataItem.id, DataItem.embedding).where(
            DataItem.project_id == project_id,
            DataItem.job_id != job_id,
            DataItem.embedding.isnot(None)
        )
    )
    existing_items = existing_result.all()
    
    duplicates_removed = 0
    
    for item in new_items:
        if not item.content:
            continue
        
        # Generate embedding
        try:
            embedding = EmbeddingService.generate_text_embedding(item.content)
            if embedding:
                item.embedding = embedding
                
                # Check for duplicates against existing items
                for existing_id, existing_embedding in existing_items:
                    if existing_embedding:
                        similarity = EmbeddingService.cosine_similarity(embedding, existing_embedding)
                        if similarity >= 0.92:
                            # Mark as duplicate or remove
                            logger.info(f"Duplicate found: {item.id} is {similarity:.2f} similar to {existing_id}")
                            item.item_metadata = item.item_metadata or {}
                            item.item_metadata['duplicate_of'] = str(existing_id)
                            item.item_metadata['duplicate_similarity'] = similarity
                            duplicates_removed += 1
                            break
        except Exception as e:
            logger.warning(f"Failed to generate embedding for item {item.id}: {e}")
    
    await db.commit()
    
    if duplicates_removed > 0:
        logger.info(f"Smart dedup found {duplicates_removed} duplicates")
    
    return duplicates_removed


async def filter_low_quality_items(db: AsyncSession, job_id: UUID, min_score: float = 0.3) -> int:
    """Filter out low quality items that don't meet minimum threshold."""
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id,
            DataItem.quality_score.isnot(None),
            DataItem.quality_score < min_score
        )
    )
    low_quality_items = result.scalars().all()
    
    if not low_quality_items:
        return 0
    
    filtered_count = 0
    
    for item in low_quality_items:
        # Mark as low quality instead of deleting (for review)
        item.item_metadata = item.item_metadata or {}
        item.item_metadata['quality_filtered'] = True
        item.item_metadata['quality_filter_reason'] = f"score below threshold ({item.quality_score:.2f} < {min_score})"
        filtered_count += 1
    
    await db.commit()
    
    logger.info(f"Marked {filtered_count} items as low quality (score < {min_score})")
    
    return filtered_count


async def generate_embeddings_for_job(db: AsyncSession, job_id: UUID) -> int:
    """Generate embeddings for all text items in a job."""
    try:
        from app.services.embedding_service import EmbeddingService
    except ImportError:
        logger.warning("Embedding service not available")
        return 0
    
    result = await db.execute(
        select(DataItem).where(
            DataItem.job_id == job_id,
            DataItem.data_type == "text",
            DataItem.content.isnot(None),
            DataItem.embedding.is_(None)
        )
    )
    items = result.scalars().all()
    
    if not items:
        return 0
    
    generated_count = 0
    
    for item in items:
        try:
            embedding = EmbeddingService.generate_text_embedding(item.content)
            if embedding:
                item.embedding = embedding
                generated_count += 1
        except Exception as e:
            logger.warning(f"Failed to generate embedding for item {item.id}: {e}")
    
    if generated_count > 0:
        await db.commit()
        logger.info(f"Generated embeddings for {generated_count} items")
    
    return generated_count


async def download_media_for_items(
    db: AsyncSession,
    project_id: UUID,
    job_id: UUID,
    config: dict
) -> int:
    """Download media files for data items that have source URLs but no file_path."""
    
    if not config.get("download_media", False):
        return 0
    
    # Get items with source URLs but no file path
    result = await db.execute(
        select(DataItem).where(
            DataItem.project_id == project_id,
            DataItem.job_id == job_id,
            DataItem.data_type.in_(["image", "audio", "video"]),
            DataItem.source_url.isnot(None),
            DataItem.file_path.is_(None)
        )
    )
    items = result.scalars().all()
    
    if not items:
        return 0
    
    logger.info(f"Downloading media for {len(items)} items")
    
    # Get proxy if configured
    proxy_url = None
    if config.get("use_proxy"):
        proxy = await proxy_manager.get_proxy(config.get("proxy_strategy", "round_robin"))
        if proxy:
            proxy_url = proxy.full_url
    
    # Download in batches
    downloaded = 0
    urls = [item.source_url for item in items if item.source_url]
    
    results = await media_downloader.download_batch(
        urls,
        project_id,
        proxy=proxy_url
    )
    
    # Update items with downloaded file info
    url_to_result = {r["url"]: r for r in results}
    
    for item in items:
        if item.source_url in url_to_result:
            result = url_to_result[item.source_url]
            item.file_path = result["file_path"]
            item.file_size = result["file_size"]
            item.mime_type = result["mime_type"]
            downloaded += 1
    
    await db.commit()
    
    logger.info(f"Downloaded {downloaded}/{len(items)} media files")
    return downloaded


class JobNotFoundError(Exception):
    """Raised when a job is not found in the database."""
    pass


async def execute_scraping_job(job_id: str) -> dict:
    """Execute a scraping job based on its provider."""
    async with get_db_session() as db:
        # Get job
        result = await db.execute(
            select(ScrapingJob).where(ScrapingJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise JobNotFoundError(f"Job not found: {job_id}")
        
        # Check if job was cancelled
        if job.status == "cancelled":
            logger.warning(f"Job {job_id} was cancelled, skipping execution")
            raise JobNotFoundError(f"Job was cancelled: {job_id}")
        
        # Get project for user_id
        project_result = await db.execute(
            select(Project).where(Project.id == job.project_id)
        )
        project = project_result.scalar_one()
        
        # Update job status
        job.status = "running"
        job.last_run = datetime.now(timezone.utc)
        await db.commit()
        
        await add_job_log(db, job.id, "info", f"Starting job: {job.name}")
        
        try:
            # Setup proxy if configured
            if job.config.get("proxies"):
                for proxy_config in job.config["proxies"]:
                    proxy_manager.add_proxy(proxy_config)
                await add_job_log(db, job.id, "info", f"Loaded {len(job.config['proxies'])} proxies")
            
            # Get appropriate scraper
            scraper = None
            api_key = None
            
            if job.provider == "serpapi":
                api_key = await get_api_key(db, project.user_id, "serpapi")
                if not api_key:
                    raise ValueError("SerpAPI key not configured")
                scraper = SerpAPIScraper(api_key)
            
            elif job.provider == "apify":
                api_key = await get_api_key(db, project.user_id, "apify")
                if not api_key:
                    raise ValueError("Apify token not configured")
                scraper = ApifyScraper(api_key)
            
            elif job.provider == "custom":
                scraper = CustomScraper()
            
            elif job.provider == "browserless":
                api_key = await get_api_key(db, project.user_id, "browserless")
                if not api_key:
                    raise ValueError("Browserless token not configured")
                scraper = BrowserlessScraper(api_key)
            
            elif job.provider == "twitter":
                api_key = await get_api_key(db, project.user_id, "twitter")
                if not api_key:
                    raise ValueError("Twitter bearer token not configured")
                scraper = TwitterScraper(api_key)
            
            elif job.provider == "reddit":
                client_id = await get_api_key(db, project.user_id, "reddit_client_id")
                client_secret = await get_api_key(db, project.user_id, "reddit_client_secret")
                if not client_id or not client_secret:
                    raise ValueError("Reddit API credentials not configured")
                scraper = RedditScraper(client_id, client_secret)
            
            elif job.provider == "youtube":
                api_key = await get_api_key(db, project.user_id, "youtube")
                scraper = YouTubeScraper(api_key)  # Works without API key too
            
            elif job.provider == "github":
                api_key = await get_api_key(db, project.user_id, "github")
                scraper = GitHubScraper(api_key)  # Works without token too
            
            elif job.provider == "newsapi":
                api_key = await get_api_key(db, project.user_id, "newsapi")
                if not api_key:
                    raise ValueError("NewsAPI key not configured")
                scraper = NewsAPIScraper(api_key)
            
            elif job.provider == "google_news":
                scraper = GoogleNewsScraper()
            
            elif job.provider == "hackernews":
                scraper = HackerNewsScraper()
            
            elif job.provider == "arxiv":
                scraper = ArxivScraper()
            
            elif job.provider == "wikipedia":
                scraper = WikipediaScraper()
            
            elif job.provider == "sitemap":
                scraper = SitemapCrawler()
            
            elif job.provider == "rss":
                scraper = RSSCrawler()
            
            elif job.provider == "webcrawler":
                scraper = WebCrawler()
            
            elif job.provider == "image_scraper":
                scraper = ImageScraper()
            
            elif job.provider == "audio_scraper":
                scraper = AudioScraper()
            
            elif job.provider == "video_scraper":
                scraper = VideoScraper()
            
            else:
                raise ValueError(f"Unknown provider: {job.provider}")
            
            # Execute scraping
            await add_job_log(db, job.id, "info", f"Using provider: {job.provider}")
            items = await scraper.scrape(job.config, job.project_id, db, job.id)
            
            await add_job_log(
                db, job.id, "info",
                f"Scraping completed. Collected {len(items)} items."
            )
            
            # Download media if enabled
            downloaded = await download_media_for_items(
                db, job.project_id, job.id, job.config
            )
            
            if downloaded > 0:
                await add_job_log(
                    db, job.id, "info",
                    f"Downloaded {downloaded} media files."
                )
            
            # Auto-extract labels from metadata (categories, tags, etc.)
            labels_extracted = await extract_labels_from_metadata(db, job.id)
            if labels_extracted > 0:
                await add_job_log(
                    db, job.id, "info",
                    f"Extracted labels for {labels_extracted} items from metadata."
                )
            
            # ML Auto-labeling (keyword-based classification)
            if job.config.get("enable_auto_labeling", True):
                ml_labels = await ml_auto_label_items(db, job.id)
                if ml_labels > 0:
                    await add_job_log(
                        db, job.id, "info",
                        f"ML auto-labeled {ml_labels} items with topic/sentiment labels."
                    )
            
            # Auto-compute quality scores for all scraped items
            quality_computed = await compute_quality_scores_for_job(db, job.id)
            if quality_computed > 0:
                await add_job_log(
                    db, job.id, "info",
                    f"Computed quality scores for {quality_computed} items."
                )
            
            # Quality filtering (mark low quality items)
            if job.config.get("enable_quality_filter", True):
                min_quality = job.config.get("min_quality_score", 0.3)
                filtered = await filter_low_quality_items(db, job.id, min_quality)
                if filtered > 0:
                    await add_job_log(
                        db, job.id, "info",
                        f"Marked {filtered} items as low quality (score < {min_quality})."
                    )
            
            # Generate embeddings for text items
            if job.config.get("enable_embeddings", True):
                embeddings_generated = await generate_embeddings_for_job(db, job.id)
                if embeddings_generated > 0:
                    await add_job_log(
                        db, job.id, "info",
                        f"Generated embeddings for {embeddings_generated} text items."
                    )
            
            # Smart deduplication using embeddings
            if job.config.get("enable_smart_dedup", True):
                duplicates = await smart_dedup_for_job(db, job.project_id, job.id)
                if duplicates > 0:
                    await add_job_log(
                        db, job.id, "info",
                        f"Found {duplicates} semantically similar duplicates."
                    )
            
            # Update job status
            job.status = "completed"
            job.error_message = None
            job.retry_count = 0  # Reset retry count on success
            await db.commit()
            
            await add_job_log(
                db, job.id, "info",
                f"Job completed successfully. Total items: {len(items)}"
            )
            
            return {
                "success": True,
                "items_count": len(items),
                "media_downloaded": downloaded,
                "job_id": job_id
            }
        
        except Exception as e:
            logger.error(f"Job execution failed: {str(e)}")
            
            # Update job status
            job.status = "failed"
            job.error_message = str(e)
            job.retry_count += 1
            await db.commit()
            
            await add_job_log(
                db, job.id, "error",
                f"Job failed: {str(e)}",
                details={"retry_count": job.retry_count, "max_retries": job.max_retries}
            )
            
            raise


async def retry_failed_job(job_id: str) -> dict:
    """Retry a failed job with exponential backoff."""
    async with get_db_session() as db:
        result = await db.execute(
            select(ScrapingJob).where(ScrapingJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise JobNotFoundError(f"Job not found: {job_id}")
        
        # Check if job was cancelled
        if job.status == "cancelled":
            logger.warning(f"Job {job_id} was cancelled, cannot retry")
            raise JobNotFoundError(f"Job was cancelled: {job_id}")
        
        if job.status != "failed":
            raise ValueError(f"Job is not in failed state: {job.status}")
        
        if job.retry_count >= job.max_retries:
            raise ValueError(f"Max retries ({job.max_retries}) exceeded")
        
        # Calculate backoff delay
        delay = min(60 * (2 ** job.retry_count), 3600)  # Max 1 hour
        
        await add_job_log(
            db, job.id, "info",
            f"Scheduling retry in {delay} seconds (attempt {job.retry_count + 1}/{job.max_retries})"
        )
        
        # Wait for backoff
        await asyncio.sleep(delay)
        
        # Execute job
        return await execute_scraping_job(job_id)
