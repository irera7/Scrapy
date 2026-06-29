#!/usr/bin/env python3
"""Test Wikimedia access with requests library instead of httpx."""

import requests

def test_with_requests():
    """Test with requests library which has different fingerprinting."""
    
    test_url = "https://upload.wikimedia.org/wikipedia/commons/a/a2/Karnataka_Music_Audio_%281%29.wav"
    
    tests = [
        {
            "name": "requests with browser headers",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Referer": "https://commons.wikimedia.org/",
            }
        },
        {
            "name": "requests default",
            "headers": None
        }
    ]
    
    print("Testing Wikimedia with requests library")
    print("=" * 70)
    print(f"URL: {test_url}\n")
    
    for test in tests:
        print(f"Test: {test['name']}")
        try:
            if test['headers']:
                response = requests.head(test_url, headers=test['headers'], timeout=10, allow_redirects=True)
            else:
                response = requests.head(test_url, timeout=10, allow_redirects=True)
            
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  SUCCESS! Content-Length: {response.headers.get('content-length', 'N/A')}")
                print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
            else:
                print(f"  FAILED: {response.reason}")
        except Exception as e:
            print(f"  Error: {e}")
        print()

if __name__ == "__main__":
    test_with_requests()

