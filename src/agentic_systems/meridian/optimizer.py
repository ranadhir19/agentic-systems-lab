"""Decision optimization for Meridian.

Two cooperating pieces:

1. RoutingOptimizer — contextual Thompson-sampling router. Every dispatch
   picks a worker (arm). The scalarized reward is

       r = w_q*quality - w_c*cost_norm - w_l*lat_norm + bonus(quality>=0.70)

   A separate bandit per (task-kind, difficulty-bin) gives simple, robust
   contextualization. Hard subtasks gate out generalist arms entirely, which
   keeps exploration safe where failure is expensive.

2. DecompositionPlanner — chooses between candidate decompositions
   (medium vs. medium+peer-review) by maximizing the *expected task-level*
   scalarized reward, built from the router's learned per-arm component
   means (quality, cost, latency) plus the system's aggregation model.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
import zlib

from .tasks import SubTask, Task, TaskKind


# ---------------------------------------------------------------------------
# Reward model
# ---------------------------------------------------------------------------
W_Q, W_C, W_L = 1.0, 0.6, 0.25
COST_NORM = 0.15
LAT_NORM = 8.0
SUCCESS_BONUS = 1.0
SUCCESS_BAR = 0.70


def scalar_reward(quality: float, cost: float, latency: float) -> float:
    r = (W_Q * quality - W_C * (cost / COST_NORM) - W_L * (latency / LAT_NORM))
    if quality >= SUCCESS_BAR:
        r += SUCCESS_BONUS
    return r


# ---------------------------------------------------------------------------
# Contextual Thompson-sampling router
# ---------------------------------------------------------------------------
class _Bandit:
    """Per-context bandit tracking reward and component means.

    Arms are warm-started with model-based priors derived from worker
    profiles, so a single unlucky early pull cannot lock an arm out —
    observations then refine the prior per context.
    """

    def __init__(self, arms: list[str], seed: int,
                 priors: dict[str, dict] | None = None):
        self._rng = random.Random(seed)
        self._arms = arms
        self._n: dict[str, float] = {}
        self._r_sum: dict[str, float] = {}
        self._r_sumsq: dict[str, float] = {}
        self._q_sum: dict[str, float] = {}
        self._c_sum: dict[str, float] = {}
        self._l_sum: dict[str, float] = {}
        self._real_n = {a: 0 for a in arms}
        for a in arms:
            pr = (priors or {}).get(a, {})
            w = pr.get("w", 0.0)
            self._n[a] = w
            self._r_sum[a] = pr.get("r", 0.0) * w
            self._r_sumsq[a] = pr.get("r", 0.0) ** 2 * w
            self._q_sum[a] = pr.get("q", 0.0) * w
            self._c_sum[a] = pr.get("c", 0.0) * w
            self._l_sum[a] = pr.get("l", 0.0) * w

    def select(self, arms: list[str]) -> str:
        best, best_s = None, -1e18
        for a in arms:
            n = self._n[a]
            if n == 0:
                return a  # no prior and no data: try once
            mean = self._r_sum[a] / n
            var = max(1e-6, self._r_sumsq[a] / n - mean ** 2)
            # extra exploration mass early, decaying with observations
            sample = self._rng.gauss(mean, math.sqrt(var / n) + 0.05 / (1 + n * 0.2))
            if sample > best_s:
                best, best_s = a, sample
        return best

    def update(self, arm: str, reward: float, quality: float,
               cost: float, latency: float) -> None:
        self._n[arm] += 1
        self._real_n[arm] += 1
        self._r_sum[arm] += reward
        self._r_sumsq[arm] += reward ** 2
        self._q_sum[arm] += quality
        self._c_sum[arm] += cost
        self._l_sum[arm] += latency

    def reward_mean(self, arm: str) -> float:
        n = self._n[arm]
        return self._r_sum[arm] / n if n else 0.0

    def components(self, arm: str):
        n = self._n[arm]
        if not n:
            return None
        return (self._q_sum[arm] / n, self._c_sum[arm] / n,
                self._l_sum[arm] / n)


def _context_of(task: Task) -> tuple[str, int]:
    return (task.kind.value, 0 if task.complexity <= 3 else 1)


class RoutingOptimizer:
    def __init__(self, worker_names: list[str], fleet: dict, seed: int = 21):
        self._arms = worker_names
        self._fleet = fleet
        self._bandits: dict[tuple[str, int], _Bandit] = {}
        self._seed = seed
        self.decisions = 0
        # Model-based priors: expected reward/components at middling
        # difficulty, weight 4 — enough to order arms sensibly on day
        # zero, light enough that observations quickly take over.
        self._priors = {}
        for name, w in fleet.items():
            p = w.profile
            q0 = p.base_quality - 0.10 * 0.6
            c0 = p.cost_per_call * 1.15
            l0 = p.latency_mean
            self._priors[name] = {
                "r": scalar_reward(q0, c0, l0), "q": q0, "c": c0,
                "l": l0, "w": 4.0,
            }

    def _bandit(self, ctx: tuple[str, int]) -> _Bandit:
        if ctx not in self._bandits:
            # zlib.crc32 (not hash()) so bandit seeds are stable across runs:
            # builtin hash() is salted by PYTHONHASHSEED per process.
            self._bandits[ctx] = _Bandit(
                self._arms, self._seed + zlib.crc32(repr(ctx).encode()) % 997,
                self._priors)
        return self._bandits[ctx]

    def _candidates(self, domain: str, difficulty: float) -> list[str]:
        specialists = [n for n, w in self._fleet.items()
                       if w.profile.specialty == domain]
        generals = [n for n, w in self._fleet.items()
                    if w.profile.specialty == "general"]
        return specialists + ([] if difficulty > 0.55 else generals)

    def select_worker(self, task: Task, domain: str,
                      difficulty: float = 0.0) -> str:
        ctx = _context_of(task)
        choice = self._bandit(ctx).select(self._candidates(domain, difficulty))
        self.decisions += 1
        return choice

    def observe(self, task: Task, worker: str, quality: float,
                cost: float, latency: float) -> float:
        r = scalar_reward(quality, cost, latency)
        self._bandit(_context_of(task)).update(worker, r, quality, cost, latency)
        return r

    def expected_components(self, task: Task, worker: str):
        """(E[quality], E[cost], E[latency]) — prior-blended learned means."""
        return self._bandit(_context_of(task)).components(worker)


# ---------------------------------------------------------------------------
# Decomposition planner
# ---------------------------------------------------------------------------
@dataclass
class Decomposition:
    subtasks: list[SubTask]
    granularity: str
    peer_review: bool


class DecompositionPlanner:
    """Pick the decomposition maximizing expected task-level reward.

    E[final quality] mirrors the system's aggregation: mean of subtask
    qualities, minus fan-out loss, minus expected failure drag. Cost and
    latency sum (latency partially parallel). The peer-review option adds a
    small quality lift at a known cost/latency price — the planner only
    takes it when the learned estimates say it pays.
    """

    PEER_REVIEW_Q_LIFT = 0.03
    PEER_REVIEW_COST = 0.01
    PEER_REVIEW_LAT = 0.6

    def __init__(self, optimizer: RoutingOptimizer | None = None):
        self.optimizer = optimizer

    def _domains_for(self, task: Task) -> list[str]:
        if task.kind == TaskKind.RESEARCH:
            return ["research", "research", "synthesis"]
        if task.kind == TaskKind.ANALYSIS:
            return ["analysis", "analysis", "synthesis"]
        if task.kind == TaskKind.SYNTHESIS:
            return ["research", "synthesis", "synthesis"]
        return ["research", "analysis", "synthesis"]

    def propose(self, task: Task) -> list[Decomposition]:
        domains = self._domains_for(task)
        return [self._make(task, domains, "medium", False),
                self._make(task, domains, "medium+review", True)]

    def _make(self, task: Task, domains: list[str],
              granularity: str, peer_review: bool) -> Decomposition:
        subtasks = []
        for i, d in enumerate(domains):
            difficulty = min(1.0, 0.25 + 0.15 * task.complexity)
            subtasks.append(SubTask(task.id, d, round(difficulty, 3),
                                    needs_peer_artifact=(i > 0)))
        return Decomposition(subtasks, granularity, peer_review)

    @staticmethod
    def _p_success(q_mean: float) -> float:
        # linear ramp around the success bar; planning approx only
        return max(0.0, min(1.0, (q_mean - SUCCESS_BAR) / 0.2 + 0.5))

    def score(self, task: Task, decomp: Decomposition, fleet: dict,
              horizontal: bool) -> float:
        qs, cost, lat, p_all_ok = [], 0.0, 0.0, 1.0
        for st in decomp.subtasks:
            cands = ([n for n, w in fleet.items()
                      if w.profile.specialty in (st.domain, "general")])
            # best arm by expected scalarized subtask reward
            best = None
            for n in cands:
                if self.optimizer is not None:
                    q, c, l = self.optimizer.expected_components(task, n)
                else:
                    p = fleet[n].profile
                    q, c, l = p.base_quality - 0.05, p.cost_per_call * 1.15, p.latency_mean
                r = scalar_reward(q, c, l)
                if best is None or r > best[0]:
                    best = (r, q, c, l)
            _, q, c, l = best
            if decomp.peer_review:
                q = min(1.0, q + self.PEER_REVIEW_Q_LIFT)
                c += self.PEER_REVIEW_COST
                l += self.PEER_REVIEW_LAT
            qs.append(q)
            cost += c
            lat += l
            p_all_ok *= self._p_success(q)
        # mirror of MeridianSystem._aggregate
        e_quality = (sum(qs) / len(qs) - 0.02 * max(0, len(qs) - 3)
                     - 0.10 * (1 - p_all_ok))
        e_reward = scalar_reward(e_quality, cost, lat * 0.55)
        if horizontal:
            e_reward += 0.03 * sum(1 for st in decomp.subtasks
                                   if st.needs_peer_artifact)
        return e_reward

    def plan(self, task: Task, fleet: dict, horizontal: bool) -> Decomposition:
        cands = self.propose(task)
        if self.optimizer is None:
            return cands[0]  # hand-designed default: medium, no review
        return max(cands, key=lambda d: self.score(task, d, fleet, horizontal))
