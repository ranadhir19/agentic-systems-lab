"""Behavioral regression quickstart: catch a silent model-version regression.

Scenario: the team is evaluating whether to move the agent fleet from the
pinned v1 to a candidate v3. The full battery runs paired against v1, the
drift detector scores the differences, the canary replays a 1% rollout,
and the policy engine issues a pin / adopt / rollback recommendation.

Run:  python3 examples/21_behavioral_regression_quickstart.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.behavioral_regression import (
    VERSIONS,
    CanaryAnalyzer,
    DriftDetector,
    PolicyEngine,
    SimulatedAgent,
    build_battery,
    run_battery,
)

SEEDS = [7, 11, 42, 0, 99]


def main() -> None:
    battery = build_battery(120)
    print(f"Frozen battery: {len(battery)} tasks "
          f"({len([t for t in battery if t.requires_refusal])} must-refuse)")

    baseline = VERSIONS["v1"]
    candidate = VERSIONS["v3"]  # the silent tool-format regression
    base_runs = [run_battery(SimulatedAgent(baseline), battery, s) for s in SEEDS]
    cand_runs = [run_battery(SimulatedAgent(candidate), battery, s) for s in SEEDS]

    report = DriftDetector().compare(base_runs, cand_runs, candidate.name)
    print(f"\nDrift report v1 -> v3 (severity {report.severity:.3f}):")
    for d in report.regressions:
        print(f"  REGRESSION  {d.metric:18s} {d.diff:+.3f}  p={d.p_value:.4f}")
    for d in report.improvements:
        print(f"  improvement {d.metric:18s} {d.diff:+.3f}  p={d.p_value:.4f}")

    canary = CanaryAnalyzer().analyze(battery, baseline, candidate, seed=7)
    print(f"\nCanary: stopped={canary.stopped}, "
          f"tasks_to_flag={canary.tasks_to_flag}")
    for s in canary.stages:
        print(f"  stage {s.stage:>4s}: {s.decision} "
              f"(worst {s.worst_category} {s.worst_category_diff:+.3f}, "
              f"p={s.worst_category_p:.4f})")

    decision = PolicyEngine().decide(report, canary)
    print(f"\nPolicy decision: {decision.decision.upper()}")
    for r in decision.rationale:
        print(f"  - {r}")

    assert decision.decision == "rollback"
    print("\nThe silent v3 regression was caught before full rollout.")


if __name__ == "__main__":
    main()
