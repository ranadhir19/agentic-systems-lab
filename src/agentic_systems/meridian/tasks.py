"""Task model and benchmark task generator for Meridian experiments.

A Task represents a complex, multi-domain job (e.g. "investigate a payments
outage and draft the incident report"). Tasks carry a *kind* that hints at
which domains they stress, and a *complexity* level that scales the number
of subtasks a good decomposition should produce.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random


class TaskKind(str, Enum):
    RESEARCH = "research"      # information gathering heavy
    ANALYSIS = "analysis"      # quantitative reasoning heavy
    MIXED = "mixed"            # needs research + analysis + synthesis
    SYNTHESIS = "synthesis"    # writing / consolidation heavy


@dataclass(frozen=True)
class Task:
    id: int
    kind: TaskKind
    complexity: int            # 1 (simple) .. 5 (very complex)
    title: str
    brief: str


@dataclass(frozen=True)
class SubTask:
    parent_id: int
    domain: str                # "research" | "analysis" | "synthesis"
    difficulty: float          # 0..1
    needs_peer_artifact: bool  # True -> benefits from horizontal coordination


_TASK_TITLES = {
    TaskKind.RESEARCH: [
        "Competitive landscape brief", "Vendor capability survey",
        "Regulatory change summary", "Prior-art scan",
    ],
    TaskKind.ANALYSIS: [
        "Outage root-cause analysis", "Cost anomaly investigation",
        "Capacity forecast review", "Risk exposure assessment",
    ],
    TaskKind.MIXED: [
        "Incident postmortem with remediation plan", "Market-entry dossier",
        "Build-vs-buy evaluation", "Fraud pattern investigation",
    ],
    TaskKind.SYNTHESIS: [
        "Executive decision memo", "Architecture decision record",
        "Quarterly review narrative", "Policy update draft",
    ],
}


class TaskGenerator:
    """Deterministic generator of benchmark tasks."""

    def __init__(self, seed: int = 7):
        self._rng = random.Random(seed)

    def generate(self, n: int) -> list[Task]:
        tasks = []
        kinds = list(TaskKind)
        for i in range(n):
            kind = kinds[i % len(kinds)]  # balanced mix, deterministic order
            complexity = self._rng.randint(2, 5)
            title = self._rng.choice(_TASK_TITLES[kind])
            tasks.append(Task(
                id=i,
                kind=kind,
                complexity=complexity,
                title=title,
                brief=f"{title} (complexity {complexity}/5)",
            ))
        return tasks
