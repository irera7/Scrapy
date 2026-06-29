"""Direct test of Google News scraper."""
import asyncio
import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(0, 'D:/Project/Scrap/backend')

from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test_google_news_scraper():
    print("Testing Google News scraper directly...")
    
    from app.scrapers.providers.news_scraper import GoogleNewsScraper
    
    scraper = GoogleNewsScraper()
    config = {
        "query": "technology",
        "max_results": 5,
        "use_js_rendering": False  # Use RSS
    }
    
    # Create DB session
    engine = create_async_engine("postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Get a real project ID
            from sqlalchemy import text
            result = await db.execute(text("SELECT id FROM projects LIMIT 1"))
            row = result.fetchone()
            if not row:
                print("No projects found")
                return
            
            project_id = row[0]
            
            # Get a real job ID
            result = await db.execute(text("SELECT id FROM scraping_jobs LIMIT 1"))
            job_row = result.fetchone()
            job_id = job_row[0] if job_row else None
            
            print(f"Using project_id: {project_id}")
            print(f"Using job_id: {job_id}")
            print(f"Config: {config}")
            
            # Call the RSS method directly
            print("\nCalling _scrape_rss directly...")
            items = await scraper._scrape_rss(config, project_id, db, job_id)
            
            print(f"\nResult: {len(items)} items collected")
            
            if items:
                for i, item in enumerate(items[:3]):
                    print(f"  {i+1}. {item.content[:60]}...")
            
            # Rollback to avoid saving test data
            await db.rollback()
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_google_news_scraper())

