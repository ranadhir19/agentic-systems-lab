"""Decision-partition quickstart: score five claim decisions, allocate four agents.

Runs the insurance-claim worked example end to end: complexity scoring,
the 4-agent partition with rationales, and the sequential stage plan.
Every number is deterministic.

Run:  python3 examples/09_decision_partition_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.decision_partition import (
    Scorer,
    insurance_demo,
    partition_metrics,
    workflow_plan,
)
from agentic_systems.decision_partition.scoring import CATEGORY_WEIGHTS


def main() -> None:
    scorer = Scorer()
    decisions, partition = insurance_demo(scorer)

    print("Complexity scores (blocks x weight):")
    for d in decisions:
        print(f"  {d.name:24s} blocks={len(d.blocks)} "
              f"weight={CATEGORY_WEIGHTS[d.category]:.1f} "
              f"score={scorer.score(d):4.1f}  level={scorer.level(d)}")

    print("\nAgent partition:")
    for agent in partition.agents:
        print(f"  {agent.name:20s} <- {', '.join(agent.decision_names)}")
        print(f"    rationale: {agent.rationale}")

    metrics = partition_metrics(partition, decisions)
    print(f"\nAgents: {metrics['agent_count']} (naive 1:1 would use "
          f"{metrics['naive_agent_count']}); "
          f"coordination channels {metrics['coord_channels']:.0f} vs "
          f"{metrics['naive_coord_channels']:.0f} naive.")

    plan = workflow_plan(decisions, scorer=scorer)
    print(f"\nSequential stages: {plan['stages']}")
    print(f"Critical-path score: {plan['critical_path_score']:.1f}; "
          f"cross-agent handoffs: {plan['cross_agent_handoffs']}")

    # assertions: the concept's exact numbers
    expected = {"Identity validation": 3.0, "Damage assessment": 10.0,
                "Policy rules compliance": 8.0, "Fraud detection": 10.0,
                "Final settlement": 4.0}
    for d in decisions:
        assert abs(scorer.score(d) - expected[d.name]) < 1e-9, d.name
    assert len(partition.agents) == 4
    intake = partition.agent_of("Identity validation")
    assert intake is not None and intake.name == "Intake Agent"
    assert set(intake.decision_names) == {"Identity validation", "Final settlement"}
    print("\nQuickstart OK: scores and 4-agent partition match the concept.")


if __name__ == "__main__":
    main()
