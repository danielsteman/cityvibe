"""De Buik PostGIS queries and tools for the Gastronomist agent."""

import os
from typing import Any

import psycopg2
from loguru import logger
from psycopg2.extras import RealDictCursor

# --- CONFIGURATION ---
# Note: DATABASE_URL is read dynamically in get_db_connection() to ensure
# .env file is loaded before accessing it

def get_db_connection():
    """
    Create a database connection to the De Buik database.

    Returns:
        psycopg2.connection: Database connection with RealDictCursor factory.

    Raises:
        ValueError: If DATABASE_URL environment variable is not set.
        psycopg2.Error: If connection to database fails.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in environment variables.")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

def find_restaurants(
    lat: float,
    lon: float,
    radius_meters: int = 500,
    required_tags: list[str] | None = None,
    price_preference: str | None = None,
    limit: int = 5
) -> list[dict[str, Any]]:
    """
    Find restaurants and venues using PostGIS distance and tag filtering.

    Searches the De Buik database for venues within a specified radius of a
    given location, optionally filtered by tags and price preference. Results
    are sorted by distance (closest first).

    Args:
        lat: Latitude of the search center point.
        lon: Longitude of the search center point.
        radius_meters: Search radius in meters. Defaults to 500.
        required_tags: List of tags to filter by (e.g., ["Italian", "Cozy"]).
            Uses OR logic - matches venues with any of the specified tags.
            Defaults to None (no tag filtering).
        price_preference: Price preference string. Accepted values:
            - "cheap" or "small" -> € only
            - "moderate" -> € or €€
            - "expensive" or "fine" -> €€ or €€€
            Defaults to None (no price filtering).
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        List of venue dictionaries, each containing:
        - name: Venue name
        - description: Venue description
        - venue_type: Type of venue
        - price_symbol: Price indicator (€, €€, €€€)
        - tags: List of venue tags
        - opening_hours: Opening hours information
        - booking_url: URL for booking
        - distance_meters: Distance from search center in meters

    Raises:
        psycopg2.Error: If database query fails. Errors are logged and
            an empty list is returned.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Base Query
    # We cast location to geography to get meters distance
    query = """
    SELECT 
        name,
        description,
        venue_type,
        price_range as price_symbol,
        tags,
        opening_hours,
        website_url as booking_url,
        ST_Distance(
            location::geography, 
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        ) as distance_meters
    FROM venue
    WHERE source = 'debuik'
      AND ST_DWithin(
          location::geography,
          ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
          %s
      )
    """
    params = [lon, lat, lon, lat, radius_meters]

    # 1. TAG FILTERING (Loose Match on JSONB Array)
    if required_tags and len(required_tags) > 0:
        tag_conditions = []
        for tag in required_tags:
            # We use ILIKE on the text representation of the JSON array
            # This catches "Cozy" inside ["Cozy", "Bar"]
            tag_conditions.append("tags::text ILIKE %s")
            params.append(f"%{tag}%")
        
        # Logic: Match ANY of the requested tags (OR)
        # Change to AND if you want strict matching
        query += " AND (" + " OR ".join(tag_conditions) + ")"

    # 2. PRICE FILTERING
    if price_preference:
        p = price_preference.lower()
        if "cheap" in p or "small" in p:
            query += " AND price_range = '€'"
        elif "moderate" in p:
            query += " AND (price_range = '€' OR price_range = '€€')"
        elif "expensive" in p or "fine" in p:
            query += " AND (price_range = '€€' OR price_range = '€€€')"

    # 3. SORT & LIMIT
    query += " ORDER BY distance_meters ASC LIMIT %s"
    params.append(limit)

    try:
        cur.execute(query, tuple(params))
        results = cur.fetchall()
        
        # Cleanup for JSON serialization
        clean_results = []
        for row in results:
            row_dict = dict(row)
            row_dict['distance_meters'] = int(row_dict['distance_meters'])
            clean_results.append(row_dict)
            
        return clean_results
    except Exception as e:
        logger.error(f"❌ Error querying De Buik database: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def find_restaurants_with_rag(
    query_embedding: list[float],
    lat: float,
    lon: float,
    radius_meters: int = 500,
    required_tags: list[str] | None = None,
    price_preference: str | None = None,
    similarity_threshold: float = 0.3,
    limit: int = 5
) -> list[dict[str, Any]]:
    """
    Find restaurants using RAG: vector similarity search combined with location filtering.

    Searches venues using semantic similarity (cosine distance) on embeddings combined
    with PostGIS distance filtering. Results are ranked by a combination of semantic
    similarity and geographic proximity.

    Args:
        query_embedding: Vector embedding of the user's query (1024 dimensions).
        lat: Latitude of the search center point.
        lon: Longitude of the search center point.
        radius_meters: Search radius in meters. Defaults to 500.
        required_tags: List of tags to filter by (e.g., ["Italian", "Cozy"]).
            Uses OR logic - matches venues with any of the specified tags.
            Defaults to None (no tag filtering).
        price_preference: Price preference string. Accepted values:
            - "cheap" or "small" -> € only
            - "moderate" -> € or €€
            - "expensive" or "fine" -> €€ or €€€
            Defaults to None (no price filtering).
        similarity_threshold: Minimum cosine similarity score (0-1). Lower values
            allow more diverse results. Defaults to 0.3.
        limit: Maximum number of results to return. Defaults to 5.

    Returns:
        List of venue dictionaries, each containing:
        - name: Venue name
        - description: Venue description
        - venue_type: Type of venue
        - price_symbol: Price indicator (€, €€, €€€)
        - tags: List of venue tags
        - opening_hours: Opening hours information
        - booking_url: URL for booking
        - distance_meters: Distance from search center in meters
        - similarity_score: Cosine similarity score (1 - distance)

    Raises:
        psycopg2.Error: If database query fails. Errors are logged and
            an empty list is returned.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Convert embedding list to PostgreSQL vector format string
    # pgvector accepts string format like '[0.1, 0.2, ...]'
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Base Query with Vector Similarity + Location Filtering
    # We use cosine distance operator (<=>) which returns distance (lower = more similar)
    # 1 - distance gives us similarity (higher = more similar)
    # Note: We use string interpolation for vector literal (safe since it's numeric)
    query = f"""
    SELECT 
        name,
        description,
        venue_type,
        price_range as price_symbol,
        tags,
        opening_hours,
        website_url as booking_url,
        ST_Distance(
            location::geography, 
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        ) as distance_meters,
        (1 - (vibe_embedding <=> '{embedding_str}'::vector)) as similarity_score
    FROM venue
    WHERE source = 'debuik'
      AND vibe_embedding IS NOT NULL
      AND (1 - (vibe_embedding <=> '{embedding_str}'::vector)) >= %s
      AND ST_DWithin(
          location::geography,
          ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
          %s
      )
    """
    params = [lon, lat, similarity_threshold, lon, lat, radius_meters]

    # 1. TAG FILTERING (Loose Match on JSONB Array)
    if required_tags and len(required_tags) > 0:
        tag_conditions = []
        for tag in required_tags:
            tag_conditions.append("tags::text ILIKE %s")
            params.append(f"%{tag}%")
        
        query += " AND (" + " OR ".join(tag_conditions) + ")"

    # 2. PRICE FILTERING
    if price_preference:
        p = price_preference.lower()
        if "cheap" in p or "small" in p:
            query += " AND price_range = '€'"
        elif "moderate" in p:
            query += " AND (price_range = '€' OR price_range = '€€')"
        elif "expensive" in p or "fine" in p:
            query += " AND (price_range = '€€' OR price_range = '€€€')"

    # 3. SORT BY COMBINED SCORE (similarity first, then distance)
    # Higher similarity = better semantic match
    # Lower distance = closer to location
    query += """
    ORDER BY similarity_score DESC, distance_meters ASC
    LIMIT %s
    """
    params.append(limit)

    try:
        cur.execute(query, tuple(params))
        results = cur.fetchall()
        
        # Cleanup for JSON serialization
        clean_results = []
        for row in results:
            row_dict = dict(row)
            row_dict['distance_meters'] = int(row_dict['distance_meters'])
            # Round similarity score to 3 decimals
            if row_dict.get('similarity_score') is not None:
                row_dict['similarity_score'] = round(float(row_dict['similarity_score']), 3)
            clean_results.append(row_dict)
            
        logger.info(f"🔍 RAG search found {len(clean_results)} venues")
        return clean_results
    except Exception as e:
        logger.error(f"❌ Error in RAG query: {e}")
        return []
    finally:
        cur.close()
        conn.close()