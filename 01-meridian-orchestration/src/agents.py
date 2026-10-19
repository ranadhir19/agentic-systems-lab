"""Simulated worker agents with stochastic capability profiles.

Each worker has a specialty. When a subtask matches the specialty the agent
produces higher expected quality; mismatches degrade quality and raise the
chance of failure. Cost and latency are sampled per call. Model tiers
("standard" / "pro") trade cost for quality.

These are *simulated* stand-ins so the orchestration architecture — the
actual subject of this project — can be benchmarked deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class AgentProfile:
    name: str
    specialty: str             # domain this agent is best at
    base_quality: float        # 0..1 expected quality on matched tasks
    quality_std: float
    cost_per_call: float       # dollars
    latency_mean: float        # simulated seconds
    latency_std: float
    tier: str                  # "standard" | "pro"


@dataclass
class Artifact:
    subtask_id: int
    worker: str
    domain: str
    quality: float              # 0..1
    cost: float
    latency: float
    success: bool


# A small, fixed fleet: 2 workers per domain x 2 tiers = 12 workers.
_FLEET = [
    ("r1", "research", 0.82, 0.08, 0.030, 4.0, 1.0, "standard"),
    ("r2", "research", 0.90, 0.06, 0.090, 6.0, 1.2, "pro"),
    ("a1", "analysis", 0.80, 0.09, 0.035, 5.0, 1.1, "standard"),
    ("a2", "analysis", 0.91, 0.05, 0.100, 7.0, 1.3, "pro"),
    ("s1", "synthesis", 0.81, 0.08, 0.028, 3.5, 0.9, "standard"),
    ("s2", "synthesis", 0.89, 0.06, 0.085, 5.5, 1.1, "pro"),
    ("g1", "general", 0.70, 0.10, 0.020, 3.0, 0.8, "standard"),
    ("g2", "general", 0.78, 0.08, 0.060, 4.5, 1.0, "pro"),
]


class WorkerAgent:
    def __init__(self, profile: AgentProfile, seed: int):
        self.profile = profile
        self._rng = random.Random(seed + hash(profile.name) % (2 ** 16))

    @property
    def name(self) -> str:
        return self.profile.name

    def execute(self, subtask_id: int, domain: str, difficulty: float) -> Artifact:
        p = self.profile
        matched = (p.specialty == domain) or (p.specialty == "general")
        # Mismatch penalty: harder subtasks expose the gap.
        match_bonus = 0.0 if matched else -0.18 * (0.5 + difficulty)
        quality = self._rng.gauss(p.base_quality + match_bonus, p.quality_std)
        # Difficulty separates the tiers: on the hardest subtasks standard
        # workers fall near/below the bar while pro workers hold.
        quality = max(0.0, min(1.0, quality - 0.10 * difficulty))
        success = quality >= 0.55
        cost = p.cost_per_call * (1.0 + 0.3 * difficulty) * self._rng.uniform(0.9, 1.1)
        latency = max(0.5, self._rng.gauss(p.latency_mean, p.latency_std))
        return Artifact(subtask_id, p.name, domain, quality, cost, latency, success)


def build_fleet(seed: int = 11) -> dict[str, WorkerAgent]:
    return {name: WorkerAgent(AgentProfile(name, *rest), seed)
            for name, *rest in _FLEET}
