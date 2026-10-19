"""Synthetic data generators with known ground truth.

Every generator takes an explicit seed and returns (data, ground_truth).
Ground truth is what the extraction layers are scored against in the
experiments: archetype labels, the true causal DAG, injected seasonal
periods, cascade lags, incident motifs, and ticket intent labels.
"""
from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Transactions: 5 customer archetypes, server effects, causal chain
# ---------------------------------------------------------------------------
ARCHETYPES = ["bargain", "regular", "premium", "erratic", "nightowl"]

# per-archetype: lognormal amount (mu, sigma), base error prob, session len
ARCH_PARAMS = {
    "bargain":  {"mu": 2.2, "sigma": 0.5, "err": 0.010, "sess": 3},
    "regular":  {"mu": 3.0, "sigma": 0.6, "err": 0.015, "sess": 5},
    "premium":  {"mu": 4.2, "sigma": 0.5, "err": 0.008, "sess": 7},
    "erratic":  {"mu": 3.4, "sigma": 1.4, "err": 0.060, "sess": 4},
    "nightowl": {"mu": 2.8, "sigma": 0.7, "err": 0.020, "sess": 6},
}

SERVICES = ["payments", "search", "auth"]
N_SERVERS = 20


def gen_transactions(n=10000, seed=0):
    """Generate n synthetic transactions.

    Ground-truth causal chain (linear, per transaction):
        server_load -> queue_depth -> latency -> error_prob
    Two "hot" servers (3, 11) carry extra load and drive payment latency.
    """
    rng = np.random.default_rng(seed)
    n_users = 1000
    user_arch = rng.integers(0, len(ARCHETYPES), n_users)

    user_id = rng.integers(0, n_users, n)
    arch = np.array([ARCHETYPES[user_arch[u]] for u in user_id])
    service = rng.choice(SERVICES, n, p=[0.5, 0.35, 0.15])
    server = rng.integers(0, N_SERVERS, n)

    mu = np.array([ARCH_PARAMS[a]["mu"] for a in arch])
    sigma = np.array([ARCH_PARAMS[a]["sigma"] for a in arch])
    amount = rng.lognormal(mu, sigma)

    # causal chain: hot servers -> load -> queue -> latency
    hot = np.isin(server, [3, 11]).astype(float)
    server_load = rng.normal(0.5, 0.15, n) + 0.9 * hot
    server_load = np.clip(server_load, 0.05, None)
    queue_depth = 2.0 * server_load + rng.normal(0, 0.3, n)
    queue_depth = np.clip(queue_depth, 0, None)
    latency = 40.0 + 55.0 * queue_depth + rng.normal(0, 12, n)
    latency = np.clip(latency, 5, None)

    base_err = np.array([ARCH_PARAMS[a]["err"] for a in arch])
    err_p = np.clip(base_err + 0.0006 * np.maximum(latency - 120, 0), 0, 0.5)
    error = (rng.random(n) < err_p).astype(int)

    # timestamps across 28 days, nightowls transact at night
    day = rng.integers(0, 28, n)
    hour = rng.integers(0, 24, n)
    night = arch == "nightowl"
    hour[night] = rng.integers(0, 6, night.sum())
    ts = day * 24.0 + hour + rng.random(n)

    txns = [
        {
            "txn_id": f"t{i:06d}",
            "user_id": f"u{user_id[i]:04d}",
            "server_id": f"srv{server[i]:02d}",
            "service": service[i],
            "amount": round(float(amount[i]), 2),
            "latency_ms": round(float(latency[i]), 1),
            "server_load": round(float(server_load[i]), 3),
            "queue_depth": round(float(queue_depth[i]), 2),
            "error": int(error[i]),
            "ts_hour": round(float(ts[i]), 2),
        }
        for i in range(n)
    ]
    truth = {
        "archetypes": ARCHETYPES,
        "user_archetype": [ARCHETYPES[user_arch[u]] for u in user_id],
        "causal_edges": [("server_load", "queue_depth"),
                         ("queue_depth", "latency_ms"),
                         ("latency_ms", "error")],
        "hot_servers": ["srv03", "srv11"],
        "causal_coefs": {"server_load->queue_depth": 2.0,
                         "queue_depth->latency_ms": 55.0},
    }
    return txns, truth


# ---------------------------------------------------------------------------
# Server metrics: trend + weekly seasonality + incident cascades
# ---------------------------------------------------------------------------
def gen_metrics(n_hours=24 * 28, seed=1, cascade_at=(300, 500)):
    """Hourly metrics for one service with weekly seasonality.

    Ground truth: period = 168h (weekly); cascades: cpu spike at
    cascade_at[0] propagates to latency with a 3h lag.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n_hours, dtype=float)
    trend = 0.02 * t / n_hours
    weekly = 0.25 * np.sin(2 * np.pi * t / 168.0)
    impulse = np.zeros(n_hours)
    impulse[cascade_at[0]] = 0.9
    impulse[cascade_at[1]] = 0.7
    # cascade origin: cpu spikes at the impulse hours ...
    cpu = 0.55 + trend + weekly + 1.4 * impulse + rng.normal(0, 0.05, n_hours)
    # ... memory follows with 1h lag, latency with 3h lag
    mem = 0.5 + 0.4 * np.convolve(impulse, [0.2, 0.5, 0.3], mode="same")
    mem += rng.normal(0, 0.03, n_hours)
    lat_base = 60 + 300 * np.convolve(impulse, [0.1, 0.2, 0.4, 0.3],
                                      mode="same")
    latency = lat_base + 20 * weekly + rng.normal(0, 8, n_hours)
    series = {
        "cpu": np.clip(cpu, 0.05, 1.5),
        "memory": np.clip(mem, 0.05, 1.5),
        "latency": np.clip(latency, 5, None),
    }
    truth = {"period_hours": 168.0, "cascade_lag_h": 3,
             "cascade_hours": list(cascade_at)}
    return series, truth


# ---------------------------------------------------------------------------
# Incidents: motif ground truth = cross-team boundary failures
# ---------------------------------------------------------------------------
TEAMS = ["payments", "search", "auth", "infra", "data"]


def gen_incidents(n=300, seed=2):
    """Incident reports. Ground-truth motif: 40% are cross-team boundary
    incidents (the dominant organizational failure mode)."""
    rng = np.random.default_rng(seed)
    boundary = rng.random(n) < 0.40
    team_a = rng.choice(TEAMS, n)
    team_b = rng.choice(TEAMS, n)
    # force team_b != team_a on boundary incidents
    for i in np.where(boundary)[0]:
        choices = [t for t in TEAMS if t != team_a[i]]
        team_b[i] = rng.choice(choices)
    symptoms = ["latency spike", "error burst", "timeout cascade",
                "queue buildup", "deploy regression", "config drift"]
    symptom = rng.choice(symptoms, n)
    sev = np.where(boundary, rng.choice([1, 2], n, p=[0.6, 0.4]),
                   rng.choice([2, 3, 4], n, p=[0.3, 0.5, 0.2]))
    incidents = [
        {"incident_id": f"inc{i:04d}",
         "team_a": team_a[i], "team_b": team_b[i],
         "cross_team": bool(boundary[i]),
         "symptom": symptom[i], "severity": int(sev[i]),
         "text": (f"{symptom[i]} involving {team_a[i]} and {team_b[i]}; "
                  f"sev{sev[i]}; handoff delay at team boundary"
                  if boundary[i] else
                  f"{symptom[i]} contained within {team_a[i]}; sev{sev[i]}")}
        for i in range(n)
    ]
    truth = {"motif": "cross-team boundary", "motif_rate": 0.40,
             "cross_team": boundary.tolist()}
    return incidents, truth


# ---------------------------------------------------------------------------
# Support tickets: intent + emotion ground truth
# ---------------------------------------------------------------------------
TICKET_TEMPLATES = {
    "escalation": [
        "I have contacted support three times about my invoice",
        "This is the fourth time I am asking, please escalate",
        "Nobody resolved my case, I want a manager now",
    ],
    "inquiry": [
        "What is the status of my refund request",
        "Can you explain the new pricing plan",
        "Where can I download my monthly statement",
    ],
    "complaint": [
        "Your service is down again, this is unacceptable",
        "I was charged twice and nobody helped me",
        "Terrible experience, considering cancelling",
    ],
    "request": [
        "Please reset my API credentials",
        "I would like to upgrade my subscription tier",
        "Add a new user to our enterprise account",
    ],
}

EMOTION_WORDS = {"frustrat", "urgent", "unacceptable", "terrible",
                 "immediately", "escalat", "manager", "cancel"}


def gen_tickets(n=400, seed=3):
    rng = np.random.default_rng(seed)
    intents = list(TICKET_TEMPLATES.keys())
    labels, texts = [], []
    for _ in range(n):
        intent = intents[rng.integers(len(intents))]
        texts.append(rng.choice(TICKET_TEMPLATES[intent]))
        labels.append(intent)
    tickets = [{"ticket_id": f"k{i:04d}", "text": texts[i]} for i in range(n)]
    return tickets, {"intent": labels}


# ---------------------------------------------------------------------------
# Behavioral action sequences (for L2 Markov models)
# ---------------------------------------------------------------------------
ACTIONS = ["browse", "compare", "cart", "checkout", "support", "exit"]


def gen_sequences(n_users=600, seed=4):
    """Per-user action sequences. Archetype determines the transition
    bias: bargain users loop browse->compare; premium go cart->checkout."""
    rng = np.random.default_rng(seed)
    # transition biases per archetype index
    bias = {
        0: {"browse": [0.5, 0.3, 0.05, 0.0, 0.05, 0.1]},   # bargain
        1: {"browse": [0.3, 0.25, 0.2, 0.05, 0.05, 0.15]},  # regular
        2: {"browse": [0.2, 0.15, 0.35, 0.15, 0.05, 0.1]},  # premium
        3: {"browse": [0.25, 0.2, 0.2, 0.1, 0.15, 0.1]},   # erratic
        4: {"browse": [0.35, 0.2, 0.15, 0.1, 0.05, 0.15]},  # nightowl
    }
    base_next = {
        "compare": [0.3, 0.2, 0.3, 0.1, 0.0, 0.1],
        "cart": [0.1, 0.1, 0.2, 0.45, 0.05, 0.1],
        "checkout": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        "support": [0.3, 0.1, 0.1, 0.0, 0.2, 0.3],
        "exit": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    }
    arch_of = rng.integers(0, 5, n_users)
    seqs, labels = [], []
    for u in range(n_users):
        a = arch_of[u]
        probs = dict(base_next)
        probs["browse"] = bias[a]["browse"]
        cur, seq = "browse", ["browse"]
        for _ in range(rng.integers(4, 12)):
            nxt = ACTIONS[rng.choice(len(ACTIONS), p=probs[cur])]
            seq.append(nxt)
            cur = nxt
            if cur == "exit":
                break
        seqs.append(seq)
        labels.append(ARCHETYPES[a])
    return seqs, {"archetype": labels, "actions": ACTIONS}
