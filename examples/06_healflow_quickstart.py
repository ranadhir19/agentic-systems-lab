"""HealFlow quickstart: a workflow that heals itself.

Runs the sample ETL workflow while a transient outage hits the `extract`
step twice. HealFlow diagnoses the cause, retries, and completes with
zero side effects — no manual intervention, no duplicate external actions.

Run:  python3 examples/06_healflow_quickstart.py
"""
from __future__ import annotations

from agentic_systems.healflow import (
    PREDS,
    SUBSTITUTES,
    HealFlowRuntime,
    build_injector,
    etl_flow,
)


def main() -> None:
    rt = HealFlowRuntime(build_injector(), PREDS, SUBSTITUTES)
    rt.injector.add_fault("extract", "outage", n=2)

    rep = rt.run(etl_flow(), expected_cause="transient_outage")
    print(f"success={rep.success}  side_effects={rep.side_effects}  "
          f"repairs={rep.repairs}  tool_calls={rep.tool_calls}  "
          f"diagnosis_steps={rep.diagnosis_steps}")
    assert rep.success and rep.side_effects == 0

    print("Workflow recovered itself: 2 retries, 0 side effects.")


if __name__ == "__main__":
    main()
