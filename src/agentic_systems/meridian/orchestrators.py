"""Vertical orchestration layer: meta-orchestrator and domain orchestrators.

Vertical flow
-------------
MetaOrchestrator.decompose(task)          -> per-domain SubTasks (via planner)
DomainOrchestrator.run(subtask)           -> dispatches to a worker, aggregates

The horizontal layer (blackboard) plugs in at two points:
1. After producing an artifact, a domain orchestrator *proposes* it, so a
   peer domain can *request* it instead of the meta-orchestrator re-deriving
   the dependency (escalation avoided).
2. When a subtask is flagged needs_peer_artifact, the domain orchestrator
   first tries the blackboard; only on a miss does it escalate vertically.

RunConfig selects the ablation:
    A "single"     — one orchestrator does everything, fixed worker mapping
    B "vertical"   — meta + domain orchestrators, fixed worker mapping
    C "vertical+horizontal" — B + blackboard peer coordination
    D "meridian"   — C + RoutingOptimizer + DecompositionPlanner
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random

from .agents import Artifact, build_fleet
from .blackboard import Blackboard
from .optimizer import DecompositionPlanner, RoutingOptimizer
from .tasks import SubTask, Task


@dataclass
class RunResult:
    task_id: int
    quality: float
    cost: float
    latency: float
    success: bool
    n_calls: int
    peer_resolutions: int
    escalations: int


@dataclass
class RunConfig:
    name: str
    vertical: bool = False
    horizontal: bool = False
    optimized: bool = False
    smart_fixed: bool = False  # hand-tuned difficulty-aware tiering (no learning)


class DomainOrchestrator:
    def __init__(self, domain: str, fleet: dict, blackboard: Blackboard | None,
                 optimizer: RoutingOptimizer | None, seed: int,
                 smart_fixed: bool = False):
        self.domain = domain
        self.fleet = fleet
        self.bb = blackboard
        self.opt = optimizer
        self.smart_fixed = smart_fixed
        self._rng = random.Random(seed)

    def _pick_worker(self, task: Task, subtask: SubTask) -> str:
        if self.opt is not None:
            return self.opt.select_worker(task, subtask.domain,
                                           subtask.difficulty)
        specialists = [n for n, w in self.fleet.items()
                       if w.profile.specialty == subtask.domain]
        if self.smart_fixed and subtask.difficulty > 0.7:
            # hand-tuned rule: pro tier for hard subtasks
            for n in specialists:
                if self.fleet[n].profile.tier == "pro":
                    return n
        if specialists:
            return specialists[0]
        return next(n for n, w in self.fleet.items()
                    if w.profile.specialty == "general")

    def run(self, task: Task, subtask: SubTask) -> Artifact:
        # Horizontal shortcut: reuse a peer's artifact when available.
        if self.bb is not None and subtask.needs_peer_artifact:
            peer = self.bb.request(self.domain, subtask.domain,
                                   f"artifact-for-{subtask.parent_id}")
            if peer is not None:
                # Peer artifact reused at a fraction of the cost/latency.
                return Artifact(subtask.parent_id, f"peer:{peer.domain}",
                                subtask.domain,
                                quality=min(1.0, peer.quality + 0.02),
                                cost=0.005, latency=0.8, success=True)
        worker_name = self._pick_worker(task, subtask)
        art = self.fleet[worker_name].execute(
            subtask.parent_id, subtask.domain, subtask.difficulty)
        if self.opt is not None:
            self.opt.observe(task, worker_name, art.quality, art.cost, art.latency)
        if self.bb is not None and art.success:
            self.bb.propose(self.domain, f"artifact-{subtask.parent_id}",
                            art.quality)
        return art


class MeridianSystem:
    """The full system under a given ablation config."""

    def __init__(self, config: RunConfig, seed: int = 11):
        self.config = config
        self.fleet = build_fleet(seed)
        self.bb = Blackboard() if config.horizontal else None
        self.opt = (RoutingOptimizer(list(self.fleet), self.fleet, seed + 1)
                    if config.optimized else None)
        self.planner = (DecompositionPlanner(self.opt)
                        if config.optimized else DecompositionPlanner(None))
        self._orchestrators = {
            d: DomainOrchestrator(d, self.fleet, self.bb, self.opt, seed + 2,
                                  smart_fixed=config.smart_fixed)
            for d in ("research", "analysis", "synthesis")
        }
        self._rng = random.Random(seed + 3)

    # -- config A: single orchestrator, fixed mapping ---------------------
    def _run_single(self, task: Task) -> RunResult:
        arts = []
        for i in range(task.complexity):
            domain = ["research", "analysis", "synthesis"][i % 3]
            st = SubTask(task.id, domain, difficulty=0.5, needs_peer_artifact=False)
            arts.append(self._orchestrators[domain].run(task, st))
        return self._aggregate(task, arts)

    # -- configs B/C/D -----------------------------------------------------
    def _run_hierarchical(self, task: Task) -> RunResult:
        decomp = self.planner.plan(task, self.fleet,
                                   horizontal=self.config.horizontal)
        arts = []
        for st in decomp.subtasks:
            orch = self._orchestrators[st.domain]
            arts.append(orch.run(task, st))
            if decomp.peer_review and arts[-1].success:
                # cheap peer-review pass boosts quality slightly
                arts[-1].quality = min(1.0, arts[-1].quality + 0.03)
                arts[-1].cost += 0.01
                arts[-1].latency += 0.6
        return self._aggregate(task, arts)

    def _aggregate(self, task: Task, arts: list[Artifact]) -> RunResult:
        if not arts:
            return RunResult(task.id, 0.0, 0.0, 0.0, False, 0, 0, 0)
        # Coordination loss grows with fan-out; failures drag quality down.
        qs = [a.quality for a in arts]
        quality = sum(qs) / len(qs) - 0.02 * max(0, len(arts) - 3)
        if any(not a.success for a in arts):
            quality -= 0.10
        quality = max(0.0, min(1.0, quality))
        cost = sum(a.cost for a in arts)
        latency = sum(a.latency for a in arts) * 0.55  # partial parallelism
        peer = self.bb.peer_resolutions if self.bb else 0
        esc = self.bb.escalations if self.bb else 0
        return RunResult(task.id, round(quality, 4), round(cost, 4),
                         round(latency, 2), quality >= 0.70,
                         len(arts), peer, esc)

    def run(self, task: Task) -> RunResult:
        if self.bb is not None:
            self.bb.reset()
        if not self.config.vertical:
            return self._run_single(task)
        return self._run_hierarchical(task)
