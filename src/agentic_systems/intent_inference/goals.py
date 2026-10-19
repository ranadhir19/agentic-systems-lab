"""Goal extraction: SemanticFrame (+ memory) -> structured Goals.

This replaces the intent classifier.  Instead of one label, the pipeline
produces a list of Goal objects:

    primary / secondary goals, constraints, missing information,
    confidence, and candidate tools.

Multi-intent utterances decompose per clause; context-dependent turns
inherit goals from conversation memory; implicit utterances ("I'm hungry")
surface latent goals.  Nothing here can output "unknown" — an unfamiliar
utterance still yields a best-effort goal (graceful degradation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import FINANCIAL_PREDICATES, HUNGER_PREDICATES, TOOLS
from .classifier import tokenize
from .embeddings import SemanticSpace
from .memory import ConversationMemory
from .understanding import SemanticFrame

GOAL_DESCRIPTIONS = {
    "check_balance": "Determine available funds",
    "transfer_money": "Move money between accounts",
    "reset_password": "Restore account access via password reset",
    "update_phone": "Update phone number on the account",
    "auth_assistance": "Resolve authentication blockage",
    "book_flight": "Reserve a flight",
    "cancel_booking": "Cancel an existing booking",
    "track_order": "Report order/shipment status",
    "laptop_support": "Provide laptop troubleshooting",
    "diagnose_display": "Diagnose laptop display failure",
    "diagnose_thermal": "Diagnose laptop overheating",
    "wifi_help": "Resolve Wi-Fi connectivity",
    "book_hotel": "Reserve a hotel",
    "refine_search": "Modify an existing search with new constraints",
    "interview_prep": "Help prepare for interview",
    "attire_advice": "Advise on clothing for an occasion",
    "food_need": "Address hunger: food, recipe, or restaurant",
    "restaurant_suggestion": "Recommend a restaurant",
    "creative_writing": "Produce creative text",
}

# goal -> [(question, evidence_terms)]; a question is asked only when none of
# its evidence terms appear in the utterance (the info is genuinely missing).
MISSING_INFO_RULES = {
    "diagnose_display": [
        ("Is an external monitor connected, and does it show anything?",
         {"monitor", "external", "hdmi"}),
        ("Have you tried booting into safe mode?",
         {"safe", "mode"}),
    ],
    "diagnose_thermal": [
        ("Is the fan running loudly or blocked?",
         {"fan", "loud", "noise"}),
        ("Does it overheat on a hard flat surface too?",
         {"desk", "table", "flat"}),
    ],
    "transfer_money": [
        ("How much should be transferred, and to which account?",
         {"$", "dollar", "dollars", "bucks", "hundred", "thousand",
          "savings", "checking", "account"}),
    ],
    "book_hotel": [
        ("Which dates and how many guests?",
         {"night", "nights", "guest", "guests", "january", "february",
          "march", "weekend"}),
    ],
    "book_flight": [
        ("Which date and destination airport?",
         {"monday", "tuesday", "friday", "tomorrow", "next", "morning"}),
    ],
    "refine_search": [],
    "attire_advice": [
        ("What is the dress code, if you know it?",
         {"formal", "casual", "business", "suit", "dress code"}),
    ],
}


@dataclass
class Goal:
    id: str
    kind: str = "primary"          # primary | secondary
    description: str = ""
    entities: dict = field(default_factory=dict)
    constraints: list = field(default_factory=list)
    missing_info: list = field(default_factory=list)
    confidence: float = 0.0
    tools: list = field(default_factory=list)
    from_context: bool = False

    def __post_init__(self) -> None:
        if not self.description:
            self.description = GOAL_DESCRIPTIONS.get(self.id, self.id)
        if not self.tools:
            self.tools = [t for t, gs in TOOLS.items() if self.id in gs]


def _confidence_from(sim_sum: float, n_clauses: int = 1) -> float:
    # keep the score discriminative: do not saturate on weak evidence
    return round(min(0.95, 0.25 + sim_sum * 0.9), 3)


def _margin_filter(cands: list[tuple[str, float]],
                   ratio: float = 0.45, limit: int = 3) -> list[tuple[str, float]]:
    """Keep candidates within a relative margin of the best score."""
    if not cands:
        return []
    best = cands[0][1]
    return [c for c in cands if c[1] >= ratio * best][:limit]


def _disambiguate(cands: list[tuple[str, float]],
                  text: str) -> list[tuple[str, float]]:
    """Predicate-level disambiguation: a financial main predicate suppresses
    food readings of a secondary noun ("afford lunch" is about money), and
    a hunger predicate suppresses money readings.  Discriminative context
    also resolves prototype collisions: an explicit transfer verb beats a
    balance reading; an explicit wifi mention beats the account-password
    reading of "forgot my password"."""
    toks = set(tokenize(text))
    has_fin = bool(toks & FINANCIAL_PREDICATES)
    has_hunger = bool(toks & HUNGER_PREDICATES)
    ids = {c[0] for c in cands}
    if has_fin and not has_hunger:
        cands = [c for c in cands
                 if c[0] not in ("food_need", "restaurant_suggestion")]
    if has_hunger and not has_fin:
        cands = [c for c in cands if c[0] not in ("check_balance",)]
    if "transfer_money" in ids and toks & {"transfer", "send", "wire", "move"}:
        cands = [c for c in cands if c[0] != "check_balance"]
    if "wifi_help" in ids and toks & {"wifi", "wireless", "internet", "network"}:
        cands = [c for c in cands if c[0] != "reset_password"]
    return cands


class GoalExtractor:
    def __init__(self, space: SemanticSpace | None = None) -> None:
        self.space = space or SemanticSpace()

    # -- public ---------------------------------------------------------
    def extract(self, frame: SemanticFrame,
                memory: ConversationMemory) -> list[Goal]:
        goals: list[Goal] = []
        seen: set[str] = set()
        multi = len(frame.clauses) > 1
        toks = tokenize(frame.text)

        # 0. elliptical turns ("make it cheaper") draw meaning from context,
        #    not from content words — inherit, don't prototype-match.
        if (not multi and memory.references_prior(frame.text)
                and len(toks) <= 5 and memory.active_goals):
            inherited = self._inherit(frame, memory, seen)
            if inherited:
                inherited.sort(key=lambda g: -g.confidence)
                return inherited
            # else fall through to normal extraction

        # 1. per-clause goals -> multi-intent decomposition
        if multi:
            for clause in frame.clauses:
                cands = _margin_filter(
                    _disambiguate(self.space.top_goals(clause, k=3), clause))
                for gid, score in cands:
                    if gid not in seen and score >= 0.12:
                        seen.add(gid)
                        goals.append(self._make(gid, score, frame,
                                                kind="primary"))
        else:
            # 2. whole-utterance goals (single-intent + latent)
            cands = _margin_filter(
                _disambiguate(self.space.top_goals(frame.text, k=4),
                              frame.text))
            for gid, score in cands:
                if gid not in seen and score >= 0.10:
                    seen.add(gid)
                    goals.append(self._make(gid, score, frame, kind="primary"))

        # 3. context inheritance for elliptical / anaphoric turns
        if memory.references_prior(frame.text) and memory.active_goals:
            inherited = self._inherit(frame, memory, seen)
            goals.extend(inherited)

        # 4. graceful fallback: never "unknown"
        if not goals:
            goals.append(self._make_fallback(frame))

        # rank: primary first, then confidence
        goals.sort(key=lambda g: (g.kind != "primary", -g.confidence))
        # mark secondary beyond the first two
        for g in goals[2:]:
            g.kind = "secondary"
        return goals

    # -- internals ------------------------------------------------------
    def _make(self, gid: str, score: float, frame: SemanticFrame,
              kind: str = "primary") -> Goal:
        g = Goal(id=gid, kind=kind,
                 confidence=_confidence_from(score),
                 entities=dict(frame.entities))
        # constraints from frame topics/states
        if "condition:after_login" in frame.states and gid == "diagnose_display":
            g.constraints.append("issue occurs only after login; OS-level, not hardware POST")
        if "device:laptop" in frame.entities:
            g.constraints.append("device=laptop")
        # missing info: ask only what is truly absent (evidence check)
        toks = set(tokenize(frame.text))
        for question, evidence in MISSING_INFO_RULES.get(gid, []):
            if not (toks & evidence):
                g.missing_info.append(question)
        return g

    def _inherit(self, frame: SemanticFrame, memory: ConversationMemory,
                 seen: set[str]) -> list[Goal]:
        out: list[Goal] = []
        toks = set(frame.text.lower().split())
        for prev in memory.active_goals:
            if prev.id in seen:
                continue
            # "make it cheaper" -> refine the in-flight booking goal
            if prev.id in ("book_hotel", "book_flight") and (
                    "cheaper" in toks or "cheap" in toks):
                g = Goal(id="refine_search", kind="primary",
                         description="Modify the hotel/flight search to lower price",
                         constraints=[f"previous_goal={prev.id}",
                                      "add budget constraint: minimize price"],
                         confidence=0.88, from_context=True)
                g.tools = [t for t, gs in TOOLS.items()
                           if prev.id in gs]
                seen.add("refine_search")
                out.append(g)
            # "what should I wear?" after interview context
            elif prev.id == "interview_prep" and any(
                    w in toks for w in ("wear", "dress", "clothing", "attire")):
                g = self._make("attire_advice", 0.45, frame)
                g.constraints.append("occasion=interview (from conversation memory)")
                g.from_context = True
                seen.add("attire_advice")
                out.append(g)
            # "actually cancel it" after tracking an order
            elif prev.id == "track_order" and "cancel" in toks:
                g = self._make("cancel_booking", 0.5, frame)
                g.constraints.append("target=the tracked order (from memory)")
                g.from_context = True
                seen.add("cancel_booking")
                out.append(g)
        return out

    def _make_fallback(self, frame: SemanticFrame) -> Goal:
        # Graceful degradation: describe what was understood, ask for direction.
        desc = "Handle open-ended request"
        if frame.topics:
            desc += f" about {', '.join(frame.topics[:2])}"
        return Goal(id="general_assist", kind="primary", description=desc,
                    confidence=0.30,
                    missing_info=["Could you say a little more about what you'd like me to do?"])
