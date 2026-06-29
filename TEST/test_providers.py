"""
Test script for all FREE scraping providers (no API key required).
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8099/api"
TOKEN = None
PROJECT_ID = None

async def register_and_login():
    """Register a test user and get auth token."""
    global TOKEN
    async with httpx.AsyncClient() as client:
        # Try to register
        try:
            response = await client.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": "tester@test.com",
                    "password": "test12345678",
                    "full_name": "Test User"
                }
            )
            if response.status_code == 200:
                data = response.json()
                TOKEN = data["access_token"]
                print(f"✅ Registered new user: {data['user']['email']}")
                return TOKEN
        except Exception as e:
            pass
        
        # If registration failed (user exists), try to login
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "tester@test.com",
                "password": "test12345678"
            }
        )
        if response.status_code == 200:
            data = response.json()
            TOKEN = data["access_token"]
            print(f"✅ Logged in as: {data['user']['email']}")
            return TOKEN
        else:
            print(f"❌ Login failed: {response.text}")
            return None

async def create_test_project():
    """Create a test project for scraping."""
    global PROJECT_ID
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        # Check if test project exists
        response = await client.get(f"{BASE_URL}/projects", headers=headers)
        if response.status_code == 200:
            projects = response.json()
            for project in projects:
                if project["name"] == "Provider Test Project":
                    PROJECT_ID = project["id"]
                    print(f"✅ Using existing project: {PROJECT_ID}")
                    return PROJECT_ID
        
        # Create new project
        response = await client.post(
            f"{BASE_URL}/projects",
            headers=headers,
            json={
                "name": "Provider Test Project",
                "description": "Testing all free scraping providers",
                "data_type": "mixed"
            }
        )
        if response.status_code in [200, 201]:
            data = response.json()
            PROJECT_ID = data["id"]
            print(f"✅ Created project: {PROJECT_ID}")
            return PROJECT_ID
        else:
            print(f"❌ Failed to create project: {response.text}")
            return None

async def test_provider(provider_name: str, config: dict):
    """Test a specific provider by creating a scraping job."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        print(f"\n{'='*60}")
        print(f"🔄 Testing Provider: {provider_name}")
        print(f"   Config: {json.dumps(config, indent=2)}")
        print(f"{'='*60}")
        
        # Create a job for this provider
        job_data = {
            "name": f"Test {provider_name} - {datetime.now().strftime('%H:%M:%S')}",
            "project_id": PROJECT_ID,
            "provider": provider_name,
            "config": config
        }
        
        response = await client.post(
            f"{BASE_URL}/jobs",
            headers=headers,
            json=job_data
        )
        
        if response.status_code not in [200, 201]:
            print(f"❌ Failed to create job: {response.status_code} - {response.text}")
            return False
        
        job = response.json()
        job_id = job["id"]
        print(f"   Created job: {job_id}")
        
        # Start the job
        response = await client.post(
            f"{BASE_URL}/jobs/{job_id}/run",
            headers=headers,
            json={"force": False}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start job: {response.text}")
            return False
        
        print(f"   Job started, waiting for completion...")
        
        # Poll for completion (timeout after 60 seconds)
        for i in range(30):
            await asyncio.sleep(2)
            
            response = await client.get(
                f"{BASE_URL}/jobs/{job_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                job_status = response.json()
                status = job_status["status"]
                items_count = job_status.get("items_count", 0)
                
                if status == "completed":
                    print(f"✅ {provider_name}: SUCCESS - {items_count} items scraped")
                    
                    # Fetch some sample data
                    data_response = await client.get(
                        f"{BASE_URL}/data?project_id={PROJECT_ID}&limit=3",
                        headers=headers
                    )
                    if data_response.status_code == 200:
                        data_items = data_response.json()
                        if data_items.get("items"):
                            print(f"   Sample data:")
                            for item in data_items["items"][:3]:
                                content_preview = item.get("content", "")[:100]
                                print(f"   - [{item.get('data_type')}] {content_preview}...")
                    return True
                    
                elif status == "failed":
                    error = job_status.get("error_message", "Unknown error")
                    print(f"❌ {provider_name}: FAILED - {error}")
                    return False
                    
                elif status in ["pending", "running"]:
                    print(f"   Status: {status}... ({i*2}s)")
                    continue
        
        print(f"⚠️ {provider_name}: TIMEOUT after 60 seconds")
        return False

async def main():
    """Main test function."""
    print("="*60)
    print("🧪 TESTING FREE SCRAPING PROVIDERS")
    print("   (No API keys required)")
    print("="*60)
    
    # Step 1: Authenticate
    if not await register_and_login():
        print("❌ Authentication failed. Exiting.")
        return
    
    # Step 2: Create test project
    if not await create_test_project():
        print("❌ Failed to create project. Exiting.")
        return
    
    # Step 3: Test each free provider
    results = {}
    
    # Test providers one by one
    providers_to_test = [
        # GitHub - search repositories
        ("github", {
            "type": "search_repos",
            "query": "python web scraper",
            "max_results": 5,
            "language": "python"
        }),
        
        # Hacker News - top stories
        ("hackernews", {
            "type": "top",
            "max_results": 5
        }),
        
        # arXiv - search papers
        ("arxiv", {
            "query": "machine learning",
            "max_results": 5,
            "category": "cs.AI"
        }),
        
        # Wikipedia - search articles
        ("wikipedia", {
            "type": "search",
            "query": "artificial intelligence",
            "limit": 3,
            "language": "en"
        }),
        
        # Google News - scrape headlines
        ("google_news", {
            "query": "technology",
            "max_results": 5,
            "language": "en",
            "country": "US"
        }),
        
        # YouTube - web scraping mode (no API key)
        ("youtube", {
            "type": "search",
            "query": "python tutorial",
            "max_results": 5
        }),
        
        # Custom Scraper - test with a simple website
        ("custom", {
            "urls": ["https://httpbin.org/html"],
            "extract_type": "text"
        }),
    ]
    
    for provider, config in providers_to_test:
        try:
            success = await test_provider(provider, config)
            results[provider] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            results[provider] = f"❌ ERROR: {str(e)}"
            print(f"❌ {provider}: Exception - {str(e)}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    for provider, result in results.items():
        print(f"   {provider}: {result}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

