"""Horizontal coordination layer: the blackboard.

The blackboard lets domain orchestrators coordinate *peer-to-peer* without
escalating to the meta-orchestrator. Coordination follows a lightweight
contract protocol:

    propose(artifact) -> offers an intermediate result to peers
    request(domain, need) -> asks a peer domain for an artifact
    commit(artifact) -> a peer accepts and binds to the artifact

Every cross-domain handoff that resolves on the blackboard is one
*escalation avoided* — a direct measure of the horizontal layer's value.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Posting:
    domain: str
    kind: str                  # "offer" | "request"
    payload: str
    quality: float = 0.0


class Blackboard:
    def __init__(self):
        self._postings: list[Posting] = []
        self.peer_resolutions = 0
        self.escalations = 0

    def propose(self, domain: str, payload: str, quality: float) -> None:
        self._postings.append(Posting(domain, "offer", payload, quality))

    def request(self, from_domain: str, need_domain: str, need: str) -> Posting | None:
        """A peer asks another domain for an artifact.

        Returns the best matching offer, or None if no peer can help —
        in which case the caller must escalate vertically.
        """
        candidates = [p for p in self._postings
                      if p.domain == need_domain and p.kind == "offer"]
        if not candidates:
            self.escalations += 1
            return None
        best = max(candidates, key=lambda p: p.quality)
        self.peer_resolutions += 1
        return best

    def reset_counters(self) -> None:
        self.peer_resolutions = 0
        self.escalations = 0

    def reset(self) -> None:
        """Full per-task reset: postings must not leak across tasks."""
        self._postings = []
        self.reset_counters()
