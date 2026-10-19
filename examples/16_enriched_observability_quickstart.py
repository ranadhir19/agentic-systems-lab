"""Enriched observability quickstart: one cascading incident, fully enriched.

Simulates a CDN TLS handshake failure cascading across all five layers,
runs the three-stage enrichment pipeline, reconstructs the causal chain,
and renders each role's view. Demonstrates the context chain: raw
telemetry -> processed signals -> analytic intelligence -> role slices.

Run:  python3 examples/16_enriched_observability_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.enriched_observability import (
    composer, correlate, roles, run_pipeline,
)
from agentic_systems.enriched_observability.roles import ROLES


def main() -> None:
    p = run_pipeline(seed=7)
    chain = p["chain"]
    rec, mae = correlate.chain_link_recall(chain)
    print(f"chain links={len(chain)}  link_recall={rec:.2f}  "
          f"onset_mae={mae:.1f} min")
    assert rec == 1.0, "cascade chain not fully reconstructed"

    print()
    print(composer.compose_chain_narrative(chain))
    print()
    for layer in ["application", "business"]:
        ev = p["analytics"].get(layer)
        if ev:
            print(composer.compose_layer_insight(ev))
            print()
    biz = p["analytics"]["business"]
    print(composer.compose_executive_summary(
        chain, {"revenue_at_risk_m_per_hr":
                biz.get("revenue_loss_per_hr_now", 0.0),
                "root_cause_confidence":
                biz.get("root_cause_confidence", 0.0),
                "impact_score": biz.get("impact_score", 0.0),
                "recommended_action": biz.get("recommended_action", "")}))
    print()
    for role in ROLES:
        view = roles.render_role_view(role, p["context"])
        score = roles.relevance_score(role, view)
        print(f"{role:12s} relevance={score:.2f} "
              f"fields={len(view)}")
        assert score >= 0.9, f"low relevance for {role}"

    print()
    print("One incident, one chain, five role-appropriate views.")


if __name__ == "__main__":
    main()
