"""Meridian quickstart: learned routing vs a fixed single orchestrator.

Generates 24 seeded tasks and runs them through two architectures:
  A  single orchestrator, fixed worker mapping
  D  full Meridian: vertical hierarchy + horizontal blackboard +
     Thompson-sampling router + decomposition planner

Note: 24 tasks is a small sample, so expect noise — the point here is the
machinery (decompose, route, coordinate, learn). The full 240-task
benchmark lives in 01-meridian-orchestration/experiments/.

Run:  python3 examples/01_meridian_quickstart.py
"""
from __future__ import annotations

from agentic_systems.meridian import MeridianSystem, RunConfig, TaskGenerator


def main() -> None:
    tasks = TaskGenerator(seed=7).generate(24)

    configs = [
        ("A: single", RunConfig("A", vertical=False, horizontal=False,
                                optimized=False)),
        ("D: meridian (full)", RunConfig("D", vertical=True, horizontal=True,
                                         optimized=True)),
    ]
    for label, cfg in configs:
        system = MeridianSystem(cfg, seed=7)
        results = [system.run(t) for t in tasks]
        succ = sum(1 for r in results if r.success) / len(results)
        quality = sum(r.quality for r in results) / len(results)
        cost = sum(r.cost for r in results) / len(results)
        peer = sum(r.peer_resolutions for r in results)
        print(f"{label:20s} success={succ:5.1%}  quality={quality:.3f}  "
              f"cost/task=${cost:.4f}  peer_resolutions={peer}")


if __name__ == "__main__":
    main()
