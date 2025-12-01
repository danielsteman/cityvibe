# City Vibe - Technical Architecture

## Overview

City Vibe aggregates event and activity data from multiple sources, normalizes it, and exposes it via an MCP server for LLM querying. The architecture separates data collection, processing, storage, and querying concerns.

## System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Data Sources   │────▶│   Scrapers   │────▶│   ETL       │────▶│   Storage    │
│  (Venue Sites)  │     │   (Workers)  │     │   Pipeline  │     │   Layer      │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                                                    │                   │
                                                    ▼                   ▼
                                             ┌─────────────┐     ┌──────────────┐
                                             │  Dedupe &   │     │   MCP Server │
                                             │  Validation │     │   (Query)    │
                                             └─────────────┘     └──────────────┘
                                                                        │
                                                                        ▼
                                                                 ┌──────────────┐
                                                                 │     LLM      │
                                                                 │   (Client)   │
                                                                 └──────────────┘
```

## Technology Stack

### Core Services

- **Language**: Python 3.11+ (excellent scraping/ML ecosystem)
- **Scraping Framework**:
  - **Scrapy** for structured scraping (sitemaps, RSS feeds)
  - **Playwright** for JavaScript-heavy sites
  - **BeautifulSoup4** for simple HTML parsing
- **Job Queue**: **Celery** with **Redis** broker (or **BullMQ** if Node.js preferred)
- **Database**: **PostgreSQL 15+** (structured event data, full-text search)
- **Vector DB**: **Qdrant** or **Weaviate** (semantic search, embeddings)
- **Cache**: **Redis** (frequently accessed data, rate limiting)
- **Object Storage**: **S3-compatible** (MinIO for dev, AWS S3 for prod)

### MCP & API Layer

- **MCP Server**: Python with `mcp` SDK
- **API Framework**: **FastAPI** (async, OpenAPI docs, type hints)
- **Embeddings**: **OpenAI** or **Ollama** (local) for semantic search

### Infrastructure

- **Containerization**: Docker + Docker Compose (dev), Kubernetes (prod)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logs (Loki or CloudWatch)
- **Error Tracking**: Sentry
- **CI/CD**: GitHub Actions

## Data Model

### Core Schema (PostgreSQL)

```sql
-- Venues/Sources
CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL UNIQUE,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50),
    country VARCHAR(50) NOT NULL DEFAULT 'US',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    venue_type VARCHAR(50), -- 'theater', 'museum', 'concert_hall', etc.
    scraper_config JSONB, -- source-specific scraping rules
    active BOOLEAN DEFAULT true,
    last_scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_venues_city ON venues(city);
CREATE INDEX idx_venues_location ON venues USING GIST(
    ll_to_earth(latitude, longitude)
);

-- Events/Activities
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id UUID REFERENCES venues(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    event_type VARCHAR(50), -- 'concert', 'theater', 'museum_exhibit', etc.

    -- Temporal
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    is_recurring BOOLEAN DEFAULT false,
    recurrence_pattern JSONB, -- for recurring events

    -- Location (may differ from venue)
    location_name VARCHAR(255),
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),

    -- Pricing
    price_min DECIMAL(10, 2),
    price_max DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    ticket_url TEXT,

    -- Metadata
    image_urls TEXT[],
    tags TEXT[], -- ['jazz', 'outdoor', 'family-friendly']
    age_restriction VARCHAR(50),

    -- Source tracking
    source_url TEXT NOT NULL,
    source_id VARCHAR(255), -- external ID from source
    raw_data JSONB, -- original scraped data

    -- Data quality
    confidence_score DECIMAL(3, 2), -- 0.00-1.00, data extraction confidence
    verified BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ -- auto-cleanup after event ends
);

CREATE INDEX idx_events_start_time ON events(start_time);
CREATE INDEX idx_events_city ON events USING GIN(tags);
CREATE INDEX idx_events_location ON events USING GIST(
    ll_to_earth(latitude, longitude)
);
CREATE INDEX idx_events_source ON events(venue_id, source_id);
CREATE INDEX idx_events_fulltext ON events USING GIN(
    to_tsvector('english', title || ' ' || COALESCE(description, ''))
);

-- Deduplication tracking
CREATE TABLE event_dedupe_signatures (
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    signature_hash BYTEA NOT NULL, -- hash of normalized fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (event_id, signature_hash)
);

-- Scraping jobs
CREATE TABLE scrape_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id UUID REFERENCES venues(id),
    status VARCHAR(20) NOT NULL, -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    events_found INTEGER DEFAULT 0,
    events_new INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Vector Embeddings (Qdrant/Weaviate)

Store embeddings for semantic search:

- Collection: `events_embeddings`
- Vector dimension: 1536 (OpenAI) or 384 (sentence-transformers)
- Payload: event_id, title, description, tags, event_type
- Index: HNSW for fast approximate nearest neighbor search

## Component Details

### 1. Scraping Layer

**Architecture Pattern**: Worker pool with job queue

```python
# scraper/workers/base.py
class BaseScraper:
    """Abstract base scraper with common functionality"""

    def __init__(self, venue: Venue):
        self.venue = venue
        self.rate_limiter = RateLimiter(venue.website_url)

    async def scrape(self) -> List[RawEvent]:
        """Fetch and parse events from venue website"""
        raise NotImplementedError

    def normalize_event(self, raw: RawEvent) -> Event:
        """Convert raw scraped data to normalized Event model"""
        # Common normalization logic
        pass

# scraper/workers/theater_scraper.py
class TheaterScraper(BaseScraper):
    """Venue-specific scraper implementation"""
    async def scrape(self) -> List[RawEvent]:
        # Playwright for JS-heavy sites
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(self.venue.website_url)
            # Extract events
            return events
```

**Key Features**:

- **Rate Limiting**: Per-domain rate limits, respect robots.txt
- **Retry Logic**: Exponential backoff with jitter
- **Error Handling**: Graceful degradation, error tracking
- **Configurable**: Per-venue scraping rules (selectors, patterns) stored in DB
- **Headless Browsers**: Playwright for JS-heavy sites, Scrapy for static HTML

**Job Scheduling**:

- **High-frequency venues**: Every 6 hours (concerts, theater)
- **Low-frequency venues**: Daily (museums, permanent exhibits)
- **On-demand**: Manual trigger via admin API

### 2. ETL Pipeline

**Responsibilities**:

1. **Deduplication**: Fuzzy matching on title + date + location
2. **Data Validation**: Required fields, date sanity checks
3. **Enrichment**: Geocoding addresses, extracting tags
4. **Normalization**: Standardize formats (dates, prices, categories)

```python
# etl/processor.py
class EventProcessor:
    def __init__(self):
        self.deduper = EventDeduplicator()
        self.geocoder = GeocodingService()
        self.validator = EventValidator()

    async def process(self, raw_events: List[RawEvent]) -> ProcessedBatch:
        """Process batch of raw events"""
        normalized = [self.normalize(e) for e in raw_events]
        validated = [e for e in normalized if self.validator.validate(e)]
        deduped = await self.deduper.deduplicate(validated)
        enriched = await self.enrich(deduped)
        return ProcessedBatch(enriched)

    async def enrich(self, events: List[Event]) -> List[Event]:
        """Add geocoding, tags, embeddings"""
        for event in events:
            if event.address and not event.latitude:
                coords = await self.geocoder.geocode(event.address)
                event.latitude, event.longitude = coords

            if not event.tags:
                event.tags = await self.extract_tags(event)

        return events
```

**Deduplication Strategy**:

- **Exact match**: Same title + same start_time + same venue
- **Fuzzy match**: Similar title (Levenshtein distance) + overlapping time window
- **Signature hashing**: Hash of normalized fields for fast lookup

### 3. Storage Layer

**PostgreSQL**:

- Primary source of truth for structured data
- Full-text search with `tsvector`
- PostGIS extension for geospatial queries
- Partitioning by date for events table (auto-cleanup old events)

**Vector DB (Qdrant/Weaviate)**:

- Store embeddings for semantic search
- Sync on event create/update
- Query by semantic similarity + filters

**Redis**:

- Cache frequently accessed queries (TTL: 5-15 minutes)
- Rate limiting tokens
- Job queue state

**S3**:

- Raw HTML snapshots (for debugging)
- Event images (mirrored from sources)
- Scraper logs

### 4. MCP Server

**Tool Definitions**:

```python
# mcp_server/tools.py
@mcp_tool()
async def search_events(
    query: str,
    city: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 20
) -> List[Event]:
    """
    Search for events matching natural language query.

    Uses hybrid search: semantic (vector) + keyword (full-text) + filters
    """
    # 1. Generate query embedding
    query_embedding = await embedding_service.embed(query)

    # 2. Vector search in Qdrant
    vector_results = await vector_db.search(
        query_vector=query_embedding,
        filter={
            "city": city,
            "start_time": {"gte": start_date},
            "event_type": event_type
        },
        limit=limit
    )

    # 3. Full-text search in PostgreSQL
    text_results = await db.search_events(
        query=query,
        city=city,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        max_price=max_price,
        limit=limit
    )

    # 4. Merge and rerank
    return merge_and_rerank(vector_results, text_results)

@mcp_tool()
async def get_event_details(event_id: str) -> Event:
    """Get detailed information about a specific event"""
    return await db.get_event(event_id)

@mcp_tool()
async def find_nearby_events(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    start_date: Optional[datetime] = None
) -> List[Event]:
    """Find events within radius of a location"""
    return await db.find_events_nearby(
        lat=latitude,
        lon=longitude,
        radius_km=radius_km,
        start_date=start_date
    )

@mcp_tool()
async def get_venue_events(
    venue_id: str,
    start_date: Optional[datetime] = None
) -> List[Event]:
    """Get all events for a specific venue"""
    return await db.get_venue_events(venue_id, start_date)
```

**MCP Server Implementation**:

```python
# mcp_server/server.py
from mcp import Server
from mcp.types import Tool

app = Server("cityvibe")

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="search_events",
            description="Search for events and activities using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "city": {"type": "string"},
                    # ... other params
                }
            }
        ),
        # ... other tools
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_events":
        return await search_events(**arguments)
    # ... handle other tools
```

### 5. API Layer (Optional)

FastAPI REST API for direct access (non-LLM clients):

```python
# api/routes/events.py
@router.get("/events/search")
async def search_events(
    q: str,
    city: Optional[str] = None,
    start_date: Optional[datetime] = None,
    # ... other filters
):
    """REST endpoint mirroring MCP tool functionality"""
    return await search_events_tool(
        query=q,
        city=city,
        start_date=start_date
    )
```

## Data Flow

### Scraping Flow

1. **Scheduler** (Celery Beat) triggers scrape job for venue
2. **Worker** picks up job, instantiates appropriate scraper
3. **Scraper** fetches and parses venue website → `List[RawEvent]`
4. **ETL Processor** normalizes, validates, deduplicates → `List[Event]`
5. **Database Writer** upserts events to PostgreSQL
6. **Embedding Service** generates embeddings, stores in vector DB
7. **Job Status** updated in `scrape_jobs` table

### Query Flow (MCP)

1. **LLM** calls MCP tool (e.g., `search_events`)
2. **MCP Server** receives tool call with parameters
3. **Hybrid Search**:
   - Generate query embedding
   - Vector search in Qdrant
   - Full-text search in PostgreSQL
   - Merge and rerank results
4. **Return** structured event data to LLM
5. **LLM** formats response for user

## Scalability Considerations

### Horizontal Scaling

- **Scrapers**: Stateless workers, scale based on queue depth
- **API/MCP**: Stateless, scale behind load balancer
- **Database**: Read replicas for query load, connection pooling

### Performance Optimizations

- **Caching**: Redis cache for common queries (5-15 min TTL)
- **Batch Processing**: Process events in batches, not one-by-one
- **Async Everything**: Use async/await throughout (FastAPI, asyncpg, etc.)
- **Database Indexing**: Strategic indexes on common query patterns
- **Vector Search**: Approximate nearest neighbor (HNSW) for speed

### Data Volume Estimates

- **Events per city**: ~1,000-10,000 active events
- **100 cities**: ~100K-1M events total
- **Storage**: ~50-100 bytes per event → ~50-100 MB (excluding images)
- **Scraping frequency**: ~1M requests/month (manageable with rate limiting)

## Monitoring & Observability

### Metrics (Prometheus)

- Scraping success/failure rates per venue
- Events discovered per scrape
- Query latency (p50, p95, p99)
- Database query performance
- Vector search latency
- Cache hit rates

### Logging

- Structured JSON logs
- Scraper execution logs (with raw HTML snapshots on failure)
- MCP tool call logs (for debugging LLM interactions)
- Error tracking (Sentry)

### Alerts

- Scraper failure rate > 10%
- Database connection pool exhaustion
- Vector DB unavailability
- High query latency (>1s p95)

## Deployment

### Development

```bash
docker-compose up  # PostgreSQL, Redis, Qdrant, workers, API
```

### Production

- **Kubernetes** with:
  - Deployment for API/MCP server
  - Deployment for Celery workers (auto-scaling)
  - StatefulSet for PostgreSQL (or managed DB)
  - Deployment for Qdrant
  - ConfigMaps for scraper configs
  - Secrets for API keys

### CI/CD

- GitHub Actions:
  - Run tests (unit, integration)
  - Build Docker images
  - Deploy to staging/production
  - Run database migrations

## Security Considerations

- **Rate Limiting**: Per-IP, per-API-key limits
- **Input Validation**: Sanitize all LLM-provided inputs
- **SQL Injection**: Use parameterized queries (SQLAlchemy/asyncpg)
- **Secrets Management**: Use Kubernetes secrets or AWS Secrets Manager
- **Network Security**: Private subnets, VPC for database access
- **Scraping Ethics**: Respect robots.txt, reasonable rate limits, user-agent headers

## Future Enhancements

1. **User Preferences**: Learn from LLM queries to improve ranking
2. **Event Recommendations**: Collaborative filtering
3. **Real-time Updates**: WebSocket for live event updates
4. **Multi-language**: Support queries in multiple languages
5. **Image Analysis**: Extract event info from flyers/posters
6. **Social Signals**: Aggregate social media mentions for popularity

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis
- Docker & Docker Compose

### Setup

```bash
# Clone and setup
git clone <repo>
cd cityvibe
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database setup
alembic upgrade head

# Start services
docker-compose up -d postgres redis qdrant

# Run workers
celery -A scraper.workers worker --loglevel=info

# Start MCP server
python -m mcp_server.main

# Start API (optional)
uvicorn api.main:app --reload
```
