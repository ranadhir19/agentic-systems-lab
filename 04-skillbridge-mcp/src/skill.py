"""SkillBridge MCP — portable skill definitions.

A SkillPackage is fully provider-independent:

- manifest: identity, version, capability requirements, policy tags
- instructions: provider-neutral instruction template (no provider-specific
  prompting conventions — adapters handle translation)
- workflow: ordered steps referencing *capabilities* ("text.extract"), never
  provider tool APIs
- eval_cases: executable checks used by the cross-model evaluation harness
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str               # semver
    description: str
    tags: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    data_classification: str   # "public" | "internal" | "confidential"
    approved_tools: tuple[str, ...] = ()  # capabilities allowed; empty = all required
    deprecated: bool = False


@dataclass
class Step:
    kind: str                  # "tool" | "transform"
    name: str
    capability: str = ""       # for kind == "tool"
    transform: str = ""        # for kind == "transform": named operation
    args: dict = field(default_factory=dict)


@dataclass
class EvalCase:
    name: str
    inputs: dict
    check: Callable[[dict, dict], bool]  # (outputs, expected) -> pass
    expected: dict = field(default_factory=dict)


@dataclass
class SkillPackage:
    manifest: SkillManifest
    instructions: str          # provider-neutral template, {placeholders}
    workflow: list[Step]
    eval_cases: list[EvalCase] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version
