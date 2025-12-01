# Adding a New Data Source

This guide explains where to add code when integrating a new data source into City Vibe.

## Understanding the Flow

```
New Source → Scraper → Raw Events → ETL Pipeline → Normalized Events → Database
```

## Where to Add Code Based on Source Type

### Scenario 1: New Venue Website (Same Format)

**If the new source is similar to existing sources** (e.g., another theater website):

**Location**: `services/workers/src/workers/scrapers/`

**Steps**:

1. Create a new scraper file: `services/workers/src/workers/scrapers/venue_name_scraper.py`
2. Inherit from `BaseScraper`
3. Implement the `scrape()` method
4. Return raw events as dictionaries
5. The generic ETL pipeline will handle normalization, validation, deduplication, and enrichment

**Example**:

```python
# services/workers/src/workers/scrapers/lincoln_center_scraper.py
from workers.scrapers.base import BaseScraper

class LincolnCenterScraper(BaseScraper):
    async def scrape(self) -> list[dict]:
        # Source-specific scraping logic
        # Return raw events as dicts
        return raw_events
```

**ETL**: Uses the generic `cityvibe-etl` package - no changes needed.

---

### Scenario 2: New Source Type (Different Data Format)

**If the new source has a different data structure** (e.g., RSS feed, API, CSV):

**Location**: `services/workers/src/workers/scrapers/` + `packages/cityvibe-etl/src/cityvibe_etl/normalizers/`

**Steps**:

1. **Create scraper** in `services/workers/src/workers/scrapers/`:

   ```python
   # services/workers/src/workers/scrapers/rss_feed_scraper.py
   class RSSFeedScraper(BaseScraper):
       async def scrape(self) -> list[dict]:
           # Parse RSS feed
           return raw_events
   ```

2. **Create source-specific normalizer** in `packages/cityvibe-etl/src/cityvibe_etl/normalizers/`:

   ```python
   # packages/cityvibe-etl/src/cityvibe_etl/normalizers/rss_normalizer.py
   class RSSNormalizer:
       def normalize(self, raw_event: dict, source_type: str) -> dict:
           # Convert RSS format to standard format
           return normalized_event
   ```

3. **Update EventProcessor** to use the normalizer:
   ```python
   # In event_processor.py
   def normalize(self, raw_event: dict, source_type: str = None) -> dict:
       if source_type == "rss":
           return RSSNormalizer().normalize(raw_event, source_type)
       # Generic normalization
       return self._generic_normalize(raw_event)
   ```

---

### Scenario 3: Completely Different Source (API, Database, etc.)

**If the new source requires a completely different pipeline** (e.g., real-time API, database sync):

**Option A: Extend Existing ETL** (Recommended)

- Add source-specific normalizer in `packages/cityvibe-etl/src/cityvibe_etl/normalizers/`
- Use the same validation, deduplication, and enrichment steps

**Option B: Create New Processor** (If truly different)

- Create `packages/cityvibe-etl/src/cityvibe_etl/processors/api_processor.py`
- Use when the processing logic is fundamentally different

---

## Recommended Structure

### For Most Cases (Same Format)

```
services/workers/src/workers/
└── scrapers/
    ├── base.py                    # Base scraper class
    ├── theater_scraper.py        # Venue-specific scraper
    ├── museum_scraper.py         # Venue-specific scraper
    └── new_venue_scraper.py      # Your new scraper here
```

**ETL**: No changes needed - uses `packages/cityvibe-etl/`

### For Different Formats

```
services/workers/src/workers/
└── scrapers/
    └── rss_feed_scraper.py       # New scraper

packages/cityvibe-etl/src/cityvibe_etl/
├── normalizers/                  # Source-specific normalizers
│   ├── __init__.py
│   ├── base.py                   # Base normalizer
│   ├── generic.py                # Generic normalization
│   └── rss_normalizer.py         # RSS-specific normalization
├── event_processor.py            # Updated to use normalizers
└── ... (other ETL components)
```

---

## Decision Tree

```
New Source?
│
├─ Same format as existing?
│  └─ YES → Add scraper in services/workers/src/workers/scrapers/
│     └─ Use generic ETL (no changes)
│
└─ Different format?
   └─ YES → Add scraper + normalizer
      ├─ Scraper: services/workers/src/workers/scrapers/
      └─ Normalizer: packages/cityvibe-etl/src/cityvibe_etl/normalizers/
```

---

## Example: Adding a New Website Source

### Step 1: Create Scraper

```python
# services/workers/src/workers/scrapers/lincoln_center_scraper.py
from workers.scrapers.base import BaseScraper
from playwright.async_api import async_playwright

class LincolnCenterScraper(BaseScraper):
    """Scraper for Lincoln Center website."""

    async def scrape(self) -> list[dict]:
        """
        Extract events from Lincoln Center website.

        Uses Playwright because the site is JavaScript-heavy.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.venue.website_url)

            # Wait for events to load
            await page.wait_for_selector('.event-list')

            # Extract events
            raw_events = []
            event_elements = await page.query_selector_all('.event-item')

            for element in event_elements:
                title = await element.query_selector('.event-title').inner_text()
                date_str = await element.query_selector('.event-date').inner_text()
                link = await element.query_selector('a').get_attribute('href')

                raw_events.append({
                    "title": title,
                    "start_time": date_str,  # Will be normalized by ETL
                    "source_url": f"{self.venue.website_url}{link}",
                    "venue_id": str(self.venue.id),
                })

            await browser.close()
            return raw_events
```

### Step 2: Create Scraping Task

```python
# services/workers/src/workers/tasks/scraping/scrape_venue.py
from celery import Task
from workers.scrapers.lincoln_center_scraper import LincolnCenterScraper

@Task
async def scrape_venue_task(venue_id: str) -> dict:
    """
    Celery task to scrape events from a venue.

    Args:
        venue_id: UUID of the venue to scrape

    Returns:
        Dictionary with scraping results
    """
    # TODO: Load venue from database
    # venue = await db.get_venue(venue_id)

    # Instantiate appropriate scraper based on venue type
    # scraper = get_scraper_for_venue(venue)
    scraper = LincolnCenterScraper(venue)

    # Scrape events
    raw_events = await scraper.scrape()

    # Process through ETL pipeline
    from workers.tasks.etl.process_events import process_events_task
    result = await process_events_task.delay(venue_id, raw_events)

    return result
```

### Step 2: Create Normalizer (if needed)

```python
# packages/cityvibe-etl/src/cityvibe_etl/normalizers/rss_normalizer.py
from datetime import datetime
import dateutil.parser

class RSSNormalizer:
    def normalize(self, raw_event: dict) -> dict:
        """Convert RSS format to standard event format."""
        return {
            "title": raw_event["title"],
            "description": raw_event.get("description", ""),
            "source_url": raw_event["link"],
            "start_time": dateutil.parser.parse(raw_event["published"]),
            # ... map other fields
        }
```

### Step 3: Update EventProcessor

```python
# packages/cityvibe-etl/src/cityvibe_etl/event_processor.py
from cityvibe_etl.normalizers.rss_normalizer import RSSNormalizer

class EventProcessor:
    def normalize(self, raw_event: dict) -> dict:
        source_type = raw_event.get("source_type", "generic")

        if source_type == "rss":
            return RSSNormalizer().normalize(raw_event)

        # Generic normalization for other sources
        return self._generic_normalize(raw_event)
```

---

## Summary

### For a New Website Source:

1. **Create Scraper** → `services/workers/src/workers/scrapers/venue_name_scraper.py`

   - Inherit from `BaseScraper`
   - Implement `scrape()` method
   - Extract raw event data from website (HTML/JS/API/RSS)
   - Return list of dictionaries

2. **Create Task** → `services/workers/src/workers/tasks/scraping/scrape_venue.py`

   - Celery task wrapper
   - Calls scraper, then ETL pipeline

3. **ETL Processing** → Uses `packages/cityvibe-etl/` (no changes needed)
   - Normalization, validation, deduplication, enrichment happen automatically

### File Locations:

- **Scrapers** (website extraction) → `services/workers/src/workers/scrapers/`
- **Normalizers** (format conversion) → `packages/cityvibe-etl/src/cityvibe_etl/normalizers/` (only if format is very different)
- **Generic ETL** (validation, deduplication, enrichment) → `packages/cityvibe-etl/` (reused for all sources)

**Most new website sources will only need a new scraper.** The generic ETL pipeline handles the rest.
