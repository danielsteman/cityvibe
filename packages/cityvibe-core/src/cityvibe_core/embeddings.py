"""Embedding generation using HuggingFace models."""

import os
from pathlib import Path
from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger


def download_model_weights(
    model_name: str = "mixedbread-ai/mxbai-embed-large-v1",
    cache_dir: str | Path | None = None,
) -> None:
    """
    Pre-download model weights for local testing.

    This function explicitly downloads and caches the model weights before
    first use, which is useful for local testing and to verify the setup works.

    Args:
        model_name: Name of the HuggingFace model to download
        cache_dir: Directory to cache the model. Defaults to ~/.cache/huggingface
                   or /app/.cache/huggingface in Docker
    """
    # Determine cache directory (prioritize Docker volume, then user cache)
    if cache_dir is None:
        docker_cache = Path("/app/.cache/huggingface")
        user_cache = Path.home() / ".cache" / "huggingface"
        if docker_cache.exists() or os.getenv("DOCKER_ENV"):
            cache_dir = docker_cache
        else:
            cache_dir = user_cache
    else:
        cache_dir = Path(cache_dir)

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"📥 Downloading model weights: {model_name}")
    logger.info(f"📁 Cache directory: {cache_dir}")
    logger.info("⏳ This may take a few minutes on first run...")

    # Initialize the model, which triggers the download
    # We'll create a minimal instance just to trigger the download
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            cache_folder=str(cache_dir),
            model_kwargs={"device": "cpu"},  # Use CPU for download
        )
        # Test with a small query to ensure model is fully loaded
        _ = embeddings.embed_query("test")
        logger.info(f"✅ Model weights downloaded and cached successfully")
    except Exception as e:
        logger.error(f"❌ Failed to download model weights: {e}")
        raise


def get_embeddings_model(
    model_name: str = "mixedbread-ai/mxbai-embed-large-v1",
    cache_dir: str | Path | None = None,
    device: str | None = None,
) -> HuggingFaceEmbeddings:
    """
    Initialize HuggingFace embeddings model.

    The model weights will be downloaded automatically on first use if not
    already cached. For pre-downloading weights before use, call
    `download_model_weights()` separately.

    Args:
        model_name: Name of the HuggingFace model to use
        cache_dir: Directory to cache the model. Defaults to ~/.cache/huggingface
                   or /app/.cache/huggingface in Docker
        device: Device to run model on ("cpu" or "cuda"). Auto-detects if None

    Returns:
        Initialized HuggingFaceEmbeddings instance
    """
    # Determine cache directory (prioritize Docker volume, then user cache)
    if cache_dir is None:
        docker_cache = Path("/app/.cache/huggingface")
        user_cache = Path.home() / ".cache" / "huggingface"
        if docker_cache.exists() or os.getenv("DOCKER_ENV"):
            cache_dir = docker_cache
            logger.debug(f"🔧 Using Docker cache directory: {cache_dir}")
        else:
            cache_dir = user_cache
            logger.debug(f"🔧 Using user cache directory: {cache_dir}")
    else:
        cache_dir = Path(cache_dir)

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect device if not specified
    if device is None:
        try:
            import torch  # type: ignore[import-untyped]

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
        logger.debug(f"🔧 Auto-detected device: {device}")
    else:
        logger.debug(f"🔧 Using specified device: {device}")

    logger.info(f"🚀 Initializing embeddings model: {model_name}")
    logger.info(f"📁 Cache directory: {cache_dir}")
    logger.info(f"⚙️ Device: {device}")

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        cache_folder=str(cache_dir),
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},  # Normalize for cosine similarity
    )

    logger.info(f"✅ Embeddings model initialized: {model_name}")
    return embeddings


# Global embeddings instance (lazy-loaded)
_embeddings_model: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Get or initialize the global embeddings model instance.

    Returns:
        Global HuggingFaceEmbeddings instance
    """
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = get_embeddings_model()
    return _embeddings_model


def generate_vibe_text(venue: dict[str, Any] | Any) -> str:
    """
    Generate dense vibe text from venue data for embedding.

    Creates a structured text string containing venue name, category, description,
    and tags that will be embedded for semantic search.

    Args:
        venue: Venue dictionary or SQLModel instance with venue data.
               Expected fields: name, venue_type (category), description, tags

    Returns:
        Dense vibe text string for embedding
    """
    # Extract fields from dict or object
    if isinstance(venue, dict):
        name = venue.get("name", "")
        category = venue.get("venue_type") or venue.get("category")
        description = venue.get("description")
        tags = venue.get("tags", [])
    else:
        # SQLModel instance
        name = getattr(venue, "name", "") or ""
        category = getattr(venue, "venue_type", None) or getattr(venue, "category", None)
        description = getattr(venue, "description", None)
        tags = getattr(venue, "tags", []) or []

    # Build vibe text components
    parts = [f"Name: {name}"]

    if category:
        parts.append(f"Category: {category}")

    if description:
        # Strip any HTML tags and normalize whitespace
        desc_clean = " ".join(description.split())
        parts.append(f"Description: {desc_clean}")

    if tags and isinstance(tags, list) and len(tags) > 0:
        tags_str = ", ".join(str(tag) for tag in tags if tag)
        if tags_str:
            parts.append(f"Tags: {tags_str}")

    vibe_text = ". ".join(parts) + "."

    return vibe_text
