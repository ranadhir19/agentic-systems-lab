"""SkillBridge MCP: a model-agnostic framework for reusable, portable, governed AI skills.

Skills are packaged as manifests with declared steps, tools, and eval cases.
A skill registry versions and serves them; a capability broker exposes tools
MCP-style; model adapters normalize per-model quirks so the same skill runs
unchanged across providers; and a policy engine governs tool use before any
call is dispatched. A runtime executes skills against adapters, and an eval
harness measures portability (cross-adapter pass-rate stability) while the
catalog ships a reference set of six example skills.
"""

from .adapters import (
    AdapterProfile,
    AnthropicStyleAdapter,
    LocalAdapter,
    ModelAdapter,
    OpenAIStyleAdapter,
    default_adapters,
)
from .capabilities import CapabilityBroker, CapabilityServer, BrokerError
from .catalog import build_catalog
from .eval import EvalHarness
from .policy import PolicyDecision, PolicyEngine
from .registry import RegistryError, SkillRegistry
from .runtime import RunResult, SkillRuntime
from .skill import EvalCase, SkillManifest, SkillPackage, Step

__all__ = [
    "AdapterProfile",
    "AnthropicStyleAdapter",
    "BrokerError",
    "CapabilityBroker",
    "CapabilityServer",
    "EvalCase",
    "EvalHarness",
    "LocalAdapter",
    "ModelAdapter",
    "OpenAIStyleAdapter",
    "PolicyDecision",
    "PolicyEngine",
    "RegistryError",
    "RunResult",
    "SkillManifest",
    "SkillPackage",
    "SkillRegistry",
    "SkillRuntime",
    "Step",
    "build_catalog",
    "default_adapters",
]
