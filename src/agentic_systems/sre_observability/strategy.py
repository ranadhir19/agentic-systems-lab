"""Strategy bridge: unifying SRE reliability with business strategy.

A strategic initiative portfolio is modelled as (cost, reliability value,
innovation value) triples. Under a fixed budget, a resource-allocation
optimizer trades reliability investment against innovation investment:

* ``optimize(budget, w)``: exact subset search (2^8 = 256 candidates)
  maximizing ``w * reliability + (1 - w) * innovation``;
* ``frontier(budget)``: the Pareto-efficient reliability/innovation
  frontier swept over the trade-off weight;
* ``recommend(budget)``: the balanced (w = 0.5) allocation;
* ``scorecard(selection)``: a unified leadership scorecard -- downtime,
  MTTR, incident cost, strategic ROI, delivery velocity -- from a
  transparent parametric model of a baseline quarter.
"""
from __future__ import annotations

import numpy as np

# (name, cost, reliability value, innovation value)
INITIATIVES = [
    ("boundary_observability_modules", 30, 9, 2),
    ("auto_remediation_runbooks", 25, 8, 3),
    ("chaos_engineering_program", 20, 7, 2),
    ("developer_platform_upgrade", 30, 4, 6),
    ("multiregion_failover", 45, 10, 1),
    ("checkout_flow_revamp", 40, 2, 9),
    ("ml_recommendations", 35, 1, 8),
    ("mobile_app_rewrite", 50, 1, 10),
]


def _totals(mask: int):
    cost = rel = innov = 0
    names = []
    for i, (name, c, r, v) in enumerate(INITIATIVES):
        if mask & (1 << i):
            cost += c
            rel += r
            innov += v
            names.append(name)
    return cost, rel, innov, names


def optimize(budget: int, w: float) -> dict:
    """Best feasible subset for trade-off weight w in [0, 1]."""
    best = None
    for mask in range(1 << len(INITIATIVES)):
        cost, rel, innov, names = _totals(mask)
        if cost > budget:
            continue
        val = w * rel + (1 - w) * innov
        key = (val, -cost)
        if best is None or key > best[0]:
            best = (key, {"weight": w, "cost": cost, "reliability": rel,
                          "innovation": innov, "initiatives": names})
    return best[1]


def frontier(budget: int, n_w: int = 21) -> list:
    """Pareto-efficient (reliability, innovation) allocations."""
    sols = [optimize(budget, w) for w in np.linspace(0.0, 1.0, n_w)]
    uniq = {}
    for s in sols:
        uniq[(s["reliability"], s["innovation"])] = s
    pts = sorted(uniq.values(), key=lambda s: s["reliability"])
    pareto = []
    best_innov = -1
    for s in reversed(pts):
        if s["innovation"] > best_innov:
            pareto.append(s)
            best_innov = s["innovation"]
    return sorted(pareto, key=lambda s: s["reliability"])


def recommend(budget: int) -> dict:
    """Balanced allocation: equal weight on reliability and innovation."""
    return optimize(budget, 0.5)


def scorecard(selection: dict) -> dict:
    """Unified leadership scorecard for an allocation.

    Parametric model of one quarter, anchored at a baseline quarter with
    no strategic investment: 320 min downtime, 58 min MTTR, $1.4M
    incident cost, 1.0x strategic ROI, 100 velocity points. Reliability
    investment cuts downtime/MTTR/cost; innovation investment lifts ROI
    and velocity; reliability work slightly taxes velocity.
    """
    r = selection["reliability"]
    v = selection["innovation"]
    downtime = 320.0 * max(0.25, 1 - 0.07 * r)
    mttr = 58.0 * max(0.40, 1 - 0.05 * r)
    return {
        "initiatives": selection["initiatives"],
        "cost": selection["cost"],
        "downtime_min": downtime,
        "mttr_min": mttr,
        "incident_cost_usd_m": 1.4 * downtime / 320.0,
        "strategic_roi_x": 1.0 + 0.09 * v,
        "delivery_velocity": 100 + 6 * v - 2 * r,
    }


def baseline_scorecard() -> dict:
    return scorecard({"reliability": 0, "innovation": 0,
                      "initiatives": [], "cost": 0})
