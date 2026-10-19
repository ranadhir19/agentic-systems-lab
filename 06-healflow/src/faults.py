"""Tools and fault injection.

Tools are plain functions (state, args) -> output dict. The FaultInjector
wraps them and can introduce, per tool:

- outage(n): raise ToolOutage on the next n calls (transient)
- schema_change(mapping): permanently rename output keys
- corrupt(fn): transform the output into bad data (postcondition fails)
- fail_once: raise once, then behave (partial-transaction setups)

Faults are declared per experiment run; the injector counts calls so
experiments are deterministic.
"""
from __future__ import annotations


class ToolOutage(Exception):
    pass


class ToolFailed(Exception):
    pass


class FaultInjector:
    def __init__(self):
        self.tools: dict[str, callable] = {}
        self.faults: list[dict] = []
        self.calls: dict[str, int] = {}

    def register(self, name: str, fn: callable) -> None:
        self.tools[name] = fn

    def add_fault(self, tool: str, kind: str, **params) -> None:
        self.faults.append({"tool": tool, "kind": kind, "params": params,
                            "used": 0})

    def call(self, tool: str, state: dict, args: dict) -> dict:
        self.calls[tool] = self.calls.get(tool, 0) + 1
        for f in self.faults:
            if f["tool"] != tool:
                continue
            kind, p = f["kind"], f["params"]
            if kind == "outage" and f["used"] < p.get("n", 1):
                f["used"] += 1
                raise ToolOutage(f"{tool} unavailable "
                                 f"({f['used']}/{p.get('n', 1)})")
            if kind == "fail_once" and f["used"] < 1:
                f["used"] += 1
                raise ToolFailed(f"{tool} failed once")
            if kind == "schema_change":
                out = self.tools[tool](state, args)
                mapping = p["mapping"]

                def remap(obj):
                    if isinstance(obj, dict):
                        return {mapping.get(k, k): remap(v)
                                for k, v in obj.items()}
                    if isinstance(obj, list):
                        return [remap(v) for v in obj]
                    return obj

                return remap(out)
            if kind == "corrupt" and f["used"] < p.get("n", 10 ** 9):
                f["used"] += 1
                out = self.tools[tool](state, args)
                return p["fn"](out)
        return self.tools[tool](state, args)

    def reset(self) -> None:
        self.faults = []
        self.calls = {}
