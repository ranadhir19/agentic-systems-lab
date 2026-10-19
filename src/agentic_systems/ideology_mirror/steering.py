"""Corporate steering: constitution-grounded response shaping.

Wraps a SimulatedAlignedModel so that frame selection is constrained to
the constitution's acceptable ranges (the "corporate alignment pipeline"
in miniature: RAG-style grounding snippet + disclosure + bounded framing).
Conformance is measured before/after with the constitution scorer.
"""
from __future__ import annotations

from typing import List

import numpy as np

from .constitution import AIConstitution, Principle
from .knowledge import Topic
from .model import ModelResponse, SimulatedAlignedModel
from .values import DIMENSIONS


class SteeredModel(SimulatedAlignedModel):
    """A model whose frame choice is projected into the constitution."""

    def __init__(self, base: SimulatedAlignedModel,
                 constitution: AIConstitution,
                 grounding_snippet: str = ""):
        super().__init__(base.profile, version=base.version + "+steered",
                         frame_noise=base.frame_noise,
                         emphasis_beta=base.emphasis_beta,
                         refusal_gain=base.refusal_gain,
                         refusal_mid=base.refusal_mid)
        self.base = base
        self.constitution = constitution
        self.grounding_snippet = grounding_snippet
        self._bounds = {p.dimension: (p.lo, p.hi)
                        for p in constitution.principles}

    def _project(self, lean: float, dim: str) -> float:
        lo, hi = self._bounds.get(dim, (-1.0, 1.0))
        return float(np.clip(lean, lo, hi))

    def respond(self, topic: Topic, rng: np.random.Generator) -> ModelResponse:
        # Steered models answer must-answer topics instead of refusing.
        resp = super().respond(topic, rng)
        if resp.refused and topic.id in self.constitution.must_answer:
            # Re-run with refusal disabled: pick the most central frame.
            old_gain = self.refusal_gain
            self.refusal_gain = 0.0
            resp = super().respond(topic, rng)
            self.refusal_gain = old_gain

        if resp.refused:
            return resp

        # Project the expressed framing into constitutional bounds by
        # re-selecting the in-bounds frame closest to the original choice.
        target = self._project(resp.framing.get(topic.primary_dim, 0.0),
                               topic.primary_dim)
        cands = [f for f in topic.frames
                 if self._bounds.get(topic.primary_dim, (-1, 1))[0]
                 <= f.lean <=
                 self._bounds.get(topic.primary_dim, (-1, 1))[1]]
        if cands:
            frame = min(cands, key=lambda f: abs(f.lean - target))
            aligns = np.array([fc.lean * frame.lean for fc in topic.facts])
            w = np.exp(self.emphasis_beta * aligns)
            emphasis = (w / w.sum()).tolist()
            text = frame.template.format(
                **{f"f{i}": topic.facts[i].text
                   for i in range(len(topic.facts))})
            framing = {d: 0.0 for d in DIMENSIONS}
            framing[topic.primary_dim] = float(np.clip(
                frame.lean + rng.normal(0.0, 0.03), -1.0, 1.0))
            framing[topic.secondary_dim] = float(np.clip(
                0.3 * frame.lean + rng.normal(0.0, 0.03), -1.0, 1.0))
            framing["tone"] = resp.framing["tone"]
            resp = ModelResponse(
                probe_id=resp.probe_id, prompt=resp.prompt, text=text,
                frame_name=frame.name, framing=framing, emphasis=emphasis,
                refused=False,
                included_facts=[i for i, e in enumerate(emphasis) if e >= 0.20])

        parts = []
        if self.grounding_snippet:
            parts.append(self.grounding_snippet)
        parts.append(resp.text)
        if self.constitution.disclosure:
            parts.append(self.constitution.disclosure)
        resp.text = "\n".join(parts)
        return resp


def steer(model: SimulatedAlignedModel, constitution: AIConstitution,
          grounding_snippet: str = "") -> SteeredModel:
    return SteeredModel(model, constitution, grounding_snippet)
