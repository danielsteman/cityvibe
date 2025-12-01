# City Vibe - Project Structure

This document outlines the recommended project structure using `uv` for dependency management, organized as a monorepo workspace to support backend services and future frontend applications.

## Overview

The project uses `uv` workspaces to manage multiple Python packages and services in a single repository. This structure allows:

- Shared code between services (models, database, utilities)
- Independent service deployment
- Easy addition of frontend applications
- Consistent dependency management across all components

## Root Structure

```
cityvibe/
├── pyproject.toml              # Root workspace configuration
├── uv.lock                     # Locked dependencies (generated)
├── .python-version             # Python version (3.13+)
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
│
├── docker-compose.yml           # Local development services
├── Dockerfile                   # Base Docker image (if needed)
│
├── packages/                    # Shared Python packages
│   ├── cityvibe-core/          # Core domain models & database
│   ├── cityvibe-common/        # Shared utilities & helpers
│   └── cityvibe-etl/           # ETL pipeline processors
│
├── services/                    # Backend services
│   ├── mcp-server/             # MCP server for LLM queries
│   ├── api/                     # FastAPI REST API
│   ├── workers/                 # Celery workers (scrapers, ETL)
│   └── scheduler/               # Celery Beat scheduler
│
├── apps/                        # Frontend applications (future)
│   ├── web/                     # Web app (Next.js/React)
│   └── mobile/                  # Mobile app (React Native/Flutter)
│
├── infrastructure/              # Infrastructure as code
│   ├── kubernetes/              # K8s manifests
│   ├── terraform/               # Cloud infrastructure (optional)
│   └── scripts/                 # Deployment scripts
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── alembic.ini
│
├── tests/                       # Integration tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── docs/                        # Additional documentation
    ├── ARCHITECTURE.md          # System architecture
    ├── PROJECT_STRUCTURE.md     # This file
    ├── QUICKSTART.md            # Getting started guide
    ├── README.md                # Documentation index
    ├── api/                     # API documentation
    └── deployment/              # Deployment guides
```

## Detailed Structure

### Root `pyproject.toml`

```toml
[project]
name = "cityvibe"
version = "0.1.0"
description = "City Vibe - Event aggregation and discovery platform"
readme = "README.md"
requires-python = ">=3.13"

[tool.uv.workspace]
members = [
    "packages/*",
    "services/*",
]

[tool.uv]
dev-dependencies = [
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pre-commit>=3.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
```

### `packages/cityvibe-core/` - Core Domain Models

```
packages/cityvibe-core/
├── pyproject.toml
├── README.md
└── src/
    └── cityvibe_core/
        ├── __init__.py
        │
        ├── models/              # SQLAlchemy models
        │   ├── __init__.py
        │   ├── venue.py
        │   ├── event.py
        │   ├── scrape_job.py
        │   └── base.py          # Base model with common fields
        │
        ├── schemas/              # Pydantic schemas
        │   ├── __init__.py
        │   ├── venue.py
        │   ├── event.py
        │   └── scrape_job.py
        │
        ├── database/             # Database connection & session management
        │   ├── __init__.py
        │   ├── connection.py
        │   ├── session.py
        │   └── migrations.py
        │
        └── repositories/         # Data access layer
            ├── __init__.py
            ├── venue_repository.py
            ├── event_repository.py
            └── base_repository.py
```

**`packages/cityvibe-core/pyproject.toml`:**

```toml
[project]
name = "cityvibe-core"
version = "0.1.0"
description = "Core domain models and database layer"
requires-python = ">=3.13"
dependencies = [
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "pydantic>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### `packages/cityvibe-common/` - Shared Utilities

```
packages/cityvibe-common/
├── pyproject.toml
└── src/
    └── cityvibe_common/
        ├── __init__.py
        │
        ├── config/               # Configuration management
        │   ├── __init__.py
        │   ├── settings.py
        │   └── database.py
        │
        ├── logging/               # Structured logging
        │   ├── __init__.py
        │   └── setup.py
        │
        ├── cache/                 # Redis cache utilities
        │   ├── __init__.py
        │   └── client.py
        │
        ├── geocoding/             # Geocoding service
        │   ├── __init__.py
        │   └── service.py
        │
        ├── embeddings/            # Embedding generation
        │   ├── __init__.py
        │   └── service.py
        │
        ├── vector_db/              # Vector DB client (Qdrant/Weaviate)
        │   ├── __init__.py
        │   └── client.py
        │
        └── exceptions/            # Custom exceptions
            ├── __init__.py
            └── errors.py
```

**`packages/cityvibe-common/pyproject.toml`:**

```toml
[project]
name = "cityvibe-common"
version = "0.1.0"
description = "Shared utilities and services"
requires-python = ">=3.13"
dependencies = [
    "redis>=5.0.0",
    "structlog>=23.0.0",
    "httpx>=0.25.0",
    "qdrant-client>=1.7.0",  # or weaviate-client
    "openai>=1.0.0",  # or ollama
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
```

### `packages/cityvibe-etl/` - ETL Pipeline

```
packages/cityvibe-etl/
├── pyproject.toml
├── README.md
└── src/
    └── cityvibe_etl/
        ├── __init__.py
        ├── event_processor.py    # Main orchestrator
        ├── validator.py          # Data validation
        ├── deduplicator.py       # Deduplication logic
        └── enricher.py          # Data enrichment
```

**`packages/cityvibe-etl/pyproject.toml`:**

```toml
[project]
name = "cityvibe-etl"
version = "0.1.0"
description = "ETL pipeline for processing and enriching events"
requires-python = ">=3.13"
dependencies = [
    "cityvibe-core",
    "cityvibe-common",
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
cityvibe-common = { workspace = true }
```

**Note**: The ETL pipeline is separated into its own package for reusability. It can be used by workers, API endpoints, or other services that need to process events.

### `services/mcp-server/` - MCP Server

```
services/mcp-server/
├── pyproject.toml
├── README.md
└── src/
    └── mcp_server/
        ├── __init__.py
        ├── main.py               # Entry point
        │
        ├── server.py             # MCP server setup
        ├── tools/                 # MCP tool implementations
        │   ├── __init__.py
        │   ├── search_events.py
        │   ├── get_event_details.py
        │   ├── find_nearby_events.py
        │   └── get_venue_events.py
        │
        └── services/             # Business logic
            ├── __init__.py
            ├── search_service.py
            └── hybrid_search.py
```

**`services/mcp-server/pyproject.toml`:**

```toml
[project]
name = "mcp-server"
version = "0.1.0"
description = "MCP server for LLM event queries"
requires-python = ">=3.13"
dependencies = [
    "mcp>=0.9.0",
    "cityvibe-core",
    "cityvibe-common",
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
cityvibe-common = { workspace = true }

[project.scripts]
mcp-server = "mcp_server.main:main"
```

### `services/api/` - FastAPI REST API

```
services/api/
├── pyproject.toml
├── README.md
└── src/
    └── api/
        ├── __init__.py
        ├── main.py               # FastAPI app entry point
        │
        ├── config.py             # API-specific config
        │
        ├── routes/                # API routes (domain-based)
        │   ├── __init__.py
        │   ├── events/
        │   │   ├── __init__.py
        │   │   ├── router.py
        │   │   ├── schemas.py
        │   │   ├── dependencies.py
        │   │   └── service.py
        │   │
        │   ├── venues/
        │   │   ├── __init__.py
        │   │   ├── router.py
        │   │   ├── schemas.py
        │   │   └── service.py
        │   │
        │   └── admin/             # Admin endpoints
        │       ├── __init__.py
        │       ├── router.py
        │       └── service.py
        │
        ├── middleware/            # Custom middleware
        │   ├── __init__.py
        │   ├── logging.py
        │   ├── rate_limit.py
        │   └── error_handler.py
        │
        └── dependencies/          # Shared dependencies
            ├── __init__.py
            └── database.py
```

**`services/api/pyproject.toml`:**

```toml
[project]
name = "api"
version = "0.1.0"
description = "FastAPI REST API"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "cityvibe-core",
    "cityvibe-common",
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
cityvibe-common = { workspace = true }

[project.scripts]
api = "api.main:main"
```

### `services/workers/` - Celery Workers

```
services/workers/
├── pyproject.toml
├── README.md
└── src/
    └── workers/
        ├── __init__.py
        ├── main.py               # Celery app initialization
        │
        ├── tasks/                 # Celery tasks
        │   ├── __init__.py
        │   ├── scraping/
        │   │   ├── __init__.py
        │   │   ├── scrape_venue.py
        │   │   └── scrape_scheduler.py
        │   │
        │   └── etl/
        │       ├── __init__.py
        │       └── process_events.py
        │
        └── scrapers/              # Scraper implementations (to be implemented)
            ├── __init__.py
            ├── base.py
            ├── theater_scraper.py
            ├── museum_scraper.py
            └── concert_scraper.py
```

**`services/workers/pyproject.toml`:**

```toml
[project]
name = "workers"
version = "0.1.0"
description = "Celery workers for scraping and ETL"
requires-python = ">=3.13"
dependencies = [
    "celery>=5.3.0",
    "scrapy>=2.11.0",
    "playwright>=1.40.0",
    "beautifulsoup4>=4.12.0",
    "cityvibe-core",
    "cityvibe-common",
    "cityvibe-etl",
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
cityvibe-common = { workspace = true }

[project.scripts]
worker = "workers.main:main"
```

### `services/scheduler/` - Celery Beat Scheduler

```
services/scheduler/
├── pyproject.toml
└── src/
    └── scheduler/
        ├── __init__.py
        ├── main.py               # Beat scheduler entry point
        └── schedules.py          # Schedule definitions
```

**`services/scheduler/pyproject.toml`:**

```toml
[project]
name = "scheduler"
version = "0.1.0"
description = "Celery Beat scheduler"
requires-python = ">=3.13"
dependencies = [
    "celery>=5.3.0",
    "cityvibe-core",
]

[tool.uv.sources]
cityvibe-core = { workspace = true }
```

### `apps/` - Frontend Applications (Future)

```
apps/
├── web/                          # Web application
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/
│
└── mobile/                       # Mobile application
    ├── package.json
    ├── app.json
    └── src/
        ├── screens/
        ├── components/
        └── services/
```

## Key Design Decisions

### 1. **Monorepo with uv Workspace**

- Single repository for all services and packages
- Shared dependencies managed centrally
- Easy code sharing between services
- Consistent Python version across all packages

### 2. **Domain-Driven Structure**

- Core domain models separated from services
- Services depend on core, not each other
- Clear boundaries between components

### 3. **Service Independence**

- Each service can be deployed independently
- Services share code via workspace packages
- No circular dependencies

### 4. **Future Frontend Support**

- `apps/` directory ready for web/mobile
- Frontends can consume the REST API
- Shared types can be generated from Pydantic schemas

### 5. **Source Layout (`src/`)**

- Follows Python best practices
- Avoids import path confusion
- Better IDE support

## Development Workflow

### Initial Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all workspace dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Running Services

```bash
# Start infrastructure services
docker-compose up -d postgres redis qdrant

# Run database migrations
cd packages/cityvibe-core
alembic upgrade head

# Start MCP server
cd services/mcp-server
uv run mcp-server

# Start API server
cd services/api
uv run uvicorn api.main:app --reload

# Start Celery worker
cd services/workers
uv run celery -A workers.main worker --loglevel=info

# Start Celery Beat scheduler
cd services/scheduler
uv run celery -A scheduler.main beat --loglevel=info
```

### Adding Dependencies

```bash
# Add to a specific package/service
cd services/api
uv add fastapi

# Add to root dev dependencies
uv add --dev pytest

# Sync after adding dependencies
uv sync
```

### Testing

```bash
# Run all tests
uv run pytest

# Run tests for specific package
cd packages/cityvibe-core
uv run pytest

# With coverage
uv run pytest --cov=cityvibe_core
```

## Benefits of This Structure

1. **Scalability**: Easy to add new services or packages
2. **Maintainability**: Clear separation of concerns
3. **Reusability**: Shared code in packages
4. **Type Safety**: Shared types across services
5. **Fast Development**: uv's speed for dependency management
6. **Future-Proof**: Ready for frontend applications

## Migration Path

When adding frontends:

1. **Web App**: Add to `apps/web/` with Next.js/React
2. **Mobile App**: Add to `apps/mobile/` with React Native/Flutter
3. **Shared Types**: Generate TypeScript types from Pydantic schemas
4. **API Client**: Create typed API client in frontend apps

## Notes

- All Python packages use `src/` layout for better import resolution
- Each service has its own `pyproject.toml` for independent versioning
- Workspace dependencies are declared via `tool.uv.sources`
- Database migrations live at root level (shared across services)
- Tests can be organized per-package or at root level
