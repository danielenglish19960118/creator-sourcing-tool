"""
Candidate scoring and filtering engine.

Scores each candidate against the client brief using weighted criteria:
- Follower range fit
- Engagement rate
- Content keyword overlap
- Audience region match
- Price vs. budget

All score components are normalized to a 1-5 scale; the total is a weighted sum.
Weights can be overridden per call via the `weights` argument.
"""

from typing import Any, Optional, Tuple

import pandas as pd


# Default criteria and weights (must sum to 1.0)
DEFAULT_CRITERIA = [
    {"criterion": "Follower Fit",     "weight": 0.20, "how_to_check": "Followers fall within target range"},
    {"criterion": "Engagement Rate",  "weight": 0.25, "how_to_check": "Engagement is above industry median"},
    {"criterion": "Content Fit",      "weight": 0.25, "how_to_check": "Content keywords match brand tone"},
    {"criterion": "Audience Region",  "weight": 0.15, "how_to_check": "Audience is mainly in target market"},
    {"criterion": "Price vs. Budget", "weight": 0.15, "how_to_check": "Estimated price does not exceed budget"},
]


# ---------- Safe type conversion helpers ----------
def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float; return default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int; return default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _normalize_keywords(value: Any) -> set:
    """Normalize keyword input into a lowercase set of non-empty strings."""
    if value is None:
        return set()
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        return set()
    return {str(k).strip().lower() for k in items if str(k).strip()}


def _normalize_region(value: Any) -> str:
    """Normalize region string for comparison."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_follower_range(value: Any) -> Optional[Tuple[int, int]]:
    """Normalize follower range to a (low, high) tuple, or None."""
    if value is None:
        return None
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            low, high = int(value[0]), int(value[1])
            if low > high:
                low, high = high, low
            return (low, high)
    except (TypeError, ValueError):
        return None
    return None


def _normalize_weights(weights: Optional[dict]) -> dict:
    """
    Merge user-provided weights with defaults and normalize so they sum to 1.0.

    - Missing keys fall back to DEFAULT_CRITERIA weights.
    - Non-numeric or negative values fall back to the default for that key.
    - If the merged total is <= 0, use the default weights unchanged.
    """
    default_map = {item["criterion"]: item["weight"] for item in DEFAULT_CRITERIA}

    if not weights:
        return default_map

    merged = dict(default_map)
    for key, value in weights.items():
        if key not in merged:
            continue
        v = _safe_float(value, default=-1.0)
        if v < 0:
            continue
        merged[key] = v

    total = sum(merged.values())
    if total <= 0:
        return default_map

    return {k: v / total for k, v in merged.items()}


# ---------- Individual scoring functions ----------
def _score_followers(n: int, target_range: Optional[Tuple[int, int]]) -> int:
    """Score follower count fit against target range (1-5)."""
    if target_range is None:
        return 3
    low, high = target_range
    if low <= n <= high:
        return 5
    if n < low * 0.5 or n > high * 2:
        return 1
    return 3


def _score_engagement(rate: float) -> int:
    """Score engagement rate (1-5)."""
    if rate >= 0.05:
        return 5
    if rate >= 0.02:
        return 4
    if rate >= 0.01:
        return 3
    return 2


def _score_keywords(target_kw: set, content_kw: set) -> Tuple[int, float]:
    """Score keyword overlap (1-5) and return (score, overlap_ratio)."""
    if not target_kw:
        return 3, 0.0
    overlap = len(target_kw & content_kw) / len(target_kw)
    score = min(5, max(1, round(overlap * 5)))
    return score, overlap


def _score_region(candidate_region: str, target_market: str) -> int:
    """Score audience region match (1-5)."""
    if not candidate_region or not target_market:
        return 3
    if candidate_region == target_market:
        return 5
    if candidate_region in target_market or target_market in candidate_region:
        return 3
    return 2


def _score_price(price: float, budget_max: float) -> int:
    """Score price vs. budget (1-5)."""
    if budget_max <= 0 or price <= 0:
        return 3
    if price <= budget_max:
        return 5
    if price <= budget_max * 1.2:
        return 3
    return 1


def _fmt_num(n: int) -> str:
    """Format numbers for display (1.2K, 3.4M)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ---------- Main entry ----------
def score_candidates(
    candidates: list,
    brief: dict,
    weights: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Score candidates against the client brief.

    Each candidate dict should have at least:
        name, platform, followers, engagement_rate,
        content_keywords (list or comma-separated string),
        audience_region, estimated_price

    `weights` is an optional dict mapping criterion name -> weight,
    e.g. {"Follower Fit": 0.2, "Engagement Rate": 0.3, ...}.
    Missing keys fall back to DEFAULT_CRITERIA, and the final weights
    are normalized to sum to 1.0.

    Returns a DataFrame sorted by total_score descending.
    """
    if not candidates:
        return pd.DataFrame()

    normalized_weights = _normalize_weights(weights)

    target_kw = _normalize_keywords(brief.get("keywords"))
    target_market = _normalize_region(brief.get("target_market"))
    follower_range = _normalize_follower_range(brief.get("follower_range"))
    budget_max = _safe_float(brief.get("budget_max"), 0.0)

    rows = []
    for c in candidates:
        if not isinstance(c, dict):
            continue

        name = str(c.get("name") or "").strip()
        platform = str(c.get("platform") or "").strip()
        followers = _safe_int(c.get("followers"), 0)
        engagement = _safe_float(c.get("engagement_rate"), 0.0)
        price = _safe_float(c.get("estimated_price"), 0.0)
        content_kw = _normalize_keywords(c.get("content_keywords"))
        region = _normalize_region(c.get("audience_region"))

        # Score each criterion
        follower_score = _score_followers(followers, follower_range)
        engagement_score = _score_engagement(engagement)
        kw_score, kw_overlap = _score_keywords(target_kw, content_kw)
        region_score = _score_region(region, target_market)
        price_score = _score_price(price, budget_max)

        scores = {
            "Follower Fit":     follower_score,
            "Engagement Rate":  engagement_score,
            "Content Fit":      kw_score,
            "Audience Region":  region_score,
            "Price vs. Budget": price_score,
        }

        # Weighted total using the normalized weights
        total = sum(scores[k] * normalized_weights[k] for k in scores)

        # Human-readable notes
        notes = [
            f"Followers {_fmt_num(followers)} -> {'in range' if follower_score >= 3 else 'off target'}",
            f"Engagement {engagement:.2%} -> {'healthy' if engagement_score >= 3 else 'low'}",
            f"Keyword overlap {kw_overlap:.0%}",
        ]
        if region and target_market:
            notes.append(f"Region {'match' if region_score == 5 else 'mismatch'}")

        rows.append({
            "name": name,
            "platform": platform,
            "followers": followers,
            "engagement_rate": round(engagement, 4),
            "estimated_price": price,
            **scores,
            "total_score": round(total, 2),
            "notes": "; ".join(notes),
        })

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values("total_score", ascending=False)
        .reset_index(drop=True)
    )
