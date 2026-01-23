# Dockerfile for Embeddings API service
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ; rm -rf /var/lib/apt/lists/* || true

# Install PyTorch CPU version (compatible with Python 3.12)
ENV PIP_NO_DEPS=false
RUN pip install --no-cache-dir --quiet \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install core dependencies
RUN pip install --no-cache-dir --quiet \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    pydantic>=2.0.0 \
    loguru>=0.7.0

# Install embedding dependencies
RUN pip install --no-cache-dir --quiet \
    transformers \
    sentence-transformers \
    langchain-huggingface

# Copy workspace files
COPY packages/ ./packages/
COPY services/embeddings-api/ ./services/embeddings-api/

# Set Python path
ENV PYTHONPATH=/app/packages/cityvibe-core/src:$PYTHONPATH

# Set threading environment variables
ENV OPENBLAS_NUM_THREADS=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# Expose port
EXPOSE 8001

# Run the API
CMD ["python", "services/embeddings-api/app.py"]
