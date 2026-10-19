"""HealFlow workflow model: dependency-aware DAGs with contracts.

Every step declares:
- preconditions: predicates that must hold on the state before execution
- postconditions: predicates that must hold on (state, output) after
- compensation: the tool that undoes this step's external side effect
- risk: 'low' | 'high' (high-risk repairs need human approval)
- substitutable: whether an alternate tool can replace this step's tool

Checkpoints snapshot the state before each step, so repair can roll back
to the last known-good point instead of restarting the world.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class StepDef:
    id: str
    tool: str
    args: dict = field(default_factory=dict)
    pre: tuple[str, ...] = ()
    post: tuple[str, ...] = ()
    compensation: str | None = None
    risk: str = "low"
    substitutable: bool = False
    external: bool = False      # True: has real-world side effects


@dataclass
class WorkflowDef:
    name: str
    steps: list[StepDef]        # topological order
    initial_state: dict = field(default_factory=dict)


class RunState:
    def __init__(self, workflow: WorkflowDef):
        self.workflow = workflow
        self.state: dict = copy.deepcopy(workflow.initial_state)
        self.outputs: dict[str, dict] = {}
        self.checkpoints: dict[str, dict] = {}   # step_id -> state snapshot
        self.completed: list[str] = []
        self.events: list[dict] = []
        self.tool_calls = 0

    def checkpoint(self, step_id: str) -> None:
        self.checkpoints[step_id] = copy.deepcopy(self.state)

    def rollback(self, step_id: str) -> None:
        """Restore state to before step_id; drop it and later completions.

        If step_id never completed (it failed on first execution), there is
        nothing to drop — just restore its checkpoint.
        """
        self.state = copy.deepcopy(self.checkpoints[step_id])
        if step_id in self.completed:
            idx = self.completed.index(step_id)
            self.completed = self.completed[:idx]
        for sid in list(self.outputs):
            if sid not in self.completed:
                del self.outputs[sid]

    def log(self, kind: str, **kw) -> None:
        self.events.append({"kind": kind, **kw})
