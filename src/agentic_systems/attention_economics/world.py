"""The decision stream: stakes, stated confidence, and ground truth.

Each decision carries:
  stakes      -- cost incurred if the agent acts wrongly and unaudited
  confidence  -- the agent's *stated* confidence in its own answer
  correct     -- ground truth: would the agent's autonomous answer be right?

Calibration quality is controlled by `miscalibration`: a shift added to the
stated confidence. The agent's actual competence (the Bernoulli draw for
`correct`) always follows the *true* confidence, so a miscalibrated agent
is exactly as capable but misreports how capable it is.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Decision:
    stakes: float
    confidence: float  # stated confidence
    correct: bool      # ground truth


class DecisionStream:
    """A seeded, reproducible batch of decisions."""

    def __init__(self, decisions: list[Decision]):
        self.decisions = decisions

    def __len__(self) -> int:
        return len(self.decisions)

    @property
    def stakes(self) -> np.ndarray:
        return np.array([d.stakes for d in self.decisions])

    @property
    def confidence(self) -> np.ndarray:
        return np.array([d.confidence for d in self.decisions])

    @property
    def correct(self) -> np.ndarray:
        return np.array([d.correct for d in self.decisions])

    @property
    def accuracy(self) -> float:
        return float(np.mean(self.correct))


def make_stream(
    n: int,
    *,
    stakes_median: float = 100.0,
    stakes_sigma: float = 0.8,
    homogeneous_stakes: float | None = None,
    miscalibration: float = 0.0,
    seed: int = 7,
) -> DecisionStream:
    """Build a seeded decision stream.

    Args:
        n: number of decisions.
        stakes_median / stakes_sigma: lognormal stakes distribution.
        homogeneous_stakes: if set, every decision has these stakes
            (used when the theory needs a single stake value).
        miscalibration: additive shift to stated confidence
            (+0.15 = overconfident, -0.15 = underconfident, 0 = calibrated).
        seed: RNG seed.
    """
    rng = np.random.default_rng(seed)
    if homogeneous_stakes is not None:
        stakes = np.full(n, homogeneous_stakes, dtype=float)
    else:
        stakes = rng.lognormal(
            mean=np.log(stakes_median), sigma=stakes_sigma, size=n
        )
    # True competence: skewed high, mean ~= 0.82.
    true_conf = rng.beta(a=9.0, b=2.0, size=n)
    stated = np.clip(true_conf + miscalibration, 0.01, 0.99)
    correct = rng.random(n) < true_conf
    decisions = [
        Decision(float(s), float(c), bool(k))
        for s, c, k in zip(stakes, stated, correct)
    ]
    return DecisionStream(decisions)
