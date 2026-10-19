"""Semantic understanding: utterance -> SemanticFrame.

Builds a meaning representation (entities, states, conditions, topics)
rather than a class label.  Lexicon-driven extraction over the token
stream, combined with prototype similarities from the semantic space.
Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classifier import tokenize
from .embeddings import SemanticSpace

# Lexicons: surface forms -> canonical entity/state tags.
ENTITY_LEXICON = {
    # devices
    "laptop": "device:laptop", "computer": "device:laptop", "macbook": "device:laptop",
    "router": "device:router", "phone": "device:phone", "mobile": "device:phone",
    # money
    "balance": "topic:money", "money": "topic:money", "account": "topic:money",
    "afford": "topic:money", "lunch": "topic:food", "dinner": "topic:food",
    "hungry": "state:hungry", "starving": "state:hungry",
    "food": "topic:food", "eat": "topic:food", "meal": "topic:food",
    "restaurant": "topic:food",
    # auth
    "password": "topic:auth", "otp": "topic:auth", "passcode": "topic:auth",
    "login": "topic:auth", "locked": "state:locked_out",
    # travel
    "flight": "topic:travel", "hotel": "topic:travel", "booking": "topic:booking",
    "reservation": "topic:booking",
    # symptoms
    "overheating": "symptom:thermal", "hot": "symptom:thermal",
    "dark": "symptom:display", "blank": "symptom:display", "screen": "part:screen",
    "wifi": "topic:network", "internet": "topic:network",
    # interview / clothing
    "interview": "topic:interview", "wear": "topic:clothing",
    "clothing": "topic:clothing", "attire": "topic:clothing",
    # creative
    "haiku": "topic:creative", "poem": "topic:creative",
    # order
    "order": "topic:order", "package": "topic:order", "delivery": "topic:order",
    # price
    "cheaper": "modifier:cheaper", "cheap": "modifier:cheaper",
    "cancel": "action:cancel",
}

STATE_PATTERNS = [
    ("after login", "condition:after_login"),
    ("after log in", "condition:after_login"),
    ("changed my phone", "state:phone_changed"),
    ("new phone number", "state:phone_changed"),
    ("can't receive", "state:cannot_receive"),
    ("cannot receive", "state:cannot_receive"),
    ("forgot my", "state:forgotten"),
    ("i forgot", "state:forgotten"),
    ("tomorrow", "time:tomorrow"),
]

CONJUNCTION_CUES = [" and ", " but ", " also ", ",", " plus "]


@dataclass
class SemanticFrame:
    text: str
    entities: dict[str, str]      # canonical tag -> surface form
    states: list[str]
    topics: list[str]
    clauses: list[str]            # split on conjunction cues (multi-intent)
    prototype_hits: list[tuple[str, float]]


def split_clauses(text: str) -> list[str]:
    low = " " + text.lower() + " "
    parts, cur, i = [], "", 0
    # simple splitter on cue phrases
    tmp = low
    for cue in CONJUNCTION_CUES:
        tmp = tmp.replace(cue, "\n")
    parts = [p.strip(" ,") for p in tmp.split("\n")]
    return [p for p in parts if len(p.split()) >= 2]


class SemanticUnderstanding:
    def __init__(self, space: SemanticSpace | None = None) -> None:
        self.space = space or SemanticSpace()

    def parse(self, text: str) -> SemanticFrame:
        toks = tokenize(text)
        entities, topics, states = {}, [], []
        for t in toks:
            tag = ENTITY_LEXICON.get(t)
            if not tag:
                continue
            kind = tag.split(":")[0]
            if kind in ("device",):
                entities[tag] = t
            elif kind in ("topic", "symptom", "part", "modifier", "action"):
                if tag not in topics:
                    topics.append(tag)
            elif kind == "state":
                if tag not in states:
                    states.append(tag)
        low = text.lower()
        for pat, tag in STATE_PATTERNS:
            if pat in low and tag not in states:
                states.append(tag)
        return SemanticFrame(
            text=text,
            entities=entities,
            states=states,
            topics=topics,
            clauses=split_clauses(text),
            prototype_hits=self.space.similarities(text)[:6],
        )
