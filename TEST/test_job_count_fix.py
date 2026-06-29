"""Test to verify job_id fix - items_collected should now show correct counts."""
import httpx
import asyncio
import time

BASE_URL = "http://127.0.0.1:8099/api"

async def main():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Login
        print("Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "llvllr.reza@gmail.com",
                "password": "B4u774me"
            }
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!")
        
        # Create a new test project
        print("\nCreating test project...")
        project_response = await client.post(
            f"{BASE_URL}/projects",
            json={
                "name": "Job Count Test",
                "description": "Testing that items_collected counter works"
            },
            headers=headers
        )
        
        if project_response.status_code != 201:
            print(f"Failed to create project: {project_response.text}")
            return
        
        project = project_response.json()
        project_id = project["id"]
        print(f"Created project: {project['name']} (ID: {project_id})")
        
        # Create and run a Wikipedia job (should work reliably)
        print("\nCreating Wikipedia job...")
        job_response = await client.post(
            f"{BASE_URL}/jobs",
            json={
                "project_id": project_id,
                "name": "Wikipedia - Test Count",
                "provider": "wikipedia",
                "config": {
                    "type": "search",
                    "query": "machine learning",
                    "limit": 3
                }
            },
            headers=headers
        )
        
        if job_response.status_code != 201:
            print(f"Failed to create job: {job_response.text}")
            return
        
        job = job_response.json()
        job_id = job["id"]
        print(f"Created job: {job['name']} (ID: {job_id})")
        
        # Run the job
        print("\nRunning the job...")
        run_response = await client.post(
            f"{BASE_URL}/jobs/{job_id}/run",
            headers=headers
        )
        
        if run_response.status_code != 200:
            print(f"Failed to run job: {run_response.text}")
            return
        
        print("Job queued for execution")
        
        # Wait for job to complete
        print("\nWaiting for job to complete...")
        for i in range(30):  # 30 seconds timeout
            await asyncio.sleep(1)
            
            job_status_response = await client.get(
                f"{BASE_URL}/jobs/{job_id}",
                headers=headers
            )
            job_status = job_status_response.json()
            print(f"  Status: {job_status['status']}, Items collected: {job_status.get('items_collected', 0)}")
            
            if job_status["status"] in ["completed", "failed"]:
                break
        
        # Final check
        print("\n" + "="*50)
        print("FINAL RESULT")
        print("="*50)
        
        job_final = await client.get(f"{BASE_URL}/jobs/{job_id}", headers=headers)
        job_data = job_final.json()
        
        print(f"Job Name: {job_data['name']}")
        print(f"Status: {job_data['status']}")
        print(f"Items Collected: {job_data.get('items_collected', 0)}")
        
        # Also check data items count
        data_items_response = await client.get(
            f"{BASE_URL}/data?project_id={project_id}",
            headers=headers
        )
        data_response = data_items_response.json()
        
        if isinstance(data_response, dict) and "total" in data_response:
            print(f"Actual data items in DB: {data_response['total']}")
        elif isinstance(data_response, list):
            print(f"Actual data items in DB: {len(data_response)}")
        
        if job_data.get('items_collected', 0) > 0:
            print("\n✅ SUCCESS! items_collected is now showing correct counts!")
        else:
            print("\n❌ items_collected is still 0. Job might still be processing or fix needs verification.")

if __name__ == "__main__":
    asyncio.run(main())

