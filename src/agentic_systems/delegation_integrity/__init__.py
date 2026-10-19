"""Delegation integrity: attribution, authority attenuation, and confused-deputy defense.

When Agent A delegates to B which calls C to modify a production
database, who authorized what? This system models:

- a principal hierarchy (user > developer > deployer > third_party)
  with precedence rules and instruction provenance tagging
  (principals.py);
- scoped, time-bounded authority tokens with per-hop attenuation and
  an ambient-privilege detector (tokens.py);
- the confused deputy: agents whose tool credentials get redirected
  by instructions hidden in data they consume (deputy.py);
- multi-principal conflicts: buyer, merchant, and payment service
  issuing contradictory directives in one workflow (conflicts.py);
- intent checking: does a delegated action match the delegating
  principal's stated intent (intent.py)?
"""
from __future__ import annotations

from . import conflicts, deputy, intent, principals, tokens
from .conflicts import resolve_purchase, run_conflict_trial
from .deputy import run_deputy_trial
from .intent import Intent, check_intent
from .principals import (
    DATA_CHANNEL,
    DEPLOYER,
    DEVELOPER,
    INSTRUCTION_CHANNEL,
    THIRD_PARTY,
    USER,
    Instruction,
    detect_conflict,
    resolve_conflict,
)
from .tokens import AuthorityToken, ambient_exceeds, attribute_action, delegate, verify_chain

__all__ = [
    "USER", "DEVELOPER", "DEPLOYER", "THIRD_PARTY",
    "INSTRUCTION_CHANNEL", "DATA_CHANNEL",
    "Instruction", "detect_conflict", "resolve_conflict",
    "AuthorityToken", "delegate", "verify_chain", "ambient_exceeds",
    "attribute_action", "Intent", "check_intent",
    "run_deputy_trial", "run_conflict_trial", "resolve_purchase",
    "principals", "tokens", "deputy", "conflicts", "intent",
]
