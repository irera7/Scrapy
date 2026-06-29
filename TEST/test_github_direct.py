"""Test GitHub API directly."""
import asyncio
import httpx

async def test():
    print("Testing GitHub API directly...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": "python tensorflow", "per_page": 3},
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                timeout=30
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Total count: {data.get('total_count', 0)}")
                print(f"Items returned: {len(data.get('items', []))}")
                if data.get("items"):
                    for i, item in enumerate(data["items"][:3]):
                        print(f"  {i+1}. {item.get('full_name')} - {item.get('stargazers_count')} stars")
            else:
                print(f"Error: {resp.text[:500]}")
        except Exception as e:
            print(f"Exception: {type(e).__name__}: {e}")

asyncio.run(test())

