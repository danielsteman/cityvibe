"""Interactive chat interface for the Gastronomist agent."""

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
try:
    current_path = Path(__file__).parent.resolve()
    project_root = None
    
    # Walk up directory tree to find project root (has .env file)
    # services/agents -> services -> project root
    for parent in [current_path] + list(current_path.parents):
        env_file = parent / ".env"
        if env_file.exists() and env_file.is_file():
            project_root = parent
            load_dotenv(env_file, override=False)
            logger.debug(f"📁 Loaded environment variables from {env_file}")
            break
    
    if not project_root:
        logger.warning("⚠️ Could not find .env file in parent directories")
except Exception as e:
    logger.debug(f"⚠️ Could not load .env file: {e}")

# Configure logger for cleaner chat output
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


def create_chat_state(user_message: str) -> AgentState:
    """
    Create an AgentState for chat interaction.

    Args:
        user_message: The user's message/request.

    Returns:
        AgentState configured for chat.
    """
    return {
        "messages": [HumanMessage(content=user_message)],
        "user_intent": None,
        "final_itinerary": {},
        "context_data": {
            "search_anchor": None,
            "weather": "sunny",  # Default weather
        },
        "next_agent": "gastronomist",
    }


def format_response(response: Any) -> str:
    """
    Format the agent's response for display.

    Args:
        response: The SubAgentResponse from the agent.

    Returns:
        Formatted string for display.
    """
    output = []
    
    if response.status == "needs_clarification":
        if response.question:
            output.append(f"🤔 {response.question}")
        else:
            output.append("🤔 Could you provide more details?")
    
    elif response.status == "data_found_needs_selection":
        if response.data:
            output.append(f"✅ Found {len(response.data)} options:\n")
            for i, venue in enumerate(response.data, 1):
                name = venue.get("name", "Unknown")
                distance = venue.get("distance_meters", 0)
                venue_type = venue.get("venue_type", "")
                price = venue.get("price_symbol", "")
                tags = venue.get("tags", [])
                description = venue.get("description", "")
                
                output.append(f"{i}. {name} ({venue_type}) {price}")
                if distance:
                    output.append(f"   📍 {distance}m away")
                if tags:
                    output.append(f"   🏷️  {', '.join(tags[:3])}")
                if description:
                    desc = description[:100] + "..." if len(description) > 100 else description
                    output.append(f"   📝 {desc}")
                output.append("")
        else:
            output.append("❌ No venues found matching your criteria.")
    
    elif response.status == "complete":
        output.append("✅ Request completed!")
    
    if response.reasoning:
        output.append(f"\n💭 {response.reasoning}")
    
    return "\n".join(output)


def main():
    """Run interactive chat with the Gastronomist agent."""
    logger.info("🍽️  Welcome to the Gastronomist Agent Chat!")
    logger.info("Ask me about restaurants, bars, breakfast, lunch, or dinner in Amsterdam!")
    logger.info("Type 'quit', 'exit', or 'bye' to end the conversation.\n")
    
    # Check if Ollama is running
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info(f"🔗 Connecting to Ollama at {ollama_url}")
    
    # Check database
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("⚠️ DATABASE_URL not set - I can chat but can't search for venues")
    else:
        logger.info("✅ Database connection configured")
    
    # Check embeddings API
    embeddings_api_url = os.getenv("EMBEDDINGS_API_URL", "http://localhost:8001")
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{embeddings_api_url}/health")
            if response.status_code == 200:
                logger.info("✅ RAG embeddings API available (semantic search enabled)")
            else:
                logger.warning(f"⚠️ Embeddings API returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Embeddings API not available: {e}")
        logger.info("💡 Start the embeddings API with: docker compose up -d embeddings-api")
        logger.info("   (Will use non-RAG search until API is available)\n")
    
    logger.info("=" * 60 + "\n")
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye", "q"]:
                logger.info("\n👋 Goodbye! Enjoy your meal!")
                break
            
            # Create state with conversation history
            messages = [HumanMessage(content=msg) for msg in conversation_history] + [
                HumanMessage(content=user_input)
            ]
            state = {
                "messages": messages,
                "user_intent": None,
                "final_itinerary": {},
                "context_data": {
                    "search_anchor": None,
                    "weather": "sunny",
                },
                "next_agent": "gastronomist",
            }
            
            # Get agent response
            logger.info("🤖 Thinking...")
            result = gastronomist_node(state)
            response = result["final_response"]
            
            # Display response
            print(f"\n🍽️  Gastronomist:")
            formatted = format_response(response)
            print(formatted)
            print()
            
            # Add to conversation history
            conversation_history.append(user_input)
            # Add a summary of the response to history (optional, for context)
            if response.question:
                conversation_history.append(f"Agent asked: {response.question}")
        
        except KeyboardInterrupt:
            logger.info("\n\n👋 Goodbye! Enjoy your meal!")
            break
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            print(f"An error occurred: {e}\n")


if __name__ == "__main__":
    main()
