#!/bin/bash
# Ingest 250 venues using Python 3.12 (supports embeddings)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Starting venue ingestion with Python 3.12 (with embeddings support)"

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is not installed"
    echo "💡 Install with: brew install python@3.12"
    exit 1
fi

# Use existing embeddings venv or create it
VENV_DIR="$PROJECT_ROOT/.venv-embeddings"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python 3.12 virtual environment..."
    python3.12 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    echo "📥 Installing dependencies..."
    pip install --quiet --upgrade pip
    
    # Install NumPy first (required by PyTorch, use 1.x for compatibility)
    pip install --quiet "numpy<2.0"
    
    # Install PyTorch CPU version (Python 3.12 compatible)
    pip install --quiet \
        torch \
        --index-url https://download.pytorch.org/whl/cpu
    
    # Install embedding dependencies
    pip install --quiet \
        sentence-transformers \
        langchain-huggingface
    
    # Install project dependencies
    pip install --quiet \
        sqlalchemy>=2.0.0 \
        sqlmodel>=0.0.14 \
        asyncpg>=0.29.0 \
        psycopg2-binary>=2.9.0 \
        geoalchemy2>=0.14.0 \
        loguru>=0.7.0 \
        pgvector>=0.3.0 \
        python-dotenv>=1.0.0 \
        celery>=5.0.0 \
        playwright \
        beautifulsoup4 \
        deep-translator \
        httpx
else
    source "$VENV_DIR/bin/activate"
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/packages/cityvibe-core/src:$PROJECT_ROOT/packages/cityvibe-common/src:$PROJECT_ROOT/services/workers/src:$PYTHONPATH"

# Load .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Run ingestion script
echo "📊 Running ingestion script..."
python "$PROJECT_ROOT/scripts/ingest_250_venues.py"

echo ""
echo "✅ Ingestion complete!"
