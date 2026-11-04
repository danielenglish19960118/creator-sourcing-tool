"""
Enhanced MCP server exposing creator-sourcing tools for enterprise AI agents,
equipped with basic API key validation for rental/subscription models.
"""

import json
import os
from mcp.server.fastmcp import FastMCP
from core_logic import source_and_score

mcp = FastMCP(
    "creator-sourcing-saas",
    instructions=(
        "Enterprise-grade creator sourcing and scoring microservice. "
        "Requires a valid tenant subscription key."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("MCP_PORT", 8000)),
)

@mcp.tool()
def source_creators_secure(
    api_token: str,
    product: str,
    target_market: str,
    budget_max: int,
    keywords: str,
    candidates_json: str,
) -> list:
    """
    Securely source and score creators based on a brand brief with token validation.
    """
    expected_token = os.environ.get("SAAS_MASTER_TOKEN", "demo-token-123")
    if api_token != expected_token:
        raise PermissionError("Invalid or expired SaaS subscription token.")

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
    mcp.run(transport="streamable-http")
