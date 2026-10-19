"""Meridian — multi-orchestrator multi-agent routing with online decision optimization.

A vertical orchestration layer (meta-orchestrator + domain orchestrators)
combined with a horizontal blackboard for peer artifact sharing. A
contextual Thompson-sampling bandit (``RoutingOptimizer``) learns per-domain
worker routing online; ``DecompositionPlanner`` decides how to split tasks.
``MeridianSystem`` runs the ablation configurations A/B/C/D used by the
experiments, all seeded and reproducible.
"""

from __future__ import annotations

from .orchestrators import DomainOrchestrator, MeridianSystem, RunConfig, RunResult
from .tasks import SubTask, Task, TaskGenerator, TaskKind
from .agents import AgentProfile, Artifact, WorkerAgent, build_fleet
from .blackboard import Blackboard, Posting
from .optimizer import Decomposition, DecompositionPlanner, RoutingOptimizer, scalar_reward

__all__ = [
    "MeridianSystem",
    "RunConfig",
    "RunResult",
    "DomainOrchestrator",
    "Task",
    "SubTask",
    "TaskKind",
    "TaskGenerator",
    "AgentProfile",
    "Artifact",
    "WorkerAgent",
    "build_fleet",
    "Blackboard",
    "Posting",
    "RoutingOptimizer",
    "DecompositionPlanner",
    "Decomposition",
    "scalar_reward",
]
