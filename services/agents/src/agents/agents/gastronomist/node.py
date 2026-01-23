"""LangGraph node for the Gastronomist agent."""

from pathlib import Path
from typing import cast

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from loguru import logger

import httpx

from ...state import AgentState, SubAgentResponse
from ...utils import load_agent_prompt
from .tools import find_restaurants, find_restaurants_with_rag

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    # Find project root by walking up directory tree to find .env file
    current_path = Path(__file__).parent
    project_root = None
    
    # Walk up directory tree to find project root (has .env file)
    for parent in [current_path] + list(current_path.parents):
        env_file = parent / ".env"
        if env_file.exists():
            project_root = parent
            break
    
    if project_root:
        load_dotenv(project_root / ".env")
        logger.debug(f"📁 Loaded environment variables from {project_root / '.env'}")
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass

# Load the Prompt
SYSTEM_PROMPT_BASE = load_agent_prompt("gastronomist")
# Add JSON enforcement suffix for local models
SYSTEM_PROMPT = f"{SYSTEM_PROMPT_BASE}\n\nIMPORTANT: You must return your response as a valid JSON object matching the SubAgentResponse schema. Do not include any conversational text outside the JSON."

# Initialize local Ollama LLM (lazy-loaded, cached globally)
_llm: ChatOllama | None = None


def get_llm() -> ChatOllama:
    """
    Get or initialize the global local Ollama LLM instance.

    Uses Ollama with Llama 3.1 model running locally or in Docker.
    Model must be pulled and running in Ollama service.

    Returns:
        ChatOllama instance for generating responses.

    Raises:
        ConnectionError: If Ollama service is not accessible at the configured base URL.
    """
    global _llm
    if _llm is None:
        # Get Ollama base URL from environment (defaults to localhost for local testing)
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # Use tinyllama as default (smallest memory footprint ~637MB)
        # For better quality, use llama3.2:1b (requires ~1.3GB) or llama3.1 (requires 4.8GB+)
        model = os.getenv("OLLAMA_MODEL", "tinyllama")
        
        logger.info(f"🚀 Initializing Ollama LLM: {model}")
        logger.info(f"🔗 Using Ollama at: {base_url}")
        
        _llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0,  # Deterministic outputs for structured responses
        )
        logger.info(f"✅ Ollama LLM initialized: {model}")
    return _llm

# MVP Geocoder: Maps Neighborhoods to Coords
AMSTERDAM_LOCATIONS = {
    "center": (52.3702, 4.8952),
    "centrum": (52.3702, 4.8952),
    "dam": (52.3729, 4.8936),
    "de pijp": (52.3563, 4.8970),
    "pijp": (52.3563, 4.8970),
    "jordaan": (52.3752, 4.8806),
    "west": (52.3718, 4.8643),
    "oud-west": (52.3663, 4.8692),
    "oost": (52.3619, 4.9262),
    "east": (52.3619, 4.9262),
    "noord": (52.3946, 4.9056),
    "north": (52.3946, 4.9056),
    "zuid": (52.3402, 4.8762),
    "ndsm": (52.4005, 4.8943),
    "museumplein": (52.3582, 4.8814)
}

def resolve_location(location_name: str | None, anchor: dict | None) -> tuple[float | None, float | None]:
    """
    Resolve latitude and longitude from user input or context anchor.

    Attempts to determine coordinates using a priority order:
    1. User-provided location name (matched against known Amsterdam neighborhoods)
    2. Context anchor (e.g., movie/event location) if available
    3. Returns None, None if neither source provides valid coordinates

    Args:
        location_name: User-provided location string (e.g., "De Pijp", "Center").
            Can be None if not provided.
        anchor: Context dictionary containing location information from a
            previous selection (e.g., movie venue). Should contain 'lat' and
            'lon' keys if available. Can be None.

    Returns:
        Tuple of (latitude, longitude) as floats, or (None, None) if location
        cannot be resolved. The tuple is always returned even if values are None.
    """
    # 1. Try to resolve User Input Name
    if location_name:
        key = location_name.lower().strip()
        for loc, coords in AMSTERDAM_LOCATIONS.items():
            if loc in key:
                return coords[0], coords[1]
    
    # 2. Fallback to Anchor (Movie/Event Location)
    if anchor and 'lat' in anchor:
        return anchor['lat'], anchor['lon']
        
    return None, None

def _extract_user_query(messages: list) -> str:
    """
    Extract the latest user query from message history.

    Args:
        messages: List of LangChain messages.

    Returns:
        User query string, or empty string if not found.
    """
    # Find the last human message (user input)
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            if isinstance(content, str):
                return content
            # Handle list of content blocks if needed
            if isinstance(content, list):
                text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
                if text_parts:
                    return " ".join(text_parts)
    return ""


def gastronomist_node(state: AgentState) -> dict[str, SubAgentResponse]:
    """
    LangGraph node for the Gastronomist agent with RAG support.

    Processes user requests for restaurant/bar/breakfast/lunch recommendations.
    Uses RAG (Retrieval-Augmented Generation) with vector similarity search to find
    semantically relevant venues. Implements human-in-the-loop behavior by asking
    clarifying questions when insufficient information is available.

    The agent:
    1. Analyzes the request to determine if location and cuisine/vibe are specified
    2. Returns clarification questions if information is missing
    3. Embeds the user query for semantic search
    4. Executes RAG-based database searches combining vector similarity and location filtering
    5. Handles location resolution failures and empty search results gracefully

    Args:
        state: The current agent state containing messages, context data,
            and other graph state information.

    Returns:
        Dictionary with 'final_response' key containing a SubAgentResponse with:
        - status: "complete", "needs_clarification", or "data_found_needs_selection"
        - question: Clarifying question if status is "needs_clarification"
        - search_params: Search parameters if status is "data_found_needs_selection"
        - data: List of venue results if search was successful
    """
    # 1. Setup Context
    context_data = state.get("context_data", {})
    anchor = context_data.get("search_anchor") 
    weather = context_data.get("weather", "Unknown")
    
    # Inform the agent about the anchor state
    anchor_status = f"Existing Anchor: {anchor.get('name', 'N/A')}" if anchor else "Existing Anchor: NONE"
    
    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nCONTEXT:\n- {anchor_status}\n- Weather: {weather}"),
        *state["messages"]
    ]

    # 2. Extract user query for RAG embedding
    user_query = _extract_user_query(state["messages"])
    
    # 3. Generate query embedding via embeddings API (Docker service)
    query_embedding: list[float] | None = None
    if user_query:
        try:
            embeddings_api_url = os.getenv("EMBEDDINGS_API_URL", "http://localhost:8001")
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{embeddings_api_url}/embed",
                    json={"text": user_query},
                )
                response.raise_for_status()
                result = response.json()
                query_embedding = result["embedding"]
                logger.debug(f"🔍 Embedded user query via API ({result['dimensions']} dimensions)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate query embedding via API: {e}. Falling back to non-RAG search.")

    # 4. Invoke LLM
    llm_instance = get_llm()
    structured_llm = llm_instance.with_structured_output(SubAgentResponse)
    response = cast(SubAgentResponse, structured_llm.invoke(messages))

    # 5. Validate LLM Response
    if response.status == "data_found_needs_selection":
        if not response.search_params:
            logger.warning(
                "⚠️ LLM returned 'data_found_needs_selection' without search_params. "
                "Converting to 'needs_clarification'."
            )
            response.status = "needs_clarification"
            response.question = "I need a bit more information. What type of cuisine or vibe are you looking for?"
            response.data = None
    elif response.status == "needs_clarification":
        if not response.question:
            logger.warning(
                "⚠️ LLM returned 'needs_clarification' without a question. "
                "Adding default clarification question."
            )
            response.question = "Could you provide more details about what you're looking for?"

    # 6. Execution Logic with RAG
    if response.status == "data_found_needs_selection":
        params = response.search_params or {}
        
        # Determine Location
        lat, lon = resolve_location(params.get("location_name"), anchor)
        
        if lat is None or lon is None:
            # Failed to resolve location -> Ask user
            response.status = "needs_clarification"
            response.question = "I'm not sure which area you mean. Could you specify (e.g., Center, De Pijp)?"
            response.data = None
        else:
            # Determine Radius (Shrink if raining)
            radius = 250 if weather == "rain" else 600
            if params.get("location_name"): 
                radius = 800  # Wider search for general neighborhood queries
            
            # Execute RAG Search if embedding is available, otherwise fallback to regular search
            if query_embedding and len(query_embedding) > 0:
                logger.info("🚀 Using RAG-based semantic search")
                results = find_restaurants_with_rag(
                    query_embedding=query_embedding,
                    lat=lat,
                    lon=lon,
                    radius_meters=radius,
                    required_tags=params.get("tags", []),
                    price_preference=params.get("price"),
                    similarity_threshold=0.3,  # Minimum similarity score
                    limit=5
                )
            else:
                logger.info("🔍 Using non-RAG search (no embedding available)")
                results = find_restaurants(
                    lat=lat,
                    lon=lon,
                    radius_meters=radius,
                    required_tags=params.get("tags", []),
                    price_preference=params.get("price"),
                    limit=5
                )
            
            if not results:
                response.status = "needs_clarification"
                response.question = "I couldn't find a spot with those exact matches nearby. Want to try a different cuisine?"
                response.data = None
            else:
                response.data = results
                # Call LLM again to format a response that uses the found results
                logger.info("📝 Formatting response with found venues")
                format_messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"""The user asked: "{user_query}"

I found {len(results)} venues matching their request. Here are the results:
{_format_venues_for_llm(results)}

Please format a response that:
1. Acknowledges what the user asked for
2. Mentions 2-3 specific venues by name with brief highlights (cuisine, vibe, distance)
3. Uses the 'reasoning' field to explain why these venues match the user's request
4. Sets 'question' to a helpful follow-up if needed, or None if the results speak for themselves

IMPORTANT: You do NOT need to return the 'data' field - it's already set. Just return a valid JSON SubAgentResponse with:
- status='data_found_needs_selection'
- reasoning: A brief explanation mentioning specific venue names
- question: Optional follow-up question or None
- data: Can be empty/null (will be ignored)"""
                    ),
                ]
                formatted_response = cast(
                    SubAgentResponse,
                    structured_llm.invoke(format_messages)
                )
                # Keep the data but use the LLM's formatted reasoning and question
                response.reasoning = formatted_response.reasoning
                response.question = formatted_response.question
                logger.debug(f"✅ LLM formatted response with reasoning: {response.reasoning[:100]}...")

    return {
        "final_response": response
    }


def _format_venues_for_llm(venues: list[dict]) -> str:
    """
    Format venue data for LLM consumption.

    Args:
        venues: List of venue dictionaries from database

    Returns:
        Formatted string describing venues
    """
    formatted = []
    for i, venue in enumerate(venues, 1):
        name = venue.get("name", "Unknown")
        venue_type = venue.get("venue_type", "venue")
        price = venue.get("price_range", "N/A")
        distance = venue.get("distance_meters", 0)
        tags = ", ".join(venue.get("tags", []))
        description = venue.get("description", "")
        desc_preview = description[:150] + "..." if len(description) > 150 else description
        
        formatted.append(
            f"{i}. {name} ({venue_type}) - {price}\n"
            f"   Distance: {int(distance)}m | Tags: {tags}\n"
            f"   {desc_preview}"
        )
    return "\n\n".join(formatted)