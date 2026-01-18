"""Script to pre-download embeddings model weights for local testing."""

from cityvibe_core.embeddings import download_model_weights
from loguru import logger

if __name__ == "__main__":
    logger.info("📥 Starting model weights download for local testing...")
    try:
        download_model_weights()
        logger.info("✅ Model weights download completed successfully!")
        logger.info("💡 You can now run your ETL pipeline without waiting for downloads")
    except Exception as e:
        logger.error(f"❌ Failed to download model weights: {e}")
        raise
