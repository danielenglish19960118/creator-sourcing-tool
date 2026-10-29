"""
Pure business logic for creator sourcing. No Streamlit dependencies.

Used by both app.py (Streamlit UI) and mcp_server.py (MCP endpoint for OKX.AI).
"""

from typing import Optional

from scoring import score_candidates, DEFAULT_CRITERIA
from draft_generator import generate_outreach_drafts


def build_brief(
    product: str,
    target_market: str,
    goal: str = "",
    budget_min: int = 0,
    budget_max: int = 0,
    follower_range: tuple = (1000, 1_000_000),
    keywords: Optional[list] = None,
) -> dict:
    """Build a standardized brief dict."""
    return {
        "product": product,
        "target_market": target_market,
        "goal": goal,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "follower_range": follower_range,
        "keywords": keywords or [],
    }


def normalize_weights(weight_map: dict) -> dict:
    """Normalize weights to sum to 1.0; fall back to defaults if total <= 0."""
    total = sum(weight_map.values())
    if total <= 0:
        return {item["criterion"]: item["weight"] for item in DEFAULT_CRITERIA}
    return {k: v / total for k, v in weight_map.items()}


def source_and_score(
    candidates: list,
    brief: dict,
    weights: Optional[dict] = None,
) -> list:
    """
    Score candidates and return a JSON-serializable list of dicts.

    - candidates: list of candidate dicts
    - brief: from build_brief()
    - weights: optional dict mapping criterion name -> weight
    """
    df = score_candidates(candidates, brief, weights=weights)
    return df.to_dict(orient="records")


def create_drafts(
    brief: dict,
    candidate: dict,
    api_key: str,
) -> list:
    """Generate outreach drafts for a single candidate."""
    return generate_outreach_drafts(brief, candidate, api_key=api_key)
