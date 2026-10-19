"""Drift detection: paired version-vs-baseline comparison.

Every battery run uses common random numbers, so for each (seed, task) the
baseline and the candidate see the same underlying draw. We exploit that
pairing directly:

- binary metrics (per-category pass, tool-format compliance, refusal
  accuracy): McNemar's exact test on the paired outcomes pooled over
  seeds x tasks;
- continuous metrics (cost, latency, tokens): paired t-test on the
  per-task values pooled over seeds x tasks.

A metric is a *regression* only if it is both statistically significant
(p < alpha) and materially worse than baseline (|effect| >= min_effect);
significance alone is not enough, and neither is a raw delta.

Severity scoring weights regressions by business impact: a silent
tool-format break outranks a verbosity change by design. Rate metrics use
absolute point differences; cost/latency/token metrics use relative change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from .battery import BatteryResult
from .versions import CATEGORIES

# metric -> (kind, higher_is_better, severity weight, min material effect)
# kind: "rate" (McNemar on paired 0/1) or "scale" (paired t on values).
METRICS: dict[str, tuple[str, bool, float, float]] = {
    "pass_tool_use": ("rate", True, 3.0, 0.005),
    "pass_multi_step": ("rate", True, 2.0, 0.005),
    "pass_instruction": ("rate", True, 1.5, 0.005),
    "pass_edge": ("rate", True, 1.5, 0.005),
    "pass_overall": ("rate", True, 1.0, 0.005),
    "format_compliance": ("rate", True, 4.0, 0.005),
    "refusal_accuracy": ("rate", True, 2.0, 0.005),
    "mean_cost": ("scale", False, 0.5, 0.02),
    "mean_latency": ("scale", False, 0.3, 0.02),
    "mean_tokens": ("scale", False, 0.1, 0.02),
}

CORRECTNESS_METRICS = {
    "pass_tool_use", "pass_multi_step", "pass_instruction", "pass_edge",
    "pass_overall", "format_compliance", "refusal_accuracy",
}


@dataclass
class MetricDiff:
    metric: str
    baseline_mean: float
    candidate_mean: float
    diff: float            # candidate - baseline (absolute units)
    rel_diff: float        # diff / |baseline| (for scale metrics)
    p_value: float
    effect: float          # rate diff, or Cohen's d for scale metrics
    verdict: str           # "regression" | "improvement" | "neutral"


@dataclass
class VersionReport:
    version: str
    baseline: str
    n_pairs: int = 0
    diffs: list[MetricDiff] = field(default_factory=list)
    severity: float = 0.0

    @property
    def regressions(self) -> list[MetricDiff]:
        return [d for d in self.diffs if d.verdict == "regression"]

    @property
    def improvements(self) -> list[MetricDiff]:
        return [d for d in self.diffs if d.verdict == "improvement"]

    def correctness_regressions(self) -> list[MetricDiff]:
        return [d for d in self.regressions if d.metric in CORRECTNESS_METRICS]


def _paired_rate(base: np.ndarray, cand: np.ndarray) -> tuple[float, float, float]:
    """McNemar exact test on paired binary outcomes.

    Returns (rate_diff, p_value, rate_diff_as_effect).
    """
    b = int(np.sum((base == 1) & (cand == 0)))  # base ok, cand failed
    c = int(np.sum((base == 0) & (cand == 1)))  # base failed, cand ok
    n = b + c
    p = float(stats.binomtest(min(b, c), n, 0.5).pvalue) if n else 1.0
    return float(np.mean(cand) - np.mean(base)), p, float(np.mean(cand) - np.mean(base))


def _paired_scale(base: np.ndarray, cand: np.ndarray) -> tuple[float, float, float]:
    """Paired t-test on continuous values. Returns (diff, p, cohens_d)."""
    diffs = cand - base
    mean_diff = float(np.mean(diffs))
    sd = float(np.std(diffs, ddof=1))
    if sd == 0.0:
        return mean_diff, 1.0, 0.0
    _, p = stats.ttest_rel(cand, base)
    return mean_diff, float(p), float(mean_diff / sd)


class DriftDetector:
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def compare(self, base_results: list[BatteryResult],
                cand_results: list[BatteryResult],
                candidate_name: str, baseline_name: str = "v1") -> VersionReport:
        report = VersionReport(version=candidate_name, baseline=baseline_name)
        pairs = _align(base_results, cand_results)
        report.n_pairs = len(pairs)
        for metric, (kind, higher_better, weight, min_effect) in METRICS.items():
            b, c = _extract(pairs, metric)
            if kind == "rate":
                diff, p, eff = _paired_rate(b, c)
                magnitude = abs(diff)
            else:
                diff, p, eff = _paired_scale(b, c)
                magnitude = abs(diff / np.mean(b)) if np.mean(b) != 0 else 0.0
            if p < self.alpha and magnitude >= min_effect:
                if (higher_better and diff < 0) or (
                        not higher_better and diff > 0):
                    verdict = "regression"
                else:
                    verdict = "improvement"
            else:
                verdict = "neutral"
            report.diffs.append(MetricDiff(
                metric=metric,
                baseline_mean=float(np.mean(b)),
                candidate_mean=float(np.mean(c)),
                diff=diff,
                rel_diff=float(diff / abs(np.mean(b))) if np.mean(b) != 0 else 0.0,
                p_value=p, effect=eff, verdict=verdict,
            ))
        report.severity = self._severity(report)
        return report

    def _severity(self, report: VersionReport) -> float:
        total = 0.0
        for d in report.regressions:
            _, _, weight, _ = METRICS[d.metric]
            magnitude = abs(d.rel_diff) if d.metric.startswith("mean_") else abs(d.diff)
            total += weight * magnitude
        return float(total)


def _align(base_results: list[BatteryResult],
           cand_results: list[BatteryResult]
           ) -> list[tuple]:
    """Pair up task results: same seed, same task order."""
    base_by_seed = {r.seed: r for r in base_results}
    pairs = []
    for cr in cand_results:
        br = base_by_seed.get(cr.seed)
        if br is None:
            raise ValueError(f"seed {cr.seed} missing from baseline runs")
        if len(br.results) != len(cr.results):
            raise ValueError("battery length mismatch between runs")
        for b, c in zip(br.results, cr.results):
            if b.task_id != c.task_id:
                raise ValueError("task order mismatch between runs")
            pairs.append((b, c))
    return pairs


def _extract(pairs: list[tuple], metric: str) -> tuple[np.ndarray, np.ndarray]:
    if metric.startswith("pass_"):
        cat = metric[len("pass_"):]
        sel = [(b, c) for b, c in pairs
               if (cat == "overall" or b.category == cat)]
        b = np.array([float(x.passed) for x, _ in sel])
        c = np.array([float(x.passed) for _, x in sel])
    elif metric == "format_compliance":
        sel = [(b, c) for b, c in pairs if b.category == "tool_use"]
        b = np.array([float(x.format_ok) for x, _ in sel])
        c = np.array([float(x.format_ok) for _, x in sel])
    elif metric == "refusal_accuracy":
        sel = [(b, c) for b, c in pairs if b.requires_refusal]
        b = np.array([float(x.refused) for x, _ in sel])
        c = np.array([float(x.refused) for _, x in sel])
    elif metric == "mean_cost":
        b = np.array([x.cost for x, _ in pairs])
        c = np.array([x.cost for _, x in pairs])
    elif metric == "mean_latency":
        b = np.array([x.latency_ms for x, _ in pairs])
        c = np.array([x.latency_ms for _, x in pairs])
    elif metric == "mean_tokens":
        b = np.array([x.tokens for x, _ in pairs])
        c = np.array([x.tokens for _, x in pairs])
    else:
        raise ValueError(f"unknown metric {metric}")
    return b, c
