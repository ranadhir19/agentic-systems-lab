"""Policy engine: pin / auto-adopt / rollback recommendations.

The policy is deliberately conservative: a candidate is adopted only when
the drift detector finds real improvements and no correctness regressions,
and the canary did not stop it. A significant correctness regression means
rollback; a cost increase with no compensating benefit means pin the
current version. Every decision carries a human-readable rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .canary import CanaryReport
from .detector import CORRECTNESS_METRICS, VersionReport

ADOPT = "auto_adopt"
PIN = "pin"
ROLLBACK = "rollback"


@dataclass
class PolicyDecision:
    version: str
    decision: str
    rationale: list[str] = field(default_factory=list)
    severity: float = 0.0


class PolicyEngine:
    def __init__(self, cost_tolerance: float = 0.25,
                 severe_effect: float = 0.05):
        self.cost_tolerance = cost_tolerance
        self.severe_effect = severe_effect

    def decide(self, report: VersionReport,
               canary: CanaryReport | None = None) -> PolicyDecision:
        rationale: list[str] = []
        correct = report.correctness_regressions()
        severe = [d for d in correct if abs(d.diff) >= self.severe_effect]

        # 1. Canary stop always wins: the rollout already saw production harm.
        if canary is not None and canary.stopped:
            stage = canary.stages[-1]
            rationale.append(
                f"canary stopped at {stage.stage} stage "
                f"({stage.cumulative_tasks} tasks): worst category "
                f"{stage.worst_category} diff {stage.worst_category_diff:+.3f} "
                f"(p={stage.worst_category_p:.4f})"
            )
            return PolicyDecision(report.version, ROLLBACK, rationale,
                                  report.severity)

        # 2. Significant correctness regression -> rollback.
        if severe:
            names = ", ".join(
                f"{d.metric} ({d.diff:+.3f}, p={d.p_value:.4f})" for d in severe)
            rationale.append(f"significant correctness regression: {names}")
            return PolicyDecision(report.version, ROLLBACK, rationale,
                                  report.severity)

        # 3. Cost regression without compensating benefit -> pin.
        cost = next((d for d in report.diffs if d.metric == "mean_cost"), None)
        if (cost is not None and cost.verdict == "regression"
                and cost.rel_diff > self.cost_tolerance
                and not report.improvements):
            rationale.append(
                f"cost up {cost.rel_diff:.0%} with no correctness gain: "
                f"pin {report.baseline}"
            )
            return PolicyDecision(report.version, PIN, rationale,
                                  report.severity)

        # 4. Strict improvement, no correctness regressed -> adopt. A cost
        # increase within tolerance is acceptable when correctness improves.
        if report.improvements and not report.correctness_regressions():
            names = ", ".join(d.metric for d in report.improvements)
            rationale.append(f"strict improvement, nothing regressed: {names}")
            if cost is not None and cost.verdict == "regression":
                rationale.append(
                    f"cost up {cost.rel_diff:.0%}, accepted: correctness "
                    f"improved with no correctness regressions"
                )
            return PolicyDecision(report.version, ADOPT, rationale,
                                  report.severity)

        # 5. Default: conservative pin.
        if correct:
            names = ", ".join(d.metric for d in correct)
            rationale.append(f"minor correctness regressions, no severe: {names}")
        else:
            rationale.append("no significant change either way")
        rationale.append(f"conservative default: pin {report.baseline}")
        return PolicyDecision(report.version, PIN, rationale, report.severity)
