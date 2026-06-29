"""Test Google News via API with fresh job."""
import requests
import time
import os

os.environ["NO_PROXY"] = "*"

BASE_URL = "http://127.0.0.1:8099/api"

def main():
    # Login
    print("Logging in...")
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
    print("Login successful!")
    
    # Create a new project for this test
    print("\nCreating test project...")
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": "Google News Test",
            "description": "Testing Google News with RSS",
            "data_type": "text"
        },
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 201:
        print(f"Failed to create project: {response.text}")
        return
    
    project = response.json()
    project_id = project["id"]
    print(f"Created project: {project['name']} ({project_id})")
    
    # Create Google News job with RSS (no JS)
    print("\nCreating Google News job...")
    response = requests.post(
        f"{BASE_URL}/jobs",
        json={
            "project_id": project_id,
            "name": "Google News - RSS Test",
            "provider": "google_news",
            "config": {
                "query": "artificial intelligence",
                "max_results": 10,
                "use_js_rendering": False  # Use RSS feed
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
    print(f"Created job: {job['name']} ({job_id})")
    
    # Run the job
    print("\nRunning job...")
    response = requests.post(f"{BASE_URL}/jobs/{job_id}/run", headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Failed to run job: {response.text}")
        return
    
    print("Job queued, waiting for completion...")
    
    # Wait for completion
    for i in range(60):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30)
        job_data = response.json()
        status = job_data["status"]
        items = job_data.get("items_collected", 0)
        error = job_data.get("error_message", "")
        
        print(f"  [{i+1}s] Status: {status}, Items: {items}")
        
        if status == "completed":
            print(f"\n✅ SUCCESS! Collected {items} items from Google News!")
            break
        elif status == "failed":
            print(f"\n❌ FAILED: {error}")
            break
    else:
        print("\nTimeout waiting for job")
    
    # Check the data items
    print("\nChecking collected data...")
    response = requests.get(
        f"{BASE_URL}/data",
        params={"project_id": project_id, "limit": 5},
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        items_list = data.get("items", data) if isinstance(data, dict) else data
        if items_list:
            print(f"Sample items:")
            for item in items_list[:3]:
                title = item.get("content", "")[:60] if item.get("content") else "N/A"
                print(f"  - {title}...")

if __name__ == "__main__":
    main()

