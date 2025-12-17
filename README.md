# City Vibe

City Vibe indexes fun things to do in cities. We do this by collecting data from websites that list activities such as concerts, theatre shows, museums, and more. This data is processed to make it queryable for a language model.

## Project Structure

This is a monorepo managed with [uv](https://github.com/astral-sh/uv) workspaces, containing:

- **Packages**: Shared Python libraries (`cityvibe-core`, `cityvibe-common`, `cityvibe-etl`)
- **Services**: Backend services (MCP server, FastAPI API, Celery workers, Agents service)
- **Apps**: Frontend applications (web and mobile - coming soon)

## Quick Start

See [QUICKSTART.md](./docs/QUICKSTART.md) for detailed setup instructions.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Start infrastructure
docker-compose up -d

# Run services (see docs/QUICKSTART.md for details)
```

## Documentation

- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System architecture and design
- [PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md) - Detailed project structure
- [QUICKSTART.md](./docs/QUICKSTART.md) - Getting started guide
- [SOPS.md](./docs/SOPS.md) - Secrets management with SOPS

## Technology Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **Database**: PostgreSQL 15+
- **Vector DB**: Qdrant
- **Cache**: Redis
- **API Framework**: FastAPI
- **MCP Server**: Python MCP SDK
- **Task Queue**: Celery
- **Agents**: LangGraph multi-agent system
