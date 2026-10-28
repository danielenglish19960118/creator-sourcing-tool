import pandas as pd


# 默认筛选维度与权重
DEFAULT_CRITERIA = [
    {"criterion": "粉丝数匹配", "weight": 0.20, "how_to_check": "粉丝数落在目标区间"},
    {"criterion": "互动率", "weight": 0.25, "how_to_check": "互动率高于行业中位数"},
    {"criterion": "内容调性匹配", "weight": 0.25, "how_to_check": "内容关键词与品牌调性一致"},
    {"criterion": "受众地区匹配", "weight": 0.15, "how_to_check": "受众主要位于目标市场"},
    {"criterion": "报价在预算内", "weight": 0.15, "how_to_check": "预估报价不超过预算上限"},
]


def score_candidates(candidates: list[dict], brief: dict) -> pd.DataFrame:
    """
    candidates: 每个 dict 至少包含 name, followers, engagement_rate,
                content_keywords(list), audience_region, estimated_price
    brief: 客户填写的需求
    """
    rows = []
    for c in candidates:
        scores = {}
        reasons = []

        # 1. 粉丝数匹配
        follower_score = _score_followers(c.get("followers", 0), brief.get("follower_range"))
        scores["粉丝数匹配"] = follower_score
        reasons.append(f"粉丝数 {_fmt_num(c.get('followers', 0))} -> {'匹配' if follower_score >= 3 else '偏差'}")

        # 2. 互动率
        eng = c.get("engagement_rate", 0)
        eng_score = _score_engagement(eng)
        scores["互动率"] = eng_score
        reasons.append(f"互动率 {eng:.2%} -> {'良好' if eng_score >= 3 else '偏低'}")

        # 3. 内容调性（关键词重合）
        target_kw = set(brief.get("keywords", []))
        content_kw = set(c.get("content_keywords", []))
        overlap = len(target_kw & content_kw) / max(len(target_kw), 1)
        kw_score = min(5, max(1, round(overlap * 5)))
        scores["内容调性匹配"] = kw_score
        reasons.append(f"关键词重合 {overlap:.0%}")

        # 4. 受众地区
        region_score = 5 if c.get("audience_region") == brief.get("target_market") else 2
        scores["受众地区匹配"] = region_score

        # 5. 报价
        price = c.get("estimated_price", 0)
        budget = brief.get("budget_max", 0)
        if budget and price:
            price_score = 5 if price <= budget else (3 if price <= budget * 1.2 else 1)
        else:
            price_score = 3  # 未知
        scores["报价在预算内"] = price_score

        # 加权总分
        total = sum(
            scores[item["criterion"]] * item["weight"]
            for item in DEFAULT_CRITERIA
        )

        rows.append({
            "name": c.get("name", ""),
            "platform": c.get("platform", ""),
            "followers": c.get("followers", 0),
            "engagement_rate": c.get("engagement_rate", 0),
            "estimated_price": c.get("estimated_price", 0),
            **scores,
            "total_score": round(total, 2),
            "notes": "; ".join(reasons),
        })

    df = pd.DataFrame(rows).sort_values("total_score", ascending=False).reset_index(drop=True)
    return df


def _score_followers(n: int, target_range: tuple | None) -> int:
    if not target_range:
        return 3
    low, high = target_range
    if low <= n <= high:
        return 5
    if n < low * 0.5 or n > high * 2:
        return 1
    return 3


def _score_engagement(rate: float) -> int:
    if rate >= 0.05:
        return 5
    if rate >= 0.02:
        return 4
    if rate >= 0.01:
        return 3
    return 2


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)
