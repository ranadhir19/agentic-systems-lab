"""Collective Memory Fabric (CMF): a model-agnostic protocol for shared
agent memory.

A memory is a structured, versioned *claim* — never a bare string:

    claim = (subject, predicate, value) + confidence + evidence
            + provenance (agent, model family, timestamp)
            + validity window + version + status + access policy

Lifecycle: propose -> validate -> [merge | admit | reconcile] -> serve
           -> expire | correct | revoke. Nothing is ever deleted: superseded
and revoked claims remain as tombstones, so the fabric can explain *why*
it believes what it believes.

The central mechanism is evidence-weighted, recency-aware reconciliation
with distinct-agent quorum: a claim's strength is

    score = confidence * (0.5 + 0.5*recency) * (1 + 0.25 * distinct_agents)

where distinct_agents counts *independent observers* inside the quorum
window — not raw evidence items. One loud agent, however confident, cannot
outvote several independent ones. This is what stops misinformation
propagation while still letting genuine fact flips converge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import uuid


@dataclass
class Claim:
    id: str
    subject: str
    predicate: str
    value: str
    confidence: float
    evidence: list[tuple[str, int]]   # (agent_id, ts) — independent observations
    agent_id: str
    model_family: str
    ts: int
    valid_from: int
    valid_until: int
    version: int = 1
    status: str = "active"            # active|superseded|revoked|expired|rejected
    supersedes: str | None = None
    access: str = "internal"
    last_touch: int = 0               # last tick this claim earned evidence

    def to_mcp_resource(self) -> dict:
        """Serialize as an MCP-style resource (model-agnostic exchange)."""
        return {
            "uri": f"cmf://claims/{self.id}",
            "name": f"{self.subject}.{self.predicate}",
            "mimeType": "application/json",
            "text": json.dumps({
                "subject": self.subject, "predicate": self.predicate,
                "value": self.value, "confidence": self.confidence,
                "evidence": self.evidence, "provenance": {
                    "agent": self.agent_id, "model_family": self.model_family,
                    "ts": self.ts},
                "validity": [self.valid_from, self.valid_until],
                "version": self.version, "status": self.status,
                "supersedes": self.supersedes, "access": self.access,
            }),
        }


class FabricError(Exception):
    pass


class MemoryFabric:
    """The Collective Memory Fabric."""

    def __init__(self, ttl: int = 40, quorum_window: int = 10,
                 min_confidence: float = 0.3):
        self.ttl = ttl
        self.quorum_window = quorum_window
        self.min_confidence = min_confidence
        self._chains: dict[tuple[str, str], list[Claim]] = {}
        self.admissions = 0
        self.merges = 0
        self.reconciliations = 0
        self.rejections = 0

    # -- admission ------------------------------------------------------
    def admit(self, agent_id: str, model_family: str, subject: str,
              predicate: str, value: str, confidence: float,
              evidence: list[tuple[str, int]], ts: int,
              access: str = "internal") -> tuple[str, Claim]:
        self.admissions += 1
        if confidence < self.min_confidence or not evidence:
            self.rejections += 1
            return ("rejected", self._mk(agent_id, model_family, subject,
                                         predicate, value, confidence,
                                         evidence, ts, "rejected", access))
        key = (subject, predicate)
        chain = self._chains.setdefault(key, [])
        # merge: same value already active -> strengthen, don't fork.
        # Fresh evidence refreshes validity and recency: a claim that keeps
        # being confirmed does not go stale.
        for c in chain:
            if (c.status == "active" and c.value == value
                    and c.valid_from <= ts <= c.valid_until):
                for e in evidence:
                    if e not in c.evidence:
                        c.evidence.append(e)
                c.confidence = max(c.confidence, confidence)
                c.valid_until = max(c.valid_until, ts + self.ttl)
                c.last_touch = ts
                self.merges += 1
                return ("merged", c)
        new = self._mk(agent_id, model_family, subject, predicate, value,
                       confidence, list(evidence), ts, "active", access,
                       version=len(chain) + 1,
                       valid_until=ts + self.ttl)
        conflicts = [c for c in chain
                     if c.status == "active" and c.value != value
                     and not (ts > c.valid_until or ts + self.ttl < c.valid_from)]
        if not conflicts:
            chain.append(new)
            return ("admitted", new)
        self.reconciliations += 1
        winner = self._reconcile(new, conflicts, chain, ts)
        if winner is new:
            for c in conflicts:
                c.status = "superseded"
                c.supersedes = new.id
            chain.append(new)
            return ("admitted_by_reconciliation", new)
        new.status = "superseded"
        new.supersedes = winner.id
        chain.append(new)
        return ("rejected_by_reconciliation", new)

    def _mk(self, agent_id, model_family, subject, predicate, value,
            confidence, evidence, ts, status, access, version=1,
            valid_until=None) -> Claim:
        return Claim(id=uuid.uuid4().hex[:12], subject=subject,
                     predicate=predicate, value=value, confidence=confidence,
                     evidence=evidence, agent_id=agent_id,
                     model_family=model_family, ts=ts, valid_from=ts,
                     valid_until=valid_until if valid_until is not None else ts,
                     version=version, status=status, access=access,
                     last_touch=ts)

    def _recent_supporters(self, claim: Claim, chain: list[Claim],
                           ts: int) -> set[str]:
        agents = {a for (a, t) in claim.evidence
                  if 0 <= ts - t <= self.quorum_window}
        for c in chain:
            if c.value == claim.value and c is not claim:
                agents |= {a for (a, t) in c.evidence
                           if 0 <= ts - t <= self.quorum_window}
        return agents

    def _score(self, claim: Claim, chain: list[Claim], ts: int) -> float:
        n = len(self._recent_supporters(claim, chain, ts))
        # recency follows the freshest confirmation, not creation time
        recency = max(0.0, 1.0 - (ts - claim.last_touch) / (2 * self.quorum_window))
        return claim.confidence * (0.5 + 0.5 * recency) * (1 + 0.25 * n)

    def _reconcile(self, new: Claim, conflicts: list[Claim],
                   chain: list[Claim], ts: int) -> Claim:
        cands = [new] + conflicts
        return max(cands, key=lambda c: self._score(c, chain, ts))

    # -- read ------------------------------------------------------------
    def query(self, agent_id: str, subject: str, predicate: str,
              at: int) -> Claim | None:
        chain = self._chains.get((subject, predicate), [])
        live = [c for c in chain
                if c.status == "active" and c.valid_from <= at <= c.valid_until]
        if not live:
            return None
        return max(live, key=lambda c: c.version)

    def sweep(self, at: int) -> int:
        n = 0
        for chain in self._chains.values():
            for c in chain:
                if c.status == "active" and at > c.valid_until:
                    c.status = "expired"
                    n += 1
        return n

    # -- correction & revocation ------------------------------------------
    def propose_correction(self, agent_id: str, model_family: str,
                           subject: str, predicate: str, value: str,
                           confidence: float, evidence: list[tuple[str, int]],
                           ts: int) -> tuple[str, Claim]:
        """A correction is just a new claim — it goes through admission."""
        return self.admit(agent_id, model_family, subject, predicate, value,
                          confidence, evidence, ts)

    def revoke(self, claim_id: str, by_agent: str,
               evidence: list[tuple[str, int]], ts: int) -> bool:
        """Revocation needs quorum: 2+ distinct agents, or the author."""
        for chain in self._chains.values():
            for c in chain:
                if c.id == claim_id and c.status == "active":
                    supporters = {by_agent} | {a for (a, _) in evidence}
                    if len(supporters) >= 2 or by_agent == c.agent_id:
                        c.status = "revoked"
                        return True
                    return False
        return False

    def contradiction_rate(self, at: int) -> float:
        tot, bad = 0, 0
        for (s, p), chain in self._chains.items():
            live = {c.value for c in chain
                    if c.status == "active" and c.valid_from <= at <= c.valid_until}
            tot += 1
            if len(live) > 1:
                bad += 1
        return bad / tot if tot else 0.0
