"""Metrics: decay-curve fitting, cost-per-success, confidence intervals."""
from __future__ import annotations

import numpy as np


def wilson_ci(successes: int, trials: int, z: float = 1.96):
    """Wilson score interval for a binomial proportion."""
    if trials == 0:
        return (0.0, 1.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def fit_exponential_decay(horizons, success_rates):
    """Fit success(N) = q^N by log-linear regression.

    Returns (q_hat, r_squared). Only horizons with success_rate > 0
    are used (log of zero is undefined); callers should ensure the
    shortest horizons have nonzero success.
    """
    xs, ys = [], []
    for n, s in zip(horizons, success_rates):
        if s > 0:
            xs.append(n)
            ys.append(np.log(s))
    xs = np.array(xs, dtype=float)
    ys = np.array(ys)
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    # least squares: ys = a + b*xs ; expect a ~ 0, b = log(q)
    A = np.vstack([np.ones_like(xs), xs]).T
    coef, residuals, _, _ = np.linalg.lstsq(A, ys, rcond=None)
    a, b = coef
    y_pred = a + b * xs
    ss_res = float(np.sum((ys - y_pred) ** 2))
    ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return (float(np.exp(b)), float(r2))


def cost_per_success(total_cost: float, successes: int) -> float:
    """Mean cost to produce one successful task. inf if no successes."""
    if successes == 0:
        return float("inf")
    return total_cost / successes


def summarize(reports):
    """Aggregate a list of RunReports into (success_rate, mean_cost,
    total_cost, successes, trials)."""
    trials = len(reports)
    successes = sum(1 for r in reports if r.success)
    total_cost = sum(r.cost for r in reports)
    mean_cost = total_cost / trials if trials else 0.0
    return {
        "success_rate": successes / trials if trials else 0.0,
        "mean_cost": mean_cost,
        "total_cost": total_cost,
        "successes": successes,
        "trials": trials,
        "cost_per_success": cost_per_success(total_cost, successes),
        "ci": wilson_ci(successes, trials),
    }
