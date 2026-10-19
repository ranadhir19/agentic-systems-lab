"""SRE-Observability quickstart: the boundary problem, found and fixed.

Simulates one day of telemetry across six observability layers with
injected intra-layer and cascading incidents, runs a per-layer observer
agent on each, and shows:

1. intra-layer incidents are detected in ~1 minute;
2. the boundary-assessment workflow identifies the service->product
   boundary as the observability blind spot, from telemetry alone;
3. installing the targeted fix (near-raw cross-layer visibility)
   restores that boundary;
4. the unified MAS responder handles a cascade with the right runbook
   and lower MTTR than siloed observers;
5. the strategy bridge recommends a reliability/innovation portfolio.

Run:  python3 examples/10_sre_observability_quickstart.py
"""
from __future__ import annotations

import numpy as np

from agentic_systems.sre_observability import (
    LAYERS,
    SiloedResponder,
    UnifiedResponder,
    assess_boundaries,
    assess_layers,
    install_export_fix,
    observe_all,
    rank_boundaries,
    recommend,
    reset_export_overrides,
    scorecard,
    simulate,
)


def main() -> None:
    sim = simulate(seed=0)
    alerts = observe_all(sim, seed=0)

    lstats = assess_layers(sim, alerts)
    intra_recall = np.mean([s.seg_recall for s in lstats.values()])
    intra_ttd = np.mean([s.mean_ttd for s in lstats.values()
                         if s.mean_ttd == s.mean_ttd])
    print(f"intra-layer: mean segment recall {intra_recall:.2f}, "
          f"mean time-to-detect {intra_ttd:.1f} min")

    bstats = assess_boundaries(sim, alerts)
    weakest = rank_boundaries(bstats)[0]
    print(f"weakest boundary (telemetry alone): "
          f"{weakest.boundary[0]}->{weakest.boundary[1]} "
          f"(recall {weakest.recall:.2f}, gap {weakest.gap:.2f})")
    assert weakest.boundary == ("service", "product")

    install_export_fix("service", "product")
    fixed = observe_all(sim, seed=0)
    after = assess_boundaries(sim, fixed)[("service", "product")]
    print(f"after targeted fix: service->product recall "
          f"{weakest.recall:.2f} -> {after.recall:.2f}")
    assert after.recall > weakest.recall
    reset_export_overrides()

    rng = np.random.default_rng(0)
    silo = SiloedResponder().respond(sim, alerts, np.random.default_rng(1))
    uni = UnifiedResponder().respond(sim, alerts, np.random.default_rng(1))
    s_mttr = np.mean([r["mttr_min"] for r in silo])
    u_mttr = np.mean([r["mttr_min"] for r in uni])
    s_ok = np.mean([r["correct"] for r in silo])
    u_ok = np.mean([r["correct"] for r in uni])
    print(f"cascades: siloed correct-runbook {s_ok:.0%}, MTTR {s_mttr:.0f} min"
          f" | unified correct-runbook {u_ok:.0%}, MTTR {u_mttr:.0f} min")

    rec = recommend(100)
    sc = scorecard(rec)
    print(f"Strategy: invest ${rec['cost']}k -> downtime "
          f"{sc['downtime_min']:.0f} min/qtr, strategic ROI "
          f"{sc['strategic_roi_x']:.2f}x")
    print("Boundary problem quantified, weakest link fixed, "
          "MAS response faster.")


if __name__ == "__main__":
    main()
