"""Test YouTube scraper."""
import asyncio
import httpx
import re
import json

async def test_youtube_api():
    """Test if YouTube API is accessible (requires API key)."""
    print("1. Testing YouTube Data API (requires API key)...")
    print("   Skipping - no API key configured\n")

async def test_youtube_scraping():
    """Test YouTube scraping without API."""
    print("2. Testing YouTube web scraping (no API key)...")
    
    query = "python tutorial"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://www.youtube.com/results",
                params={"search_query": query},
                headers=headers,
                timeout=30,
                follow_redirects=True
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response length: {len(response.text)} chars")
            
            # Try to find ytInitialData
            match = re.search(r'var ytInitialData = ({.*?});', response.text, re.DOTALL)
            if match:
                print("   Found ytInitialData: YES")
                try:
                    data = json.loads(match.group(1))
                    
                    # Navigate to video results
                    contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                    
                    video_count = 0
                    for section in contents:
                        item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                        for item in item_section:
                            if "videoRenderer" in item:
                                video_count += 1
                    
                    print(f"   Videos found in response: {video_count}")
                    
                    if video_count > 0:
                        # Get first video
                        for section in contents:
                            item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                            for item in item_section:
                                video = item.get("videoRenderer", {})
                                if video:
                                    video_id = video.get("videoId")
                                    title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                                    print(f"   First video: {title[:50]}... (ID: {video_id})")
                                    break
                            break
                except json.JSONDecodeError as e:
                    print(f"   JSON parse error: {e}")
            else:
                print("   Found ytInitialData: NO")
                print("   YouTube may have changed their page structure or is blocking the request")
                
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {e}")

async def test_youtube_direct_video():
    """Test accessing a YouTube video page directly."""
    print("\n3. Testing direct video page access...")
    
    video_id = "dQw4w9WgXcQ"  # Famous video
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://www.youtube.com/watch?v={video_id}",
                headers=headers,
                timeout=30,
                follow_redirects=True
            )
            
            print(f"   Status: {response.status_code}")
            
            # Check for player response
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', response.text, re.DOTALL)
            if match:
                print("   Found ytInitialPlayerResponse: YES")
            else:
                print("   Found ytInitialPlayerResponse: NO")
                
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {e}")

async def main():
    print("=" * 60)
    print("YouTube Scraper Diagnostic")
    print("=" * 60 + "\n")
    
    await test_youtube_api()
    await test_youtube_scraping()
    await test_youtube_direct_video()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("- YouTube scraping without API key parses HTML/JS data")
    print("- If videos aren't found, YouTube may be blocking or structure changed")
    print("- For reliable results, use YouTube Data API v3 with an API key")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

