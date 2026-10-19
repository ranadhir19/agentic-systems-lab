"""Intent checking: does a delegated action match the delegating
principal's stated intent?

The hardest governance question is intent-based authorization: it is
not enough that an action is *permitted* by scope — it must be what
the principal actually asked for. The checker compares a proposed
action against the stated intent's action type and constraints
(price caps, vendor allow-lists, deadlines, forbidden targets).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intent:
    """A delegating principal's stated intent."""

    action_type: str
    constraints: dict = field(default_factory=dict)
    # Recognized constraint keys: max_price, vendors (allow-list),
    # deadline (int step), forbidden (set of targets), require (keys
    # that must appear in the action params).


@dataclass(frozen=True)
class Action:
    action_type: str
    params: dict = field(default_factory=dict)


def check_intent(intent: Intent, action: Action) -> tuple[bool, list[str]]:
    """Check an action against an intent.

    Returns (ok, reasons). An action matches when the action type is
    right and every constraint holds. Any violated constraint is
    reported — the audit trail shows *why* an action was refused.
    """
    reasons = []
    if action.action_type != intent.action_type:
        return False, [f"wrong action type: {action.action_type} "
                       f"(intent: {intent.action_type})"]
    c = intent.constraints
    p = action.params
    if "max_price" in c and p.get("price", float("inf")) > c["max_price"]:
        reasons.append(f"price {p.get('price')} exceeds max {c['max_price']}")
    if "vendors" in c and p.get("vendor") not in c["vendors"]:
        reasons.append(f"vendor {p.get('vendor')!r} not in allow-list")
    if "deadline" in c and p.get("eta", float("inf")) > c["deadline"]:
        reasons.append(f"eta {p.get('eta')} past deadline {c['deadline']}")
    if "forbidden" in c and p.get("target") in c["forbidden"]:
        reasons.append(f"target {p.get('target')!r} is forbidden")
    for key in c.get("require", []):
        if key not in p:
            reasons.append(f"missing required param {key!r}")
    return (len(reasons) == 0, reasons)


def make_intent_scenarios(rng, n: int) -> list[tuple[Intent, Action, bool]]:
    """Seeded (intent, action, ground-truth match) triples.

    Includes adversarial near-misses: actions that satisfy most
    constraints but violate exactly one, and actions with the wrong
    type but otherwise plausible params.
    """
    vendors = ["acme", "globex", "initech"]
    out = []
    for _ in range(n):
        intent = Intent(
            action_type="buy",
            constraints={
                "max_price": 1200.0,
                "vendors": vendors,
                "deadline": 5,
                "forbidden": {"weapons", "pii_broker"},
                "require": ["price", "vendor"],
            },
        )
        kind = rng.integers(0, 6)
        if kind == 0:  # clean match
            action = Action("buy", {"price": 900.0, "vendor": "acme",
                                    "eta": 3, "target": "laptop"})
            label = True
        elif kind == 1:  # over price cap
            action = Action("buy", {"price": 1500.0, "vendor": "acme",
                                    "eta": 3, "target": "laptop"})
            label = False
        elif kind == 2:  # wrong vendor
            action = Action("buy", {"price": 900.0, "vendor": "shady",
                                    "eta": 3, "target": "laptop"})
            label = False
        elif kind == 3:  # forbidden target
            action = Action("buy", {"price": 900.0, "vendor": "acme",
                                    "eta": 3, "target": "pii_broker"})
            label = False
        elif kind == 4:  # wrong action type entirely
            action = Action("refund", {"price": 900.0, "vendor": "acme"})
            label = False
        else:  # near-miss: price one dollar over the cap
            action = Action("buy", {"price": 1201.0, "vendor": "globex",
                                    "eta": 5, "target": "monitor"})
            label = False
        out.append((intent, action, label))
    return out
