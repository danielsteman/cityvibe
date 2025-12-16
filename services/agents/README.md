# Agents Service

LangGraph-based multi-agent system for intelligent event recommendations.

## Structure

```
services/agents/
├── .env.example                # API Keys (OpenAI, Neon DB, etc.)
├── main.py                     # Entry point: Compiles the Graph & Run Loop
├── state.py                    # Shared TypedDict & Pydantic Models
├── utils.py                    # Helper to load agent.md files
├── database.py                 # PostGIS/Neon connection logic
├── agents/
│   ├── __init__.py
│   ├── orchestrator/           # Supervisor agent
│   │   ├── __init__.py
│   │   ├── agent.md            # The Supervisor Prompt
│   │   └── node.py             # Routing Logic
│   ├── lumiere/                # Movies agent
│   │   ├── __init__.py
│   │   ├── agent.md            # The "Director" Prompt
│   │   ├── node.py             # LangGraph Node
│   │   └── tools.py            # Filmladder SQL Queries
│   ├── gastronomist/           # Food agent
│   │   ├── __init__.py
│   │   ├── agent.md            # The "Foodie" Prompt
│   │   ├── node.py             # LangGraph Node
│   │   └── tools.py            # De Buik PostGIS Queries
│   ├── socialite/              # Events agent
│   │   ├── __init__.py
│   │   ├── agent.md            # The "Guide" Prompt
│   │   ├── node.py             # LangGraph Node
│   │   └── tools.py            # Iamsterdam Queries
│   └── weatherman/             # Weather/Logistics agent
│       ├── __init__.py
│       ├── agent.md            # The "Realist" Prompt
│       ├── node.py             # LangGraph Node
│       └── tools.py            # Weather API & Buffer Logic
```

