"""Test script for the Gastronomist agent node."""

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from agents.agents.gastronomist.node import gastronomist_node
from agents.state import AgentState
from loguru import logger

# Load environment variables from .env file if it exists
# Walk up directory tree to find project root (has .env file)
try:
    current_path = Path(__file__).parent
    project_root = None
    
    # Walk up directory tree to find project root (has .env file)
    for parent in [current_path] + list(current_path.parents):
        env_file = parent / ".env"
        if env_file.exists():
            project_root = parent
            load_dotenv(env_file)
            logger.debug(f"📁 Loaded environment variables from {env_file}")
            break
except Exception as e:
    logger.debug(f"⚠️ Could not load .env file: {e}")


def create_test_state(
    user_message: str,
    anchor: dict[str, Any] | None = None,
    weather: str = "sunny",
) -> AgentState:
    """
    Create a test AgentState for testing the gastronomist node.

    Args:
        user_message: The user's message/request.
        anchor: Optional anchor context (e.g., movie venue location).
        weather: Weather condition. Defaults to "sunny".

    Returns:
        AgentState configured for testing.
    """
    return {
        "messages": [HumanMessage(content=user_message)],
        "user_intent": None,
        "final_itinerary": {},
        "context_data": {
            "search_anchor": anchor,
            "weather": weather,
        },
        "next_agent": "gastronomist",
    }


def test_scenario(
    name: str,
    user_message: str,
    anchor: dict[str, Any] | None = None,
    weather: str = "sunny",
) -> None:
    """
    Test a specific scenario with the gastronomist agent.

    Args:
        name: Name/description of the test scenario.
        user_message: The user's message.
        anchor: Optional anchor context.
        weather: Weather condition.
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"🧪 Testing: {name}")
    logger.info(f"{'=' * 80}")
    logger.info(f"📝 User message: {user_message}")
    if anchor:
        logger.info(f"📍 Anchor: {anchor.get('name', 'N/A')} at ({anchor.get('lat')}, {anchor.get('lon')})")
    logger.info(f"🌤️  Weather: {weather}")

    state = create_test_state(user_message, anchor, weather)
    result = gastronomist_node(state)
    response = result["final_response"]

    logger.info(f"\n📊 Response Status: {response.status}")
    if response.question:
        logger.info(f"❓ Question: {response.question}")
    if response.search_params:
        logger.info(f"🔍 Search Params: {response.search_params}")
    if response.data:
        logger.info(f"✅ Found {len(response.data)} venues:")
        for i, venue in enumerate(response.data[:3], 1):  # Show first 3
            logger.info(f"   {i}. {venue.get('name', 'N/A')} - {venue.get('distance_meters', 0)}m away")
    if response.reasoning:
        logger.info(f"💭 Reasoning: {response.reasoning}")


def main():
    """Run test scenarios for the gastronomist agent."""
    logger.info("ℹ️  Using Ollama (Llama 3.1) for generation")
    logger.info("ℹ️  Using Mixedbread AI (mxbai-embed-large-v1) for embeddings")
    logger.info("ℹ️  Ensure Ollama is running (locally or via Docker)")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning(
            "⚠️ DATABASE_URL not set - database searches will fail, "
            "but LLM responses can still be tested"
        )
        logger.info("💡 Set it with: export DATABASE_URL='postgresql://...'")

    logger.info("🚀 Starting Gastronomist Agent Tests")
    logger.info("=" * 80)

    # Test Scenario 1: Missing Location
    test_scenario(
        "Missing Location - Should ask for neighborhood",
        "I want Italian food",
    )

    # Test Scenario 2: Missing Cuisine/Vibe
    test_scenario(
        "Missing Cuisine/Vibe - Should ask for type of food",
        "Dinner in De Pijp",
    )

    # Test Scenario 3: Complete Request
    test_scenario(
        "Complete Request - Should search and return results",
        "Cozy Italian restaurant in De Pijp",
    )

    # Test Scenario 4: With Anchor Context
    test_scenario(
        "With Anchor Context - Uses movie location",
        "Dinner nearby",
        anchor={
            "name": "Tuschinski",
            "type": "cinema",
            "lat": 52.3702,
            "lon": 4.8952,
        },
    )

    # Test Scenario 5: Vague Request
    test_scenario(
        "Vague Request - Should ask clarifying questions",
        "I'm hungry",
    )

    # Test Scenario 6: Weather-aware (rain)
    test_scenario(
        "Weather-aware (Rain) - Smaller search radius",
        "Italian food in Center",
        weather="rain",
    )

    logger.info(f"\n{'=' * 80}")
    logger.info("✅ All test scenarios completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
