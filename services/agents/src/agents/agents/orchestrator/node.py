"""Routing logic for the orchestrator agent.

Deep-agent style planning workflow (LangGraph) for the Amsterdam Orchestrator.
Takes a user prompt + context, runs Orchestrator (intent + clarify/plan).
CLARIFY: returns questions. PLAN: itinerary skeleton + routing_plan.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, SecretStr, ValidationError

from langgraph.graph import StateGraph, END

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


# -------------------------
# Helpers
# -------------------------

def load_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def safe_json_loads(text: str) -> Dict[str, Any]:
    t = text.strip()
    # Strip fenced blocks if model returns them
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    return json.loads(t)


def llm_json(llm: BaseChatModel, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls an LLM and expects JSON back (dict).
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]
    resp = llm.invoke(messages)
    raw: str
    if isinstance(resp.content, str):
        raw = resp.content
    else:
        parts = [
            b.get("text", "") if isinstance(b, dict) else str(b)
            for b in (resp.content or [])
        ]
        raw = "".join(parts)
    return safe_json_loads(raw)


# -------------------------
# Pydantic schemas matching orchestrator prompt output
# -------------------------

Mode = Literal["CLARIFY", "PLAN"]
IntentMode = Literal["PLANNER", "TICKET", "BROWSER", "STROLLER"]


class ClarifyingQuestion(BaseModel):
    id: str
    question: str
    options: List[str] = Field(default_factory=list)
    why_needed: str


class Origin(BaseModel):
    label: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class TimeWindow(BaseModel):
    start: Optional[str] = None  # "HH:MM"
    end: Optional[str] = None


class Party(BaseModel):
    size: Optional[int] = None
    type: Literal["solo", "couple", "friends", "family", "business", "unknown"] = "unknown"


class UserIntent(BaseModel):
    request_type: Literal["itinerary", "recommendations"]
    date: Optional[str] = None  # "YYYY-MM-DD"
    time_window: TimeWindow = Field(default_factory=TimeWindow)
    party: Party = Field(default_factory=Party)
    budget: Optional[str] = None
    vibe: List[str] = Field(default_factory=list)
    origin: Origin = Field(default_factory=Origin)


class SkeletonSlotConstraints(BaseModel):
    vibe: List[str] = Field(default_factory=list)
    indoors: Optional[bool] = None
    budget: Optional[str] = None


class SkeletonSlot(BaseModel):
    slot: str
    time: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: str
    constraints: SkeletonSlotConstraints = Field(default_factory=SkeletonSlotConstraints)


class RoutingCall(BaseModel):
    agent: Literal["Gastronomist", "Socialite", "Lumière", "Weerman"]
    priority: int
    task: str  # Comprehensive task description (3-5 sentences): objective, context, constraints, expected behavior
    context: Dict[str, Any] = Field(default_factory=dict)  # Full user context (party, vibe, time, area, etc.)
    query: Dict[str, Any]  # structured_constraints for machine-readable params
    expected_result_count: int = 10


class Safety(BaseModel):
    no_invention: bool = True
    notes: str


class OrchestratorOutput(BaseModel):
    mode: Mode
    intent_mode: IntentMode
    clarifying_questions: List[ClarifyingQuestion] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    user_intent: UserIntent
    itinerary_skeleton: List[SkeletonSlot] = Field(default_factory=list)
    routing_plan: List[RoutingCall] = Field(default_factory=list)
    safety: Safety


# -------------------------
# LangGraph State
# -------------------------

class PlanState(TypedDict, total=False):
    # inputs
    user_message: str
    now: str  # ISO time in Europe/Amsterdam
    user_context: Dict[str, Any]  # {lat, lon, location_label, local_or_tourist, language}
    signals: Dict[str, Any]  # {weather: {...}}

    # outputs
    orchestrator_raw: Dict[str, Any]
    orchestrator: Dict[str, Any]
    mode: Mode
    intent_mode: IntentMode
    final_answer: str


# -------------------------
# Nodes
# -------------------------

def orchestrator_node_factory(llm: BaseChatModel, prompt_path: str):
    system_prompt = load_prompt(prompt_path)

    def orchestrator_node(state: PlanState) -> PlanState:
        payload = {
            "user_message": state.get("user_message", ""),
            "now": state.get("now"),
            "user_context": state.get("user_context", {}),
            "signals": state.get("signals", {}),
        }

        raw = llm_json(llm, system_prompt, payload)
        state["orchestrator_raw"] = raw

        try:
            parsed = OrchestratorOutput.model_validate(raw)
        except ValidationError as e:
            # fail closed into CLARIFY
            state["orchestrator"] = {}
            state["mode"] = "CLARIFY"
            state["intent_mode"] = "PLANNER"
            state["final_answer"] = (
                "I’m missing a couple details to plan this. "
                "How many people is it for, what budget (€ / €€ / €€€), and what vibe do you want?"
            )
            return state

        state["orchestrator"] = parsed.model_dump()
        state["mode"] = parsed.mode
        state["intent_mode"] = parsed.intent_mode

        # Create a user-facing answer (simple, deterministic) from parsed JSON
        if parsed.mode == "CLARIFY":
            lines = ["Quick questions so I can plan this properly:"]
            for q in parsed.clarifying_questions[:3]:
                lines.append(f"- {q.question}")
            if parsed.assumptions:
                lines.append("")
                lines.append("Assumptions I made (tell me if wrong):")
                for a in parsed.assumptions:
                    lines.append(f"- {a}")
            state["final_answer"] = "\n".join(lines)
        else:
            # PLAN
            lines = ["**Plan**"]
            for s in parsed.itinerary_skeleton:
                t = s.time or "TBD"
                lines.append(f"- **{t}** — {s.slot} ({s.duration_minutes or 'TBD'} min)")
                if s.notes:
                    lines.append(f"  {s.notes}")
            lines.append("")
            lines.append("**Tasks per sub-agent**")
            for call in sorted(parsed.routing_plan, key=lambda c: c.priority):
                task = getattr(call, "task", None) or ""
                brief = f"{call.agent} (priority {call.priority}): {task}"
                if call.expected_result_count and call.expected_result_count != 10:
                    brief += f" [fetch {call.expected_result_count} options]"
                lines.append(f"- {brief}")
            if parsed.assumptions:
                lines.append("")
                lines.append("Assumptions:")
                for a in parsed.assumptions:
                    lines.append(f"- {a}")
            state["final_answer"] = "\n".join(lines)

        return state

    return orchestrator_node


def route_by_mode(state: PlanState) -> str:
    return state.get("mode", "CLARIFY")


# -------------------------
# Build workflow
# -------------------------

def build_workflow(llm: BaseChatModel, orchestrator_prompt_path: str):
    g = StateGraph(PlanState)

    g.add_node("orchestrator", orchestrator_node_factory(llm, orchestrator_prompt_path))

    g.set_entry_point("orchestrator")
    # Right now orchestrator is terminal (later you’ll add executor/blender nodes)
    g.add_conditional_edges(
        "orchestrator",
        route_by_mode,
        {
            "CLARIFY": END,
            "PLAN": END
        }
    )
    return g.compile()


# -------------------------
# Interactive run
# -------------------------

def _format_transcript(turns: List[tuple[str, str]], current: str) -> str:
    """Format conversation history + current user message for orchestrator."""
    parts: List[str] = []
    for u, a in turns:
        parts.append(f"User: {u}")
        parts.append(f"Assistant: {a}")
    parts.append(f"User: {current}")
    return "\n\n".join(parts)


def _default_state(user_message: str, conversation: List[tuple[str, str]] | None = None) -> PlanState:
    """Build default plan state for interactive use."""
    tz = ZoneInfo("Europe/Amsterdam")
    now = datetime.now(tz).isoformat()
    msg = _format_transcript(conversation or [], user_message)
    return {
        "user_message": msg,
        "now": now,
        "user_context": {
            "location_label": None,
            "lat": None,
            "lon": None,
            "local_or_tourist": "unknown",
            "language": "en",
        },
        "signals": {"weather": {"condition": "unknown", "temp_c": None}},
    }


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        for d in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
            env = d / ".env"
            if env.is_file():
                load_dotenv(env)
                break
    except ImportError:
        pass

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not set. Set it in .env or your environment.")
        raise SystemExit(1)

    llm: BaseChatModel = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "o4-mini"),
        api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
    )

    prompt_path = Path(__file__).resolve().parent / "agent.md"
    workflow = build_workflow(llm=llm, orchestrator_prompt_path=str(prompt_path))

    print("Orchestrator — Plan Amsterdam activities. Type your request, or 'quit' / 'exit' to stop.\n")

    conversation: List[tuple[str, str]] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye", "q"):
            print("Bye.")
            break

        state = _default_state(user_input, conversation)
        result = workflow.invoke(state)
        final = result.get("final_answer", "(no reply)")

        print("\nOrchestrator:")
        print(final)
        print(f"\n[MODE: {result.get('mode', '?')}]\n")

        conversation.append((user_input, final))
