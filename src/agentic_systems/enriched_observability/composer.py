"""Insight composer: human-readable enriched narratives.

These templates stand in for LLM-based log summarization. The text is
deterministic and seeded; the measured scientific contribution is the
enrichment pipeline (raw -> processed -> analytic), not the prose quality.
The README states this limitation explicitly.
"""
from __future__ import annotations


def compose_layer_insight(ev: dict, driver: str | None = None) -> str:
    """One enriched narrative for an analytic event record."""
    base = (f"{ev['layer'].title()} signal `{ev['metric']}` anomalous from "
            f"minute {ev['start']} to {ev['end']} (peak |z|={ev['peak_z']}). "
            f"Failure probability {ev['failure_probability']:.0%}; "
            f"impact score {ev['impact_score']:.2f}.")
    if driver:
        base += (f" Correlated driver: {driver} "
                 f"(root-cause confidence {ev['root_cause_confidence']:.0%}).")
    if ev["time_to_breach_min"] is not None:
        base += (f" Threshold breach forecast in "
                 f"{ev['time_to_breach_min']:.0f} minutes.")
    base += f" Recommended action: {ev['recommended_action']}"
    return base


def compose_chain_narrative(chain: list[dict]) -> str:
    """Cross-layer causal chain narrative for the cascade."""
    if not chain:
        return "No cross-layer causal chain reconstructed."
    lines = ["Reconstructed causal chain (onset order):"]
    for i, link in enumerate(chain, 1):
        lines.append(
            f"{i}. [{link['layer']}] {link['metric']} @ minute {link['onset']} "
            f"-- {link['label']} (link confidence {link['confidence']:.0%})")
    return "\n".join(lines)


def compose_executive_summary(chain: list[dict], business_ev: dict) -> str:
    """Boardroom-ready summary from the business-layer analytic record."""
    rev = business_ev.get("revenue_at_risk_m_per_hr", 0.0)
    return (
        f"EXECUTIVE SUMMARY: {len(chain)}-layer incident chain detected. "
        f"Revenue at risk ${rev:.1f}M/hour. Root-cause confidence "
        f"{business_ev.get('root_cause_confidence', 0):.0%}. "
        f"Impact score {business_ev.get('impact_score', 0):.2f}. "
        f"Recommended: {business_ev.get('recommended_action', 'investigate')}")
