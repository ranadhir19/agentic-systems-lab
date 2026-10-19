"""Decision model for complexity-scored agent partitioning.

A Decision is the unit of work to be allocated to agents. Its complexity is
driven by how many distinct state groups (partition blocks) the agent must
distinguish to decide correctly, scaled by whether the decision is simple
or composite.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SIMPLE = "simple"
COMPOSITE = "composite"

VALID_CATEGORIES = (SIMPLE, COMPOSITE)


@dataclass
class Decision:
    """One decision in a multi-agent workflow.

    Attributes:
        name: human-readable decision name.
        category: "simple" or "composite" (from the problem statement).
        blocks: distinct state groups that influence the decision outcome.
            The count of blocks is the raw complexity signal.
        domains: domain tags used to judge whether two medium decisions are
            similar enough to share an agent.
        compute_cost: abstract compute units per evaluation (optional).
        latency_ms: expected latency per evaluation in ms (optional).
        depends_on: names of decisions that must complete first (used by
            the sequential planner).
    """

    name: str
    category: str
    blocks: list[str] = field(default_factory=list)
    domains: tuple[str, ...] = ()
    compute_cost: float = 0.0
    latency_ms: float = 0.0
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"category must be one of {VALID_CATEGORIES}, got {self.category!r}"
            )
        self.blocks = list(self.blocks)
        self.domains = tuple(self.domains)
        self.depends_on = tuple(self.depends_on)
        if len(self.blocks) == 0:
            raise ValueError(f"decision {self.name!r} needs at least one state block")
