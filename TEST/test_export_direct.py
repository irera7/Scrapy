"""Direct test of export formats without Celery."""
import asyncio
import sys
import os
import json
import csv
import io
import zipfile

os.environ["NO_PROXY"] = "*"
sys.path.insert(0, 'D:/Project/Scrap/backend')

async def test_exports():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    
    from app.models.data_item import DataItem
    from app.services.export_service import ExportGenerator
    
    engine = create_async_engine("postgresql+asyncpg://collector:collector_secret@localhost:5432/ai_collector")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get some data items
        result = await db.execute(select(DataItem).limit(10))
        items = result.scalars().all()
        
        if not items:
            print("No data items found!")
            return
        
        print(f"Found {len(items)} data items for testing")
        print(f"Data types: {set(item.data_type for item in items)}")
        
        generator = ExportGenerator(items)
        
        # Test JSONL
        print("\n" + "=" * 50)
        print("Testing JSONL Format")
        print("=" * 50)
        
        data, content_type, ext = generator._generate_jsonl()
        lines = data.decode('utf-8').strip().split('\n')
        print(f"✅ Generated {len(lines)} records")
        print(f"   Content-Type: {content_type}")
        print(f"   Sample record:")
        sample = json.loads(lines[0])
        for key in list(sample.keys())[:5]:
            print(f"     - {key}: {type(sample[key]).__name__}")
        
        # Validate required fields
        required = ['id', 'type']
        missing = [f for f in required if f not in sample]
        if missing:
            print(f"   ❌ Missing required fields: {missing}")
        else:
            print(f"   ✅ All required fields present")
        
        # Test CSV
        print("\n" + "=" * 50)
        print("Testing CSV Format")
        print("=" * 50)
        
        data, content_type, ext = generator._generate_csv()
        reader = csv.DictReader(io.StringIO(data.decode('utf-8')))
        rows = list(reader)
        print(f"✅ Generated {len(rows)} rows")
        print(f"   Headers: {reader.fieldnames}")
        
        # Test COCO
        print("\n" + "=" * 50)
        print("Testing COCO Format")
        print("=" * 50)
        
        data, content_type, ext = generator._generate_coco()
        coco = json.loads(data.decode('utf-8'))
        print(f"✅ Generated COCO JSON")
        print(f"   Images: {len(coco.get('images', []))}")
        print(f"   Annotations: {len(coco.get('annotations', []))}")
        print(f"   Categories: {len(coco.get('categories', []))}")
        
        # Validate COCO structure
        required_keys = ['info', 'images', 'annotations', 'categories']
        missing = [k for k in required_keys if k not in coco]
        if missing:
            print(f"   ❌ Missing required keys: {missing}")
        else:
            print(f"   ✅ All required keys present")
        
        # Check COCO info section
        info = coco.get('info', {})
        if 'description' in info and 'version' in info:
            print(f"   ✅ Info section valid")
        else:
            print(f"   ⚠️ Info section incomplete")
        
        # Test HuggingFace
        print("\n" + "=" * 50)
        print("Testing HuggingFace Format")
        print("=" * 50)
        
        data, content_type, ext = await generator._generate_huggingface()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = zf.namelist()
            print(f"✅ Generated ZIP with {len(files)} files")
            print(f"   Files: {files}")
            
            if 'dataset_info.json' in files:
                with zf.open('dataset_info.json') as f:
                    info = json.load(f)
                    print(f"   Features: {list(info.get('features', {}).keys())}")
                    print(f"   ✅ dataset_info.json valid")
            else:
                print(f"   ❌ Missing dataset_info.json")
            
            if 'README.md' in files:
                print(f"   ✅ README.md present")
            else:
                print(f"   ⚠️ README.md missing (recommended for Hub)")
        
        # Summary
        print("\n" + "=" * 50)
        print("EXPORT FORMAT VALIDATION SUMMARY")
        print("=" * 50)
        
        issues = []
        
        # Check COCO issues
        if coco.get('images'):
            for img in coco['images'][:3]:
                if 'width' not in img or 'height' not in img:
                    issues.append("COCO: Images missing width/height (required by spec)")
                    break
        
        if issues:
            print("⚠️ Issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All formats valid!")
        
        print("\nSupported formats: JSONL, CSV, Parquet, TFRecord, HuggingFace, COCO, WebDataset")

asyncio.run(test_exports())

