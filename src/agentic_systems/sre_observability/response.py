"""Incident response loop with cross-layer context engineering.

Context engineering: alerts from all observers are clustered in time into
unified incident contexts (one incident = one context spanning every
affected layer), enriched with the suspected origin layer.

Response: detection -> triage (runbook selection from the context) ->
remediation -> verification. Two modes are compared on identical alert
streams:

* siloed: each layer-observer triages only its own alerts, so cascades
  fragment into partial contexts and the wrong runbook is often chosen;
* unified (MAS): all alerts share one context, the cascade is recognized,
  the cascade runbook is chosen, and triage is faster.

MTTR is measured end to end in simulated minutes.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

RUNBOOKS = {
    "restart_scale": 25,
    "reroute": 30,
    "rollback_pods": 35,
    "rollback_deploy": 40,
    "db_failover": 45,
    "revert_experiment": 30,
    "cascade_response": 60,
    "default": 35,
}

LAYER_RUNBOOK = {
    "infra": "restart_scale",
    "network": "reroute",
    "platform": "rollback_pods",
    "app": "rollback_deploy",
    "service": "db_failover",
    "product": "revert_experiment",
}

VERIFY_MIN = 10
TRIAGE_SILOED = 15
TRIAGE_UNIFIED = 5
ESCALATION_MIN = 20


@dataclass
class IncidentContext:
    cid: int
    alerts: list = field(default_factory=list)
    owner: str = "unified"  # "unified" or an observer layer (siloed)

    @property
    def t_start(self) -> int:
        return min(a.t for a in self.alerts)

    @property
    def t_end(self) -> int:
        return max(a.t for a in self.alerts)

    @property
    def layers(self) -> set:
        return {a.layer for a in self.alerts}

    @property
    def origin(self) -> str:
        first = min(self.alerts, key=lambda a: a.t)
        return first.layer


def build_contexts(alerts: list, gap: int = 45, owner: str = "unified",
                   start_cid: int = 0) -> list:
    """Cluster alerts into incident contexts by temporal proximity."""
    contexts = []
    cur = None
    for a in sorted(alerts, key=lambda x: x.t):
        if cur is None or a.t - cur.alerts[-1].t > gap:
            cur = IncidentContext(cid=start_cid + len(contexts), owner=owner)
            contexts.append(cur)
        cur.alerts.append(a)
    return contexts


def triage(context: IncidentContext) -> str:
    """Choose a runbook from the unified context.

    Three or more affected layers means a cascade; otherwise the runbook
    of the dominant layer.
    """
    if len(context.layers) >= 3:
        return "cascade_response"
    dom = Counter(a.layer for a in context.alerts).most_common(1)[0][0]
    return LAYER_RUNBOOK.get(dom, "default")


def _remediate(runbook: str, correct: str,
               rng: np.random.Generator) -> float:
    base = RUNBOOKS[runbook]
    if runbook == correct:
        return max(5.0, float(rng.normal(base, base * 0.2)))
    # Wrong runbook: wasted attempt, escalation, then the right one.
    return (base + ESCALATION_MIN
            + max(5.0, float(rng.normal(RUNBOOKS[correct],
                                       RUNBOOKS[correct] * 0.2))))


def _correct_runbook(incident) -> str:
    if incident.kind == "cascade":
        return "cascade_response"
    layer = incident.segments[0].layer
    return LAYER_RUNBOOK.get(layer, "default")


class SiloedResponder:
    """Each observer triages only its own alert stream."""

    def respond(self, sim, alerts_by_layer: dict,
                rng: np.random.Generator) -> list:
        reports = []
        for inc in sim.incidents:
            if inc.kind != "cascade":
                continue
            origin = inc.segments[0].layer
            own = [a for a in alerts_by_layer[origin]
                   if inc.onset - 30 <= a.t <= inc.end + 90]
            if not own:
                det, ctx = 120.0, None
            else:
                ctxs = build_contexts(own, owner=origin)
                ctx = max(ctxs, key=lambda c: len(c.alerts))
                det = float(ctx.t_start - inc.onset)
            rb = triage(ctx) if ctx is not None else "default"
            correct = _correct_runbook(inc)
            rem = _remediate(rb, correct, rng)
            reports.append({
                "incident": inc.id, "mode": "siloed",
                "detection_min": max(det, 0.0),
                "runbook": rb, "correct": rb == correct,
                "mttr_min": max(det, 0.0) + TRIAGE_SILOED + rem + VERIFY_MIN,
            })
        return reports


class UnifiedResponder:
    """MAS mode: every alert shares one cross-layer context."""

    def respond(self, sim, alerts_by_layer: dict,
                rng: np.random.Generator) -> list:
        alerts = [a for lst in alerts_by_layer.values() for a in lst]
        contexts = build_contexts(alerts, owner="unified")
        reports = []
        for inc in sim.incidents:
            if inc.kind != "cascade":
                continue
            cands = [c for c in contexts
                     if c.t_start <= inc.end + 90 and c.t_end >= inc.onset - 30
                     and (c.layers & set(inc.layers))]
            if not cands:
                det, ctx = 120.0, None
            else:
                ctx = max(cands, key=lambda c: len(c.layers & set(inc.layers)))
                det = float(ctx.t_start - inc.onset)
            rb = triage(ctx) if ctx is not None else "default"
            correct = _correct_runbook(inc)
            rem = _remediate(rb, correct, rng)
            reports.append({
                "incident": inc.id, "mode": "unified",
                "detection_min": max(det, 0.0),
                "runbook": rb, "correct": rb == correct,
                "mttr_min": max(det, 0.0) + TRIAGE_UNIFIED + rem + VERIFY_MIN,
            })
        return reports
