"""Cross-model evaluation harness.

Runs every eval case of every skill across every adapter in two modes:

- skillbridge: portable skill via the adapter (damped provider variance)
- raw:        ad-hoc per-provider prompting (full provider variance)

Reports per-(skill, mode): pass rate per adapter, cross-adapter std dev,
and the portability score = worst-adapter pass rate.
"""
from __future__ import annotations

import statistics


class EvalHarness:
    def __init__(self, runtime):
        self.runtime = runtime

    def evaluate(self, skill_names: list[str], adapters: list,
                 modes=("skillbridge", "raw"), seed: int = 0):
        results = {}
        for sname in skill_names:
            skill = self.runtime.registry.resolve(sname)
            for adapter in adapters:
                for mode in modes:
                    passed, total = 0, 0
                    for i, case in enumerate(skill.eval_cases):
                        res = self.runtime.run(
                            sname, adapter, case.inputs, mode=mode,
                            seed=seed + i)
                        total += 1
                        if res.allowed and case.check(res.outputs,
                                                      case.expected):
                            passed += 1
                    results[(sname, adapter.name, mode)] = {
                        "passed": passed, "total": total,
                        "rate": passed / total if total else 0.0,
                    }
        return results

    @staticmethod
    def portability(results: dict, skill: str, mode: str,
                    adapters: list) -> dict:
        rates = [results[(skill, a.name, mode)]["rate"] for a in adapters]
        return {
            "mean": statistics.fmean(rates),
            "min": min(rates),
            "std": statistics.pstdev(rates),
            "per_adapter": {a.name: r for a, r in zip(adapters, rates)},
        }
