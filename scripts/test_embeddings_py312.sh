#!/bin/bash
# Test embeddings with Python 3.12 locally
# This script creates a temporary Python 3.12 environment to test embeddings

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Setting up Python 3.12 test environment for embeddings..."

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is not installed"
    echo "💡 Install with: brew install python@3.12"
    exit 1
fi

# Create temporary venv
VENV_DIR="$PROJECT_ROOT/.venv-embeddings"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python 3.12 virtual environment..."
    python3.12 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "📥 Installing dependencies..."
pip install --quiet --upgrade pip

# Install NumPy first (required by PyTorch)
# Use NumPy 1.x for better compatibility with PyTorch
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
    pgvector>=0.3.0

echo "✅ Dependencies installed"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/packages/cityvibe-core/src:$PROJECT_ROOT/services/workers/src:$PYTHONPATH"

# Load .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Run embedding generation test
echo ""
echo "🧪 Testing embedding generation..."
echo ""

LIMIT="${1:-3}"
python "$PROJECT_ROOT/scripts/generate_embeddings.py" "$LIMIT"

echo ""
echo "✅ Test complete!"
echo "💡 To clean up: rm -rf $VENV_DIR"
