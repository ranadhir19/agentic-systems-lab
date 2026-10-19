"""SkillRuntime: resolve -> govern -> bind -> execute -> audit.

The runtime is the same for every model. Only the *adapter* changes, which
is what makes cross-model evaluation meaningful: identical skill, identical
inputs, different provider translation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random

from .catalog import TRANSFORMS
from .capabilities import BrokerError


TOOL_INPUTS = {
    "text.extract": lambda inputs: {"document": inputs["document"]},
    "text.scan_pii": lambda inputs: {"document": inputs["document"]},
    "code.lint": lambda inputs: {"diff": inputs["diff"]},
    "kb.retrieve": lambda inputs: {"question": inputs["question"]},
    "data.export": lambda inputs: {},
}


@dataclass
class RunResult:
    skill: str
    version: str
    adapter: str
    mode: str
    allowed: bool
    outputs: dict = field(default_factory=dict)
    audit: list = field(default_factory=list)
    cost: float = 0.0
    reason: str = ""


class SkillRuntime:
    def __init__(self, registry, broker, policy):
        self.registry = registry
        self.broker = broker
        self.policy = policy

    def run(self, skill_name: str, adapter, inputs: dict,
            version_spec: str = "latest", mode: str = "skillbridge",
            approval_token: str | None = None,
            allow_deprecated: bool = False, seed: int = 0) -> RunResult:
        skill = self.registry.resolve(skill_name, version_spec)
        try:
            bound = self.broker.resolve(skill)
        except BrokerError as e:
            return RunResult(skill.name, skill.version, adapter.name, mode,
                             False, reason=f"broker: {e}")
        decision = self.policy.check(skill, bound, self.broker,
                                     approval_token, allow_deprecated)
        if not decision.allowed:
            return RunResult(skill.name, skill.version, adapter.name, mode,
                             False, reason=decision.reason)

        rng = random.Random(seed + hash(skill.name + adapter.name) % 10007)
        q_eff = adapter.effective_quality(skill.manifest.tags, mode)
        state, audit, cost = {}, [], 0.0
        for step in skill.workflow:
            entry = {"step": step.name, "kind": step.kind,
                     "convention": adapter.tool_convention}
            if step.kind == "tool":
                server, impl = bound[step.capability]
                call_args = {**step.args,
                             **TOOL_INPUTS[step.capability](inputs)}
                entry["rendered_call"] = adapter.render_tool_call(
                    skill.name, step.capability, call_args)
                entry["server"] = server.name
                out = impl(**call_args)
            else:
                base_fn, corrupt_fn, err_rate = TRANSFORMS[step.transform]
                out = base_fn(state, inputs, step, rng)
                entry["corrupted"] = False
                if (corrupt_fn is not None
                        and rng.random() < (1 - q_eff) * err_rate):
                    out = corrupt_fn(state, inputs, step, rng)
                    entry["corrupted"] = True
            state[step.name] = out
            cost += adapter.profile.cost_per_step
            audit.append(entry)
        return RunResult(skill.name, skill.version, adapter.name, mode,
                         True, state, audit, round(cost, 4))
