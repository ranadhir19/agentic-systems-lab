"""Conversation memory: multi-turn context tracking.

Traditional dialogue managers are stateless across turns.  The inference
pipeline keeps a working memory of entities, active goals, resolved
references, and pending questions so later turns resolve against earlier
state ("Make it cheaper", "What should I wear?").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classifier import tokenize


@dataclass
class Turn:
    speaker: str  # "user" | "assistant"
    text: str
    goals: list = field(default_factory=list)


class ConversationMemory:
    def __init__(self) -> None:
        self.turns: list[Turn] = []
        self.entities: dict[str, str] = {}     # e.g. {"destination": "Chicago"}
        self.active_goals: list = []           # Goal objects from goals.py
        self.pending_questions: list[str] = []
        self.facts: dict[str, str] = {}        # e.g. {"interview_date": "tomorrow"}

    # -- writes ----------------------------------------------------------
    def add_user(self, text: str) -> None:
        self.turns.append(Turn("user", text))

    def add_assistant(self, text: str, goals: list | None = None) -> None:
        self.turns.append(Turn("assistant", text, goals or []))

    def remember_entity(self, key: str, value: str) -> None:
        self.entities[key] = value

    def remember_fact(self, key: str, value: str) -> None:
        self.facts[key] = value

    def set_active_goals(self, goals: list) -> None:
        self.active_goals = goals

    # -- reads -----------------------------------------------------------
    def last_user_turn(self) -> str:
        for t in reversed(self.turns):
            if t.speaker == "user":
                return t.text
        return ""

    def previous_user_turn(self) -> str:
        seen = 0
        for t in reversed(self.turns):
            if t.speaker == "user":
                seen += 1
                if seen == 2:
                    return t.text
        return ""

    def references_prior(self, text: str) -> bool:
        """Does this utterance contain anaphoric / elliptical reference?"""
        toks = set(tokenize(text))
        markers = {"it", "that", "this", "cheaper", "more", "less", "them",
                   "those", "theirs", "same"}
        return bool(toks & markers) or len(toks) <= 4

    def summary(self) -> str:
        parts = []
        if self.entities:
            parts.append("entities=" + str(self.entities))
        if self.facts:
            parts.append("facts=" + str(self.facts))
        if self.active_goals:
            parts.append("goals=" + str([g.id for g in self.active_goals]))
        return "; ".join(parts) if parts else "(empty)"
