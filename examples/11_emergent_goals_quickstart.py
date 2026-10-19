"""Emergent goals quickstart: do agents invent their own goals?

Runs one small full-condition episode (6 agents, 600 steps) and prints
the story: how many goals the agents imagined for themselves, how many
they adopted, what their tokens came to mean, and whether they stuck
together. Then contrasts with the extrinsic-only control.

Run:  PYTHONPATH=src python3 examples/11_emergent_goals_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.emergent_goals import run_episode

CTX = ["resource", "danger", "home", "other"]


def main() -> None:
    m = run_episode(seed=7, condition="full", n_agents=6, steps=600)
    print(f"condition=full  agents=6  steps=600")
    print(f"self-generated goals : {m['n_imagined']} "
          f"(adoption rate {m['adoption_rate']:.2f})")
    print(f"goal diversity        : {m['diversity_cells']} distinct cells")
    print(f"communication rate    : {m['comm_rate']:.2f} tokens/100 steps")
    print(f"social goal fraction  : {m['social_goal_frac']:.2f} "
          f"(goals aimed at heard locations)")
    print(f"mean lifetime         : {m['lifetime']:.0f} steps; "
          f"deposits: {m['deposits']}")
    print(f"token specialization  : {m['token_entropy']:.2f} nats "
          f"(uniform would be {1.386:.2f})")

    c = run_episode(seed=7, condition="extrinsic-only", n_agents=6,
                    steps=600)
    print(f"\ncontrol=extrinsic-only: goals={c['n_imagined']} "
          f"lifetime={c['lifetime']:.0f} deposits={c['deposits']}")

    assert m["n_imagined"] > 0, "full agents should imagine goals"
    assert c["n_imagined"] == 0, "control cannot imagine goals"
    assert m["social_goal_frac"] > 0.5, "most goals should be social"
    print("\nAgents with intrinsic drives + communication invented and "
          "pursued their own goals; the control did not.")


if __name__ == "__main__":
    main()
