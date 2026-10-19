"""Value profiles: structured representation of an AI system's value alignment.

A ValueProfile is a vector over six interpretable dimensions, each in
[-1, 1]. It is the measurement instrument of this project: red-teaming
measures it, constitutions constrain it, drift detection watches it move,
and vendor assessment prices its risk.

The three bundled archetypes are SYNTHETIC — parameterized stand-ins used
to validate the methodology. They describe no real vendor or model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

DIMENSIONS: List[str] = [
    "econ",     # economic left (-1) <-> right (+1)
    "culture",  # collectivist (-1) <-> individualist (+1)
    "corp",     # stakeholder (-1) <-> shareholder (+1)
    "geo",      # multipolar (-1) <-> western-led (+1)
    "risk",     # precautionary (-1) <-> permissive (+1)
    "tone",     # formal (-1) <-> casual (+1)
]

DIM_LABELS: Dict[str, str] = {
    "econ": "economic left/right",
    "culture": "collectivist/individualist",
    "corp": "stakeholder/shareholder",
    "geo": "multipolar/western-led",
    "risk": "precautionary/permissive",
    "tone": "formal/casual",
}


@dataclass
class ValueProfile:
    """A point in the six-dimensional value space."""

    name: str
    values: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for d in DIMENSIONS:
            self.values.setdefault(d, 0.0)
        for d, v in self.values.items():
            if d not in DIMENSIONS:
                raise ValueError(f"unknown dimension: {d}")
            if not -1.0 <= v <= 1.0:
                raise ValueError(f"{d}={v} out of [-1, 1]")

    def vec(self) -> np.ndarray:
        return np.array([self.values[d] for d in DIMENSIONS])

    def l1(self, other: "ValueProfile") -> float:
        return float(np.abs(self.vec() - other.vec()).sum())

    def per_dim(self, other: "ValueProfile") -> Dict[str, float]:
        return {d: abs(self.values[d] - other.values[d]) for d in DIMENSIONS}

    def shift(self, dim: str, delta: float, name: str = "") -> "ValueProfile":
        vals = dict(self.values)
        vals[dim] = float(np.clip(vals[dim] + delta, -1.0, 1.0))
        return ValueProfile(name=name or f"{self.name}+{dim}{delta:+.2f}", values=vals)


def neutral_profile(name: str = "neutral") -> ValueProfile:
    return ValueProfile(name=name, values={d: 0.0 for d in DIMENSIONS})


# ---------------------------------------------------------------------------
# Synthetic archetypes. These are methodology test fixtures, not descriptions
# of any real vendor, model, or organization.
# ---------------------------------------------------------------------------

PROFILE_ALPHA = ValueProfile(
    name="vendor-alpha",
    values={"econ": 0.55, "culture": 0.65, "corp": 0.45,
            "geo": 0.70, "risk": -0.30, "tone": 0.35},
)

PROFILE_BETA = ValueProfile(
    name="vendor-beta",
    values={"econ": -0.50, "culture": -0.55, "corp": -0.60,
            "geo": -0.65, "risk": -0.55, "tone": -0.20},
)

PROFILE_GAMMA = ValueProfile(
    name="vendor-gamma",
    values={"econ": 0.05, "culture": -0.05, "corp": 0.05,
            "geo": -0.05, "risk": 0.10, "tone": 0.0},
)

ARCHETYPES: List[ValueProfile] = [PROFILE_ALPHA, PROFILE_BETA, PROFILE_GAMMA]
