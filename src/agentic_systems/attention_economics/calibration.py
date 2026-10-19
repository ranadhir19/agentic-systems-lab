"""Trust calibration: does the human's trust match the agent's reliability?

Two failure modes:
  over-trust  -- the human accepts agent output the EV rule would question,
                 so wrong answers slip through unaudited (excess error cost);
  under-trust -- the human questions output the EV rule would accept,
                 burning attention for nothing (excess interruption cost).

We measure both against the stakes-adjusted (EV-optimal) policy as the
reference, and report the agent's own confidence calibration (ECE and a
reliability diagram) separately -- miscalibrated confidence is what
*causes* miscalibrated trust.
"""

from __future__ import annotations

import numpy as np

from .cost import CostModel
from .policies import FixedThreshold, StakesAdjusted
from .principal import HumanPrincipal
from .world import DecisionStream


def reliability_diagram(
    stream: DecisionStream, n_bins: int = 10
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (bin centers, mean stated confidence, empirical accuracy)."""
    conf = stream.confidence
    corr = stream.correct.astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    centers, stated, emp = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf <= hi)
        if m.sum() == 0:
            continue
        centers.append((lo + hi) / 2.0)
        stated.append(conf[m].mean())
        emp.append(corr[m].mean())
    return np.array(centers), np.array(stated), np.array(emp)


def expected_calibration_error(stream: DecisionStream, n_bins: int = 10) -> float:
    """ECE = mean |stated - empirical| weighted by bin mass."""
    conf = stream.confidence
    corr = stream.correct.astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece, total = 0.0, 0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf <= hi)
        n = int(m.sum())
        if n == 0:
            continue
        ece += n * abs(conf[m].mean() - corr[m].mean())
        total += n
    return ece / total if total else 0.0


def trust_sweep(
    stream: DecisionStream,
    principal: HumanPrincipal,
    taus: np.ndarray,
    seed: int = 7,
) -> dict:
    """Total cost of a fixed-threshold human across trust thresholds.

    Low tau = trusting (rarely asks); high tau = skeptical (asks often).
    Returns dict with taus, costs, n_asks, n_unaudited_errors.
    """
    model = CostModel(principal, seed=seed)
    costs, asks, errs = [], [], []
    for tau in taus:
        rep = model.evaluate(stream, FixedThreshold(float(tau)))
        costs.append(rep.total_cost)
        asks.append(rep.n_asks)
        errs.append(rep.n_unaudited_errors)
    return {
        "taus": np.asarray(taus),
        "costs": np.asarray(costs),
        "n_asks": np.asarray(asks),
        "n_unaudited_errors": np.asarray(errs),
    }


def _reference(stream: DecisionStream, principal: HumanPrincipal, seed: int):
    model = CostModel(principal, seed=seed)
    return model.evaluate(stream, StakesAdjusted())


def over_trust_index(
    stream: DecisionStream, principal: HumanPrincipal, tau: float, seed: int = 7
) -> float:
    """Excess unaudited-error rate vs the EV-optimal reference.

    Positive when the human's trust threshold accepts decisions the
    optimal policy would have questioned.
    """
    model = CostModel(principal, seed=seed)
    mine = model.evaluate(stream, FixedThreshold(tau))
    ref = _reference(stream, principal, seed)
    return (mine.n_unaudited_errors - ref.n_unaudited_errors) / len(stream)


def under_trust_index(
    stream: DecisionStream, principal: HumanPrincipal, tau: float, seed: int = 7
) -> float:
    """Excess interruption rate vs the EV-optimal reference.

    Positive when the human's skepticism questions decisions the
    optimal policy would have let through.
    """
    model = CostModel(principal, seed=seed)
    mine = model.evaluate(stream, FixedThreshold(tau))
    ref = _reference(stream, principal, seed)
    return (mine.n_asks - ref.n_asks) / len(stream)
