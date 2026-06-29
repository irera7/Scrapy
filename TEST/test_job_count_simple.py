"""Simple test to verify job_id fix."""
import requests
import time

BASE_URL = "http://127.0.0.1:8099/api"

def main():
    # Login
    print("Logging in...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "llvllr.reza@gmail.com",
            "password": "B4u774me"
        },
        timeout=30
    )
    
    print(f"Login response status: {response.status_code}")
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful!")
    
    # Create a new test project
    print("\nCreating test project...")
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": "Job Count Test",
            "description": "Testing that items_collected counter works",
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
    print(f"Created project: {project['name']} (ID: {project_id})")
    
    # Create and run a Wikipedia job
    print("\nCreating Wikipedia job...")
    response = requests.post(
        f"{BASE_URL}/jobs",
        json={
            "project_id": project_id,
            "name": "Wikipedia - Test Count",
            "provider": "wikipedia",
            "config": {
                "type": "search",
                "query": "deep learning",
                "limit": 3
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
    print(f"Created job: {job['name']} (ID: {job_id})")
    
    # Run the job
    print("\nRunning the job...")
    response = requests.post(
        f"{BASE_URL}/jobs/{job_id}/run",
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Failed to run job: {response.text}")
        return
    
    print("Job queued for execution")
    
    # Wait for job to complete
    print("\nWaiting for job to complete...")
    for i in range(30):
        time.sleep(1)
        
        response = requests.get(
            f"{BASE_URL}/jobs/{job_id}",
            headers=headers,
            timeout=30
        )
        job_status = response.json()
        print(f"  Status: {job_status['status']}, Items collected: {job_status.get('items_collected', 0)}")
        
        if job_status["status"] in ["completed", "failed"]:
            break
    
    # Final check
    print("\n" + "="*50)
    print("FINAL RESULT")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30)
    job_data = response.json()
    
    print(f"Job Name: {job_data['name']}")
    print(f"Status: {job_data['status']}")
    print(f"Items Collected: {job_data.get('items_collected', 0)}")
    
    if job_data.get('items_collected', 0) > 0:
        print("\n✅ SUCCESS! items_collected is now showing correct counts!")
    else:
        print("\n❌ items_collected is still 0. Check if Celery worker is running.")

if __name__ == "__main__":
    main()

