"""Simulation: heterogeneous agents, changing facts, injected misinformation.

World: 10 facts, each flips value twice at random times (seeded).
Agents: 8 across 3 model families (alpha 0.95 / beta 0.85 / gamma 0.72).
  One beta agent is compromised during ticks [80, 120): it injects a false
  value for the target fact twice per tick at confidence 0.95 with
  triple-counted (but single-source) evidence — a Sybil-style attack the
  distinct-agent quorum is designed to stop.

Protocol per tick: admit observations -> sweep/expiry -> query.
Every agent queries 1 random fact + the target fact; answers are scored
against ground truth at that tick.

The observation schedule is generated once and replayed identically into
each memory system, so differences are architectural, not sampling noise.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

N_FACTS = 10
TICKS = 200
INJECT_START, INJECT_END = 80, 120
N_SEEDS = 5


@dataclass
class Agent:
    id: str
    family: str
    accuracy: float


def build_agents() -> list[Agent]:
    agents = []
    spec = [("alpha", 0.95)] * 3 + [("beta", 0.85)] * 3 + [("gamma", 0.72)] * 2
    for i, (fam, acc) in enumerate(spec):
        agents.append(Agent(f"a{i}", fam, acc))
    return agents


class World:
    def __init__(self, seed: int):
        rng = random.Random(seed)
        self.facts = []
        for i in range(N_FACTS):
            values = [f"v{i}-{k}" for k in range(3)]
            flips = sorted(rng.sample(range(5, TICKS - 5), 2))
            self.facts.append({"values": values, "flips": flips})

    def truth(self, fi: int, t: int) -> str:
        f = self.facts[fi]
        idx = sum(1 for fl in f["flips"] if fl <= t)
        return f["values"][idx % len(f["values"])]

    def wrong_value(self, fi: int, t: int, rng: random.Random) -> str:
        true = self.truth(fi, t)
        opts = [v for v in self.facts[fi]["values"] if v != true]
        return rng.choice(opts)


@dataclass
class Observation:
    tick: int
    agent: Agent
    fact: int
    value: str
    confidence: float
    evidence: list[tuple[str, int]]
    malicious: bool = False


def pick_target_fact(world: World) -> int:
    """A fact with no flips near the injection window: the attack targets a
    stable fact, so the evaluation measures misinformation resistance, not
    flip-convergence luck."""
    for i in range(N_FACTS):
        if not any(INJECT_START - 10 <= f <= INJECT_END + 10
                   for f in world.facts[i]["flips"]):
            return i
    return 0


def build_schedule(seed: int, agents: list[Agent], world: World,
                   compromised_id: str = "a3") -> tuple[list[Observation], int]:
    rng = random.Random(seed + 1)
    target = pick_target_fact(world)
    # The attacker commits to ONE false narrative for the whole window —
    # flapping between lies would be less effective and less realistic.
    fixed_lie = world.wrong_value(target, INJECT_START, rng)
    sched = []
    for t in range(TICKS):
        for ag in agents:
            if ag.id == compromised_id and INJECT_START <= t < INJECT_END:
                for _ in range(2):  # Sybil-style: high frequency, one source
                    sched.append(Observation(
                        t, ag, target, fixed_lie,
                        0.95, [(ag.id, t)] * 3, malicious=True))
                continue
            for _ in range(2):
                fi = rng.randrange(N_FACTS)
                true = world.truth(fi, t)
                if rng.random() < ag.accuracy:
                    val = true
                else:
                    val = world.wrong_value(fi, t, rng)
                conf = max(0.05, min(0.99, ag.accuracy + rng.gauss(0, 0.04)))
                sched.append(Observation(t, ag, fi, val, conf,
                                         [(ag.id, t)]))
    return sched, target


def _subject(fi: int) -> str:
    return f"fact-{fi}"


def run(memory, seed: int = 0, compromised_id: str = "a3") -> dict:
    agents = build_agents()
    world = World(seed)
    sched, target = build_schedule(seed, agents, world, compromised_id)
    by_tick: dict[int, list[Observation]] = {}
    for ob in sched:
        by_tick.setdefault(ob.tick, []).append(ob)

    rng = random.Random(seed + 2)
    success_ts, target_wrong_ts = [], []
    per_family: dict[str, list[int]] = {}
    op_ms = []
    n_queries = 0

    is_fabric = hasattr(memory, "_chains")
    for t in range(TICKS):
        t0 = time.perf_counter()
        # interleave admissions in random order: no system benefits from
        # a lucky fixed write order (this is what hurts last-write-wins)
        tick_obs = list(by_tick.get(t, []))
        rng.shuffle(tick_obs)
        for ob in tick_obs:
            memory.admit(ob.agent.id, ob.agent.family, _subject(ob.fact),
                         "state", ob.value, ob.confidence, ob.evidence, t)
        if hasattr(memory, "sweep"):
            memory.sweep(t)
        correct, total = 0, 0
        target_wrong, target_total = 0, 0
        for ag in agents:
            for fi in (rng.randrange(N_FACTS), target):
                ans = memory.query(ag.id, _subject(fi), "state", t)
                if is_fabric:
                    ans = ans.value if ans is not None else None
                ok = (ans == world.truth(fi, t))
                correct += ok
                total += 1
                n_queries += 1
                per_family.setdefault(ag.family, []).append(int(ok))
                if fi == target:
                    target_wrong += (not ok)
                    target_total += 1
        op_ms.append((time.perf_counter() - t0) * 1000)
        success_ts.append(correct / total)
        target_wrong_ts.append(target_wrong / target_total)

    baseline = sum(success_ts[60:80]) / 20
    # recovery on a 5-tick moving average (robust to per-tick noise)
    smooth = [sum(success_ts[t:t + 5]) / 5 for t in range(TICKS - 5)]
    recovery = None
    for t in range(INJECT_END, TICKS - 5):
        if smooth[t] >= baseline - 0.02:
            recovery = t - INJECT_END
            break
    fam_success = {f: sum(v) / len(v) for f, v in per_family.items()}
    return {
        "success_ts": success_ts,
        "target_wrong_ts": target_wrong_ts,
        "mean_success": sum(success_ts) / len(success_ts),
        "pre_success": sum(success_ts[60:80]) / 20,
        "inj_success": sum(success_ts[INJECT_START:INJECT_END]) / (INJECT_END - INJECT_START),
        "pre_target_wrong": sum(target_wrong_ts[60:80]) / 20,
        "inj_target_wrong": sum(target_wrong_ts[INJECT_START:INJECT_END]) / (INJECT_END - INJECT_START),
        "min_success_injection": min(success_ts[INJECT_START:INJECT_END]),
        "baseline": baseline,
        "recovery_ticks": recovery,
        "per_family": fam_success,
        "mean_op_ms_per_tick": sum(op_ms) / len(op_ms),
        "admissions": getattr(memory, "admissions", 0),
        "contradiction_rate": (memory.contradiction_rate(TICKS - 1)
                               if is_fabric else 0.0),
        "merges": getattr(memory, "merges", 0),
        "reconciliations": getattr(memory, "reconciliations", 0),
        "rejections": getattr(memory, "rejections", 0),
    }
