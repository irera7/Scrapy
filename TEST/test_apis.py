"""Test if external APIs are accessible."""
import asyncio
import httpx

async def test_scrapers():
    print("Testing external APIs...\n")
    
    print("1. GitHub API...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": "python ai", "per_page": 2},
                timeout=30
            )
            data = resp.json()
            items = data.get("items", [])
            print(f"   Status: {resp.status_code}")
            print(f"   Items found: {len(items)}")
            if items:
                print(f"   First repo: {items[0].get('full_name')}")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n2. Hacker News API...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=30
            )
            story_ids = resp.json()
            print(f"   Status: {resp.status_code}")
            print(f"   Story IDs found: {len(story_ids)}")
            
            # Get first story details
            if story_ids:
                story_resp = await client.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_ids[0]}.json",
                    timeout=30
                )
                story = story_resp.json()
                print(f"   First story: {story.get('title', 'N/A')[:50]}...")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n3. arXiv API...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": "all:machine learning", "max_results": 2},
                timeout=60
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response length: {len(resp.text)} chars")
            if "<entry>" in resp.text:
                print("   Contains entries: YES")
            else:
                print("   Contains entries: NO")
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n4. Google News (scraping)...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://news.google.com/search",
                params={"q": "technology", "hl": "en", "gl": "US"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=30,
                follow_redirects=True
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response length: {len(resp.text)} chars")
            if "<article" in resp.text.lower():
                print("   Contains articles: YES")
            else:
                print("   Contains articles: NO (may need JS rendering)")
        except Exception as e:
            print(f"   ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrapers())

