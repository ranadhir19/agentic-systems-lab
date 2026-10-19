"""Collective Memory Fabric.

A governed collective-memory protocol for multi-agent systems: agents commit
versioned claims with supporting evidence, and the fabric reconciles them
through evidence-weighted quorum rather than naive averaging. Claims expire
after a bounded TTL and can be revoked by their author, so stale or injected
beliefs are contained instead of spreading across the fleet.

Public API:
    MemoryFabric: the fabric itself (commit/retract/query, quorum reads)
    Claim: an immutable versioned claim record
    FabricError: base exception for fabric operations
    IndependentMemory, NaiveSharedMemory, ProvenanceMemory: ablation baselines
    Agent, World, Observation: multi-agent simulation primitives
    build_agents, run: simulation entry points
"""

from .memory import MemoryFabric, Claim, FabricError
from .baselines import IndependentMemory, NaiveSharedMemory, ProvenanceMemory
from .simulation import Agent, World, Observation, build_agents, run

__all__ = [
    "MemoryFabric",
    "Claim",
    "FabricError",
    "IndependentMemory",
    "NaiveSharedMemory",
    "ProvenanceMemory",
    "Agent",
    "World",
    "Observation",
    "build_agents",
    "run",
]
