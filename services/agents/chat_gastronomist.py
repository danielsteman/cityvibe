"""Run RAG retrieval for a query and print which venues are returned.

Usage:
    uv run python chat_gastronomist.py "cozy Italian restaurant in Jordaan"
    uv run python chat_gastronomist.py "breakfast spot" --location "de pijp" --limit 15

If results are poor (e.g. wrong cuisine): embeddings include Cuisine from
features.kitchen. Regenerate them after updating vibe text:

    python scripts/generate_embeddings.py --regenerate
    # or with limit:  python scripts/generate_embeddings.py 500 --regenerate
"""

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from loguru import logger

from agents.agents.gastronomist.tools import find_restaurants, find_restaurants_with_rag

# Load .env from project root
for parent in [Path(__file__).resolve().parent] + list(Path(__file__).resolve().parents):
    env_file = parent / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)
        break

# Amsterdam neighborhood -> (lat, lon)
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
    "museumplein": (52.3582, 4.8814),
}


def resolve_location(name: str | None) -> tuple[float, float]:
    """Resolve location name to (lat, lon). Defaults to center if unknown."""
    if name:
        key = name.lower().strip()
        for loc, coords in AMSTERDAM_LOCATIONS.items():
            if loc in key:
                return coords[0], coords[1]
    return AMSTERDAM_LOCATIONS["center"]


def embed_query(text: str, api_url: str) -> list[float] | None:
    """Get embedding for text via embeddings API. Returns None on failure."""
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{api_url}/embed", json={"text": text})
            r.raise_for_status()
            return r.json()["embedding"]
    except Exception as e:
        logger.warning(f"⚠️ Embeddings API error: {e}")
        return None


def print_venues(venues: list[dict], *, rag: bool) -> None:
    """Print retrieved venues with similarity (if RAG) and other fields."""
    if not venues:
        print("No venues found.")
        return

    kind = "RAG" if rag else "non-RAG"
    print(f"\n📋 Retrieved {len(venues)} venues ({kind})\n")
    print("-" * 80)

    for i, v in enumerate(venues, 1):
        name = v.get("name", "?")
        vtype = v.get("venue_type", "")
        price = v.get("price_symbol", "")
        dist = v.get("distance_meters", 0)
        tags = v.get("tags", [])
        raw = v.get("description") or ""
        desc = raw[:120] + "..." if len(raw) > 120 else raw

        line = f"{i}. {name}  ({vtype})  {price}  ·  {dist} m away"
        if rag and "similarity_score" in v:
            line += f"  ·  similarity {v['similarity_score']:.3f}"
        print(line)
        if tags:
            print(f"   🏷️  {', '.join(str(t) for t in tags[:6])}")
        if desc:
            print(f"   📝 {desc}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run RAG retrieval for a query and print which venues are returned."
    )
    parser.add_argument("query", help="Search query (e.g. 'cozy Italian in Jordaan')")
    parser.add_argument(
        "--location",
        default="center",
        help="Area in Amsterdam (e.g. jordaan, de pijp, center). Default: center",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max venues to return (default 10)")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.45,
        help="Min similarity for RAG (default 0.45). Lower = more recall, less precise.",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=800,
        help="Search radius in meters (default 800)",
    )
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not set. Set it in .env.")
        sys.exit(1)
    # Gastronomist tools use psycopg2 (sync). Convert async URL if present.
    if "+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        os.environ["DATABASE_URL"] = db_url

    api_url = os.getenv("EMBEDDINGS_API_URL", "http://localhost:8001")
    lat, lon = resolve_location(args.location)

    print(f"🔍 Query: \"{args.query}\"")
    print(f"📍 Location: {args.location} ({lat:.4f}, {lon:.4f})  |  radius={args.radius}m  |  limit={args.limit}")
    print()

    # 1. Try RAG
    embedding = embed_query(args.query, api_url)
    if embedding:
        logger.info("🚀 Using RAG (semantic search + location filter)")
        venues = find_restaurants_with_rag(
            query_embedding=embedding,
            lat=lat,
            lon=lon,
            radius_meters=args.radius,
            required_tags=None,
            price_preference=None,
            similarity_threshold=args.similarity_threshold,
            limit=args.limit,
        )
        print_venues(venues, rag=True)
    else:
        logger.info("🔍 Embeddings API unavailable — using non-RAG search (location + radius only)")
        venues = find_restaurants(
            lat=lat,
            lon=lon,
            radius_meters=args.radius,
            required_tags=None,
            price_preference=None,
            limit=args.limit,
        )
        print_venues(venues, rag=False)


if __name__ == "__main__":
    main()
