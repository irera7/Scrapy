"""Test Wikimedia API directly."""
import asyncio
import httpx
import os

os.environ["NO_PROXY"] = "*"

async def test():
    async with httpx.AsyncClient() as client:
        # Test Wikimedia image search
        print("Testing Wikimedia Commons Image API...")
        try:
            response = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": "cat filetype:bitmap",
                    "srnamespace": "6",
                    "srlimit": "10",
                    "format": "json"
                },
                timeout=30,
                follow_redirects=True
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200 and response.text:
                data = response.json()
                results = data.get("query", {}).get("search", [])
                print(f"Image results: {len(results)}")
                for r in results[:3]:
                    print(f"  - {r['title']}")
            else:
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test())
