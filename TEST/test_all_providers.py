"""Test all free providers through the API."""
import requests
import time
import os

# Bypass proxy for local requests
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

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
    print("Login successful!\n")
    
    # Create project
    print("Creating test project...")
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": "Provider Test - Fixed",
            "description": "Testing all free providers after job_id fix",
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
    print(f"Created project: {project['name']}\n")
    
    # Test providers
    providers = [
        ("github", "GitHub Repos", {
            "type": "search_repos",
            "query": "python tensorflow",
            "max_results": 3
        }),
        ("arxiv", "arXiv Papers", {
            "query": "deep learning",
            "max_results": 3
        }),
        ("wikipedia", "Wikipedia Articles", {
            "type": "search",
            "query": "artificial intelligence",
            "limit": 3
        }),
    ]
    
    results = []
    
    for provider, name, config in providers:
        print(f"Testing {provider}...")
        
        # Create job
        response = requests.post(
            f"{BASE_URL}/jobs",
            json={
                "project_id": project_id,
                "name": name,
                "provider": provider,
                "config": config
            },
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 201:
            print(f"  Failed to create job: {response.text}")
            results.append((provider, "FAILED", "Job creation failed"))
            continue
        
        job = response.json()
        job_id = job["id"]
        print(f"  Created job: {job_id}")
        
        # Run job
        response = requests.post(f"{BASE_URL}/jobs/{job_id}/run", headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"  Failed to run job: {response.text}")
            results.append((provider, "FAILED", "Job run failed"))
            continue
        
        print(f"  Job queued, waiting...")
        
        # Wait for completion
        items_collected = 0
        status = "pending"
        for i in range(60):  # 60 seconds timeout
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30)
            job_data = response.json()
            status = job_data["status"]
            items_collected = job_data.get("items_collected", 0)
            
            if status in ["completed", "failed"]:
                break
        
        print(f"  Status: {status}, Items: {items_collected}")
        results.append((provider, status, items_collected))
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    for provider, status, items in results:
        status_icon = "✅" if status == "completed" and items > 0 else "❌"
        print(f"{status_icon} {provider}: {status} - {items} items")
    
    print("\nNote: HackerNews and Google News have network issues on this machine")

if __name__ == "__main__":
    main()

