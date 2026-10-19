"""Forge: discrete-event simulator of an LLM inference serving engine.

Model
-----
- Time advances in *iterations*. Each iteration, every running request
  generates one token.
- Iteration cost grows with the batch:  ``t_iter = T0 + K * batch_tokens``.
- The KV cache holds ``MAX_KV_TOKENS`` tokens; a request occupies
  ``prompt_len + generated_so_far``. Requests that don't fit wait.
- Prefill of a prompt of length P costs ``ceil(P / PREFILL_CHUNK)`` iters.

Policies
--------
- ``static-fcfs``: fixed batch size B; a batch runs to completion before the
  next starts (the naive baseline).
- ``continuous``: iteration-level batching — freed slots are refilled every
  iteration from the queue in arrival order (vLLM-style).
- ``continuous-srpt``: continuous + shortest-remaining-tokens-first
  admission, which favors quick requests to cut queueing.

Metrics per request: TTFT (arrival -> first token), end-to-end latency,
plus engine throughput and mean KV utilization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import random

T0 = 10.0          # ms base cost per iteration
K = 0.004          # ms per token in the running batch
MAX_KV_TOKENS = 8192
PREFILL_CHUNK = 512
STATIC_BATCH = 8


@dataclass
class Request:
    id: int
    arrival: float            # ms
    prompt_len: int
    gen_len: int
    generated: int = 0
    prefill_left: int = 0
    first_token_at: float = -1.0
    done_at: float = -1.0

    @property
    def kv_tokens(self) -> int:
        return self.prompt_len + self.generated

    @property
    def remaining(self) -> int:
        return self.prefill_left + (self.gen_len - self.generated)


@dataclass
class Stats:
    ttft: list[float] = field(default_factory=list)
    e2e: list[float] = field(default_factory=list)
    completed: int = 0
    sim_time: float = 0.0
    util_samples: list[float] = field(default_factory=list)

    def report(self) -> dict:
        import statistics
        s = sorted(self.e2e)
        p99 = s[int(0.99 * (len(s) - 1))] if s else 0.0
        return {
            "n": self.completed,
            "mean_ttft_ms": statistics.fmean(self.ttft) if self.ttft else 0.0,
            "mean_e2e_ms": statistics.fmean(self.e2e) if self.e2e else 0.0,
            "p99_e2e_ms": p99,
            "throughput_rps": self.completed / (self.sim_time / 1000)
                              if self.sim_time else 0.0,
            "mean_kv_util": statistics.fmean(self.util_samples)
                            if self.util_samples else 0.0,
        }


def _gen_requests(n: int, lam: float, seed: int) -> list[Request]:
    """Poisson arrivals (lam per ms), uniform-ish sizes."""
    rng = random.Random(seed)
    reqs, t = [], 0.0
    for i in range(n):
        t += rng.expovariate(lam)
        p = rng.randint(64, 512)
        g = rng.randint(32, 256)
        reqs.append(Request(i, t, p, g, prefill_left=(p + PREFILL_CHUNK - 1) // PREFILL_CHUNK))
    return reqs


class Engine:
    def __init__(self, policy: str):
        assert policy in ("static-fcfs", "continuous", "continuous-srpt")
        self.policy = policy

    def run(self, requests: list[Request]) -> Stats:
        stats = Stats()
        queue: list[Request] = []
        running: list[Request] = []
        arrivals = sorted(requests, key=lambda r: r.arrival)
        ai = 0
        t = 0.0
        static_busy_until = 0.0

        def kv_used() -> int:
            return sum(r.kv_tokens for r in running)

        def admit(r: Request):
            r.prefill_left = (r.prompt_len + PREFILL_CHUNK - 1) // PREFILL_CHUNK
            running.append(r)

        while ai < len(arrivals) or queue or running:
            # arrivals
            while ai < len(arrivals) and arrivals[ai].arrival <= t:
                queue.append(arrivals[ai])
                ai += 1

            # admission
            if self.policy == "static-fcfs":
                if not running and t >= static_busy_until and queue:
                    batch = queue[:STATIC_BATCH]
                    del queue[:STATIC_BATCH]
                    for r in batch:
                        admit(r)
            else:
                order = (sorted(queue, key=lambda r: r.remaining)
                         if self.policy == "continuous-srpt" else queue)
                for r in list(order):
                    if kv_used() + r.prompt_len <= MAX_KV_TOKENS:
                        queue.remove(r)
                        admit(r)
                    # else: keep waiting (no preemption in this model)

            if not running:
                # jump to next arrival
                t = arrivals[ai].arrival if ai < len(arrivals) else t + 1
                continue

            # one iteration
            batch_tokens = kv_used()
            t += T0 + K * batch_tokens
            stats.util_samples.append(batch_tokens / MAX_KV_TOKENS)
            done = []
            for r in running:
                if r.prefill_left > 0:
                    r.prefill_left -= 1
                    if r.prefill_left == 0 and r.first_token_at < 0:
                        r.first_token_at = t
                else:
                    r.generated += 1
                    if r.first_token_at < 0:
                        r.first_token_at = t
                    if r.generated >= r.gen_len:
                        r.done_at = t
                        done.append(r)
            for r in done:
                running.remove(r)
                stats.ttft.append(r.first_token_at - r.arrival)
                stats.e2e.append(r.done_at - r.arrival)
                stats.completed += 1
            if self.policy == "static-fcfs" and not running:
                static_busy_until = t

        stats.sim_time = t
        return stats
