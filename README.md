# AI Data Collector

Enterprise platform for web scraping and data collection for AI model training.

## Features

### 🌐 Data Collection
- **Multi-Source Collection**: Scrape from Google, Twitter, Reddit, YouTube, and custom websites
- **Multiple Data Types**: Text, images, audio, video, and structured data
- **Job Scheduling**: Cron-based scheduling with retry mechanisms
- **Real-time Monitoring**: WebSocket-based live updates

### 🤖 ML Dataset Management (NEW!)
- **Dataset Splitting**: Automatic train/validation/test splitting with stratification
- **Annotation Studio**: Multi-modal annotation (BBox, NER, Classification, Polygon, Keypoints)
- **Data Augmentation**: Text & Image augmentation with configurable rules
- **Versioning**: Track dataset evolution with full version history
- **Similarity Search**: Find duplicates and similar items using embeddings
- **Active Learning**: Smart suggestions for optimal labeling
- **Dataset Cards**: HuggingFace-compatible dataset documentation

### 📤 Export
- **AI-Ready Exports**: JSONL, CSV, Parquet, TFRecord, HuggingFace, COCO formats
- **Incremental Export**: Export only changes since last export
- **Stratified Sampling**: Maintain class distribution in samples
- **Split Filtering**: Export specific splits (train/val/test)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, SQLAlchemy |
| Queue | Celery, Redis |
| Database | PostgreSQL 15 |
| Storage | MinIO (S3-compatible) |
| Scraping | Playwright, httpx, BeautifulSoup |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Development Setup

1. **Clone and setup environment**:
```bash
cp env.example .env
```

2. **Start infrastructure services**:
```bash
docker-compose up -d postgres redis minio
```

3. **Setup Backend**:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8099
```

4. **Start Celery Worker** (new terminal):
```bash
cd backend
.\venv\Scripts\activate
celery -A app.workers.celery_app worker --loglevel=info
```

5. **Setup Frontend**:
```bash
cd frontend
npm install
npm run dev -- -p 3899
```

6. **Access the application**:
- Frontend: http://localhost:3899
- Backend API: http://localhost:8099
- API Docs: http://localhost:8099/docs
- MinIO Console: http://localhost:9001

### Docker Deployment

```bash
docker-compose up -d
```

## Project Structure

```
ai-data-collector/
├── frontend/                    # Next.js App
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   └── dashboard/
│   │   │       └── dataset/     # ML Dataset pages (NEW)
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   └── lib/                 # Utilities & API client
│   └── package.json
│
├── backend/                     # FastAPI Server
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   └── dataset.py       # Dataset management API (NEW)
│   │   ├── core/                # Config, security, storage
│   │   ├── models/              # SQLAlchemy models
│   │   │   └── dataset.py       # Version, Card, Annotation models (NEW)
│   │   ├── schemas/             # Pydantic schemas
│   │   │   └── dataset.py       # Dataset schemas (NEW)
│   │   ├── services/            # Business logic
│   │   │   ├── augmentation_service.py  # Data augmentation (NEW)
│   │   │   └── embedding_service.py     # Embeddings & similarity (NEW)
│   │   ├── scrapers/            # Scraper implementations
│   │   └── workers/             # Celery tasks
│   └── requirements.txt
│
├── docs/                        # Documentation (NEW)
│   ├── ML_FEATURES_GUIDE.md     # Persian guide
│   └── ML_FEATURES_GUIDE_EN.md  # English guide
│
├── docker-compose.yml
└── README.md
```

## API Providers

| Provider | Description | Data Types |
|----------|-------------|------------|
| SerpAPI | Google, Bing, YouTube search | Text, Image, Video |
| Apify | Pre-built web scrapers | All |
| Custom | Playwright-based scraping | Text, Image |
| Twitter | Tweets and media | Text, Image, Video |
| Reddit | Posts and comments | Text, Image, Video |

## Environment Variables

```env
# Database
POSTGRES_USER=collector
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ai_collector

# JWT
SECRET_KEY=your-secret-key

# API Keys (optional)
SERPAPI_KEY=
APIFY_TOKEN=
TWITTER_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
```

## Export Formats

- **JSONL**: JSON Lines for LLM training (OpenAI, Anthropic)
- **CSV**: General purpose, spreadsheet compatible
- **Parquet**: Columnar format for big data processing
- **HuggingFace**: Datasets library compatible
- **COCO**: Computer vision annotation format

## Documentation

### ML Features Guide
For comprehensive documentation on ML dataset features:
- 📖 [Persian/Farsi Guide](docs/ML_FEATURES_GUIDE.md)
- 📖 [English Guide](docs/ML_FEATURES_GUIDE_EN.md)

### Quick Links
| Feature | Description |
|---------|-------------|
| [Dataset Dashboard](/dashboard/dataset) | Overview & statistics |
| [Annotation Studio](/dashboard/dataset/annotations) | Multi-modal annotation |
| [Data Augmentation](/dashboard/dataset/augmentation) | Augmentation rules |
| [API Docs](http://localhost:8099/docs) | Full API reference |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

