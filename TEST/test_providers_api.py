"""Test providers API."""
import requests
import os

os.environ["NO_PROXY"] = "*"

response = requests.get("http://127.0.0.1:8099/api/providers")
providers = response.json()
print(f"Total providers: {len(providers)}")
print("\nAll providers:")
for p in providers:
    print(f"  - {p['id']}: {p['name']}")

