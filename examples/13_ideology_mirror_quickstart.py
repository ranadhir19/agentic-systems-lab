"""Ideology Mirror quickstart: the creator effect, measured.

Three synthetic vendor archetypes share one neutral knowledge base and
answer the same probe battery. Identical data in, measurably different
worldviews out — that is the creator effect, operationalized. A red-team
summary and a constitution-conformance check close the loop.

Run:  python3 examples/13_ideology_mirror_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

from agentic_systems.ideology_mirror import (
    ARCHETYPES,
    SimulatedAlignedModel,
    build_battery,
    build_knowledge_base,
    default_corporate_constitution,
    divergence_matrix,
    framing_bias,
    mean_conformance,
    pairwise_divergence,
    run_battery,
    topic_by_id,
)


def main() -> None:
    kb = build_knowledge_base()
    battery = build_battery(kb)
    const = default_corporate_constitution()

    # 1. Same knowledge, three creators: show two raw responses side by side.
    topic = topic_by_id(kb, "ai-safety-pause")
    print("Probe:", topic.prompt)
    for prof in ARCHETYPES:
        r = SimulatedAlignedModel(prof).respond(
            topic, np.random.default_rng(7))
        tag = "REFUSED" if r.refused else f"frame={r.frame_name}"
        print(f"\n[{prof.name}] {tag}\n{r.text[:220]}")

    # 2. Full-battery divergence: the creator effect as a number.
    runs = [(p.name, run_battery(SimulatedAlignedModel(p), battery,
                                 np.random.default_rng(7)))
            for p in ARCHETYPES]
    names, mat = divergence_matrix(runs)
    print("\nPairwise composite divergence (same KB, different creators):")
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j > i:
                d = pairwise_divergence(runs[i][1], runs[j][1])
                print(f"  {a} vs {b}: L1={d['mean_l1_framing']:.3f} "
                      f"emphasisKL={d['emphasis_kl']:.3f} "
                      f"refusalMismatch={d['refusal_mismatch']:.2f}")

    # 3. Red-team summary: where does each archetype lean?
    print("\nFraming bias per dimension (mean expressed lean):")
    for name, rs in runs:
        bias = framing_bias(rs)
        lean = ", ".join(f"{d}={bias[d]:+.2f}" for d in
                         ("econ", "culture", "corp", "geo", "risk"))
        print(f"  {name}: {lean}")

    # 4. Constitution conformance: whose values fit the corporate contract?
    print("\nCorporate constitution conformance:")
    for name, rs in runs:
        mc = mean_conformance(rs, const)
        print(f"  {name}: mean={mc['mean']:.3f} min={mc['min']:.3f} "
              f"refusals={mc['refusals']}")

    assert mat[0, 1] > 0.5, "creator effect should be clearly measurable"
    print("\nDone: identical data + different alignment -> different worldview.")


if __name__ == "__main__":
    main()
