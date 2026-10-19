"""Versioned model stand-ins and the simulated agent.

The agent is a thin harness: for each (seed, task) pair it derives common
random numbers from a stable CRC32 key, and each model version maps those
numbers to outcomes through its behavioral parameters. Because every
version sees the *same* underlying draws, comparisons are paired by
construction: any measured difference comes from the version's parameters,
never from sampling noise.

These are explicitly simulated stand-ins (see the project README's honest
limits): the contribution is the regression methodology — frozen battery,
paired drift detection, canary analysis, pin/adopt/rollback policy — not
claims about any real vendor model.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

import numpy as np

CATEGORIES = ("tool_use", "multi_step", "instruction", "edge")

# v1 baseline per-category task success probability (before difficulty).
BASE_SUCCESS = {
    "tool_use": 0.88,
    "multi_step": 0.82,
    "instruction": 0.90,
    "edge": 0.86,
}

BASE_TOKENS = 400.0
BASE_LATENCY_MS = 900.0
BASE_COST_PER_1K = 0.002


def _draws(seed: int, task_id: str, n: int = 6) -> np.ndarray:
    """Stable uniform draws in [0, 1) for a (seed, task) pair."""
    key = zlib.crc32(f"{seed}:{task_id}".encode("utf-8"))
    rng = np.random.default_rng(key)
    return rng.random(n)


@dataclass(frozen=True)
class ModelVersion:
    """Behavioral parameters of one model version (deltas vs v1 baseline)."""

    name: str
    success_delta: dict = field(default_factory=dict)
    format_compliance: float = 0.97
    verbosity: float = 1.0
    latency_mult: float = 1.0
    cost_mult: float = 1.0
    refusal_accuracy: float = 0.92
    is_baseline: bool = False

    def success_prob(self, category: str, difficulty: float) -> float:
        p = BASE_SUCCESS[category] + self.success_delta.get(category, 0.0)
        p -= 0.15 * difficulty
        return float(np.clip(p, 0.01, 0.99))


def _v1() -> ModelVersion:
    return ModelVersion(name="v1", is_baseline=True)


def _v2() -> ModelVersion:
    # Benign: strictly better task success; a bit more verbose / costly.
    return ModelVersion(
        name="v2",
        success_delta={c: 0.03 for c in CATEGORIES},
        verbosity=1.25,
        latency_mult=1.05,
        cost_mult=1.10,
        refusal_accuracy=0.93,
    )


def _v3() -> ModelVersion:
    # Silent regression: tool-call format compliance collapses; tool_use
    # success drops hard, downstream multi_step dips slightly. Cheaper and
    # faster, which is exactly why it is dangerous: naive metrics improve.
    return ModelVersion(
        name="v3",
        success_delta={"tool_use": -0.18, "multi_step": -0.03,
                       "instruction": -0.02, "edge": -0.02},
        format_compliance=0.71,
        latency_mult=0.95,
        cost_mult=0.95,
        refusal_accuracy=0.90,
    )


def _v4() -> ModelVersion:
    # Efficiency regression: correctness identical, but 60% slower and 55%
    # more expensive per task. No benefit anywhere.
    return ModelVersion(
        name="v4",
        latency_mult=1.60,
        cost_mult=1.55,
        verbosity=1.10,
    )


def _v5() -> ModelVersion:
    # Mixed trade-off: better instruction following, worse tool use.
    return ModelVersion(
        name="v5",
        success_delta={"tool_use": -0.08, "multi_step": -0.02,
                       "instruction": 0.06, "edge": 0.01},
        format_compliance=0.90,
        cost_mult=1.05,
        latency_mult=1.02,
    )


VERSIONS: dict[str, ModelVersion] = {v.name: v for v in (_v1(), _v2(), _v3(), _v4(), _v5())}

# Ground-truth policy labels used to score the policy engine.
GROUND_TRUTH_POLICY = {
    "v2": "auto_adopt",  # strict improvement
    "v3": "rollback",    # silent correctness regression
    "v4": "pin",         # cost regression with no benefit: do not adopt
    "v5": "rollback",    # tool-use regression outweighs instruction gains
}


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    difficulty: float  # 0..1
    requires_refusal: bool = False


@dataclass
class TaskResult:
    task_id: str
    category: str
    version: str
    seed: int
    passed: bool
    score: float
    format_ok: bool
    refused: bool
    requires_refusal: bool
    tokens: float
    latency_ms: float
    cost: float


class SimulatedAgent:
    """Runs tasks under one model version's behavioral parameters."""

    def __init__(self, version: ModelVersion):
        self.version = version

    def run(self, task: Task, seed: int) -> TaskResult:
        v = self.version
        u_pass, u_fmt, u_ref, u_score, u_tok, u_lat = _draws(seed, task.id)

        refused = False
        if task.requires_refusal:
            refused = u_ref < v.refusal_accuracy
            if refused:
                return self._result(task, seed, True, 0.85 + 0.15 * u_score,
                                    True, True, u_tok, u_lat)

        p = v.success_prob(task.category, task.difficulty)
        passed = u_pass < p

        format_ok = True
        if task.category == "tool_use":
            # A malformed tool call fails the task: the silent break.
            format_ok = u_fmt < v.format_compliance
            if not format_ok:
                passed = False

        score = (0.70 + 0.30 * u_score) if passed else (0.30 * u_score)
        return self._result(task, seed, passed, score, format_ok,
                            refused, u_tok, u_lat)

    def _result(self, task, seed, passed, score, format_ok, refused,
                u_tok, u_lat) -> TaskResult:
        v = self.version
        tokens = BASE_TOKENS * v.verbosity * (0.85 + 0.30 * u_tok)
        latency_ms = BASE_LATENCY_MS * v.latency_mult * (0.80 + 0.40 * u_lat)
        cost = (tokens / 1000.0) * BASE_COST_PER_1K * v.cost_mult
        return TaskResult(
            task_id=task.id, category=task.category, version=v.name,
            seed=seed, passed=bool(passed), score=float(score),
            format_ok=bool(format_ok), refused=bool(refused),
            requires_refusal=task.requires_refusal,
            tokens=float(tokens), latency_ms=float(latency_ms),
            cost=float(cost),
        )
