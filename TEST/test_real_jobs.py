"""
Create real scraping jobs for all FREE providers on the production server.
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "https://scrap.nexairalab.net/api"
EMAIL = "llvllr.reza@gmail.com"
PASSWORD = "B4u774me"

async def login():
    """Login and get access token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Logged in as: {data['user']['email']}")
            return data["access_token"]
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None

async def get_or_create_project(token: str):
    """Get or create a test project."""
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # List existing projects
        response = await client.get(f"{BASE_URL}/projects", headers=headers)
        if response.status_code == 200:
            projects = response.json()
            # Look for test project
            for project in projects:
                if project["name"] == "Free Providers Test":
                    print(f"✅ Using existing project: {project['id']}")
                    return project["id"]
        
        # Create new project
        response = await client.post(
            f"{BASE_URL}/projects",
            headers=headers,
            json={
                "name": "Free Providers Test",
                "description": "Testing all free scraping providers",
                "data_type": "mixed"
            }
        )
        if response.status_code in [200, 201]:
            project = response.json()
            print(f"✅ Created project: {project['id']}")
            return project["id"]
        else:
            print(f"❌ Failed to create project: {response.text}")
            return None

async def create_and_run_job(token: str, project_id: str, job_name: str, provider: str, config: dict):
    """Create and run a scraping job."""
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"\n{'='*60}")
        print(f"🔄 Creating job: {job_name}")
        print(f"   Provider: {provider}")
        print(f"   Config: {json.dumps(config, indent=2)}")
        
        # Create job
        response = await client.post(
            f"{BASE_URL}/jobs",
            headers=headers,
            json={
                "name": job_name,
                "project_id": project_id,
                "provider": provider,
                "config": config
            }
        )
        
        if response.status_code not in [200, 201]:
            print(f"❌ Failed to create job: {response.status_code} - {response.text}")
            return None
        
        job = response.json()
        job_id = job["id"]
        print(f"   Created job: {job_id}")
        
        # Run the job
        response = await client.post(
            f"{BASE_URL}/jobs/{job_id}/run",
            headers=headers,
            json={"force": False}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start job: {response.text}")
            return None
        
        print(f"   Job started, waiting for completion...")
        
        # Poll for completion (timeout after 90 seconds)
        for i in range(45):
            await asyncio.sleep(2)
            
            response = await client.get(
                f"{BASE_URL}/jobs/{job_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                job_status = response.json()
                status = job_status["status"]
                items_count = job_status.get("items_collected", 0)
                
                if status == "completed":
                    print(f"✅ {job_name}: COMPLETED - {items_count} items collected")
                    return {"status": "completed", "items": items_count, "job_id": job_id}
                    
                elif status == "failed":
                    error = job_status.get("error_message", "Unknown error")
                    print(f"❌ {job_name}: FAILED - {error}")
                    return {"status": "failed", "error": error, "job_id": job_id}
                    
                elif status in ["pending", "queued", "running"]:
                    if i % 5 == 0:  # Print every 10 seconds
                        print(f"   Status: {status}... ({i*2}s)")
                    continue
        
        print(f"⚠️ {job_name}: TIMEOUT after 90 seconds")
        return {"status": "timeout", "job_id": job_id}

async def main():
    """Main function to create all test jobs."""
    print("="*60)
    print("🧪 CREATING REAL SCRAPING JOBS FOR FREE PROVIDERS")
    print("="*60)
    
    # Step 1: Login
    token = await login()
    if not token:
        print("❌ Could not login. Exiting.")
        return
    
    # Step 2: Get or create project
    project_id = await get_or_create_project(token)
    if not project_id:
        print("❌ Could not get project. Exiting.")
        return
    
    # Step 3: Define jobs for each free provider
    jobs = [
        # GitHub - Search repositories
        ("GitHub Repos - Python AI", "github", {
            "type": "search_repos",
            "query": "machine learning python",
            "max_results": 10,
            "language": "python"
        }),
        
        # Hacker News - Top stories
        ("Hacker News - Top Stories", "hackernews", {
            "type": "top",
            "max_results": 10
        }),
        
        # arXiv - AI papers
        ("arXiv - AI Papers", "arxiv", {
            "query": "large language models",
            "max_results": 10,
            "category": "cs.AI"
        }),
        
        # Wikipedia - Search articles
        ("Wikipedia - AI Articles", "wikipedia", {
            "type": "search",
            "query": "machine learning",
            "limit": 5,
            "language": "en"
        }),
        
        # Google News - Tech headlines
        ("Google News - Tech", "google_news", {
            "query": "artificial intelligence",
            "max_results": 10,
            "language": "en",
            "country": "US"
        }),
        
        # YouTube - Search videos (no API key)
        ("YouTube - Python Tutorials", "youtube", {
            "type": "search",
            "query": "python programming tutorial",
            "max_results": 5
        }),
        
        # Custom Scraper - Example.com
        ("Custom - Example.com", "custom", {
            "urls": ["https://example.com", "https://www.iana.org/domains/reserved"],
            "extract_type": "text"
        }),
    ]
    
    # Step 4: Create and run each job
    results = {}
    
    for job_name, provider, config in jobs:
        try:
            result = await create_and_run_job(token, project_id, job_name, provider, config)
            results[job_name] = result
        except Exception as e:
            print(f"❌ {job_name}: Exception - {str(e)}")
            results[job_name] = {"status": "error", "error": str(e)}
    
    # Step 5: Print summary
    print("\n" + "="*60)
    print("📊 JOB RESULTS SUMMARY")
    print("="*60)
    
    completed = 0
    failed = 0
    total_items = 0
    
    for job_name, result in results.items():
        if result:
            status = result.get("status", "unknown")
            if status == "completed":
                items = result.get("items", 0)
                print(f"✅ {job_name}: {items} items")
                completed += 1
                total_items += items
            elif status == "failed":
                print(f"❌ {job_name}: {result.get('error', 'Failed')}")
                failed += 1
            else:
                print(f"⚠️ {job_name}: {status}")
                failed += 1
        else:
            print(f"❌ {job_name}: No result")
            failed += 1
    
    print("="*60)
    print(f"   Completed: {completed}/{len(jobs)}")
    print(f"   Total items collected: {total_items}")
    print(f"   Project ID: {project_id}")
    print("="*60)
    print("\n🔗 View results at: https://scrap.nexairalab.net/dashboard")

if __name__ == "__main__":
    asyncio.run(main())

