"""
MCP server exposing creator-sourcing tools for OKX.AI A2MCP registration.

Run locally:
    pip install mcp
    python mcp_server.py

Expose to the internet (for OKX.AI):
    cloudflared tunnel --url http://localhost:8000

The public URL + /mcp is your A2MCP endpoint.
"""

import json

from mcp.server.fastmcp import FastMCP

from core_logic import source_and_score


mcp = FastMCP(
    "creator-sourcing",
    instructions=(
        "Source and score micro-influencers for a brand campaign. "
        "Accepts a JSON list of candidate objects and returns a scored shortlist."
    ),
)


@mcp.tool()
def source_creators(
    product: str,
    target_market: str,
    budget_max: int,
    keywords: str,
    candidates_json: str,
) -> list:
    """
    Source and score creators based on a brand brief.

    Args:
        product: Product or service name (e.g., "Taiwanese skincare brand").
        target_market: Target market (e.g., "Southeast Asia, North America").
        budget_max: Maximum budget per creator in TWD.
        keywords: Comma-separated content keywords (e.g., "skincare, beauty").
        candidates_json: JSON array of candidate objects. Each must contain:
            name, platform, followers, engagement_rate, estimated_price,
            audience_region, content_keywords

    Returns:
        List of scored candidates with total_score and per-criterion scores.
    """
    try:
        candidates = json.loads(candidates_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"candidates_json is not valid JSON: {e}")

    if not isinstance(candidates, list) or len(candidates) == 0:
        raise ValueError("candidates_json must be a non-empty JSON array")

    brief = {
        "product": product,
        "target_market": target_market,
        "goal": "",
        "budget_max": budget_max,
        "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
    }

    return source_and_score(candidates=candidates, brief=brief)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
