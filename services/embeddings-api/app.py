"""Embeddings API service for generating query embeddings via HTTP."""

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

# Add cityvibe-core to path
sys.path.insert(0, str(Path("/app/packages/cityvibe-core/src")))

from cityvibe_core.embeddings import get_embeddings

app = FastAPI(title="CityVibe Embeddings API", version="1.0.0")

# CORS middleware to allow requests from agent
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global embeddings model (lazy-loaded)
_embeddings_model = None


def get_embeddings_model():
    """Get or initialize the global embeddings model."""
    global _embeddings_model
    if _embeddings_model is None:
        logger.info("🚀 Initializing embeddings model...")
        _embeddings_model = get_embeddings()
        logger.info("✅ Embeddings model initialized")
    return _embeddings_model


class EmbedRequest(BaseModel):
    """Request model for embedding generation."""

    text: str


class EmbedResponse(BaseModel):
    """Response model for embedding generation."""

    embedding: list[float]
    dimensions: int


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "embeddings-api"}


@app.post("/embed", response_model=EmbedResponse)
async def generate_embedding(request: EmbedRequest):
    """
    Generate embedding for a text query.

    Args:
        request: EmbedRequest containing the text to embed

    Returns:
        EmbedResponse with the embedding vector and dimensions
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        embeddings_model = get_embeddings_model()
        embedding = embeddings_model.embed_query(request.text.strip())

        return EmbedResponse(
            embedding=embedding,
            dimensions=len(embedding),
        )
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize embeddings model on startup."""
    logger.info("🚀 Starting Embeddings API service")
    # Pre-load the model
    get_embeddings_model()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
