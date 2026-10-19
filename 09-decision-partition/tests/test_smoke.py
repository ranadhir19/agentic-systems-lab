"""Smoke tests for decision-partition."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.decision_partition import (
    COMPOSITE,
    SIMPLE,
    Decision,
    DynamicPartitioner,
    Scorer,
    assignment_churn,
    critical_path_score,
    insurance_claim_decisions,
    insurance_demo,
    partition_decisions,
    partition_metrics,
    topological_stages,
    workflow_plan,
)


def test_insurance_scores_match_concept():
    scorer = Scorer()
    expected = {"Identity validation": (3, "low"),
                "Damage assessment": (10, "high"),
                "Policy rules compliance": (8, "medium"),
                "Fraud detection": (10, "high"),
                "Final settlement": (4, "low")}
    for d in insurance_claim_decisions():
        score = scorer.score(d)
        assert abs(score - expected[d.name][0]) < 1e-9, (d.name, score)
        assert scorer.level(d) == expected[d.name][1], d.name


def test_insurance_four_agent_partition():
    decisions, partition = insurance_demo()
    assert len(partition.agents) == 4
    by_name = {a.name: set(a.decision_names) for a in partition.agents}
    assert by_name["Damage Specialist"] == {"Damage assessment"}
    assert by_name["Fraud Specialist"] == {"Fraud detection"}
    assert by_name["Compliance Agent"] == {"Policy rules compliance"}
    assert by_name["Intake Agent"] == {"Identity validation", "Final settlement"}


def test_partition_beats_naive_on_overhead():
    decisions, partition = insurance_demo()
    m = partition_metrics(partition, decisions)
    assert m["agent_count"] == 4
    assert m["naive_agent_count"] == 5
    assert m["overhead_estimate"] < m["naive_overhead_estimate"]
    assert abs(m["agent_reduction"] - 0.2) < 1e-9


def test_medium_decisions_share_by_domain():
    a = Decision("A", COMPOSITE, [f"b{i}" for i in range(3)],
                 domains=("fraud", "risk"))
    b = Decision("B", COMPOSITE, [f"c{i}" for i in range(3)],
                 domains=("fraud", "risk"))
    c = Decision("C", COMPOSITE, [f"d{i}" for i in range(3)],
                 domains=("legal", "policy"))
    p = partition_decisions([a, b, c])
    assert len(p.agents) == 2  # A+B share, C stands alone (dissimilar domain)
    assert p.agent_of("A") is p.agent_of("B")
    assert p.agent_of("C") is not p.agent_of("A")


def test_low_decisions_group_into_one_agent():
    ds = [Decision(f"L{i}", SIMPLE, [f"b{j}" for j in range(2)]) for i in range(4)]
    p = partition_decisions(ds)
    assert len(p.agents) == 1
    assert len(p.agents[0].decisions) == 4


def test_dynamic_rescore_triggers_on_threshold_crossing():
    decisions, _ = insurance_demo()
    dyn = DynamicPartitioner(decisions)
    # identity: 3 blocks (score 3, low) -> add 3 blocks -> score 6 (medium)
    ev = dyn.observe("Identity validation",
                     added_blocks=("Biometric", "Device binding", "Liveness"))
    assert ev.crossed_threshold
    assert ev.old_level == "low" and ev.new_level == "medium"
    rec = dyn.maybe_repartition()
    assert rec is not None
    assert any("Identity validation" in t for t in rec.triggers)
    # identity should no longer sit with final settlement in the low agent
    assert (dyn._last_partition.agent_of("Identity validation")
            is not dyn._last_partition.agent_of("Final settlement"))


def test_dynamic_no_crossing_no_repartition():
    decisions, _ = insurance_demo()
    dyn = DynamicPartitioner(decisions)
    ev = dyn.observe("Fraud detection", added_blocks=("Velocity anomaly",))
    assert not ev.crossed_threshold  # 10 -> 12, still high
    assert dyn.maybe_repartition() is None
    assert len(dyn.history) == 1  # only the initial partition


def test_dynamic_stability_tracking():
    decisions, _ = insurance_demo()
    dyn = DynamicPartitioner(decisions)
    before = dyn._last_partition.grouping()
    dyn.observe("Final settlement", added_blocks=("Escalation path",))
    rec = dyn.maybe_repartition()  # 4 -> 5, low -> medium
    assert rec is not None
    assert 0.0 <= rec.stability_vs_prev <= 1.0
    assert rec.stability_vs_prev < 1.0  # settlement moved agents


def test_sequential_stages_follow_dependencies():
    decisions = insurance_claim_decisions()
    stages = topological_stages(decisions)
    names = [[d.name for d in s] for s in stages]
    assert names[0] == ["Identity validation"]
    assert set(names[1]) == {"Damage assessment", "Policy rules compliance",
                             "Fraud detection"}
    assert names[2] == ["Final settlement"]


def test_critical_path_score():
    decisions = insurance_claim_decisions()
    # longest chain: identity(3) -> damage(10) -> settlement(4) = 17
    assert abs(critical_path_score(decisions) - 17.0) < 1e-9


def test_workflow_plan_handoffs():
    decisions = insurance_claim_decisions()
    plan = workflow_plan(decisions)
    assert plan["max_concurrent_agents"] == 3  # stage 1: 3 agents
    # identity->damage/fraud/policy and damage/fraud/policy->settlement
    # cross agents: 3 (identity->each) + 3 (each->settlement) = 6
    assert plan["cross_agent_handoffs"] == 6


def test_latency_addon_can_promote_decision():
    d = Decision("Slow check", SIMPLE, ["ok", "flag"], latency_ms=8000.0)
    base = Scorer()
    assert base.level(d) == "low"  # 2 blocks x 1.0 = 2
    heavy = Scorer(latency_weight=4.0, latency_ref_ms=1000.0)
    # 2 + 4 * 8 = 34 -> high -> dedicated agent
    assert heavy.level(d) == "high"
    p = partition_decisions([d], scorer=heavy)
    assert len(p.agents) == 1 and len(p.agents[0].decisions) == 1


def test_assignment_churn_metric():
    decisions, p1 = insurance_demo()
    p2 = partition_decisions(decisions)  # generic names, same groupings
    # generic namer gives same grouping -> churn 0 despite different names
    assert assignment_churn(p1, p2) == 0.0
    p3 = partition_decisions([Decision(f"D{i}", COMPOSITE,
                                       [f"b{j}" for j in range(5)])
                              for i in range(2)])
    assert assignment_churn(p1, p3) == 1.0
