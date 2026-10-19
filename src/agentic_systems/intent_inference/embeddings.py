"""Semantic space for intent inference.

Instead of classifying into a fixed catalog, the pipeline embeds the
utterance and matches it against *situation prototypes* — descriptions of
what a user might be trying to accomplish.  Intent is never a direct
classification target; it emerges from semantic similarity plus
rule-driven goal extraction.

Implementation: TF-IDF over the prototype corpus with synonym expansion,
cosine similarity.  numpy only, deterministic.
"""

from __future__ import annotations

import numpy as np

from .catalog import PROTOTYPES, PROTO_REQUIRES, SYNONYMS
from .classifier import TfidfVectorizer, tokenize


def expand(text: str) -> str:
    """Append synonyms so paraphrase neighborhoods overlap in TF-IDF space."""
    toks = tokenize(text)
    extra: list[str] = []
    for t in toks:
        extra.extend(SYNONYMS.get(t, []))
    return text + " " + " ".join(extra)


def _gated(prototype_id: str, text: str) -> bool:
    """A prototype only fires when its discriminative terms are present.

    Checked against RAW tokens (not synonym-expanded): expansion is for
    similarity, but gating needs the actual words — otherwise "hungry"
    would license the restaurant prototype via expanded "restaurant".
    """
    required = PROTO_REQUIRES.get(prototype_id)
    if not required:
        return True
    toks = set(tokenize(text))
    return bool(toks & required)


class SemanticSpace:
    def __init__(self) -> None:
        corpus = [expand(desc) for _, desc, _ in PROTOTYPES]
        self.vec = TfidfVectorizer().fit(corpus)
        self.proto_matrix = self.vec.transform(corpus)
        self.proto_ids = [pid for pid, _, _ in PROTOTYPES]
        self.proto_goals = {pid: goals for pid, _, goals in PROTOTYPES}

    def similarities(self, text: str) -> list[tuple[str, float]]:
        q = self.vec.transform([expand(text)])[0]
        sims = self.proto_matrix @ q
        order = np.argsort(-sims)
        return [(self.proto_ids[i], float(sims[i])) for i in order]

    def top_goals(self, text: str, k: int = 4,
                  min_sim: float = 0.08) -> list[tuple[str, float]]:
        """Aggregate prototype similarities into goal scores.

        Prototypes failing their REQUIRES gate are excluded before scoring.
        """
        scores: dict[str, float] = {}
        for pid, sim in self.similarities(text)[:k]:
            if sim < min_sim or not _gated(pid, text):
                continue
            for g in self.proto_goals[pid]:
                scores[g] = scores.get(g, 0.0) + sim
        return sorted(scores.items(), key=lambda kv: -kv[1])
