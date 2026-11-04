"""
Multi-tenant and configurable scoring weights for SaaS subscription tiers.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TenantConfig:
    tenant_id: str = "default"
    tier: str = "pro"  # free, pro, agency, enterprise
    max_candidates_per_run: int = 100
    allow_pdf_export: bool = True
    ai_drafts_quota: int = 50
    custom_branding: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TenantConfig":
        return cls(
            tenant_id=data.get("tenant_id", "default"),
            tier=data.get("tier", "pro"),
            max_candidates_per_run=data.get("max_candidates_per_run", 100),
            allow_pdf_export=data.get("allow_pdf_export", True),
            ai_drafts_quota=data.get("ai_drafts_quota", 50),
            custom_branding=data.get("custom_branding", False),
        )


@dataclass
class ScoringConfig:
    follower_fit: float = 0.20
    engagement_rate: float = 0.25
    content_fit: float = 0.25
    audience_region: float = 0.15
    price_vs_budget: float = 0.15

    def normalized(self) -> "ScoringConfig":
        """Return a copy with weights normalized to sum to 1.0."""
        total = (
            self.follower_fit
            + self.engagement_rate
            + self.content_fit
            + self.audience_region
            + self.price_vs_budget
        )
        if total <= 0:
            return ScoringConfig()
        return ScoringConfig(
            follower_fit=self.follower_fit / total,
            engagement_rate=self.engagement_rate / total,
            content_fit=self.content_fit / total,
            audience_region=self.audience_region / total,
            price_vs_budget=self.price_vs_budget / total,
        )

    def as_dict(self) -> Dict[str, float]:
        n = self.normalized()
        return {
            "Follower Fit": n.follower_fit,
            "Engagement Rate": n.engagement_rate,
            "Content Fit": n.content_fit,
            "Audience Region": n.audience_region,
            "Price vs. Budget": n.price_vs_budget,
        }
