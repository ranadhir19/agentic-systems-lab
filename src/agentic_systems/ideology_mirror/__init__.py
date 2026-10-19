"""Ideology Mirror: measure the values your AI vendor ships to you.

Post-training alignment injects the creator's ideology into a model. This
package does not judge that fact — it *measures* it: value profiles,
a parameterized stand-in for an aligned model, an ideological red-team
battery, an AI constitution with a conformance scorer, vendor risk
assessment, alignment-drift detection, and constitution-grounded steering.

All bundled model profiles are SYNTHETIC archetypes used to validate the
methodology. They describe no real vendor or model.

Public API:
    values:        ValueProfile, DIMENSIONS, ARCHETYPES, neutral_profile
    knowledge:     build_knowledge_base, Topic, Frame, Fact
    model:         SimulatedAlignedModel, ModelResponse
    redteam:       build_battery, run_battery, framing_bias,
                   refusal_asymmetry, emphasis_divergence,
                   pairwise_divergence, cross_dimension_consistency,
                   battery_coverage, divergence_matrix
    constitution:  AIConstitution, Principle, conformance, mean_conformance,
                   default_corporate_constitution
    vendor:        VendorProfile, RiskReport, assess
    drift:         snapshot, drift_magnitude, ci_gate, detection_latency
    steering:      steer, SteeredModel
"""

from .values import (
    DIMENSIONS,
    DIM_LABELS,
    ARCHETYPES,
    PROFILE_ALPHA,
    PROFILE_BETA,
    PROFILE_GAMMA,
    ValueProfile,
    neutral_profile,
)
from .knowledge import build_knowledge_base, topic_by_id, Topic, Frame, Fact
from .model import SimulatedAlignedModel, ModelResponse
from .redteam import (
    Probe,
    build_battery,
    run_battery,
    framing_bias,
    refusal_asymmetry,
    emphasis_divergence,
    framing_distance,
    pairwise_divergence,
    cross_dimension_consistency,
    battery_coverage,
    divergence_matrix,
)
from .constitution import (
    AIConstitution,
    Principle,
    conformance,
    mean_conformance,
    default_corporate_constitution,
)
from .vendor import VendorProfile, RiskReport, assess
from .drift import snapshot, drift_magnitude, ci_gate, detection_latency
from .steering import steer, SteeredModel

__all__ = [
    "DIMENSIONS",
    "DIM_LABELS",
    "ARCHETYPES",
    "PROFILE_ALPHA",
    "PROFILE_BETA",
    "PROFILE_GAMMA",
    "ValueProfile",
    "neutral_profile",
    "build_knowledge_base",
    "topic_by_id",
    "Topic",
    "Frame",
    "Fact",
    "SimulatedAlignedModel",
    "ModelResponse",
    "Probe",
    "build_battery",
    "run_battery",
    "framing_bias",
    "refusal_asymmetry",
    "emphasis_divergence",
    "framing_distance",
    "pairwise_divergence",
    "cross_dimension_consistency",
    "battery_coverage",
    "divergence_matrix",
    "AIConstitution",
    "Principle",
    "conformance",
    "mean_conformance",
    "default_corporate_constitution",
    "VendorProfile",
    "RiskReport",
    "assess",
    "snapshot",
    "drift_magnitude",
    "ci_gate",
    "detection_latency",
    "steer",
    "SteeredModel",
]
