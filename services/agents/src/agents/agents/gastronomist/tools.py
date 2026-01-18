"""De Buik PostGIS queries and tools for the Gastronomist agent."""

import os
from typing import Any

import psycopg2
from loguru import logger
from psycopg2.extras import RealDictCursor

# --- CONFIGURATION ---
DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """
    Create a database connection to the De Buik database.

    Returns:
        psycopg2.connection: Database connection with RealDictCursor factory.

    Raises:
        ValueError: If DATABASE_URL environment variable is not set.
        psycopg2.Error: If connection to database fails.
    """
    if not DB_URL:
        raise ValueError("DATABASE_URL is not set in environment variables.")
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

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
        price_symbol,
        tags,
        opening_hours,
        url as booking_url,
        ST_Distance(
            location::geography, 
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        ) as distance_meters
    FROM venues
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
            query += " AND price_symbol = '€'"
        elif "moderate" in p:
            query += " AND (price_symbol = '€' OR price_symbol = '€€')"
        elif "expensive" in p or "fine" in p:
            query += " AND (price_symbol = '€€' OR price_symbol = '€€€')"

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