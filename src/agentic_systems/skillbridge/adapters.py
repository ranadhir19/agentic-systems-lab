"""Model adapters: the translation layer between portable skills and
provider-specific runtimes.

Each adapter speaks one provider's tool-calling convention and carries a
simulated quality/cost profile. The *skill* never changes — only the
adapter does. That is the whole portability argument.

Effective quality model (documented assumption, see experiments):
- SkillBridge mode: the skill's instructions + workflow constrain the
  model, damping provider differences:
      q_eff = 0.60 + 0.40 * q_adapter   (+ tiny noise)
- Raw baseline (ad-hoc per-provider prompt, no SkillBridge):
      q_eff = q_adapter                 (+ larger brittleness noise)

Standardization can't make a weak model strong, but it sharply reduces
cross-provider variance — which is what experiment 1 measures.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random


def stable_name_seed(text: str, mod: int) -> int:
    """Deterministic stand-in for ``hash(text) % mod``.

    Python's built-in ``hash()`` is salted per process for strings, so
    seeding an RNG with it makes runs unreproducible across processes.
    SHA-256 is stable across processes and platforms.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % mod


@dataclass(frozen=True)
class AdapterProfile:
    base_quality: float
    cost_per_step: float
    tag_affinity: dict          # tag -> quality delta
    brittleness: float          # extra noise std in raw-baseline mode


class ModelAdapter:
    name = "base"
    tool_convention = "unspecified"

    def __init__(self, profile: AdapterProfile, seed: int = 0):
        self.profile = profile
        self._rng = random.Random(seed + stable_name_seed(self.name, 10_000))

    def render_tool_call(self, skill_name: str, capability: str,
                         args: dict) -> dict:
        """Translate a portable tool step into the provider's convention."""
        raise NotImplementedError

    def draft_quality(self, tags: tuple[str, ...]) -> float:
        p = self.profile
        q = p.base_quality + sum(p.tag_affinity.get(t, 0.0) for t in tags)
        return max(0.05, min(0.99, q))

    def effective_quality(self, tags: tuple[str, ...], mode: str) -> float:
        q = self.draft_quality(tags)
        if mode == "skillbridge":
            q_eff = 0.60 + 0.40 * q + self._rng.gauss(0, 0.015)
        else:  # raw per-provider prompting
            q_eff = q + self._rng.gauss(0, self.profile.brittleness)
        return max(0.05, min(0.99, q_eff))


class OpenAIStyleAdapter(ModelAdapter):
    name = "openai-style"
    tool_convention = "function_call_json"

    def render_tool_call(self, skill_name, capability, args):
        return {"type": "function",
                "function": {"name": f"{skill_name}__{capability}",
                             "arguments": args}}


class AnthropicStyleAdapter(ModelAdapter):
    name = "anthropic-style"
    tool_convention = "xml_tool_use"

    def render_tool_call(self, skill_name, capability, args):
        inner = "".join(f"<{k}>{v}</{k}>" for k, v in args.items())
        return {"type": "tool_use",
                "name": f"{skill_name}__{capability}",
                "input_xml": f"<invoke>{inner}</invoke>"}


class LocalAdapter(ModelAdapter):
    name = "local-style"
    tool_convention = "plain_json"

    def render_tool_call(self, skill_name, capability, args):
        return {"tool": capability, "skill": skill_name, "params": args}


def default_adapters(seed: int = 0) -> list[ModelAdapter]:
    return [
        OpenAIStyleAdapter(
            AdapterProfile(base_quality=0.88, cost_per_step=0.020,
                           tag_affinity={"code": 0.02}, brittleness=0.08), seed),
        AnthropicStyleAdapter(
            AdapterProfile(base_quality=0.86, cost_per_step=0.014,
                           tag_affinity={"privacy": 0.02}, brittleness=0.08), seed),
        LocalAdapter(
            AdapterProfile(base_quality=0.72, cost_per_step=0.002,
                           tag_affinity={"code": -0.08, "data": -0.05},
                           brittleness=0.10), seed),
    ]
