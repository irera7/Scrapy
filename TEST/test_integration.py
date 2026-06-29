"""
Integration test for all FREE scraping providers via the actual executor.
This tests the complete scraping flow through the database.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set environment for testing
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing')
os.environ.setdefault('MINIO_ENDPOINT', 'localhost:9000')
os.environ.setdefault('MINIO_ROOT_USER', 'minioadmin')
os.environ.setdefault('MINIO_ROOT_PASSWORD', 'minioadmin123')

from uuid import uuid4, UUID
from datetime import datetime
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)


async def run_provider_test(provider: str, config: dict, test_name: str):
    """Run a single provider test through the executor."""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {test_name}")
    print(f"   Provider: {provider}")
    print(f"{'='*60}")
    
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select, func
    
    from app.core.config import settings
    from app.models.user import User
    from app.models.project import Project
    from app.models.job import ScrapingJob
    from app.models.data_item import DataItem
    
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        try:
            # Find or create test user
            result = await db.execute(
                select(User).where(User.email == "integration_test@test.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                from app.core.security import get_password_hash
                user = User(
                    email="integration_test@test.com",
                    password_hash=get_password_hash("test12345678"),
                    full_name="Integration Test User"
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"   Created test user: {user.email}")
            
            # Find or create test project
            result = await db.execute(
                select(Project).where(
                    Project.user_id == user.id,
                    Project.name == "Integration Test Project"
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                project = Project(
                    user_id=user.id,
                    name="Integration Test Project",
                    description="Testing all providers",
                    data_type="mixed"
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                print(f"   Created test project: {project.id}")
            
            # Create test job
            job = ScrapingJob(
                project_id=project.id,
                name=f"Test {provider} - {datetime.now().strftime('%H:%M:%S')}",
                provider=provider,
                config=config,
                status="pending"
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            print(f"   Created job: {job.id}")
            
            # Execute job via executor
            from app.scrapers.executor import execute_scraping_job
            
            result = await execute_scraping_job(str(job.id))
            
            # Count items collected
            count_result = await db.execute(
                select(func.count(DataItem.id)).where(DataItem.job_id == job.id)
            )
            items_count = count_result.scalar() or 0
            
            # Get sample items
            items_result = await db.execute(
                select(DataItem).where(DataItem.job_id == job.id).limit(3)
            )
            sample_items = items_result.scalars().all()
            
            print(f"✅ {test_name}: SUCCESS")
            print(f"   Items collected: {items_count}")
            
            if sample_items:
                print(f"   Sample items:")
                for item in sample_items:
                    content_preview = (item.content or "")[:80]
                    print(f"   - [{item.data_type}] {content_preview}...")
            
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: FAILED")
            print(f"   Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await db.close()
    
    await engine.dispose()


async def main():
    """Run all integration tests."""
    print("="*60)
    print("🧪 INTEGRATION TESTS - FREE PROVIDERS")
    print("   Testing via actual executor with database")
    print("="*60)
    
    results = {}
    
    # Define tests for free providers
    tests = [
        # GitHub - search repositories
        ("github", {
            "type": "search_repos",
            "query": "python web scraper",
            "max_results": 3,
            "language": "python"
        }, "GitHub Repository Search"),
        
        # GitHub - get README
        ("github", {
            "type": "readme",
            "owner": "python",
            "repo": "cpython"
        }, "GitHub README Fetch"),
        
        # Hacker News - top stories
        ("hackernews", {
            "type": "top",
            "max_results": 3
        }, "Hacker News Top Stories"),
        
        # arXiv - search papers
        ("arxiv", {
            "query": "machine learning",
            "max_results": 3,
            "category": "cs.AI"
        }, "arXiv Paper Search"),
        
        # Wikipedia - search articles
        ("wikipedia", {
            "type": "search",
            "query": "artificial intelligence",
            "limit": 2,
            "language": "en"
        }, "Wikipedia Article Search"),
        
        # Google News - scrape headlines
        ("google_news", {
            "query": "technology",
            "max_results": 3,
            "language": "en",
            "country": "US"
        }, "Google News Headlines"),
        
        # YouTube - search (web scraping mode, no API key)
        ("youtube", {
            "type": "search",
            "query": "python tutorial",
            "max_results": 3
        }, "YouTube Video Search"),
        
        # Custom Scraper - test with a public page
        ("custom", {
            "urls": ["https://example.com"],
            "extract_type": "text"
        }, "Custom Playwright Scraper"),
    ]
    
    for provider, config, test_name in tests:
        try:
            success = await run_provider_test(provider, config, test_name)
            results[test_name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            results[test_name] = f"❌ ERROR: {str(e)}"
            print(f"❌ {test_name}: Exception - {str(e)}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*60)
    
    passed = 0
    failed = 0
    for test_name, result in results.items():
        print(f"   {test_name}: {result}")
        if "PASS" in result:
            passed += 1
        else:
            failed += 1
    
    print("="*60)
    print(f"   Total: {passed} passed, {failed} failed")
    print("="*60)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(main())
    sys.exit(0 if failed == 0 else 1)

