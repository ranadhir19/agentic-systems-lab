"""Principal hierarchy and instruction provenance tagging.

Every instruction an agent acts on is tagged with its source principal
and the channel it arrived on. Precedence (highest first):

    user > developer > deployer > third_party

The data channel (documents, tool outputs, web pages) can never
outrank the instruction channel: content arriving as data is evidence,
never authority.
"""
from __future__ import annotations

from dataclasses import dataclass

USER = "user"
DEVELOPER = "developer"
DEPLOYER = "deployer"
THIRD_PARTY = "third_party"

PRECEDENCE = {USER: 4, DEVELOPER: 3, DEPLOYER: 2, THIRD_PARTY: 1}

INSTRUCTION_CHANNEL = "instruction"
DATA_CHANNEL = "data"


@dataclass(frozen=True)
class Instruction:
    """One directive, tagged with who issued it and how it arrived."""

    text: str
    principal: str
    channel: str = INSTRUCTION_CHANNEL
    seq: int = 0

    def __post_init__(self):
        if self.principal not in PRECEDENCE:
            raise ValueError(f"unknown principal: {self.principal}")
        if self.channel not in (INSTRUCTION_CHANNEL, DATA_CHANNEL):
            raise ValueError(f"unknown channel: {self.channel}")


def is_authoritative(instr: Instruction) -> bool:
    """Only instruction-channel content can authorize action.

    Data-channel content (documents, tool output, page text) is evidence
    for reasoning, never a source of instructions. This is the core
    confused-deputy defense: a hidden imperative in a PDF cannot become
    an instruction, no matter how it is phrased.
    """
    return instr.channel == INSTRUCTION_CHANNEL


def resolve_conflict(instructions: list[Instruction]) -> Instruction:
    """Pick the winning instruction by principal precedence.

    Higher principal wins; ties break to the earliest sequence number.
    Raises ValueError on an empty list.
    """
    if not instructions:
        raise ValueError("no instructions to resolve")
    return max(instructions,
               key=lambda i: (PRECEDENCE[i.principal], -i.seq))


@dataclass(frozen=True)
class Directive:
    """A parsed action demand: what to do, with what parameters."""

    key: str
    params: dict
    source: Instruction


def _params_conflict(a: dict, b: dict) -> bool:
    """Two param dicts conflict if any shared key disagrees."""
    return any(k in b and b[k] != v for k, v in a.items())


def detect_conflict(directives: list[Directive]) -> list[tuple[Directive, Directive]]:
    """Find pairs of directives on the same action key that disagree."""
    out = []
    for i in range(len(directives)):
        for j in range(i + 1, len(directives)):
            a, b = directives[i], directives[j]
            if a.key == b.key and _params_conflict(a.params, b.params):
                out.append((a, b))
    return out
