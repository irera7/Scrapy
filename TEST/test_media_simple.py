"""Simpler media test with better queries."""
import requests
import time
import os

os.environ["NO_PROXY"] = "*"

BASE_URL = "http://127.0.0.1:8099/api"


def login():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "llvllr.reza@gmail.com", "password": "B4u774me"},
        timeout=30
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(headers, name, data_type):
    response = requests.post(
        f"{BASE_URL}/projects",
        json={"name": name, "description": f"Test {data_type}", "data_type": data_type},
        headers=headers, timeout=30
    )
    return response.json()


def run_job(headers, project_id, name, provider, config):
    # Create
    response = requests.post(
        f"{BASE_URL}/jobs",
        json={"project_id": project_id, "name": name, "provider": provider, "config": config},
        headers=headers, timeout=30
    )
    if response.status_code != 201:
        print(f"  ❌ Failed: {response.text[:100]}")
        return None
    
    job_id = response.json()["id"]
    
    # Run
    requests.post(f"{BASE_URL}/jobs/{job_id}/run", headers=headers, timeout=30)
    
    # Wait
    for i in range(30):
        time.sleep(1)
        job = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30).json()
        if job["status"] == "completed":
            print(f"  ✅ {job.get('items_collected', 0)} items")
            return job
        elif job["status"] == "failed":
            print(f"  ❌ {job.get('error_message', 'Error')[:50]}")
            return job
    return None


def main():
    print("=" * 50)
    print("MEDIA SCRAPING TEST")
    print("=" * 50)
    
    headers = login()
    print("✅ Logged in\n")
    
    # Images - Unsplash works
    print("🖼️ IMAGES")
    proj = create_project(headers, "Images", "image")
    
    print("  Unsplash (nature):")
    run_job(headers, proj["id"], "Unsplash Nature", "image_scraper", {
        "source": "unsplash",
        "query": "nature",
        "max_results": 10
    })
    
    print("  Wikimedia Commons (cat):")
    run_job(headers, proj["id"], "Wikimedia Cats", "image_scraper", {
        "source": "wikimedia",
        "query": "cat",
        "max_results": 10
    })
    
    # Videos - Wikimedia
    print("\n🎬 VIDEOS")
    proj = create_project(headers, "Videos", "video")
    
    print("  Wikimedia Commons (wildlife video):")
    run_job(headers, proj["id"], "Wikimedia Wildlife", "video_scraper", {
        "source": "wikimedia",
        "query": "video wildlife",
        "max_results": 10
    })
    
    # Audio - Wikimedia
    print("\n🎵 AUDIO")
    proj = create_project(headers, "Audio", "audio")
    
    print("  Wikimedia Commons (music audio):")
    run_job(headers, proj["id"], "Wikimedia Audio", "audio_scraper", {
        "source": "wikimedia",
        "query": "music audio",
        "max_results": 10
    })
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()

