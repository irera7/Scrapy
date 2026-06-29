"""Check job logs."""
import requests
import os

os.environ["NO_PROXY"] = "*"

BASE_URL = "http://127.0.0.1:8099/api"

# Login
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "llvllr.reza@gmail.com", "password": "B4u774me"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get latest jobs
response = requests.get(f"{BASE_URL}/jobs?limit=5", headers=headers)
jobs = response.json()

print("Recent Jobs:")
for job in jobs[:5]:
    print(f"\nJob: {job['name']} ({job['id']})")
    print(f"  Status: {job['status']}")
    print(f"  Items: {job.get('items_collected', 0)}")
    print(f"  Error: {job.get('error_message', 'None')}")
    
    # Get logs for this job
    log_response = requests.get(f"{BASE_URL}/jobs/{job['id']}/logs", headers=headers)
    logs = log_response.json()
    
    if logs:
        print(f"  Logs ({len(logs)} entries):")
        for log in logs[:5]:
            print(f"    [{log['level']}] {log['message'][:80]}")

