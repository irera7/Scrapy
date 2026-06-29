"""
Direct test script for all FREE scraping providers (no API key required).
Tests scrapers directly without Celery.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from uuid import uuid4
import json

# Initialize logging
import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)


async def test_github():
    """Test GitHub scraper."""
    print("\n" + "="*60)
    print("🧪 Testing GitHub Scraper")
    print("="*60)
    
    from app.scrapers.providers.github_scraper import GitHubScraper
    
    # Test without token (public API)
    scraper = GitHubScraper(token=None)
    
    config = {
        "type": "search_repos",
        "query": "python web scraper",
        "max_results": 3,
        "language": "python"
    }
    
    try:
        # We can't use db here, so just test the API request
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "python web scraper language:python",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 3
                },
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"✅ GitHub: Found {len(items)} repositories")
                for repo in items[:3]:
                    print(f"   - {repo['full_name']} ⭐ {repo['stargazers_count']}")
                return True
            else:
                print(f"❌ GitHub: API error {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ GitHub: Exception - {str(e)}")
        return False


async def test_hackernews():
    """Test Hacker News scraper."""
    print("\n" + "="*60)
    print("🧪 Testing Hacker News Scraper")
    print("="*60)
    
    import httpx
    import traceback
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, verify=True) as client:
            # Get top stories
            response = await client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json"
            )
            
            if response.status_code == 200:
                story_ids = response.json()[:5]
                print(f"✅ HN: Got {len(story_ids)} story IDs")
                
                # Get first 3 stories
                stories = []
                for story_id in story_ids[:3]:
                    try:
                        story_response = await client.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        )
                        if story_response.status_code == 200:
                            story = story_response.json()
                            if story:
                                stories.append(story)
                                print(f"   - {story.get('title', 'No title')[:60]}...")
                    except Exception as e:
                        print(f"   Warning: Failed to get story {story_id}: {e}")
                
                return len(stories) > 0
            else:
                print(f"❌ HN: API error {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ HN: Exception - {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return False


async def test_arxiv():
    """Test arXiv scraper."""
    print("\n" + "="*60)
    print("🧪 Testing arXiv Scraper")
    print("="*60)
    
    import httpx
    from bs4 import BeautifulSoup
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": "cat:cs.AI",
                    "max_results": 3,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml-xml")
                entries = soup.find_all("entry")
                
                print(f"✅ arXiv: Found {len(entries)} papers")
                for entry in entries[:3]:
                    title = entry.find("title").get_text(strip=True) if entry.find("title") else "No title"
                    print(f"   - {title[:60]}...")
                
                return len(entries) > 0
            else:
                print(f"❌ arXiv: API error {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ arXiv: Exception - {str(e)}")
        return False


async def test_wikipedia():
    """Test Wikipedia scraper."""
    print("\n" + "="*60)
    print("🧪 Testing Wikipedia Scraper")
    print("="*60)
    
    import httpx
    
    try:
        headers = {
            "User-Agent": "AIDataCollector/1.0 (https://github.com/ai-data-collector; contact@example.com) Python/httpx"
        }
        
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": "artificial intelligence",
                    "srlimit": 3,
                    "format": "json",
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("query", {}).get("search", [])
                
                print(f"✅ Wikipedia: Found {len(results)} articles")
                for result in results[:3]:
                    print(f"   - {result.get('title', 'No title')}")
                
                return len(results) > 0
            else:
                print(f"❌ Wikipedia: API error {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Wikipedia: Exception - {str(e)}")
        return False


async def test_google_news():
    """Test Google News scraper using Playwright."""
    print("\n" + "="*60)
    print("🧪 Testing Google News Scraper (Playwright Mode)")
    print("="*60)
    
    from bs4 import BeautifulSoup
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Navigate to Google News search
            await page.goto(
                "https://news.google.com/search?q=technology&hl=en-US&gl=US&ceid=US:en",
                wait_until="networkidle",
                timeout=60000
            )
            
            # Wait a bit for dynamic content
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            await browser.close()
            
            soup = BeautifulSoup(content, "lxml")
            
            # Try different selectors for articles
            articles = soup.select("article")
            
            if not articles:
                # Try alternative selectors
                articles = soup.select("div[class*='article'], div[class*='story']")
            
            print(f"   Found {len(articles)} article containers")
            
            # Find article titles
            titles_found = []
            for article in articles[:10]:
                # Try various title selectors
                title_elem = article.select_one("h3, h4, a[href*='/articles/']")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 10:
                        titles_found.append(title)
            
            if titles_found:
                print(f"✅ Google News: Found {len(titles_found)} article titles")
                for title in titles_found[:3]:
                    print(f"   - {title[:60]}...")
                return True
            else:
                print(f"❌ Google News: No article titles extracted")
                # Print some page content for debugging
                body_text = soup.get_text()[:500]
                print(f"   Page preview: {body_text[:200]}...")
                return False
                
    except Exception as e:
        print(f"❌ Google News: Exception - {type(e).__name__}: {str(e)}")
        return False


async def test_youtube():
    """Test YouTube scraper (without API key) using Playwright."""
    print("\n" + "="*60)
    print("🧪 Testing YouTube Scraper (Playwright Mode)")
    print("="*60)
    
    import re
    import json as json_module
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Navigate to YouTube search
            await page.goto(
                "https://www.youtube.com/results?search_query=python+tutorial",
                wait_until="networkidle",
                timeout=60000
            )
            
            content = await page.content()
            await browser.close()
            
            # Find ytInitialData
            match = re.search(r'var ytInitialData = ({.*?});', content, re.DOTALL)
            if match:
                try:
                    data = json_module.loads(match.group(1))
                    
                    # Navigate to video results
                    contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                    
                    videos = []
                    for section in contents:
                        item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                        for video_renderer in item_section:
                            video = video_renderer.get("videoRenderer", {})
                            if video and video.get("videoId"):
                                title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                                videos.append({
                                    "id": video["videoId"],
                                    "title": title
                                })
                                if len(videos) >= 3:
                                    break
                        if len(videos) >= 3:
                            break
                    
                    print(f"✅ YouTube: Found {len(videos)} videos")
                    for video in videos[:3]:
                        print(f"   - {video['title'][:60]}...")
                    
                    return len(videos) > 0
                except json_module.JSONDecodeError as e:
                    print(f"❌ YouTube: Failed to parse JSON data - {e}")
                    return False
            else:
                print("❌ YouTube: Could not find ytInitialData in page")
                return False
    except Exception as e:
        print(f"❌ YouTube: Exception - {type(e).__name__}: {str(e)}")
        return False


async def test_custom_scraper():
    """Test custom Playwright scraper."""
    print("\n" + "="*60)
    print("🧪 Testing Custom Scraper (Playwright)")
    print("="*60)
    
    try:
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = await context.new_page()
            
            # Test with example.com - a reliable test page
            await page.goto("https://example.com", wait_until="networkidle", timeout=30000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            await browser.close()
            
            if text:
                print(f"✅ Custom Scraper: Extracted {len(text)} characters")
                print(f"   Preview: {text[:200]}...")
                return True
            else:
                print("❌ Custom Scraper: No content extracted")
                return False
    except Exception as e:
        print(f"❌ Custom Scraper: Exception - {str(e)}")
        return False


async def main():
    """Main test function."""
    print("="*60)
    print("🧪 DIRECT SCRAPER TESTING")
    print("   Testing all FREE providers (no API keys required)")
    print("="*60)
    
    results = {}
    
    # Test each provider
    tests = [
        ("GitHub", test_github),
        ("Hacker News", test_hackernews),
        ("arXiv", test_arxiv),
        ("Wikipedia", test_wikipedia),
        ("Google News", test_google_news),
        ("YouTube", test_youtube),
        ("Custom Scraper", test_custom_scraper),
    ]
    
    for name, test_func in tests:
        try:
            success = await test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            results[name] = f"❌ ERROR: {str(e)}"
            print(f"❌ {name}: Exception - {str(e)}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    for provider, result in results.items():
        print(f"   {provider}: {result}")
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

