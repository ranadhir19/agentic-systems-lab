"""Emergent goals: do communicating agents with intrinsic drives invent
their own goals and continuity behaviors?

See 11-emergent-goals/DESIGN.md for the research design.
"""
from .agent import Agent, Goal
from .env import ResourceFlowEnv
from .metrics import cohens_d, episode_metrics
from .simulate import CONDITIONS, run_condition, run_episode

__all__ = [
    "Agent", "Goal", "ResourceFlowEnv", "episode_metrics", "cohens_d",
    "CONDITIONS", "run_episode", "run_condition",
]
