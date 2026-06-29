"""Test Google News scraper with new JS rendering."""
import asyncio
import os

os.environ["NO_PROXY"] = "*"

async def test_rss():
    """Test RSS feed method (no JS required)."""
    print("=" * 60)
    print("Testing Google News RSS Feed")
    print("=" * 60)
    
    import httpx
    from bs4 import BeautifulSoup
    
    rss_url = "https://news.google.com/rss/search?q=technology&hl=en&gl=US&ceid=US:en"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(rss_url, timeout=30, follow_redirects=True)
            print(f"Status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, "lxml-xml")
            items = soup.find_all("item")
            
            print(f"Articles found: {len(items)}")
            
            for item in items[:3]:
                title = item.find("title").get_text(strip=True) if item.find("title") else "N/A"
                source = item.find("source").get_text(strip=True) if item.find("source") else "N/A"
                print(f"  - {title[:60]}... ({source})")
                
        except Exception as e:
            print(f"ERROR: {e}")

async def test_playwright():
    """Test Playwright JS rendering."""
    print("\n" + "=" * 60)
    print("Testing Google News with Playwright (JS Rendering)")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            url = "https://news.google.com/search?q=technology&hl=en&gl=US&ceid=US:en"
            print(f"Navigating to: {url}")
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for articles
            await page.wait_for_selector("article", timeout=10000)
            
            articles = await page.query_selector_all("article")
            print(f"Articles found: {len(articles)}")
            
            for article in articles[:3]:
                title_elem = await article.query_selector("h3 a, h4 a")
                if title_elem:
                    title = await title_elem.inner_text()
                    print(f"  - {title[:60]}...")
            
            await browser.close()
            
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        print("Note: Playwright may not work in Celery on Windows due to asyncio limitations")

async def test_full_scraper():
    """Test the full scraper through the API."""
    print("\n" + "=" * 60)
    print("Testing Full Google News Scraper via API")
    print("=" * 60)
    
    import requests
    
    BASE_URL = "http://127.0.0.1:8099/api"
    
    # Login
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "llvllr.reza@gmail.com", "password": "B4u774me"},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get first project
    response = requests.get(f"{BASE_URL}/projects", headers=headers, timeout=30)
    projects = response.json()
    if not projects:
        print("No projects found")
        return
    
    project_id = projects[0]["id"]
    
    # Create Google News job
    response = requests.post(
        f"{BASE_URL}/jobs",
        json={
            "project_id": project_id,
            "name": "Google News - Tech Test",
            "provider": "google_news",
            "config": {
                "query": "artificial intelligence",
                "max_results": 5,
                "use_js_rendering": False  # Use RSS for testing
            }
        },
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 201:
        print(f"Failed to create job: {response.text}")
        return
    
    job = response.json()
    job_id = job["id"]
    print(f"Created job: {job_id}")
    
    # Run job
    response = requests.post(f"{BASE_URL}/jobs/{job_id}/run", headers=headers, timeout=30)
    print("Job queued, waiting...")
    
    import time
    for i in range(30):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30)
        job_data = response.json()
        status = job_data["status"]
        items = job_data.get("items_collected", 0)
        
        if status in ["completed", "failed"]:
            print(f"Status: {status}, Items: {items}")
            break
    else:
        print("Timeout waiting for job")

async def main():
    await test_rss()
    # Skip Playwright test as it may fail on Windows/Celery
    # await test_playwright()
    await test_full_scraper()

if __name__ == "__main__":
    asyncio.run(main())

