"""Smoke tests for leadership-insights."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agentic_systems.leadership_insights import (
    generate_enterprise, build_unified, resolution_scores,
    dora_metrics, pr_analytics, detect_bottlenecks,
    license_report, reclaim_opportunities,
    resolution_timelines, csat_drivers, EscalationPredictor,
    productivity_satisfaction, skill_gaps, retention_risk, retention_scores,
    run_insights,
)


def _u():
    data, gt = generate_enterprise(7)
    return build_unified(data), gt


def test_generation_deterministic():
    d1, _ = generate_enterprise(7)
    d2, _ = generate_enterprise(7)
    assert len(d1["jira"]) == len(d2["jira"])
    assert len(d1["github"]) == len(d2["github"])
    assert d1["jira"].cycle_h.sum() == d2["jira"].cycle_h.sum()


def test_entity_resolution_near_perfect():
    u, _ = _u()
    s = resolution_scores(u)
    assert s["f1"] >= 0.99, s
    assert s["fallback_accuracy"] == 1.0, s


def test_bottleneck_found():
    u, gt = _u()
    bn = detect_bottlenecks(u)
    assert bn.loc["platform", "bottleneck"]
    assert bn.bottleneck.sum() == 1  # no false positives


def test_license_waste_recovered():
    u, gt = _u()
    df, summary = reclaim_opportunities(u)
    truth = gt["waste_premium_ids"] | gt["waste_suite_ids"]
    found = set(df.employee_id)
    assert found == truth
    assert summary["annual_saving"] == (12 * 180 + 8 * 95) * 12


def test_escalation_cluster_found():
    u, gt = _u()
    esc = u["snow"].groupby("service").escalated.mean()
    assert esc.idxmax() == gt["escalation_cluster_service"]


def test_retention_topk():
    u, gt = _u()
    rr = retention_risk(u)
    sc = retention_scores(rr, k=10)
    assert sc["recall_at_k"] >= 0.6, sc


def test_escalation_predictor_trains():
    u, _ = _u()
    s = u["snow"].reset_index(drop=True)
    tr, te = s.iloc[:400], s.iloc[400:560]
    m = EscalationPredictor().fit(tr)
    # Rare event: principled operating point is the train base rate —
    # flag anything riskier than background.
    sc = m.scores(te, threshold=float(tr.escalated.mean()))
    # Honest bar for a 12%-base-rate event with weak features: beat the
    # ~0.12 F1 of a random predictor while catching ~1 in 4 escalations.
    assert sc["f1"] > 0.13, sc
    assert sc["recall"] > 0.2, sc


def test_siloed_misses_cross_source():
    u, _ = _u()
    integ = run_insights(u, "integrated")
    silo = run_insights(u, "siloed")
    assert len(integ) > len(silo)
    assert all(i["n_sources"] == 1 for i in silo)


def test_lenses_run():
    u, _ = _u()
    assert len(dora_metrics(u)) == 6
    assert len(pr_analytics(u)) == 6
    assert len(license_report(u)) == 3
    assert len(resolution_timelines(u)) > 0
    assert "corr_csat_logresolve" in csat_drivers(u)
    assert len(skill_gaps(u)[0]) == 5
    assert "corr_points_satisfaction" in productivity_satisfaction(u)
