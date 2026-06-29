"""Test and validate export formats against standards."""
import os
import json
import io
import csv
import tempfile
import zipfile

os.environ["NO_PROXY"] = "*"

def test_jsonl_format(data: bytes) -> dict:
    """Validate JSONL format."""
    issues = []
    lines = data.decode('utf-8').strip().split('\n')
    
    if not lines:
        issues.append("Empty JSONL file")
        return {"valid": False, "issues": issues}
    
    required_fields = ['id', 'type']
    
    for i, line in enumerate(lines):
        try:
            record = json.loads(line)
            
            # Check required fields
            for field in required_fields:
                if field not in record:
                    issues.append(f"Line {i+1}: Missing required field '{field}'")
            
            # Validate id is string
            if 'id' in record and not isinstance(record['id'], str):
                issues.append(f"Line {i+1}: 'id' should be string")
            
            # Validate labels is array
            if 'labels' in record and not isinstance(record['labels'], list):
                issues.append(f"Line {i+1}: 'labels' should be array")
                
        except json.JSONDecodeError as e:
            issues.append(f"Line {i+1}: Invalid JSON - {e}")
    
    return {
        "valid": len(issues) == 0,
        "record_count": len(lines),
        "issues": issues[:5]  # Limit issues
    }


def test_csv_format(data: bytes) -> dict:
    """Validate CSV format."""
    issues = []
    
    try:
        content = data.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        rows = list(reader)
        if not rows:
            issues.append("Empty CSV file")
            return {"valid": False, "issues": issues}
        
        # Check headers
        expected_headers = ['id', 'type', 'content']
        for header in expected_headers:
            if header not in reader.fieldnames:
                issues.append(f"Missing expected header: {header}")
        
        # Validate rows
        for i, row in enumerate(rows):
            if not row.get('id'):
                issues.append(f"Row {i+1}: Missing 'id'")
        
        return {
            "valid": len(issues) == 0,
            "record_count": len(rows),
            "headers": list(reader.fieldnames),
            "issues": issues[:5]
        }
    except Exception as e:
        return {"valid": False, "issues": [str(e)]}


def test_coco_format(data: bytes) -> dict:
    """Validate COCO JSON format against official spec."""
    issues = []
    
    try:
        coco = json.loads(data.decode('utf-8'))
        
        # Required top-level keys
        required_keys = ['info', 'images', 'annotations', 'categories']
        for key in required_keys:
            if key not in coco:
                issues.append(f"Missing required key: {key}")
        
        # Validate info section
        if 'info' in coco:
            info_fields = ['description', 'version', 'year']
            for field in info_fields:
                if field not in coco['info']:
                    issues.append(f"info.{field} is missing (recommended)")
        
        # Validate images
        if 'images' in coco:
            for i, img in enumerate(coco['images']):
                if 'id' not in img:
                    issues.append(f"Image {i}: Missing 'id'")
                if 'file_name' not in img:
                    issues.append(f"Image {i}: Missing 'file_name'")
                # width and height are required in COCO
                if 'width' not in img or 'height' not in img:
                    issues.append(f"Image {i}: Missing 'width' or 'height' (required by COCO)")
        
        # Validate categories
        if 'categories' in coco:
            for i, cat in enumerate(coco['categories']):
                if 'id' not in cat:
                    issues.append(f"Category {i}: Missing 'id'")
                if 'name' not in cat:
                    issues.append(f"Category {i}: Missing 'name'")
        
        # Validate annotations
        if 'annotations' in coco:
            for i, ann in enumerate(coco['annotations'][:10]):  # Check first 10
                if 'id' not in ann:
                    issues.append(f"Annotation {i}: Missing 'id'")
                if 'image_id' not in ann:
                    issues.append(f"Annotation {i}: Missing 'image_id'")
                if 'category_id' not in ann:
                    issues.append(f"Annotation {i}: Missing 'category_id'")
        
        return {
            "valid": len(issues) == 0,
            "images_count": len(coco.get('images', [])),
            "annotations_count": len(coco.get('annotations', [])),
            "categories_count": len(coco.get('categories', [])),
            "issues": issues[:10]
        }
    except Exception as e:
        return {"valid": False, "issues": [str(e)]}


def test_huggingface_format(data: bytes) -> dict:
    """Validate HuggingFace Datasets format."""
    issues = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = zf.namelist()
            
            # Check required files
            required_files = ['dataset_info.json']
            for req in required_files:
                if req not in files:
                    issues.append(f"Missing required file: {req}")
            
            # Check for data file
            data_files = [f for f in files if f.endswith('.jsonl') or f.endswith('.arrow') or f.endswith('.parquet')]
            if not data_files:
                issues.append("No data file found (expected .jsonl, .arrow, or .parquet)")
            
            # Validate dataset_info.json
            if 'dataset_info.json' in files:
                with zf.open('dataset_info.json') as f:
                    info = json.load(f)
                    
                    if 'features' not in info:
                        issues.append("dataset_info.json: Missing 'features'")
                    if 'splits' not in info:
                        issues.append("dataset_info.json: Missing 'splits'")
                    
                    # Check feature types
                    if 'features' in info:
                        for name, feat in info['features'].items():
                            if '_type' not in feat and 'dtype' not in feat:
                                issues.append(f"Feature '{name}': Missing type information")
            
            # Check README
            if 'README.md' not in files:
                issues.append("Missing README.md (recommended for HuggingFace Hub)")
            
            return {
                "valid": len(issues) == 0,
                "files": files,
                "issues": issues
            }
    except Exception as e:
        return {"valid": False, "issues": [str(e)]}


def main():
    print("=" * 60)
    print("EXPORT FORMAT VALIDATION TEST")
    print("=" * 60)
    
    import requests
    
    # Login
    response = requests.post(
        "http://127.0.0.1:8099/api/auth/login",
        json={"email": "llvllr.reza@gmail.com", "password": "B4u774me"}
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get a project with data
    projects = requests.get("http://127.0.0.1:8099/api/projects", headers=headers).json()
    
    if not projects:
        print("No projects found!")
        return
    
    # Find a project with items
    project_id = None
    for p in projects:
        items = requests.get(
            f"http://127.0.0.1:8099/api/data?project_id={p['id']}&limit=1",
            headers=headers
        ).json()
        
        item_count = items.get('total', len(items.get('items', items))) if isinstance(items, dict) else len(items)
        if item_count > 0:
            project_id = p['id']
            print(f"Using project: {p['name']} ({item_count} items)")
            break
    
    if not project_id:
        print("No project with data found!")
        return
    
    # Test each export format
    formats_to_test = ['jsonl', 'csv', 'coco', 'huggingface']
    
    results = {}
    
    for fmt in formats_to_test:
        print(f"\n{'='*40}")
        print(f"Testing {fmt.upper()} format")
        print('='*40)
        
        # Create export
        response = requests.post(
            "http://127.0.0.1:8099/api/exports",
            json={
                "project_id": project_id,
                "name": f"Test Export - {fmt}",
                "format": fmt,
                "filters": {"limit": 10}
            },
            headers=headers
        )
        
        if response.status_code != 201:
            print(f"  Failed to create export: {response.text}")
            results[fmt] = {"valid": False, "error": "Failed to create"}
            continue
        
        export = response.json()
        export_id = export["id"]
        
        # Wait for export to complete
        import time
        for _ in range(30):
            time.sleep(1)
            status = requests.get(
                f"http://127.0.0.1:8099/api/exports/{export_id}",
                headers=headers
            ).json()
            
            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                print(f"  Export failed: {status.get('error_message')}")
                results[fmt] = {"valid": False, "error": status.get('error_message')}
                break
        else:
            print("  Export timeout")
            results[fmt] = {"valid": False, "error": "Timeout"}
            continue
        
        if status["status"] != "completed":
            continue
        
        # Download and validate
        response = requests.get(
            f"http://127.0.0.1:8099/api/exports/{export_id}/download",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"  Failed to download: {response.text}")
            continue
        
        data = response.content
        
        # Validate format
        if fmt == 'jsonl':
            result = test_jsonl_format(data)
        elif fmt == 'csv':
            result = test_csv_format(data)
        elif fmt == 'coco':
            result = test_coco_format(data)
        elif fmt == 'huggingface':
            result = test_huggingface_format(data)
        else:
            result = {"valid": True, "note": "Format not validated"}
        
        results[fmt] = result
        
        # Print results
        if result["valid"]:
            print(f"  ✅ VALID")
        else:
            print(f"  ❌ ISSUES FOUND")
        
        for key, value in result.items():
            if key != 'valid':
                print(f"    {key}: {value}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for fmt, result in results.items():
        status = "✅" if result.get("valid") else "❌"
        print(f"{status} {fmt.upper()}: {'Valid' if result.get('valid') else 'Has Issues'}")
        if not result.get("valid") and result.get("issues"):
            for issue in result["issues"][:3]:
                print(f"     - {issue}")


if __name__ == "__main__":
    main()

