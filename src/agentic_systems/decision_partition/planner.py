"""Sequential planner: stage-aware partitioning for dependent decisions.

Multi-step workflows have dependencies (settlement needs damage, policy
and fraud first). The planner topologically stages decisions, partitions
each stage independently (agents are reusable across stages, since stages
run in order), and measures handoff cost plus critical-path complexity:

    critical_path = max over dependency chains of (sum of stage max scores)

so the operator sees both the longest reasoning chain and where
cross-agent handoffs fall.
"""
from __future__ import annotations

from .decisions import Decision
from .partition import Partition, cross_agent_handoffs, partition_decisions
from .scoring import Scorer


def topological_stages(decisions: list[Decision]) -> list[list[Decision]]:
    """Group decisions into execution stages by dependency depth."""
    by_name = {d.name: d for d in decisions}
    depth: dict[str, int] = {}

    def _depth(name: str, seen: tuple[str, ...]) -> int:
        if name in seen:
            raise ValueError(f"dependency cycle involving {name!r}")
        if name in depth:
            return depth[name]
        d = by_name.get(name)
        if d is None:
            raise KeyError(f"decision {name!r} depends on unknown {name!r}")
        if not d.depends_on:
            depth[name] = 0
        else:
            depth[name] = 1 + max(_depth(dep, seen + (name,))
                                  for dep in d.depends_on)
        return depth[name]

    for d in decisions:
        _depth(d.name, ())
    max_depth = max(depth.values(), default=-1)
    stages: list[list[Decision]] = [[] for _ in range(max_depth + 1)]
    for d in decisions:
        stages[depth[d.name]].append(d)
    return stages


def stage_partitions(decisions: list[Decision],
                     scorer: Scorer | None = None,
                     namer=None) -> list[Partition]:
    """Partition each topological stage independently."""
    scorer = scorer or Scorer()
    return [partition_decisions(stage, scorer=scorer, namer=namer)
            for stage in topological_stages(decisions)]


def critical_path_score(decisions: list[Decision],
                        scorer: Scorer | None = None) -> float:
    """Max over dependency chains of summed decision scores (longest chain)."""
    scorer = scorer or Scorer()
    by_name = {d.name: d for d in decisions}
    memo: dict[str, float] = {}

    def _best(name: str) -> float:
        if name in memo:
            return memo[name]
        d = by_name[name]
        own = scorer.score(d)
        if not d.depends_on:
            memo[name] = own
        else:
            memo[name] = own + max(_best(dep) for dep in d.depends_on)
        return memo[name]

    return max((_best(d.name) for d in decisions), default=0.0)


def workflow_plan(decisions: list[Decision],
                  scorer: Scorer | None = None,
                  namer=None) -> dict:
    """Full sequential plan: stages, per-stage partitions, handoffs, critical path."""
    scorer = scorer or Scorer()
    stages = topological_stages(decisions)
    parts = stage_partitions(decisions, scorer=scorer, namer=namer)
    # global partition for handoff accounting across the whole workflow
    global_partition = partition_decisions(decisions, scorer=scorer, namer=namer)
    return {
        "stages": [[d.name for d in stage] for stage in stages],
        "stage_partitions": parts,
        "stage_agent_counts": [len(p.agents) for p in parts],
        "max_concurrent_agents": max((len(p.agents) for p in parts), default=0),
        "global_partition": global_partition,
        "cross_agent_handoffs": cross_agent_handoffs(decisions, global_partition),
        "critical_path_score": critical_path_score(decisions, scorer),
    }
