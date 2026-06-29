"""Test scraping image, audio, and video data types."""
import requests
import time
import os

os.environ["NO_PROXY"] = "*"

BASE_URL = "http://127.0.0.1:8099/api"


def login():
    """Login and return auth headers."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "llvllr.reza@gmail.com", "password": "B4u774me"},
        timeout=30
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(headers, name, data_type):
    """Create a project for specific data type."""
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": name,
            "description": f"Testing {data_type} data collection",
            "data_type": data_type
        },
        headers=headers,
        timeout=30
    )
    if response.status_code != 201:
        raise Exception(f"Failed to create project: {response.text}")
    return response.json()


def create_and_run_job(headers, project_id, name, provider, config):
    """Create and run a scraping job."""
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
        return None
    
    job = response.json()
    job_id = job["id"]
    print(f"  Created job: {job_id}")
    
    # Run job
    response = requests.post(f"{BASE_URL}/jobs/{job_id}/run", headers=headers, timeout=30)
    if response.status_code != 200:
        print(f"  Failed to run job: {response.text}")
        return None
    
    # Wait for completion
    for i in range(60):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=30)
        job_data = response.json()
        status = job_data["status"]
        items = job_data.get("items_collected", 0)
        
        if status == "completed":
            print(f"  ✅ Completed: {items} items collected")
            return job_data
        elif status == "failed":
            error = job_data.get("error_message", "Unknown error")
            print(f"  ❌ Failed: {error[:100]}")
            return job_data
        
        if i % 10 == 0:
            print(f"  [{i}s] Status: {status}")
    
    print("  ⏰ Timeout")
    return None


def test_images():
    """Test image scraping using new ImageScraper."""
    print("\n" + "=" * 60)
    print("🖼️  TESTING IMAGE DATA TYPE")
    print("=" * 60)
    
    headers = login()
    
    # Create image project
    project = create_project(headers, "Image Collection Test", "image")
    project_id = project["id"]
    print(f"Created project: {project['name']}")
    
    # Test 1: Scrape images from Wikimedia Commons API
    print("\n1. Scraping images from Wikimedia Commons (API)...")
    result = create_and_run_job(
        headers,
        project_id,
        "Wikimedia Commons - Nature Images",
        "image_scraper",
        {
            "source": "wikimedia",
            "query": "nature landscape",
            "max_results": 10,
            "download_images": False
        }
    )
    
    # Test 2: Scrape from Unsplash Source
    print("\n2. Scraping images from Unsplash Source...")
    result = create_and_run_job(
        headers,
        project_id,
        "Unsplash - Technology Images",
        "image_scraper",
        {
            "source": "unsplash",
            "query": "technology",
            "max_results": 5,
            "download_images": False
        }
    )
    
    return project_id


def test_video():
    """Test video metadata scraping."""
    print("\n" + "=" * 60)
    print("🎬  TESTING VIDEO DATA TYPE")
    print("=" * 60)
    
    headers = login()
    
    # Create video project
    project = create_project(headers, "Video Collection Test", "video")
    project_id = project["id"]
    print(f"Created project: {project['name']}")
    
    # Test Internet Archive videos
    print("\n1. Scraping videos from Internet Archive...")
    result = create_and_run_job(
        headers,
        project_id,
        "Internet Archive - Documentary Videos",
        "video_scraper",
        {
            "source": "archive",
            "query": "documentary nature",
            "max_results": 10
        }
    )
    
    # Test Wikimedia videos
    print("\n2. Scraping videos from Wikimedia Commons...")
    result = create_and_run_job(
        headers,
        project_id,
        "Wikimedia Commons - Nature Videos",
        "video_scraper",
        {
            "source": "wikimedia",
            "query": "wildlife",
            "max_results": 5
        }
    )
    
    return project_id


def test_audio():
    """Test audio metadata scraping."""
    print("\n" + "=" * 60)
    print("🎵  TESTING AUDIO DATA TYPE")
    print("=" * 60)
    
    headers = login()
    
    # Create audio project
    project = create_project(headers, "Audio Collection Test", "audio")
    project_id = project["id"]
    print(f"Created project: {project['name']}")
    
    # Test Internet Archive audio
    print("\n1. Scraping audio from Internet Archive...")
    result = create_and_run_job(
        headers,
        project_id,
        "Internet Archive - Music Collection",
        "audio_scraper",
        {
            "source": "archive",
            "query": "classical music",
            "max_results": 10
        }
    )
    
    # Test Wikimedia audio
    print("\n2. Scraping audio from Wikimedia Commons...")
    result = create_and_run_job(
        headers,
        project_id,
        "Wikimedia Commons - Sound Effects",
        "audio_scraper",
        {
            "source": "wikimedia",
            "query": "sound effect",
            "max_results": 5
        }
    )
    
    return project_id


def check_results(headers, project_id):
    """Check collected data items."""
    response = requests.get(
        f"{BASE_URL}/data",
        params={"project_id": project_id, "limit": 10},
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        return items
    return []


def main():
    print("=" * 60)
    print("MEDIA DATA TYPES TEST")
    print("Using new ImageScraper, VideoScraper, AudioScraper")
    print("(No Playwright - works in Celery on Windows)")
    print("=" * 60)
    
    headers = login()
    print("✅ Login successful")
    
    results = {}
    
    # Test Images
    try:
        image_project_id = test_images()
        items = check_results(headers, image_project_id)
        results["images"] = len(items)
        print(f"\n📊 Image project has {len(items)} items")
        if items:
            print("Sample images:")
            for item in items[:3]:
                print(f"  - {item.get('content', 'N/A')[:50]}...")
    except Exception as e:
        print(f"❌ Image test failed: {e}")
        results["images"] = 0
    
    # Test Videos
    try:
        video_project_id = test_video()
        items = check_results(headers, video_project_id)
        results["videos"] = len(items)
        print(f"\n📊 Video project has {len(items)} items")
        if items:
            print("Sample videos:")
            for item in items[:3]:
                print(f"  - {item.get('content', 'N/A')[:50]}...")
    except Exception as e:
        print(f"❌ Video test failed: {e}")
        results["videos"] = 0
    
    # Test Audio
    try:
        audio_project_id = test_audio()
        items = check_results(headers, audio_project_id)
        results["audio"] = len(items)
        print(f"\n📊 Audio project has {len(items)} items")
        if items:
            print("Sample audio:")
            for item in items[:3]:
                print(f"  - {item.get('content', 'N/A')[:50]}...")
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        results["audio"] = 0
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"🖼️  Images: {results.get('images', 0)} items")
    print(f"🎬  Videos: {results.get('videos', 0)} items")
    print(f"🎵  Audio:  {results.get('audio', 0)} items")
    print("=" * 60)


if __name__ == "__main__":
    main()
