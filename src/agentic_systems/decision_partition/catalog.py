"""Worked example from the concept: smart insurance claim processing.

Five decisions, scored exactly as in the concept write-up:

    Decision                 Blocks  Weight  Score  Level
    Identity validation          3     1.0    3.0   low
    Damage assessment            5     2.0   10.0   high
    Policy rules compliance      4     2.0    8.0   medium
    Fraud detection              5     2.0   10.0   high
    Final settlement             4     1.0    4.0   low

Note on the damage-assessment blocks: the concept lists six state phrases
(minor / moderate / severe / total loss / disputed documentation / unknown)
but scores five blocks; we model five canonical blocks with "disputed or
unknown documentation" folded into one.

Expected partition: four agents -- Damage Specialist, Fraud Specialist,
Compliance Agent, Intake Agent (identity validation + final settlement).

Dependencies: damage, policy and fraud build on identity; settlement needs
damage, policy and fraud.
"""
from __future__ import annotations

from .decisions import COMPOSITE, SIMPLE, Decision
from .partition import HIGH, LOW, MEDIUM, Partition, partition_decisions
from .scoring import Scorer


def insurance_claim_decisions() -> list[Decision]:
    return [
        Decision(
            name="Identity validation",
            category=SIMPLE,
            blocks=["Correct ID", "Expired ID", "Mismatched records"],
            domains=("identity", "intake"),
        ),
        Decision(
            name="Damage assessment",
            category=COMPOSITE,
            blocks=["Minor", "Moderate", "Severe", "Total loss",
                    "Disputed or unknown documentation"],
            domains=("damage", "assessment"),
            depends_on=("Identity validation",),
        ),
        Decision(
            name="Policy rules compliance",
            category=COMPOSITE,
            blocks=["Coverage full", "Coverage partial",
                    "Exclusion applies", "Policy lapsed"],
            domains=("policy", "compliance", "legal"),
            depends_on=("Identity validation",),
        ),
        Decision(
            name="Fraud detection",
            category=COMPOSITE,
            blocks=["Normal", "Suspicious location", "Pattern mismatch",
                    "Past fraud history", "Model abnormality"],
            domains=("fraud", "risk"),
            depends_on=("Identity validation",),
        ),
        Decision(
            name="Final settlement",
            category=SIMPLE,
            blocks=["Approve", "Reduce", "Reject", "Manual review"],
            domains=("settlement", "intake"),
            depends_on=("Damage assessment", "Policy rules compliance",
                        "Fraud detection"),
        ),
    ]


def insurance_namer(kind: str, group: list[Decision]) -> str:
    """Canonical agent names from the concept write-up."""
    names = {d.name for d in group}
    if names == {"Damage assessment"}:
        return "Damage Specialist"
    if names == {"Fraud detection"}:
        return "Fraud Specialist"
    if names == {"Policy rules compliance"}:
        return "Compliance Agent"
    if names == {"Identity validation", "Final settlement"}:
        return "Intake Agent"
    # fallback to generic naming outside the canonical groupings
    from .partition import default_namer
    return default_namer(kind, group)


def insurance_demo(scorer: Scorer | None = None) -> tuple[list[Decision], Partition]:
    decisions = insurance_claim_decisions()
    partition = partition_decisions(decisions, scorer=scorer or Scorer(),
                                    namer=insurance_namer)
    return decisions, partition
