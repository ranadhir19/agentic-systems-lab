"""L6 (intent/meaning semantics) and L7 (abstract cognitive semantics).

L6 turns raw text into intent frames: {intent, emotion, risk, priority,
missing_info} with confidence scores. L7 abstracts across incidents into
organizational motifs: recurring structural patterns with support —
the "organizational memory" layer.
"""
from __future__ import annotations

import numpy as np

from .common import kmeans

INTENT_KEYWORDS = {
    "escalation": ["escalat", "manager", "three times", "fourth time",
                   "nobody resolved"],
    "inquiry": ["status", "explain", "where can", "what is"],
    "complaint": ["unacceptable", "terrible", "charged twice", "down again",
                  "cancelling"],
    "request": ["please reset", "would like", "add a new", "upgrade"],
}

EMOTION_LEXICON = {
    "frustration": ["frustrat", "unacceptable", "terrible", "three times",
                    "fourth time", "nobody"],
    "urgency": ["urgent", "immediately", "asap", "now"],
    "churn_risk": ["cancelling", "considering", "terrible"],
}

PRIORITY_RULES = [
    ({"escalation"}, 3),
    ({"complaint"}, 2),
    ({"request"}, 1),
    ({"inquiry"}, 0),
]


def _hits(text, keywords):
    t = text.lower()
    return sum(1 for k in keywords if k in t)


def extract_l6(tickets):
    """Intent frame per ticket."""
    frames = []
    for tk in tickets:
        text = tk["text"]
        scores = {intent: _hits(text, kws)
                  for intent, kws in INTENT_KEYWORDS.items()}
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        conf = scores[best] / max(total, 1)
        emotions = {e: _hits(text, kws)
                    for e, kws in EMOTION_LEXICON.items()}
        dom_emotion = max(emotions, key=emotions.get)
        priority = 0
        for intents, p in PRIORITY_RULES:
            if best in intents:
                priority = p
        risk = "high" if (emotions["churn_risk"] > 0 or best == "escalation") \
            else ("medium" if emotions["frustration"] > 0 else "low")
        missing = []
        if best == "escalation":
            missing = ["case_id", "previous_ticket_ids"]
        elif best == "request":
            missing = ["account_id"]
        frames.append({
            "ticket_id": tk["ticket_id"],
            "intent": best,
            "confidence": round(float(conf), 3),
            "emotion": dom_emotion if emotions[dom_emotion] > 0 else "neutral",
            "risk": risk,
            "priority": priority,
            "missing_info": missing,
        })
    return {"frames": frames}


def incident_vector(inc):
    """Numeric incident signature for motif mining."""
    return np.array([
        1.0 if inc["cross_team"] else 0.0,
        inc["severity"] / 4.0,
        len(inc["symptom"]) / 20.0,
        1.0 if "boundary" in inc["text"] else 0.0,
    ])


def extract_l7(incidents, k=4, seed=0):
    """Cluster incident signatures -> motifs with support and a
    natural-language summary. The flagship motif: failures concentrate
    at cross-team boundaries."""
    X = np.array([incident_vector(i) for i in incidents])
    labels, centroids = kmeans(X, k, seed=seed)
    motifs = []
    for j in range(k):
        members = [incidents[i] for i in range(len(incidents))
                   if labels[i] == j]
        if not members:
            continue
        cross = sum(1 for m in members if m["cross_team"]) / len(members)
        sev = float(np.mean([m["severity"] for m in members]))
        if cross > 0.6:
            summary = (f"cross-team boundary failures: {len(members)} "
                       f"incidents ({cross:.0%} cross-team), "
                       f"avg severity {sev:.1f}")
            kind = "coordination_boundary"
        elif sev < 2.5:
            summary = (f"contained single-team incidents: {len(members)}, "
                       f"avg severity {sev:.1f}")
            kind = "contained"
        else:
            summary = (f"mixed incident cluster: {len(members)}, "
                       f"avg severity {sev:.1f}")
            kind = "mixed"
        motifs.append({"kind": kind, "support": len(members),
                       "cross_team_rate": round(cross, 3),
                       "avg_severity": round(sev, 2),
                       "summary": summary})
    motifs.sort(key=lambda m: -m["support"])
    return {"motifs": motifs, "k": k}
