"""Dynamic re-scoring: update complexity as evidence arrives.

Beliefs change: new state distinctions are discovered, old ones are
retired, a decision is reclassified simple <-> composite. The
DynamicPartitioner applies evidence updates, detects complexity-level
threshold crossings, and re-partitions only when a crossing forces an
assignment change. It tracks assignment stability across re-partitions so
operators can see how volatile the agent topology is.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .decisions import COMPOSITE, SIMPLE, Decision
from .partition import Partition, assignment_churn, partition_decisions
from .scoring import Scorer


@dataclass
class EvidenceEvent:
    step: int
    decision_name: str
    change: str
    old_score: float
    new_score: float
    old_level: str
    new_level: str

    @property
    def crossed_threshold(self) -> bool:
        return self.old_level != self.new_level


@dataclass
class RepartitionRecord:
    step: int
    partition: Partition
    triggers: list[str]
    stability_vs_prev: float  # 1 - churn; 1.0 means nothing moved


class DynamicPartitioner:
    """Holds live decisions, applies evidence, re-partitions on crossings."""

    def __init__(self,
                 decisions: list[Decision],
                 scorer: Scorer | None = None,
                 namer=None) -> None:
        self.decisions: dict[str, Decision] = {d.name: d for d in decisions}
        self.scorer = scorer or Scorer()
        self.namer = namer
        self.step = 0
        self.events: list[EvidenceEvent] = []
        self.history: list[RepartitionRecord] = []
        self._last_partition: Partition | None = None
        # initial partition at step 0
        self.repartition(triggers=["initial"])

    def observe(self,
                decision_name: str,
                added_blocks: tuple[str, ...] = (),
                removed_blocks: tuple[str, ...] = (),
                new_category: str | None = None) -> EvidenceEvent:
        """Apply one evidence update; returns the scored event."""
        if decision_name not in self.decisions:
            raise KeyError(f"unknown decision {decision_name!r}")
        d = self.decisions[decision_name]
        old_score = self.scorer.score(d)
        old_level = self.scorer.level(d)

        for b in removed_blocks:
            if b in d.blocks:
                d.blocks.remove(b)
        d.blocks.extend(b for b in added_blocks if b not in d.blocks)
        if new_category is not None:
            if new_category not in (SIMPLE, COMPOSITE):
                raise ValueError(f"bad category {new_category!r}")
            d.category = new_category
        if not d.blocks:
            raise ValueError(f"decision {d.name!r} would be left with no blocks")

        new_score = self.scorer.score(d)
        new_level = self.scorer.level(d)
        parts = []
        if added_blocks:
            parts.append(f"+{len(added_blocks)} blocks")
        if removed_blocks:
            parts.append(f"-{len(removed_blocks)} blocks")
        if new_category is not None:
            parts.append(f"category->{new_category}")
        event = EvidenceEvent(
            step=self.step + 1,
            decision_name=decision_name,
            change=", ".join(parts) or "no-op",
            old_score=old_score,
            new_score=new_score,
            old_level=old_level,
            new_level=new_level,
        )
        self.events.append(event)
        self.step += 1
        return event

    def repartition(self, triggers: list[str] | None = None) -> RepartitionRecord:
        """Recompute the partition; record stability vs the previous one."""
        partition = partition_decisions(
            list(self.decisions.values()), scorer=self.scorer, namer=self.namer)
        if self._last_partition is None:
            stability = 1.0
        else:
            stability = 1.0 - assignment_churn(self._last_partition, partition)
        record = RepartitionRecord(
            step=self.step,
            partition=partition,
            triggers=list(triggers or []),
            stability_vs_prev=stability,
        )
        self.history.append(record)
        self._last_partition = partition
        return record

    def maybe_repartition(self) -> RepartitionRecord | None:
        """Re-partition only if the latest event crossed a level threshold."""
        if not self.events:
            return None
        latest = self.events[-1]
        if latest.crossed_threshold:
            return self.repartition(
                triggers=[f"{latest.decision_name}: "
                           f"{latest.old_level}->{latest.new_level}"])
        return None

    def scores(self) -> dict[str, float]:
        return {name: self.scorer.score(d)
                for name, d in self.decisions.items()}

    def levels(self) -> dict[str, str]:
        return {name: self.scorer.level(d)
                for name, d in self.decisions.items()}
