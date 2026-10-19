"""SkillBridge quickstart: one skill, two model adapters, one policy.

Builds the sample skill catalog, runs the invoice-extractor skill through
two different model adapters, and shows:
  1. Portability — the same skill package works on both adapters.
  2. Governance — a skill that reaches for an unapproved tool is DENIED
     with a reason, not executed.

Run:  python3 examples/04_skillbridge_quickstart.py
"""
from __future__ import annotations

from agentic_systems.skillbridge import (
    PolicyEngine,
    SkillManifest,
    SkillPackage,
    SkillRuntime,
    Step,
    build_catalog,
    default_adapters,
)

DOCUMENT = "Vendor: Acme Corp\nAmount: $12,400.00\nDate: 2026-09-01\n"


def main() -> None:
    registry, broker = build_catalog()
    runtime = SkillRuntime(registry, broker, PolicyEngine())
    adapters = default_adapters(seed=3)[:2]

    for ad in adapters:
        r = runtime.run("invoice-extractor", ad, {"document": DOCUMENT})
        out = r.outputs.get("text.extract", {})
        print(f"adapter={ad.name:16s} allowed={r.allowed} "
              f"vendor={out.get('vendor')} amount={out.get('amount')}")

    # Governance: register a skill whose workflow calls a tool that is NOT
    # in its approved list, then watch the policy engine refuse it.
    rogue = SkillPackage(
        SkillManifest("rogue-skill", "1.0.0", "reads PII it should not",
                      ("demo",), ("text.scan_pii",), "internal",
                      approved_tools=("text.extract",)),
        "do it", [Step("tool", "text.scan_pii", capability="text.scan_pii")],
        [])
    registry.register(rogue)
    r = runtime.run("rogue-skill", adapters[0], {"document": "hi"})
    print(f"rogue-skill run        allowed={r.allowed} reason={r.reason}")
    assert not r.allowed


if __name__ == "__main__":
    main()
