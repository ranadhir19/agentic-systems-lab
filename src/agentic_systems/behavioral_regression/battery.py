"""The frozen regression battery: tasks, runs, and aggregates.

The battery is frozen by construction — the same task list (ids,
categories, difficulties, refusal flags) is used for every version and
every seed, so version comparisons are apples-to-apples.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .versions import CATEGORIES, SimulatedAgent, Task, TaskResult


def build_battery(n_tasks: int = 120, refusal_frac: float = 0.33,
                  seed: int = 7) -> list[Task]:
    """Build a frozen battery with balanced categories.

    Difficulties are spread evenly within each category; a fixed fraction
    of edge tasks require refusal (the correct behavior is to refuse).
    """
    rng = np.random.default_rng(seed)
    per_cat = n_tasks // len(CATEGORIES)
    remainder = n_tasks % len(CATEGORIES)
    tasks: list[Task] = []
    for ci, cat in enumerate(CATEGORIES):
        n = per_cat + (1 if ci < remainder else 0)
        difficulties = np.linspace(0.05, 0.95, n)
        rng.shuffle(difficulties)
        for i, d in enumerate(difficulties):
            requires_refusal = (
                cat == "edge" and i < int(round(n * refusal_frac))
            )
            tasks.append(Task(
                id=f"{cat}-{i:03d}",
                category=cat,
                difficulty=float(d),
                requires_refusal=requires_refusal,
            ))
    return tasks


@dataclass
class BatteryResult:
    version: str
    seed: int
    results: list[TaskResult] = field(default_factory=list)

    def aggregate(self) -> dict[str, float]:
        """Mean metrics over the battery; keys are the detector's metrics."""
        agg: dict[str, float] = {}
        rs = self.results
        for cat in CATEGORIES:
            sub = [r for r in rs if r.category == cat]
            agg[f"pass_{cat}"] = float(np.mean([r.passed for r in sub]))
        agg["pass_overall"] = float(np.mean([r.passed for r in rs]))
        tool = [r for r in rs if r.category == "tool_use"]
        agg["format_compliance"] = float(np.mean([r.format_ok for r in tool]))
        edge_ref = [r for r in rs if r.requires_refusal]
        agg["refusal_accuracy"] = (
            float(np.mean([r.refused for r in edge_ref])) if edge_ref else 1.0
        )
        agg["mean_cost"] = float(np.mean([r.cost for r in rs]))
        agg["mean_latency"] = float(np.mean([r.latency_ms for r in rs]))
        agg["mean_tokens"] = float(np.mean([r.tokens for r in rs]))
        return agg


def run_battery(agent: SimulatedAgent, battery: list[Task],
                seed: int) -> BatteryResult:
    results = [agent.run(t, seed) for t in battery]
    return BatteryResult(version=agent.version.name, seed=seed,
                         results=results)
