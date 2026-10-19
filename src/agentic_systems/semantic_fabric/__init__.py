"""Semantic Fabric: store meaning, not data.

A semantic intelligence fabric that extracts eight layers of semantics
from raw reality and persists only the compressed cognition:

    L0 structural   schema, entities, relations
    L1 statistical   distributions, drift, correlations, entropy
    L2 behavioral   archetypes, Markov transition models
    L3 relational   typed edges with strength + confidence
    L4 temporal     trends, cycles, cascades, decay
    L5 causal       discovered DAG, linear SCM, interventions,
                   counterfactuals, root-cause walks
    L6 intent       intent frames from text
    L7 cognitive    organizational motifs across incidents

Public API:
    synth:      gen_transactions, gen_metrics, gen_incidents,
                gen_tickets, gen_sequences
    extract:    extract_l0 .. extract_l4
    causal:     extract_l5, do_intervention, counterfactual, root_cause
    cognitive:  extract_l6, extract_l7
    store:      SemanticStore, content_hash
    freshness:  FreshnessMonitor
    reasoning:  FabricReasoner
    pipeline:   build_fabric
"""

from . import synth
from .extract import (extract_l0, extract_l1, extract_l2, extract_l3,
                      extract_l4)
from .causal import (extract_l5, do_intervention, counterfactual,
                     root_cause)
from .cognitive import extract_l6, extract_l7
from .store import SemanticStore, content_hash
from .freshness import FreshnessMonitor
from .reasoning import FabricReasoner
from .pipeline import build_fabric, CAUSAL_VARS

__all__ = [
    "synth",
    "extract_l0",
    "extract_l1",
    "extract_l2",
    "extract_l3",
    "extract_l4",
    "extract_l5",
    "do_intervention",
    "counterfactual",
    "root_cause",
    "extract_l6",
    "extract_l7",
    "SemanticStore",
    "content_hash",
    "FreshnessMonitor",
    "FabricReasoner",
    "build_fabric",
    "CAUSAL_VARS",
]
