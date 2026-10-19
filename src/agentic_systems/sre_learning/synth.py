"""Synthetic but realistic incident/change/postmortem generators.

Everything is seeded and carries ground-truth labels, so experiments can
measure linking accuracy, prediction quality, and learning velocity
honestly. The world model:

* 8 services in a dependency DAG with criticality tiers.
* Changes with 7 risk features; incident probability is a known logistic
  function of those features (the "historical truth" agents must learn).
* Incidents with root causes from a fixed taxonomy, symptom pools,
  metric-signature templates, and resolution actions with known success
  rates.
* Postmortems as templated text carrying explicit causal statements.

No emojis. numpy only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------------------
# Static world knowledge
# ---------------------------------------------------------------------------

SERVICES = [
    # name, tier (criticality 0..1), dependencies
    ("api-gateway", 0.9, []),
    ("checkout", 1.0, ["api-gateway"]),
    ("payments", 1.0, ["checkout"]),
    ("ledger", 0.9, ["payments"]),
    ("inventory", 0.6, ["checkout"]),
    ("search", 0.5, ["api-gateway"]),
    ("reco", 0.4, ["search"]),
    ("notify", 0.3, ["checkout"]),
]

CHANGE_TYPES = ["code", "config", "infra", "db_migration"]

# Root-cause taxonomy: symptoms, metric signature, likely change types,
# resolution actions with success probabilities.
CAUSES = {
    "deploy_regression": {
        "symptoms": ["error_rate_spike", "latency_p99_up", "5xx_burst"],
        "change_types": ["code"],
        "actions": [("rollback", 0.93), ("forward_fix", 0.71), ("scale_out", 0.22)],
        "mechanism": "a faulty code path raised exceptions on the hot path",
    },
    "config_flag_misroute": {
        "symptoms": ["traffic_misroute", "latency_p99_up", "error_rate_spike"],
        "change_types": ["config"],
        "actions": [("revert_flag", 0.95), ("forward_fix", 0.68), ("rollback", 0.55)],
        "mechanism": "a misconfigured flag routed traffic to the wrong pool",
    },
    "db_pool_exhaustion": {
        "symptoms": ["db_wait_time_up", "timeout_errors", "latency_p99_up"],
        "change_types": ["db_migration", "code"],
        "actions": [("raise_pool_limit", 0.88), ("kill_long_queries", 0.74), ("failover_replica", 0.61)],
        "mechanism": "connection demand exceeded the pool after a query-plan change",
    },
    "cache_stampede": {
        "symptoms": ["db_cpu_spike", "latency_p99_up", "timeout_errors"],
        "change_types": ["config", "code"],
        "actions": [("warm_cache", 0.82), ("enable_request_coalescing", 0.77), ("scale_out", 0.45)],
        "mechanism": "a thundering herd hit the database after cache invalidation",
    },
    "cert_expiry": {
        "symptoms": ["tls_handshake_failures", "downstream_timeouts", "error_rate_spike"],
        "change_types": ["infra"],
        "actions": [("rotate_cert", 0.97), ("failover_replica", 0.52), ("rollback", 0.18)],
        "mechanism": "an expired certificate broke mutual TLS between services",
    },
    "downstream_timeout_cascade": {
        "symptoms": ["downstream_timeouts", "latency_p99_up", "queue_backlog"],
        "change_types": ["code", "infra"],
        "actions": [("raise_timeouts", 0.66), ("shed_load", 0.78), ("failover_replica", 0.58)],
        "mechanism": "slow downstream responses cascaded into queue buildup",
    },
    "disk_full": {
        "symptoms": ["disk_usage_100", "write_errors", "error_rate_spike"],
        "change_types": ["infra"],
        "actions": [("purge_logs", 0.9), ("expand_volume", 0.93), ("failover_replica", 0.4)],
        "mechanism": "unrotated logs filled the volume and writes failed",
    },
    "dns_misconfig": {
        "symptoms": ["dns_nxdomain", "traffic_misroute", "error_rate_spike"],
        "change_types": ["config", "infra"],
        "actions": [("fix_dns_record", 0.94), ("revert_flag", 0.5), ("failover_replica", 0.44)],
        "mechanism": "a bad DNS record sent clients to a decommissioned endpoint",
    },
}

# Known ground-truth weights for the change -> incident logistic model.
# Order: [bias, is_config, is_infra, is_db, criticality, blast_radius,
#         night_deploy, inexperience, complexity, low_coverage]
TRUE_W = np.array([-4.6, 0.9, 0.7, 1.1, 1.4, 1.8, 1.2, 1.0, 0.9, 1.3])

ACTION_POOL = sorted({a for c in CAUSES.values() for a, _ in c["actions"]})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Change:
    id: int
    service: str
    change_type: str
    criticality: float
    blast_radius: float
    hour: int
    author_exp: float
    complexity: float
    test_coverage: float
    t: float  # timestamp (hours since epoch of the synthetic world)
    caused_incident: bool = False
    incident_id: int = -1

    def features(self) -> np.ndarray:
        ct = CHANGE_TYPES.index(self.change_type)
        return np.array([
            1.0 if self.change_type == "config" else 0.0,
            1.0 if self.change_type == "infra" else 0.0,
            1.0 if self.change_type == "db_migration" else 0.0,
            self.criticality,
            self.blast_radius,
            1.0 if (self.hour < 6 or self.hour >= 22) else 0.0,
            1.0 - self.author_exp,
            self.complexity,
            1.0 - self.test_coverage,
        ])


@dataclass
class Incident:
    id: int
    service: str
    t_start: float
    root_cause: str
    symptoms: list
    metric_sig: np.ndarray  # 24-dim signature template + noise
    affected: list
    change_id: int = -1  # -1 => organic (no change caused it)
    resolution_action: str = ""
    resolution_success: bool = False
    resolution_minutes: float = 0.0
    postmortem: str = ""
    severity: int = 3


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _dependents(service: str) -> list:
    deps = {name: ds for name, _, ds in SERVICES}
    out = []
    for name, _, _ in SERVICES:
        # services that (transitively) depend on `service`
        stack, seen = [name], set()
        found = False
        while stack and not found:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for d in deps[cur]:
                if d == service:
                    found = True
                    break
                stack.append(d)
        if found:
            out.append(name)
    return out


def _metric_signature(rng: np.random.Generator, cause: str) -> np.ndarray:
    """24-step signature: ramp-up, plateau, recovery. Cause-specific shape."""
    shapes = {
        "deploy_regression": (0.9, 0.2), "config_flag_misroute": (0.7, 0.5),
        "db_pool_exhaustion": (0.5, 0.8), "cache_stampede": (1.0, 0.1),
        "cert_expiry": (0.95, 0.0), "downstream_timeout_cascade": (0.4, 0.7),
        "disk_full": (0.3, 0.9), "dns_misconfig": (0.85, 0.3),
    }
    spike, ramp = shapes[cause]
    t = np.arange(24)
    sig = spike * (1 - np.exp(-np.maximum(t - 4, 0) / (2 + 8 * ramp)))
    sig = sig * np.exp(-np.maximum(t - 16, 0) / 6.0)
    return sig + rng.normal(0, 0.05, 24)


def _postmortem(rng: np.random.Generator, inc: Incident, change: Change | None) -> str:
    cause = CAUSES[inc.root_cause]
    lines = [
        f"Postmortem for incident {inc.id} on {inc.service} "
        f"(severity {inc.severity}).",
        f"Root cause: {inc.root_cause}. {cause['mechanism']}.",
    ]
    # causal statements the CausalityAgent will parse
    for sym in inc.symptoms[:2]:
        lines.append(f"Causal: {inc.root_cause} caused {sym} on {inc.service}.")
    if change is not None:
        lines.append(
            f"Causal: change {change.id} ({change.change_type} on "
            f"{change.service}) triggered {inc.root_cause}."
        )
    lines.append(
        f"Resolution: {inc.resolution_action} "
        f"({'succeeded' if inc.resolution_success else 'failed'}) in "
        f"{inc.resolution_minutes:.0f} minutes."
    )
    return " ".join(lines)


class World:
    """Seeded generator for the SRE training world.

    Optional concept drift: after ``drift_day`` (in hours), incident
    probabilities follow ``drift_W`` instead of ``TRUE_W`` — modeling
    e.g. new deployment automation that changes the risk profile.
    """

    def __init__(self, seed: int = 7, drift_day: float | None = None,
                 drift_W: np.ndarray | None = None):
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.drift_day = drift_day
        self.drift_W = drift_W
        self.changes: list[Change] = []
        self.incidents: list[Incident] = []
        self._svc = {n: (tier, ds) for n, tier, ds in SERVICES}

    # -- changes ---------------------------------------------------------
    def gen_changes(self, n: int, t0: float = 0.0, span_h: float = 24 * 180) -> list[Change]:
        rng = self.rng
        out = []
        for i in range(n):
            svc = SERVICES[rng.integers(len(SERVICES))][0]
            tier = self._svc[svc][0]
            ct = rng.choice(CHANGE_TYPES, p=[0.45, 0.3, 0.15, 0.1])
            ch = Change(
                id=len(self.changes) + len(out),
                service=svc,
                change_type=ct,
                criticality=tier,
                blast_radius=float(rng.beta(2, 5)),
                hour=int(rng.integers(24)),
                author_exp=float(rng.beta(5, 2)),
                complexity=float(rng.beta(2, 4)),
                test_coverage=float(rng.beta(4, 2)),
                t=t0 + float(rng.uniform(0, span_h)),
            )
            out.append(ch)
        self.changes.extend(out)
        return out

    def _incident_prob(self, ch: Change) -> float:
        W = TRUE_W
        if self.drift_W is not None and self.drift_day is not None \
                and ch.t >= self.drift_day:
            W = self.drift_W
        z = W[0] + W[1:] @ ch.features()
        return float(1 / (1 + np.exp(-z)))

    # -- incidents -------------------------------------------------------
    def gen_incidents(self, changes: list[Change], organic_frac: float = 0.2,
                      postmortem_frac: float = 0.6) -> list[Incident]:
        rng = self.rng
        out = []
        # change-caused incidents: onset clusters soon after the change
        # (exponential, mean 6h, clipped to the 24h linking window)
        for ch in changes:
            p = self._incident_prob(ch)
            if rng.random() < p:
                ch.caused_incident = True
                dt = min(float(rng.exponential(6.0)), 24.0)
                inc = self._make_incident(ch.service, ch.t + max(dt, 0.1),
                                          ch, rng)
                ch.incident_id = inc.id
                out.append(inc)
        # organic incidents (no change link)
        n_org = int(len(out) * organic_frac / max(1 - organic_frac, 1e-9))
        t_lo = min(c.t for c in changes) if changes else 0.0
        t_hi = max(c.t for c in changes) if changes else 0.0
        for _ in range(n_org):
            svc = SERVICES[rng.integers(len(SERVICES))][0]
            t = rng.uniform(t_lo, t_hi) if changes else 0.0
            out.append(self._make_incident(svc, t, None, rng))
        # postmortems for a subset
        for inc in out:
            if rng.random() < postmortem_frac:
                ch = self.changes[inc.change_id] if inc.change_id >= 0 else None
                inc.postmortem = _postmortem(rng, inc, ch)
        out.sort(key=lambda i: i.t_start)
        for i, inc in enumerate(out):
            inc.id = i
        self.incidents.extend(out)
        return out

    def _make_incident(self, service: str, t: float, change: Change | None,
                       rng: np.random.Generator) -> Incident:
        if change is not None:
            cands = [c for c, v in CAUSES.items()
                     if change.change_type in v["change_types"]]
            cause = cands[rng.integers(len(cands))]
        else:
            cause = list(CAUSES)[rng.integers(len(CAUSES))]
        spec = CAUSES[cause]
        n_sym = int(rng.integers(2, 4))
        symptoms = list(rng.choice(spec["symptoms"],
                                   size=min(n_sym, len(spec["symptoms"])),
                                   replace=False))
        affected = sorted(set([service] + _dependents(service)))
        actions = spec["actions"]
        probs = np.array([p for _, p in actions])
        # resolution: pick action ~ historical popularity, sample success
        pop = np.array([0.5, 0.3, 0.2][:len(actions)])
        pop = pop / pop.sum()
        ai = rng.choice(len(actions), p=pop)
        action, p_ok = actions[ai]
        ok = bool(rng.random() < p_ok)
        minutes = float(rng.uniform(15, 240) * (1.6 if not ok else 1.0))
        return Incident(
            id=-1, service=service, t_start=t, root_cause=cause,
            symptoms=symptoms, metric_sig=_metric_signature(rng, cause),
            affected=affected,
            change_id=change.id if change is not None else -1,
            resolution_action=action, resolution_success=ok,
            resolution_minutes=minutes,
            severity=int(rng.choice([1, 2, 3, 4], p=[0.05, 0.2, 0.5, 0.25])),
        )

    # -- convenience ------------------------------------------------------
    def feature_matrix(self, changes: list[Change]) -> np.ndarray:
        return np.stack([c.features() for c in changes])

    def labels(self, changes: list[Change]) -> np.ndarray:
        return np.array([1.0 if c.caused_incident else 0.0 for c in changes])
