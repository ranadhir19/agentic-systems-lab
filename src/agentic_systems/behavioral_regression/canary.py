"""Canary analysis: staged rollout with stop/rollback decision rules.

A candidate version is exposed to a small slice of traffic first. At each
stage we run the candidate and the baseline on the *same* canary tasks
(paired by common random numbers) and test, overall and per category,
whether the candidate is materially worse. A significant regression at any
stage stops the rollout; otherwise the candidate is promoted to the next
stage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .battery import BatteryResult, run_battery
from .versions import CATEGORIES, ModelVersion, SimulatedAgent, Task


@dataclass
class CanaryStageResult:
    stage: str
    n_tasks: int
    overall_diff: float
    overall_p: float
    worst_category: str
    worst_category_diff: float
    worst_category_p: float
    decision: str  # "promote" | "hold" | "stop_rollback"
    cumulative_tasks: int


@dataclass
class CanaryReport:
    version: str
    stages: list[CanaryStageResult] = field(default_factory=list)
    stopped: bool = False
    tasks_to_flag: int | None = None  # cumulative tasks when stopped

    @property
    def final_decision(self) -> str:
        if not self.stages:
            return "hold"
        return self.stages[-1].decision


class CanaryAnalyzer:
    def __init__(self, stages: tuple[tuple[str, int], ...] = (("1%", 40), ("10%", 160)),
                 alpha: float = 0.05, stop_margin: float = 0.02):
        self.stages = stages
        self.alpha = alpha
        self.stop_margin = stop_margin

    def analyze(self, battery: list[Task], baseline: ModelVersion,
                candidate: ModelVersion, seed: int) -> CanaryReport:
        base_agent = SimulatedAgent(baseline)
        cand_agent = SimulatedAgent(candidate)
        report = CanaryReport(version=candidate.name)
        # Stratified subset: the battery is grouped by category, so shuffle
        # with a seed derived from the run seed before slicing.
        order = np.random.default_rng(seed + 999).permutation(len(battery))
        shuffled = [battery[i] for i in order]
        cumulative = 0
        for stage_name, n in self.stages:
            subset = shuffled[:n]
            base_res = run_battery(base_agent, subset, seed)
            cand_res = run_battery(cand_agent, subset, seed)
            overall_diff, overall_p = _paired_diff_p(
                base_res, cand_res, category=None)
            worst_cat, worst_diff, worst_p = None, 0.0, 1.0
            for cat in CATEGORIES:
                diff, p = _paired_diff_p(base_res, cand_res, category=cat)
                if diff < worst_diff:
                    worst_cat, worst_diff, worst_p = cat, diff, p
            cumulative += n
            # Stop if the candidate is significantly worse overall, or in
            # any single category with a material effect.
            if ((overall_p < self.alpha and overall_diff < -self.stop_margin)
                    or (worst_p < self.alpha and worst_diff < -0.03)):
                decision = "stop_rollback"
                report.stopped = True
                report.tasks_to_flag = cumulative
            elif overall_diff < 0 or worst_diff < -0.01:
                decision = "hold"
            else:
                decision = "promote"
            report.stages.append(CanaryStageResult(
                stage=stage_name, n_tasks=n,
                overall_diff=overall_diff, overall_p=overall_p,
                worst_category=worst_cat, worst_category_diff=worst_diff,
                worst_category_p=worst_p, decision=decision,
                cumulative_tasks=cumulative,
            ))
            if decision == "stop_rollback":
                break
        return report


def _paired_diff_p(base_res: BatteryResult, cand_res: BatteryResult,
                   category: str | None) -> tuple[float, float]:
    """Mean paired pass-rate difference (candidate - baseline) and p-value."""
    b = [r for r in base_res.results
         if category is None or r.category == category]
    c = [r for r in cand_res.results
         if category is None or r.category == category]
    # Results are in identical task order; pair elementwise.
    diffs = np.array([float(ci.passed) - float(bi.passed)
                      for bi, ci in zip(b, c)])
    mean_diff = float(np.mean(diffs))
    if np.std(diffs, ddof=1) == 0.0:
        return mean_diff, 1.0
    t = mean_diff / (np.std(diffs, ddof=1) / np.sqrt(len(diffs)))
    # One-sided: we only care about the candidate being worse, so the
    # p-value is P(T <= t) for negative t.
    p = float(stats.t.cdf(t, df=len(diffs) - 1)) if t < 0 else 1.0
    return mean_diff, p
