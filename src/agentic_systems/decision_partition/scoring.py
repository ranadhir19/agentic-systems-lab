"""Complexity scoring for decisions.

Core model (from the concept):

    score = |partition blocks| x category weight

with category weights simple = 1.0, composite = 2.0, and complexity levels
high (score >= 10), medium (5 <= score < 10), low (score < 5).

Optional cost add-ons let compute and latency influence the effective
score, so a nominally simple but expensive decision can earn a dedicated
agent:

    effective = base + w_lat * (latency_ms / latency_ref)
                    + w_cmp * (compute_cost / compute_ref)

Weights are in score-units per reference unit; the references normalize
latency and compute into the same units as the base score.
"""
from __future__ import annotations

from dataclasses import dataclass

from .decisions import COMPOSITE, SIMPLE, Decision

CATEGORY_WEIGHTS = {SIMPLE: 1.0, COMPOSITE: 2.0}

LOW_MAX = 5.0   # score < 5  -> "low"
HIGH_MIN = 10.0  # score >= 10 -> "high"

HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def complexity_score(decision: Decision,
                     weights: dict[str, float] | None = None) -> float:
    """Base complexity score: |blocks| x category weight."""
    w = (weights or CATEGORY_WEIGHTS)[decision.category]
    return float(len(decision.blocks)) * w


def complexity_level(score: float,
                     low_max: float = LOW_MAX,
                     high_min: float = HIGH_MIN) -> str:
    """Bucket a score into high / medium / low."""
    if score >= high_min:
        return HIGH
    if score >= low_max:
        return MEDIUM
    return LOW


def effective_score(decision: Decision,
                    weights: dict[str, float] | None = None,
                    latency_weight: float = 0.0,
                    compute_weight: float = 0.0,
                    latency_ref_ms: float = 1000.0,
                    compute_ref: float = 10.0) -> float:
    """Base score plus normalized compute/latency add-ons."""
    base = complexity_score(decision, weights)
    lat_term = latency_weight * (decision.latency_ms / latency_ref_ms)
    cmp_term = compute_weight * (decision.compute_cost / compute_ref)
    return base + lat_term + cmp_term


@dataclass
class Scorer:
    """Configurable scorer: weights, thresholds, and cost add-ons."""

    weights: dict[str, float] | None = None
    low_max: float = LOW_MAX
    high_min: float = HIGH_MIN
    latency_weight: float = 0.0
    compute_weight: float = 0.0
    latency_ref_ms: float = 1000.0
    compute_ref: float = 10.0

    def score(self, decision: Decision) -> float:
        return effective_score(
            decision,
            weights=self.weights,
            latency_weight=self.latency_weight,
            compute_weight=self.compute_weight,
            latency_ref_ms=self.latency_ref_ms,
            compute_ref=self.compute_ref,
        )

    def base_score(self, decision: Decision) -> float:
        return complexity_score(decision, self.weights)

    def level(self, decision: Decision) -> str:
        return complexity_level(self.score(decision), self.low_max, self.high_min)

    def level_of_score(self, score: float) -> str:
        return complexity_level(score, self.low_max, self.high_min)
