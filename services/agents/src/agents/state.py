"""Shared TypedDict & Pydantic Models."""

from typing import Any, Literal, TypedDict, Annotated
from operator import add
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class AgentState(TypedDict, total=True):
    """
    The State of the LangGraph execution.
    Passed down to every node.
    """
    # Chat History (Appends new messages to the list)
    messages: Annotated[list[BaseMessage], add]
    
    # High-level Intent (Planner, Single Ticket, Browser)
    user_intent: Literal["planner", "single_activity", "browser", "stroll"] | None
    
    # The Concrete Plan (The "Shopping Cart")
    # Example: {
    #   "anchor": {"name": "Dune", "type": "movie", "lat": 52.3, ...},
    #   "dinner": {"name": "Rijsel", "type": "restaurant", ...}
    # }
    final_itinerary: dict[str, Any]
    
    # Shared Context (Environment & Anchors)
    # Example: {
    #   "weather": "rain",
    #   "date": "2023-10-27",
    #   "search_anchor": {"lat": 52.3, "lon": 4.9, "name": "Tuschinski"}
    # }
    context_data: dict[str, Any]
    
    # Routing Flag (Which node runs next?)
    next_agent: str


class SubAgentResponse(BaseModel):
    """Standard response format for sub-agents."""
    status: Literal["complete", "needs_clarification", "data_found_needs_selection"]
    
    # Payload for talking to the User
    question: str | None = Field(None, description="Clarifying question if needed")
    missing_info: str | None = Field(None, description="What info is missing (e.g. 'cuisine')")
    
    # Payload for the Tool (The Search Intent)
    search_params: dict[str, Any] | None = Field(
        None, 
        description="Filters: {'tags': ['Italian'], 'location_name': 'De Pijp'}"
    )
    
    # Payload for the Result
    data: list[dict] | None = Field(None, description="Results found")
    reasoning: str | None = Field(None, description="Why these were chosen")
