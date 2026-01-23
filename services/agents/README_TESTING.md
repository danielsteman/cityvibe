# Testing the Gastronomist Agent

This guide shows how to test the gastronomist agent with the new open-source LLM and RAG integration.

## Prerequisites

1. **Environment Variables**: Set `DATABASE_URL` if you want to test database searches:
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cityvibe"
   ```

2. **Dependencies**: Ensure dependencies are installed:
   ```bash
   cd services/agents
   uv sync
   ```

## Running the Test

### Option 1: Run from services/agents directory

```bash
cd services/agents
PYTHONPATH=src uv run python test_gastronomist.py
```

### Option 2: Run from project root

```bash
cd /path/to/cityvibe
PYTHONPATH=services/agents/src uv run --directory services/agents python test_gastronomist.py
```

## What to Expect

1. **First Run**: The open-source Mistral-7B-Instruct model will download (~14GB). This may take 10-30 minutes depending on your internet connection.

2. **Subsequent Runs**: The model is cached in `~/.cache/huggingface/`, so subsequent runs will be much faster.

3. **Test Scenarios**: The test runs 6 different scenarios:
   - Missing location (should ask for neighborhood)
   - Missing cuisine/vibe (should ask for type of food)
   - Complete request (should search and return results)
   - With anchor context (uses movie location)
   - Vague request (should ask clarifying questions)
   - Weather-aware (rain - smaller search radius)

## Testing RAG Functionality

The RAG (vector similarity search) is automatically used when:
- User query is successfully embedded
- Venues with embeddings exist in the database

To verify RAG is working:
1. Ensure venues in your database have `vibe_embedding` column populated
2. Check logs for "🚀 Using RAG-based semantic search" message

## Troubleshooting

### Import Errors
If you get import errors, ensure PYTHONPATH includes `services/agents/src`:
```bash
export PYTHONPATH=services/agents/src:$PYTHONPATH
```

### Model Download Issues
If model download fails:
- Check internet connection
- Verify sufficient disk space (~15GB for model + cache)
- Check HuggingFace authentication if using gated models

### Database Connection
If `DATABASE_URL` is not set, the LLM responses will still work, but database searches will fail. This is fine for testing the LLM reasoning logic.
