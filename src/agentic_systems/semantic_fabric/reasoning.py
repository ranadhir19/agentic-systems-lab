"""Reasoning API: query the semantic fabric without touching raw data.

All reasoning consumes versioned artifacts from the SemanticStore:
retrieval (nearest archetype / motif), simulation (Markov rollout,
causal do-interventions), root-cause analysis (upstream DAG walk), and
semantic summarization (the compression readout).
"""
from __future__ import annotations

import numpy as np

from .causal import do_intervention, root_cause


class FabricReasoner:
    """Answer queries from persisted semantics alone."""

    def __init__(self, store):
        self.store = store

    # -- retrieval ------------------------------------------------------
    def nearest_archetype(self, behavior_vec):
        """Which behavioral archetype does this user resemble?"""
        l2 = self.store.get("L2", "behavior")["artifact"]
        C = np.array(l2["centroids"])
        v = np.asarray(behavior_vec, float)
        v = (v - v.mean()) / (v.std() + 1e-9)
        d2 = ((C - v) ** 2).sum(1)
        j = int(d2.argmin())
        return {"archetype": j, "members": l2["members_per_archetype"][j],
                "distance": round(float(np.sqrt(d2[j])), 4)}

    def relevant_motif(self, symptom):
        """Motif most relevant to a symptom keyword."""
        l7 = self.store.get("L7", "incidents")["artifact"]
        scored = []
        for m in l7["motifs"]:
            s = 1.0 if m["kind"] == "coordination_boundary" and \
                symptom in ("latency", "handoff", "timeout") else 0.2
            scored.append((s, m))
        scored.sort(key=lambda kv: -kv[0])
        return scored[0][1]

    # -- simulation -----------------------------------------------------
    def simulate_markov(self, archetype, start_action, steps, seed=0):
        """Roll the archetype's Markov chain forward."""
        l2 = self.store.get("L2", "behavior")["artifact"]
        rng = np.random.default_rng(seed)
        T = np.array(l2["transition_matrices"][archetype])
        actions = l2["actions"]
        cur = start_action
        path = [cur]
        for _ in range(steps):
            row = np.array(T[actions.index(cur)], dtype=float)
            row = np.clip(row, 0.0, None)
            s = row.sum()
            row = row / s if s > 0 else np.ones_like(row) / len(row)
            row[-1] += 1.0 - row.sum()  # exact normalization
            cur = actions[rng.choice(len(actions), p=row)]
            path.append(cur)
        return path

    def what_if(self, target, value):
        """Causal intervention on the stored SCM: do(target=value)."""
        l5 = self.store.get("L5", "transactions")["artifact"]
        baseline = {n: 0.0 for n in l5["names"]}
        return do_intervention(l5, target, value, baseline)

    # -- root cause -----------------------------------------------------
    def diagnose(self, symptom, top_k=3):
        """Upstream causal walk from a symptom variable."""
        l5 = self.store.get("L5", "transactions")["artifact"]
        return root_cause(l5, symptom, top_k=top_k)

    def impacting_servers(self, service="payments", top_k=3):
        """Servers whose L3 impact edges target the service."""
        l3 = self.store.get("L3", "transactions")["artifact"]
        edges = [e for e in l3["edges"] if e["dst"] == service]
        edges.sort(key=lambda e: -e["strength"])
        return edges[:top_k]

    # -- summarization (semantic compression readout) -------------------
    def summarize(self):
        """What the fabric knows, in one screen: archetypes, patterns,
        cycles, causal chains, motifs — not rows."""
        l2 = self.store.get("L2", "behavior")["artifact"]
        l3 = self.store.get("L3", "transactions")["artifact"]
        l4 = self.store.get("L4", "metrics")["artifact"]
        l5 = self.store.get("L5", "transactions")["artifact"]
        l7 = self.store.get("L7", "incidents")["artifact"]
        return {
            "behavioral_archetypes": l2["members_per_archetype"],
            "impact_edges": len(l3["edges"]),
            "temporal_signatures": {
                k: (v["dominant_period_h"], v["trend_per_h"])
                for k, v in l4["series"].items()},
            "cascades": l4["cascades"],
            "causal_edges": l5["edges"],
            "top_motif": l7["motifs"][0]["summary"] if l7["motifs"] else None,
        }
