"""Data-First Agentic SRE: train SRE agents on historical incident truth.

Submodules:
    synth        seeded world generator (changes, incidents, postmortems)
    pipeline     extract -> enrich (change-incident linking) -> datasets
    change_agent logistic change-risk predictor + linear explanations
    causality    causal knowledge graph from postmortem statements
    similarity   learned incident similarity + active learning
    resolution   resolution recommender with counterfactual updates
    workflow     LangGraph-style conditional agent workflow
    learning     continuous-learning loop + learning-velocity metrics
"""
from .synth import World, Change, Incident, CAUSES, CHANGE_TYPES
from .pipeline import DataPipeline, EnrichedIncident
from .change_agent import (ChangeRiskPredictor, auc_score, precision_recall,
                           calibration_bins, FEATURE_NAMES)
from .causality import CausalKnowledgeGraph
from .similarity import SimilarityAgent, TfidfBaseline, make_pairs
from .resolution import ResolutionAgent
from .workflow import SREWorkflow
from .learning import ContinuousLearner

__all__ = [
    "World", "Change", "Incident", "CAUSES", "CHANGE_TYPES",
    "DataPipeline", "EnrichedIncident",
    "ChangeRiskPredictor", "auc_score", "precision_recall",
    "calibration_bins", "FEATURE_NAMES",
    "CausalKnowledgeGraph",
    "SimilarityAgent", "TfidfBaseline", "make_pairs",
    "ResolutionAgent",
    "SREWorkflow",
    "ContinuousLearner",
]
