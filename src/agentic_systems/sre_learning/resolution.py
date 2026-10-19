"""Resolution Agent: recommends actions from historical outcomes.

For each context (root-cause category, service tier bucket, change type
or "none"), it tracks per-action (successes, trials) and recommends the
action with the best smoothed success rate.

Counterfactual learning: when a recommended action *fails*, the agent
does not just record the failure — it adds a fractional pseudo-success
to the runner-up action proportional to that action's historical rate in
nearby contexts ("when X failed, Y would likely have worked, based on
similar incidents"). This is documented as counterfactual reweighting,
not observed data.

Baseline for comparison: the globally most-frequent action.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from .synth import ACTION_POOL, Incident


def _context(inc: Incident) -> tuple:
    tier = "critical" if inc.service in ("checkout", "payments", "api-gateway",
                                         "ledger") else "standard"
    return (inc.root_cause, tier)


class ResolutionAgent:
    def __init__(self, smooth: float = 2.0):
        self.smooth = smooth
        # context -> action -> [successes, trials]
        self.table: dict[tuple, dict[str, list]] = defaultdict(
            lambda: defaultdict(lambda: [0, 0]))
        self.global_counts: dict[str, list] = defaultdict(lambda: [0, 0])

    # -- training ---------------------------------------------------------
    def observe(self, incident: Incident):
        ctx = _context(incident)
        a = incident.resolution_action
        ok = 1 if incident.resolution_success else 0
        self.table[ctx][a][0] += ok
        self.table[ctx][a][1] += 1
        self.global_counts[a][0] += ok
        self.global_counts[a][1] += 1

    def fit(self, incidents: list[Incident]) -> "ResolutionAgent":
        for inc in incidents:
            if inc.resolution_action:
                self.observe(inc)
        return self

    # -- inference ---------------------------------------------------------
    def _rate(self, s: int, t: int) -> float:
        return (s + self.smooth * 0.5) / (t + self.smooth)

    def recommend(self, incident: Incident,
                  top_k: int = 1) -> list[tuple[str, float, int]]:
        """Returns (action, smoothed success rate, trials)."""
        ctx = _context(incident)
        actions = self.table.get(ctx, {})
        if not actions:
            # back off to global rates
            scored = [(a, self._rate(s, t), t)
                      for a, (s, t) in self.global_counts.items()]
        else:
            scored = [(a, self._rate(s, t), t) for a, (s, t) in actions.items()]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    # -- counterfactual update ----------------------------------------------
    def observe_with_counterfactual(self, incident: Incident,
                                    recommended: str):
        """Record the outcome; on failure, credit the runner-up with a
        fractional pseudo-success weighted by its nearby-context rate."""
        self.observe(incident)
        if not incident.resolution_success and recommended:
            ctx = _context(incident)
            cands = [(a, self._rate(s, t)) for a, (s, t)
                     in self.table[ctx].items() if a != recommended]
            if cands:
                runner, rate = max(cands, key=lambda x: x[1])
                pseudo = 0.5 * rate  # fractional, documented as counterfactual
                self.table[ctx][runner][0] += pseudo

    # -- baseline ------------------------------------------------------------
    def most_frequent_action(self) -> str:
        return max(self.global_counts.items(),
                   key=lambda kv: kv[1][1])[0]

    # -- evaluation ----------------------------------------------------------
    def success_rate(self, incidents: list[Incident],
                     baseline: bool = False) -> float:
        """Simulate: recommend per incident, then sample the outcome from
        the *ground-truth* success probability of the recommended action
        for that incident's root cause (from synth.CAUSES)."""
        from .synth import CAUSES
        rng = np.random.default_rng(99)
        wins = 0
        for inc in incidents:
            if baseline:
                action = self.most_frequent_action()
            else:
                recs = self.recommend(inc, top_k=1)
                action = recs[0][0] if recs else self.most_frequent_action()
            p = dict(CAUSES[inc.root_cause]["actions"]).get(action, 0.3)
            wins += rng.random() < p
        return wins / len(incidents) if incidents else 0.0
