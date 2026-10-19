"""Smoke tests for SRE-Observability."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.sre_observability import (
    SiloedResponder,
    UnifiedResponder,
    assess_boundaries,
    assess_layers,
    frontier,
    install_export_fix,
    observe_all,
    rank_boundaries,
    recommend,
    reset_export_overrides,
    simulate,
)


def test_sim_deterministic():
    a = simulate(seed=3)
    b = simulate(seed=3)
    for k in a.telemetry:
        assert np.array_equal(a.telemetry[k], b.telemetry[k])
    assert [i.id for i in a.incidents] == [i.id for i in b.incidents]


def test_intra_layer_recall_high():
    sim = simulate(seed=0)
    alerts = observe_all(sim, seed=0)
    for layer, s in assess_layers(sim, alerts).items():
        assert s.seg_recall >= 0.8, (layer, s.seg_recall)
        assert s.fp <= 5, (layer, s.fp)


def test_weakest_boundary_identified():
    sim = simulate(seed=0)
    alerts = observe_all(sim, seed=0)
    ranking = rank_boundaries(assess_boundaries(sim, alerts))
    assert ranking[0].boundary == ("service", "product")
    assert ranking[0].recall == 0.0


def test_targeted_fix_restores_boundary():
    sim = simulate(seed=0)
    alerts = observe_all(sim, seed=0)
    before = assess_boundaries(sim, alerts)[("service", "product")]
    install_export_fix("service", "product")
    try:
        alerts2 = observe_all(sim, seed=0)
        after = assess_boundaries(sim, alerts2)[("service", "product")]
    finally:
        reset_export_overrides()
    assert after.recall == 1.0
    assert after.f1 > before.f1


def test_unified_beats_siloed_on_cascades():
    sim = simulate(seed=0)
    alerts = observe_all(sim, seed=0)
    rs = SiloedResponder().respond(sim, alerts, np.random.default_rng(11))
    ru = UnifiedResponder().respond(sim, alerts, np.random.default_rng(11))
    assert len(rs) == len(ru) == 3
    assert np.mean([r["correct"] for r in ru]) >= \
        np.mean([r["correct"] for r in rs])
    assert np.mean([r["mttr_min"] for r in ru]) <= \
        np.mean([r["mttr_min"] for r in rs])


def test_strategy_respects_budget():
    rec = recommend(100)
    assert rec["cost"] <= 100
    assert rec["reliability"] > 0 and rec["innovation"] > 0
    fr = frontier(100)
    assert len(fr) >= 2
    # pareto trade-off: reliability strictly increases ->
    # innovation strictly decreases
    rels = [s["reliability"] for s in fr]
    inns = [s["innovation"] for s in fr]
    assert rels == sorted(rels)
    assert inns == sorted(inns, reverse=True)
