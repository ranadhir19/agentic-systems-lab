"""Orchestrator + specialized stub agents.

In the enterprise pipeline, an orchestrator dispatches decomposed subtasks
to specialized agents and synthesizes their results.  The stubs here are
deterministic stand-ins: they return structured outcomes (never free text
that would need grading by an LLM), so the benchmark measures the
*architecture* — goal inference, decomposition, delegation — not model
eloquence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import STUB_AGENTS
from .goals import Goal
from .planner import Plan, PlanStep


@dataclass
class AgentResult:
    agent: str
    goal_id: str
    outcome: str
    data: dict = field(default_factory=dict)


class StubAgent:
    """A specialist that 'executes' goals in its capability set."""

    RESPONSES = {
        "check_balance": "balance=$4,231.09",
        "transfer_money": "transfer=initiated",
        "reset_password": "reset_link=sent",
        "update_phone": "phone=updated",
        "auth_assistance": "identity=verified; access restored",
        "book_flight": "flight=reserved",
        "cancel_booking": "booking=cancelled",
        "track_order": "package=arrives Thursday",
        "laptop_support": "troubleshooting guide provided",
        "diagnose_display": "diagnosis started: display subsystem",
        "diagnose_thermal": "diagnosis started: thermal subsystem",
        "wifi_help": "network profile reset",
        "book_hotel": "hotel=reserved 2 nights",
        "refine_search": "search refined: max price lowered",
        "interview_prep": "prep plan generated",
        "attire_advice": "attire guidance provided",
        "food_need": "options: nearby restaurants + quick recipes",
        "restaurant_suggestion": "suggestion: Bella Italia downtown",
        "creative_writing": "haiku composed",
        "general_assist": "acknowledged; awaiting clarification",
    }

    def __init__(self, name: str) -> None:
        self.name = name
        self.capabilities = STUB_AGENTS[name]

    def can(self, goal_id: str) -> bool:
        return goal_id in self.capabilities

    def execute(self, goal: Goal, tool: str) -> AgentResult:
        return AgentResult(
            agent=self.name,
            goal_id=goal.id,
            outcome=self.RESPONSES.get(goal.id, "handled"),
            data={"tool": tool,
                  "constraints": goal.constraints},
        )


class Orchestrator:
    def __init__(self) -> None:
        self.agents = {name: StubAgent(name) for name in STUB_AGENTS}

    def dispatch(self, plan: Plan, goals: list[Goal]) -> list[AgentResult]:
        by_id = {g.id: g for g in goals}
        results: list[AgentResult] = []
        for step in plan.steps:
            if step.action not in ("tool", "delegate"):
                continue
            goal = by_id.get(step.goal_id)
            if goal is None:
                continue
            agent = self.agents.get(step.agent) or self._find_owner(goal.id)
            tool = step.tool or (goal.tools[0] if goal.tools else "llm.generate")
            results.append(agent.execute(goal, tool))
        # de-duplicate: one result per goal (tool+delegate both fire)
        seen: dict[str, AgentResult] = {}
        for r in results:
            seen.setdefault(r.goal_id, r)
        return list(seen.values())

    def _find_owner(self, goal_id: str) -> StubAgent:
        for agent in self.agents.values():
            if agent.can(goal_id):
                return agent
        return self.agents["LifestyleAgent"]
