"""Intent inference vs intent classification.

Two architectures for conversational AI, run side by side:

classifier:  traditional pipeline — TF-IDF + softmax regression over a
             fixed intent catalog, one label per utterance, stateless
             dialogue manager.
pipeline:    ChatGPT-style loop — conversation memory -> semantic
             understanding -> structured goal extraction (primary /
             secondary goals, constraints, missing info, confidence) ->
             planner (ask-vs-act) -> tool selection -> orchestrator
             dispatching specialist stub agents.  No intent-classification
             module exists anywhere in this path.

Public API:
    catalog:    INTENTS, TRAIN_UTTERANCES, PROTOTYPES, TEST_SUITE
    classifier: IntentClassifier, DialogueManager, Classification
    embeddings: SemanticSpace
    memory:     ConversationMemory
    understanding: SemanticUnderstanding, SemanticFrame
    goals:      GoalExtractor, Goal
    planner:    Planner, Plan, PlanStep, ToolSelector
    orchestrator: Orchestrator, StubAgent, AgentResult
    pipeline:   InferencePipeline, TurnResult
    evaluate:   evaluate_classifier, evaluate_pipeline, aggregate
"""

from .catalog import INTENTS, PROTOTYPES, TEST_SUITE, TRAIN_UTTERANCES
from .classifier import Classification, DialogueManager, IntentClassifier
from .embeddings import SemanticSpace
from .evaluate import aggregate, evaluate_classifier, evaluate_pipeline
from .goals import Goal, GoalExtractor
from .memory import ConversationMemory
from .orchestrator import AgentResult, Orchestrator, StubAgent
from .pipeline import InferencePipeline, TurnResult
from .planner import Plan, Planner, PlanStep, ToolSelector
from .understanding import SemanticFrame, SemanticUnderstanding

__all__ = [
    "INTENTS", "PROTOTYPES", "TEST_SUITE", "TRAIN_UTTERANCES",
    "Classification", "DialogueManager", "IntentClassifier",
    "SemanticSpace",
    "aggregate", "evaluate_classifier", "evaluate_pipeline",
    "Goal", "GoalExtractor",
    "ConversationMemory",
    "AgentResult", "Orchestrator", "StubAgent",
    "InferencePipeline", "TurnResult",
    "Plan", "Planner", "PlanStep", "ToolSelector",
    "SemanticFrame", "SemanticUnderstanding",
]
