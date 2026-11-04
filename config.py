"""
Pure business logic for creator sourcing. No Streamlit dependencies.

Used by both app.py (Streamlit UI) and mcp_server.py (MCP endpoint for AI agents).
"""

from typing import Optional, List, Dict, Any

from scoring import score_candidates, DEFAULT_CRITERIA
from draft_generator import generate_outreach_drafts


def build_brief(
    product: str,
    target_market: str,
    goal: str = "",
    budget_min: int = 0,
    budget_max: int = 0,
    follower_range: tuple = (1000, 1_000_000),
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a standardized campaign brief dictionary."""
    return {
        "product": product,
        "target_market": target_market,
        "goal": goal,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "follower_range": follower_range,
        "keywords": keywords or [],
    }


def normalize_weights(weight_map: Dict[str, float]) -> Dict[str, float]:
    """Normalize scoring weights to sum to 1.0; fall back to defaults if total <= 0."""
    total = sum(weight_map.values())
    if total <= 0:
        return {item["criterion"]: item["weight"] for item in DEFAULT_CRITERIA}
    return {k: v / total for k, v in weight_map.items()}


def source_and_score(
    candidates: List[Dict[str, Any]],
    brief: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Score candidates against a brief and return a JSON-serializable list of records.
    """
    df = score_candidates(candidates, brief, weights=weights)
    return df.to_dict(orient="records")


def create_drafts(
    brief: Dict[str, Any],
    candidate: Dict[str, Any],
    api_key: str,
) -> List[Dict[str, str]]:
    """Generate customized English outreach drafts for a selected candidate."""
    return generate_outreach_drafts(brief, candidate, api_key=api_key)
