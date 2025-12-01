# City Vibe ETL

ETL pipeline package for processing and enriching events. This package contains the core business logic for transforming raw scraped data into normalized, validated, deduplicated, and enriched events.

## Structure

```
cityvibe-etl/
├── event_processor.py    # Main orchestrator
├── validator.py          # Data validation
├── deduplicator.py       # Deduplication logic
└── enricher.py          # Data enrichment
```

## Pipeline Stages

1. **Normalization** - Convert raw scraped data to standardized format
2. **Validation** - Validate required fields and data quality
3. **Deduplication** - Remove duplicate events using fuzzy matching
4. **Enrichment** - Add geocoding, tags, embeddings

## Usage

```python
from cityvibe_etl.event_processor import EventProcessor

processor = EventProcessor()
result = await processor.process(raw_events)
```

## Dependencies

- `cityvibe-core` - Domain models and database access
- `cityvibe-common` - Shared utilities (geocoding, embeddings, etc.)

## Benefits

- **Reusable**: Can be used by workers, API endpoints, or other services
- **Testable**: Pure business logic, no Celery dependencies
- **Maintainable**: Clear separation of concerns
- **Scalable**: Can be used in different execution contexts
