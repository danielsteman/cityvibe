# Workers Service

Celery workers for scraping venues and processing events through the ETL pipeline.

## Overview

The workers service is responsible for:

- **Scraping**: Fetching event data from venue websites
- **Task Orchestration**: Managing Celery tasks for scraping and ETL processing
- **Delegation**: Delegating ETL processing to the `cityvibe-etl` package

**Key Design**: Workers are kept lean by delegating core ETL logic to the `cityvibe-etl` package, which can be reused across services.

## Structure

```
services/workers/
├── src/
│   └── workers/
│       ├── __init__.py
│       ├── main.py              # Celery app initialization
│       │
│       └── tasks/               # Celery task definitions
│           ├── scraping/        # Scraping tasks
│           └── etl/             # ETL task wrappers
│               └── process_events.py
└── pyproject.toml
```

**Note**: ETL pipeline logic lives in `packages/cityvibe-etl/` for reusability and separation of concerns.

## Dependencies

- **`cityvibe-core`**: Domain models and database access
- **`cityvibe-common`**: Shared utilities (geocoding, embeddings, etc.)
- **`cityvibe-etl`**: ETL pipeline processors (validation, deduplication, enrichment)
- **Celery**: Task queue framework
- **Scrapy/Playwright**: Web scraping frameworks

## ETL Pipeline Integration

Workers use the `cityvibe-etl` package for processing events. The ETL pipeline (located in `packages/cityvibe-etl/`) processes raw scraped events through these stages:

1. **Normalization** - Convert raw scraped data to standardized format
2. **Validation** - Validate required fields and data quality
3. **Deduplication** - Remove duplicate events using fuzzy matching
4. **Enrichment** - Add geocoding, tags, embeddings

See [`packages/cityvibe-etl/README.md`](../../packages/cityvibe-etl/README.md) for detailed ETL pipeline documentation.

## Usage

### Running Workers

```bash
cd services/workers
uv run celery -A workers.main worker --loglevel=info
```

### Running ETL Task

```python
from workers.tasks.etl.process_events import process_events_task

# Process events from a scrape
# This is a thin wrapper that delegates to cityvibe_etl.EventProcessor
result = process_events_task.delay(venue_id="...", raw_events=[...])
```

### Direct ETL Usage (for testing/debugging)

You can also use the ETL package directly without Celery:

```python
from cityvibe_etl import EventProcessor

processor = EventProcessor()
result = await processor.process(raw_events)
```

## Development

### Architecture Principles

- **Separation of Concerns**: Workers handle task orchestration; ETL handles business logic
- **Reusability**: ETL package can be used by API endpoints, admin tools, or batch jobs
- **Testability**: ETL logic can be tested independently without Celery

### Components

- **Tasks** (`tasks/`) - Thin Celery task wrappers that delegate to the ETL package
- **Scrapers** (`scrapers/`) - Venue-specific scraping implementations
- **ETL Logic** - Lives in `packages/cityvibe-etl/` for reusability across services

### Adding a New Website Source

When adding a new website source (venue website):

1. **Create scraper** in `scrapers/`:

   ```python
   # services/workers/src/workers/scrapers/venue_name_scraper.py
   from workers.scrapers.base import BaseScraper

   class VenueNameScraper(BaseScraper):
       async def scrape(self) -> list[dict]:
           # Extract events from website
           # Return raw event dictionaries
           return raw_events
   ```

2. **Create scraping task** in `tasks/scraping/`:

   ```python
   # services/workers/src/workers/tasks/scraping/scrape_venue.py
   @task
   async def scrape_venue_task(venue_id: str):
       scraper = VenueNameScraper(venue)
       raw_events = await scraper.scrape()
       # Process through ETL
       await process_events_task.delay(venue_id, raw_events)
   ```

3. **Register task** in `main.py` (when implemented)

4. **ETL processing** happens automatically via `cityvibe-etl` package

See `docs/SOURCE_INTEGRATION.md` for detailed examples.

### Adding a New ETL Step

ETL steps should be added to `packages/cityvibe-etl/`, not in workers. Workers will automatically benefit from ETL improvements.

## Workflow

```
1. Scheduler triggers scrape task
   ↓
2. Worker picks up task, runs scraper
   ↓
3. Scraper returns raw events
   ↓
4. Worker calls ETL task with raw events
   ↓
5. ETL task delegates to cityvibe-etl.EventProcessor
   ↓
6. ETL pipeline processes events (normalize → validate → dedupe → enrich)
   ↓
7. Processed events saved to database
```
