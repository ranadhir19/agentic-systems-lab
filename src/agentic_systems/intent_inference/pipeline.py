"""InferencePipeline: the full ChatGPT-style loop.

    user text
        -> ConversationMemory
        -> SemanticUnderstanding   (meaning, not labels)
        -> GoalExtractor           (structured goals: primary/secondary,
                                    constraints, missing info, confidence)
        -> Planner                 (decompose, ask-vs-act, tools, delegation)
        -> Orchestrator            (specialized stub agents execute)
        -> response

There is no intent-classification module anywhere in this path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .embeddings import SemanticSpace
from .goals import Goal, GoalExtractor
from .memory import ConversationMemory
from .orchestrator import AgentResult, Orchestrator
from .planner import Plan, Planner
from .understanding import SemanticFrame, SemanticUnderstanding


@dataclass
class TurnResult:
    user_text: str
    goals: list[Goal]
    plan: Plan
    questions_asked: list[str]
    agent_results: list[AgentResult]
    response: str
    used_context: bool


class InferencePipeline:
    def __init__(self, seed: int = 0) -> None:
        self.space = SemanticSpace()
        self.understanding = SemanticUnderstanding(self.space)
        self.extractor = GoalExtractor(self.space)
        self.planner = Planner()
        self.orchestrator = Orchestrator()
        self.memory = ConversationMemory()
        self.seed = seed

    def reset(self) -> None:
        self.memory = ConversationMemory()

    def turn(self, text: str) -> TurnResult:
        used_context = self.memory.references_prior(text) and bool(
            self.memory.active_goals)
        self.memory.add_user(text)

        frame: SemanticFrame = self.understanding.parse(text)
        goals: list[Goal] = self.extractor.extract(frame, self.memory)
        self.memory.set_active_goals(goals)
        # persist salient entities/facts for later turns
        for tag, surf in frame.entities.items():
            self.memory.remember_entity(tag, surf)
        if "interview_prep" in [g.id for g in goals] and \
                "time:tomorrow" in frame.states:
            self.memory.remember_fact("interview_when", "tomorrow")

        plan: Plan = self.planner.plan(goals)
        questions = [s.detail for s in plan.steps if s.action == "ask"]
        results = self.orchestrator.dispatch(plan, goals)
        response = self._respond(goals, questions, results)
        self.memory.add_assistant(response, goals)
        return TurnResult(text, goals, plan, questions, results,
                          response, used_context)

    def run_conversation(self, turns: list[str]) -> list[TurnResult]:
        self.reset()
        return [self.turn(t) for t in turns]

    # -- response synthesis (deterministic templates) --------------------
    def _respond(self, goals: list[Goal], questions: list[str],
                 results: list[AgentResult]) -> str:
        parts = []
        if questions:
            parts.append("To help: " + " ".join(questions))
        for r in results:
            parts.append(f"[{r.agent}] {r.goal_id}: {r.outcome}.")
        if not parts:
            parts.append("Understood.")
        return " ".join(parts)
