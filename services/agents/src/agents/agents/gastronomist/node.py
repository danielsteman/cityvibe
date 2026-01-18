"""LangGraph node for the Gastronomist agent."""

from typing import cast

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from ...state import AgentState, SubAgentResponse
from ...utils import load_agent_prompt
from .tools import find_restaurants

# Load the Prompt
SYSTEM_PROMPT = load_agent_prompt("gastronomist")
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

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

def gastronomist_node(state: AgentState) -> dict[str, SubAgentResponse]:
    """
    LangGraph node for the Gastronomist agent.

    Processes user requests for restaurant/bar/breakfast/lunch recommendations.
    Implements human-in-the-loop behavior by asking clarifying questions when
    insufficient information is available.

    The agent:
    1. Analyzes the request to determine if location and cuisine/vibe are specified
    2. Returns clarification questions if information is missing
    3. Executes database searches when sufficient information is available
    4. Handles location resolution failures and empty search results gracefully

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

    # 2. Invoke LLM
    structured_llm = llm.with_structured_output(SubAgentResponse)
    response = cast(SubAgentResponse, structured_llm.invoke(messages))

    # 3. Validate LLM Response
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

    # 4. Execution Logic
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
                radius = 800 # Wider search for general neighborhood queries
            
            # Execute DB Search
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

    return {
        "final_response": response
    }