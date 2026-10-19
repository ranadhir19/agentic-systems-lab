"""Smoke tests for Meridian core paths."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.blackboard import Blackboard
from src.orchestrators import MeridianSystem, RunConfig
from src.optimizer import RoutingOptimizer, scalar_reward
from src.tasks import Task, TaskKind, TaskGenerator


def test_scalar_reward_orders_correctly():
    good = scalar_reward(0.9, 0.03, 4.0)
    bad = scalar_reward(0.5, 0.03, 4.0)
    assert good > bad


def test_blackboard_peer_resolution():
    bb = Blackboard()
    bb.propose("research", "artifact-1", 0.8)
    hit = bb.request("analysis", "research", "need")
    assert hit is not None and bb.peer_resolutions == 1
    miss = bb.request("analysis", "nope", "need")
    assert miss is None and bb.escalations == 1


def test_system_runs_all_configs():
    tasks = TaskGenerator(7).generate(8)
    for cfg in [RunConfig("x"),
                RunConfig("x", vertical=True),
                RunConfig("x", vertical=True, horizontal=True),
                RunConfig("x", vertical=True, horizontal=True, optimized=True)]:
        s = MeridianSystem(cfg, seed=7)
        for t in tasks:
            r = s.run(t)
            assert 0.0 <= r.quality <= 1.0 and r.cost >= 0


def test_optimizer_learns():
    from src.agents import build_fleet
    fleet = build_fleet(7)
    opt = RoutingOptimizer(list(fleet), fleet, seed=7)
    task = Task(0, TaskKind.MIXED, 4, "t", "b")
    # feed it: pro worker great, standard worker poor, repeatedly
    for _ in range(30):
        w = opt.select_worker(task, "research", 0.9)
        if w == "r2":
            opt.observe(task, w, 0.85, 0.10, 6.0)
        else:
            opt.observe(task, w, 0.60, 0.03, 4.0)
    # after learning, pro should dominate selections on hard research tasks
    picks = [opt.select_worker(task, "research", 0.9) for _ in range(20)]
    assert picks.count("r2") >= 12, picks
