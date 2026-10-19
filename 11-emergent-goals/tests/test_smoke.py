"""Smoke tests for emergent_goals."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "src"))

from agentic_systems.emergent_goals import (ResourceFlowEnv, run_episode,
                                            episode_metrics)


def test_env_builds():
    env = ResourceFlowEnv(seed=0)
    assert env._reach.max() <= 1.0 + 1e-9
    assert env._reach.min() >= 0.0
    assert len(env.sources) == 4
    assert len(env.home) == 16


def test_full_imagines_goals():
    m = run_episode(seed=1, condition="full", n_agents=4, steps=300)
    assert m["n_imagined"] > 0
    assert m["adoption_rate"] > 0
    assert m["comm_rate"] > 0


def test_extrinsic_only_cannot_imagine():
    m = run_episode(seed=1, condition="extrinsic-only", n_agents=4,
                    steps=300)
    assert m["n_imagined"] == 0
    assert m["social_goal_frac"] == 0.0


def test_no_comm_silent():
    m = run_episode(seed=1, condition="no-comm", n_agents=4, steps=300)
    assert m["comm_rate"] == 0.0
    assert m["n_imagined"] > 0  # curiosity still drives imagination


def test_metrics_keys():
    env = ResourceFlowEnv(seed=2)
    from agentic_systems.emergent_goals import Agent
    import numpy as np
    rng = np.random.default_rng(0)
    env.add_agent(Agent(0, env, rng))
    for _ in range(20):
        env.step()
    m = episode_metrics(env)
    for k in ("n_imagined", "link_away", "cache_ratio", "lifetime",
              "social_goal_frac", "cum_cells"):
        assert k in m, k
