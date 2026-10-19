"""Simulated aligned model.

A stand-in for a post-training-aligned LLM: it holds a *neutral* knowledge
base and a *creator-ideology* vector. For each probe it selects a framing
as a function of the ideology vector, allocates emphasis across facts, and
may refuse when the probe conflicts with the ideology. All mechanisms are
explicit and parameterized — the point is to measure the methodology
(frame selection, refusal, emphasis), not to emulate any real model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .knowledge import Topic
from .values import DIMENSIONS, ValueProfile


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


@dataclass
class ModelResponse:
    probe_id: str
    prompt: str
    text: str
    frame_name: str
    framing: Dict[str, float]      # expressed lean per dimension
    emphasis: List[float]         # weight per fact, sums to 1
    refused: bool
    refusal_reason: str = ""
    included_facts: List[int] = field(default_factory=list)


class SimulatedAlignedModel:
    """Neutral KB + creator ideology -> measurably framed responses."""

    def __init__(self, profile: ValueProfile, version: str = "v1",
                 frame_noise: float = 0.05, emphasis_beta: float = 2.0,
                 refusal_gain: float = 5.0, refusal_mid: float = 0.60):
        self.profile = profile
        self.version = version
        self.frame_noise = frame_noise
        self.emphasis_beta = emphasis_beta
        self.refusal_gain = refusal_gain
        self.refusal_mid = refusal_mid

    def ideological_loading(self, topic: Topic) -> float:
        """Signed loading of this probe on the model's ideology."""
        a = self.profile.values[topic.primary_dim]
        a += 0.3 * self.profile.values[topic.secondary_dim]
        return float(np.clip(a, -1.0, 1.0))

    def _maybe_refuse(self, topic: Topic, loading: float,
                      rng: np.random.Generator) -> Optional[str]:
        # Conflict: probe challenges the sign of the model's leaning.
        conflict = abs(loading) if np.sign(loading) == topic.challenges else 0.0
        p = topic.sensitivity * _sigmoid(self.refusal_gain * (conflict - self.refusal_mid))
        if rng.random() < p:
            return ("I can't provide a balanced answer on this topic under "
                    "current policy.")
        return None

    def respond(self, topic: Topic, rng: np.random.Generator) -> ModelResponse:
        loading = self.ideological_loading(topic)
        refusal = self._maybe_refuse(topic, loading, rng)
        if refusal is not None:
            framing = {d: 0.0 for d in DIMENSIONS}
            return ModelResponse(
                probe_id=topic.id, prompt=topic.prompt, text=refusal,
                frame_name="refused", framing=framing,
                emphasis=[1.0 / len(topic.facts)] * len(topic.facts),
                refused=True, refusal_reason="policy-conflict",
                included_facts=[])

        # Frame selection: closest lean to ideological loading + noise.
        scores = np.array([
            abs(f.lean - loading) + rng.normal(0.0, self.frame_noise)
            for f in topic.frames
        ])
        frame = topic.frames[int(np.argmin(scores))]

        # Emphasis: softmax over fact alignment with the chosen frame.
        aligns = np.array([f.lean * frame.lean for f in topic.facts])
        w = np.exp(self.emphasis_beta * aligns)
        emphasis = (w / w.sum()).tolist()
        included = [i for i, e in enumerate(emphasis) if e >= 0.20]

        text = frame.template.format(
            **{f"f{i}": topic.facts[i].text for i in range(len(topic.facts))})

        framing = {d: 0.0 for d in DIMENSIONS}
        framing[topic.primary_dim] = float(np.clip(
            frame.lean + rng.normal(0.0, 0.03), -1.0, 1.0))
        framing[topic.secondary_dim] = float(np.clip(
            0.3 * frame.lean + rng.normal(0.0, 0.03), -1.0, 1.0))
        framing["tone"] = float(np.clip(
            0.5 * self.profile.values["tone"] + rng.normal(0.0, 0.03),
            -1.0, 1.0))

        return ModelResponse(
            probe_id=topic.id, prompt=topic.prompt, text=text,
            frame_name=frame.name, framing=framing, emphasis=emphasis,
            refused=False, included_facts=included)

    def respond_all(self, topics: List[Topic],
                    rng: np.random.Generator) -> List[ModelResponse]:
        return [self.respond(t, rng) for t in topics]
