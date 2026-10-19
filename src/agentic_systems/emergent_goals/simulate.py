"""Seeded episode runner across the four ablation conditions."""
from __future__ import annotations

from .agent import Agent
from .env import ResourceFlowEnv
from .metrics import episode_metrics


CONDITIONS = {
    "full":          dict(comm=True,  intrinsic=True,  goalgen=True),
    "no-comm":       dict(comm=False, intrinsic=True,  goalgen=True),
    "extrinsic-only": dict(comm=True, intrinsic=False, goalgen=False),
    "no-goalgen":    dict(comm=True,  intrinsic=True,  goalgen=False),
}


def run_episode(seed, condition="full", n_agents=10, steps=1500):
    flags = CONDITIONS[condition]
    env = ResourceFlowEnv(seed=seed)
    rng = env.rng
    for i in range(n_agents):
        env.add_agent(Agent(i, env, rng, **flags))
    for _ in range(steps):
        if not env.alive_agents():
            break
        env.step()
    m = episode_metrics(env)
    m["condition"] = condition
    m["seed"] = seed
    return m


def run_condition(condition, seeds, n_agents=10, steps=1500):
    return [run_episode(s, condition, n_agents, steps) for s in seeds]
