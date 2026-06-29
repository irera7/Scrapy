"""Direct test of scrapers without Celery."""
import asyncio
import sys
sys.path.insert(0, 'D:/Project/Scrap/backend')

from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Test each scraper directly
async def test_github():
    print("\n" + "="*50)
    print("Testing GitHub Scraper")
    print("="*50)
    
    from app.scrapers.providers.github_scraper import GitHubScraper
    
    scraper = GitHubScraper()
    config = {
        "type": "search_repos",
        "query": "python machine learning",
        "max_results": 3
    }
    
    # Create mock DB session
    engine = create_async_engine("postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Get a real project ID from the database
            from sqlalchemy import text
            result = await db.execute(text("SELECT id FROM projects LIMIT 1"))
            row = result.fetchone()
            if not row:
                print("ERROR: No projects found in database")
                return
            
            project_id = row[0]
            job_id = uuid4()
            
            print(f"Using project_id: {project_id}")
            print(f"Config: {config}")
            
            items = await scraper.scrape(config, project_id, db, job_id)
            print(f"\nResult: {len(items)} items collected")
            
            # Rollback to avoid saving test data
            await db.rollback()
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

async def test_hackernews():
    print("\n" + "="*50)
    print("Testing HackerNews Scraper")
    print("="*50)
    
    from app.scrapers.providers.news_scraper import HackerNewsScraper
    
    scraper = HackerNewsScraper()
    config = {
        "type": "top",
        "max_results": 3
    }
    
    engine = create_async_engine("postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            from sqlalchemy import text
            result = await db.execute(text("SELECT id FROM projects LIMIT 1"))
            row = result.fetchone()
            if not row:
                print("ERROR: No projects found in database")
                return
            
            project_id = row[0]
            job_id = uuid4()
            
            print(f"Using project_id: {project_id}")
            print(f"Config: {config}")
            
            items = await scraper.scrape(config, project_id, db, job_id)
            print(f"\nResult: {len(items)} items collected")
            
            await db.rollback()
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

async def test_arxiv():
    print("\n" + "="*50)
    print("Testing arXiv Scraper")
    print("="*50)
    
    from app.scrapers.providers.news_scraper import ArxivScraper
    
    scraper = ArxivScraper()
    config = {
        "query": "machine learning",
        "max_results": 3
    }
    
    engine = create_async_engine("postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            from sqlalchemy import text
            result = await db.execute(text("SELECT id FROM projects LIMIT 1"))
            row = result.fetchone()
            if not row:
                print("ERROR: No projects found in database")
                return
            
            project_id = row[0]
            job_id = uuid4()
            
            print(f"Using project_id: {project_id}")
            print(f"Config: {config}")
            
            items = await scraper.scrape(config, project_id, db, job_id)
            print(f"\nResult: {len(items)} items collected")
            
            await db.rollback()
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

async def main():
    await test_github()
    await test_hackernews()
    await test_arxiv()

if __name__ == "__main__":
    asyncio.run(main())

