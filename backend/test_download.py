#!/usr/bin/env python3
"""Test script to verify Wikimedia download with various header combinations."""

import asyncio
import httpx

async def test_download():
    """Test downloading from Wikimedia with various headers."""
    
    # Test URL from the logs
    test_url = "https://upload.wikimedia.org/wikipedia/commons/a/a2/Karnataka_Music_Audio_%281%29.wav"
    
    headers_to_test = [
        {
            "name": "Minimal headers",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        },
        {
            "name": "Complete browser headers (Chrome)",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        },
        {
            "name": "Full browser headers with Referer",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://commons.wikimedia.org/",
            }
        },
        {
            "name": "Python httpx default",
            "headers": {}
        }
    ]
    
    print("Testing Wikimedia Download with Different Headers")
    print("=" * 70)
    print(f"URL: {test_url}")
    print()
    
    for i, test in enumerate(headers_to_test, 1):
        print(f"{i}. {test['name']}:")
        if test['headers']:
            for k, v in test['headers'].items():
                print(f"   {k}: {v[:60]}...")
        else:
            print("   (using default httpx headers)")
        
        async with httpx.AsyncClient(headers=test['headers'], follow_redirects=True, timeout=30) as client:
            try:
                response = await client.head(test_url)
                if response.status_code == 200:
                    print(f"   Result: {response.status_code} OK - SUCCESS!")
                    print(f"   Content-Length: {response.headers.get('content-length', 'N/A')} bytes")
                else:
                    print(f"   Result: {response.status_code} {response.reason_phrase} - FAILED")
            except Exception as e:
                print(f"   Error: {str(e)[:60]}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_download())
