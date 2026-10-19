"""Planning: task decomposition, ask-vs-act decisions, tool selection.

The planner turns structured goals into an execution plan.  The key
decision traditional routers never make: whether to ask a clarifying
question, call a tool, or delegate — based on missing information and
confidence, not on a confidence threshold over labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import STUB_AGENTS
from .goals import Goal


@dataclass
class PlanStep:
    action: str            # "ask" | "tool" | "delegate" | "respond"
    detail: str
    goal_id: str = ""
    agent: str = ""
    tool: str = ""


@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)

    def actions(self) -> list[str]:
        return [s.action for s in self.steps]


class TaskDecomposer:
    """Split goals into ordered subtasks; order auth before money movement."""

    ORDER = ["auth_assistance", "reset_password", "update_phone",
             "check_balance", "transfer_money"]

    def order(self, goals: list[Goal]) -> list[Goal]:
        rank = {g: i for i, g in enumerate(self.ORDER)}
        return sorted(goals,
                      key=lambda g: (rank.get(g.id, 99),
                                     g.kind != "primary"))


class Planner:
    def __init__(self, ask_threshold: float = 0.55) -> None:
        self.ask_threshold = ask_threshold
        self.decomposer = TaskDecomposer()

    def plan(self, goals: list[Goal]) -> Plan:
        plan = Plan()
        for g in self.decomposer.order(goals):
            # Missing critical info -> ask first (the extractor only flags
            # info whose evidence is absent, so the question is targeted).
            if g.missing_info:
                for q in g.missing_info:
                    plan.steps.append(PlanStep(
                        action="ask", detail=q, goal_id=g.id))
                # still record the follow-on tool step so the plan is complete
                if g.tools:
                    plan.steps.append(PlanStep(
                        action="tool", detail=f"after answer: {g.tools[0]}",
                        goal_id=g.id, tool=g.tools[0]))
            elif g.tools:
                plan.steps.append(PlanStep(
                    action="tool", detail=g.tools[0],
                    goal_id=g.id, tool=g.tools[0]))
            else:
                plan.steps.append(PlanStep(
                    action="respond",
                    detail=f"answer directly: {g.description}",
                    goal_id=g.id))
            # delegate each goal to the owning specialist
            agent = self._owner(g.id)
            if agent:
                plan.steps.append(PlanStep(
                    action="delegate",
                    detail=f"{agent} owns {g.id}",
                    goal_id=g.id, agent=agent))
        return plan

    @staticmethod
    def _owner(goal_id: str) -> str:
        for agent, goals in STUB_AGENTS.items():
            if goal_id in goals:
                return agent
        return "LifestyleAgent"


class ToolSelector:
    """Choose the concrete tool call per goal (already attached by Goal)."""

    @staticmethod
    def select(goal: Goal) -> str:
        return goal.tools[0] if goal.tools else "llm.generate"
