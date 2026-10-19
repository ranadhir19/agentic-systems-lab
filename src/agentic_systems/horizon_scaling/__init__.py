"""Horizon Scaling: how does agent task success decay with horizon length,
and which architectures flatten the curve?

A task is N sequential steps with per-step fatal/corruption risk and
compounding state dependence. Agents:

- ``baseline``: linear executor, no intermediate verification
- ``checkpoints``: verify every k steps, rollback + redo on detection
- ``hierarchy``: planner decomposes into sub-tasks; narrower worker specs
- ``recovery``: checkpoints + diagnosis (targeted repair) + step retries
- ``voting``: per-step n-way majority vote

Public API:
    tasks:    TaskSpec, RunReport, draw_step, theoretical_per_step_q
    agents:   run_baseline, run_checkpoints, run_hierarchy, run_recovery,
              run_voting, run_hierarchy_checkpoints,
              theoretical_voting_per_step_q
    metrics:  wilson_ci, fit_exponential_decay, cost_per_success, summarize
    catalog:  default_spec, mix_spec, ERROR_MIXES
"""
from __future__ import annotations

from .tasks import TaskSpec, RunReport, draw_step, theoretical_per_step_q
from .agents import (
    run_baseline,
    run_checkpoints,
    run_hierarchy,
    run_recovery,
    run_voting,
    run_hierarchy_checkpoints,
    theoretical_voting_per_step_q,
)
from .metrics import wilson_ci, fit_exponential_decay, cost_per_success, summarize
from .catalog import default_spec, mix_spec, ERROR_MIXES

__all__ = [
    "TaskSpec",
    "RunReport",
    "draw_step",
    "theoretical_per_step_q",
    "run_baseline",
    "run_checkpoints",
    "run_hierarchy",
    "run_recovery",
    "run_voting",
    "run_hierarchy_checkpoints",
    "theoretical_voting_per_step_q",
    "wilson_ci",
    "fit_exponential_decay",
    "cost_per_success",
    "summarize",
    "default_spec",
    "mix_spec",
    "ERROR_MIXES",
]
