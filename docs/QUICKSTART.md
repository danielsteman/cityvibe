# Quick Start Guide

This guide will help you get the City Vibe project up and running using `uv` for dependency management.

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker and Docker Compose (for local development services)
- PostgreSQL 15+ (or use Docker)

## Initial Setup

### 1. Install uv

If you haven't already installed `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS with Homebrew:

```bash
brew install uv
```

### 2. Clone and Setup Project

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd cityvibe

# Sync all workspace dependencies
# This will create a virtual environment and install all packages
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### 3. Start Infrastructure Services

Start PostgreSQL, Redis, and Qdrant using Docker Compose:

```bash
docker-compose up -d postgres redis qdrant
```

### 4. Setup Database

```bash
# Run database migrations
cd packages/cityvibe-core
alembic upgrade head
```

### 5. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cityvibe

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenAI (for embeddings)
OPENAI_API_KEY=your-api-key-here

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Running Services

### MCP Server

```bash
cd services/mcp-server
uv run mcp-server
```

Or from the root:

```bash
uv run --package mcp-server mcp-server
```

### FastAPI REST API

```bash
cd services/api
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the root:

```bash
uv run --package api uvicorn api.main:app --reload
```

### Celery Worker

```bash
cd services/workers
uv run celery -A workers.main worker --loglevel=info
```

### Celery Beat Scheduler

```bash
cd services/scheduler
uv run celery -A scheduler.main beat --loglevel=info
```

## Development Workflow

### Adding Dependencies

To add a dependency to a specific package or service:

```bash
# Navigate to the package/service directory
cd services/api

# Add a dependency
uv add fastapi

# Add a dev dependency
uv add --dev pytest

# Sync all workspace dependencies
uv sync
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific package
cd packages/cityvibe-core
uv run pytest

# Run with coverage
uv run pytest --cov=cityvibe_core --cov-report=html
```

### Code Quality

```bash
# Format code with ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Pre-commit Hooks

Install and run pre-commit hooks:

```bash
# Install hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## Project Structure

```
cityvibe/
├── packages/           # Shared Python packages
│   ├── cityvibe-core/     # Domain models & database
│   └── cityvibe-common/   # Shared utilities
├── services/          # Backend services
│   ├── mcp-server/        # MCP server
│   ├── api/               # FastAPI REST API
│   ├── workers/           # Celery workers
│   └── scheduler/         # Celery Beat
└── apps/              # Frontend apps (future)
    ├── web/               # Web app
    └── mobile/            # Mobile app
```

## Troubleshooting

### Virtual Environment Issues

If you encounter issues with the virtual environment:

```bash
# Remove existing venv
rm -rf .venv

# Recreate and sync
uv sync
```

### Dependency Conflicts

If you have dependency conflicts:

```bash
# Update lock file
uv lock --upgrade

# Sync dependencies
uv sync
```

### Database Connection Issues

Ensure PostgreSQL is running:

```bash
# Check Docker containers
docker-compose ps

# View logs
docker-compose logs postgres
```

## Next Steps

1. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system design details
2. Review [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) for detailed structure documentation
3. Start implementing the core models in `packages/cityvibe-core`
4. Set up the database schema and migrations

## Useful Commands

```bash
# List all workspace packages
uv tree

# Show package info
uv tree --package cityvibe-core

# Run a command in a specific package context
uv run --package api python -c "import api; print(api.__version__)"

# Update all dependencies
uv sync --upgrade
```
