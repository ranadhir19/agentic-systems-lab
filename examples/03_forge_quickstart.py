"""Forge quickstart: LLM inference scheduling under high load.

Simulates 300 requests at 4 req/s under two serving policies and prints
the latency/throughput tradeoff:
  static-fcfs   — batch up, run to completion, repeat
  continuous    — iteration-level scheduling with a KV-cache cap

Expected (deterministic, seed 42): continuous batching cuts mean
end-to-end latency by roughly 9x at this load.

Run:  python3 examples/03_forge_quickstart.py
"""
from __future__ import annotations

import copy

from agentic_systems.forge import Engine, generate_requests


def main() -> None:
    reqs = generate_requests(300, 0.004, seed=42)  # 4 req/s, high load
    for policy in ("static-fcfs", "continuous"):
        stats = Engine(policy).run(copy.deepcopy(reqs))
        r = stats.report()
        print(f"{policy:12s} mean_e2e={r['mean_e2e_ms']:8.0f} ms  "
              f"p99={r['p99_e2e_ms']:8.0f} ms  "
              f"throughput={r['throughput_rps']:.2f} rps  "
              f"kv_util={r['mean_kv_util']:.0%}")


if __name__ == "__main__":
    main()
