"""
Test script to verify data items and preview functionality.
Run this to check if your data items have the necessary fields.
"""

import requests
import json

API_URL = "http://localhost:8099/api"

# Get your auth token first
print("1. Login to get token...")
login_response = requests.post(f"{API_URL}/auth/login", json={
    "email": "your_email@example.com",  # CHANGE THIS
    "password": "your_password"  # CHANGE THIS
})

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("✅ Login successful!\n")

# List projects
print("2. Getting projects...")
projects_response = requests.get(f"{API_URL}/projects", headers=headers)
projects = projects_response.json()

if not projects:
    print("❌ No projects found. Create a project first!")
    exit(1)

print(f"✅ Found {len(projects)} project(s)\n")

# Use first project
project = projects[0]
project_id = project["id"]
print(f"📁 Using project: {project['name']} (ID: {project_id})\n")

# Get data items
print("3. Getting data items...")
data_response = requests.get(
    f"{API_URL}/data",
    params={"project_id": project_id, "limit": 5},
    headers=headers
)

data = data_response.json()
items = data.get("items", [])

if not items:
    print("❌ No data items found in this project!")
    print("   Run a scraping job first to collect data.")
    exit(1)

print(f"✅ Found {data.get('total', 0)} total items (showing first 5)\n")

# Analyze items
print("=" * 70)
print("DATA ITEM ANALYSIS")
print("=" * 70)

for i, item in enumerate(items, 1):
    print(f"\n📄 Item {i}:")
    print(f"   Type: {item['data_type']}")
    print(f"   ID: {item['id']}")
    print(f"   Has content: {'✅' if item.get('content') else '❌'}")
    print(f"   Has source_url: {'✅' if item.get('source_url') else '❌'}")
    print(f"   Has file_path: {'✅' if item.get('file_path') else '❌'}")
    print(f"   Has download_url: {'✅' if item.get('download_url') else '❌'}")
    print(f"   Has labels: {'✅' if item.get('labels') and len(item['labels']) > 0 else '❌'}")
    print(f"   Has metadata: {'✅' if item.get('metadata') and len(item['metadata']) > 0 else '❌'}")
    print(f"   File size: {item.get('file_size', 'N/A')}")
    print(f"   MIME type: {item.get('mime_type', 'N/A')}")
    print(f"   Quality score: {item.get('quality_score', 'N/A')}")
    print(f"   Is processed: {item.get('is_processed', False)}")
    
    if item.get('content'):
        content_preview = item['content'][:100] + "..." if len(item['content']) > 100 else item['content']
        print(f"   Content preview: {content_preview}")
    
    if item.get('download_url'):
        print(f"   🔗 Download URL available: {item['download_url'][:50]}...")

print("\n" + "=" * 70)
print("PREVIEW MODAL FEATURES AVAILABLE:")
print("=" * 70)

for i, item in enumerate(items, 1):
    print(f"\nItem {i} ({item['data_type']}) will show:")
    
    features = []
    if item['data_type'] == 'image' and item.get('download_url'):
        features.append("✅ Image preview")
    elif item['data_type'] == 'audio' and item.get('download_url'):
        features.append("✅ Audio player")
    elif item['data_type'] == 'video' and item.get('download_url'):
        features.append("✅ Video player")
    else:
        features.append("ℹ️  No media preview (text or no file)")
    
    if item.get('content'):
        features.append("✅ Content text box")
    if item.get('source_url'):
        features.append("✅ Source URL link")
    if item.get('download_url'):
        features.append("✅ Download button")
    if item.get('labels') and len(item['labels']) > 0:
        features.append(f"✅ {len(item['labels'])} label(s)")
    if item.get('metadata') and len(item['metadata']) > 0:
        features.append(f"✅ Metadata ({len(item['metadata'])} fields)")
    
    features.append(f"✅ Quality: {item.get('quality_score', 'N/A')}")
    features.append(f"✅ Type: {item['data_type']}")
    features.append(f"✅ Created: {item.get('created_at', 'N/A')[:10]}")
    
    for feature in features:
        print(f"   {feature}")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. Go to http://localhost:3899/dashboard/data")
print("2. Select the project from dropdown")
print("3. Click the eye icon (👁️) on any item")
print("4. The modal should show all the features listed above")
print("\nModal Controls:")
print("• Click X button to close")
print("• Press ESC key to close")
print("• Click outside the modal to close")
print("=" * 70)

