# Embedding Generation with Docker

This document describes how to generate embeddings for venues using Docker, which allows us to use Python 3.12 (with PyTorch support) even when the main application uses Python 3.13.

## Overview

Embeddings are generated using the `mixedbread-ai/mxbai-embed-large-v1` model (1024 dimensions) via HuggingFace. The Docker container uses Python 3.12 to ensure compatibility with PyTorch and sentence-transformers.

## Prerequisites

- Docker and Docker Compose
- PostgreSQL running (via `docker-compose up -d postgres`)
- `DATABASE_URL` in `.env` file

## Usage

### Generate Embeddings for All Missing Venues

```bash
# Build and run the embeddings service
docker-compose --profile embeddings up --build embeddings
```

### Generate Embeddings for a Limited Number of Venues

```bash
# Generate embeddings for first 10 venues
docker-compose --profile embeddings run --rm embeddings python scripts/generate_embeddings.py 10
```

### Run as One-Off Task

```bash
# Run once and exit (non-interactive)
docker-compose --profile embeddings run --rm embeddings
```

## How It Works

1. **Docker Service**: Uses `Dockerfile.embeddings` with Python 3.12
2. **Script**: `scripts/generate_embeddings.py` finds venues with `vibe_embedding IS NULL`
3. **Generation**: For each venue:
   - Generates vibe text from venue data
   - Creates embedding using HuggingFace model
   - Saves embedding to database
4. **Caching**: Model weights cached in `embeddings_cache` Docker volume

## Integration with Scrapers

The scrapers (`scrape_source.py` and `scrape_venue.py`) already generate embeddings during scraping when available. The Docker service is primarily for:

- **Backfilling**: Adding embeddings to existing venues
- **Regenerating**: Re-creating embeddings after model updates
- **Batch processing**: Generating embeddings in bulk

## Production Deployment

In production, you can:

1. **Run as scheduled job**: Use Cron or Kubernetes CronJob to run embeddings periodically
2. **Run as background service**: Keep container running to process new venues
3. **Run on-demand**: Trigger embedding generation via API or admin interface

## Troubleshooting

### Model Download Takes Time

On first run, the model (~2GB) will download automatically. This is cached in the `embeddings_cache` volume for subsequent runs.

### Threading Issues on macOS Docker Desktop

If you see errors about "Operation not permitted" or thread creation failures on macOS, this is a Docker Desktop security limitation. These errors are typically warnings and may not prevent the script from running. 

**Workaround**: The threading warnings are non-fatal. The script should still work, but if it fails:

1. **For Production**: This issue doesn't occur in Linux Docker environments (production)
2. **For Development**: Pre-download the model weights manually or use a Linux VM
3. **Alternative**: Run embeddings generation in a cloud environment or CI/CD pipeline

### Database Connection Issues

Ensure `DATABASE_URL` in `.env` points to the correct database. In Docker, use service names (e.g., `postgres:5432`) instead of `localhost`.

### Out of Memory

If processing many venues, consider using `limit` parameter to process in batches:

```bash
docker-compose --profile embeddings run --rm embeddings python scripts/generate_embeddings.py 100
```

## Production Notes

- **Linux environments**: No threading issues expected
- **macOS Docker Desktop**: May have threading warnings (non-fatal)
- **Model caching**: First run downloads ~2GB, cached for subsequent runs
- **Scalability**: Process in batches for large numbers of venues
