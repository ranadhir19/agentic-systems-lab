"""Attention-economics quickstart: price the ask-vs-act decision.

Builds a seeded decision stream, prices every escalation policy under one
cost regime, and prints the optimal confidence threshold -- derived from
the cost ratio, not tuned.

Run:  python3 examples/19_attention_economics_quickstart.py
"""
from __future__ import annotations

import numpy as np

from agentic_systems.attention_economics import (
    AlwaysAsk,
    BudgetAware,
    FixedThreshold,
    HumanPrincipal,
    NeverAsk,
    StakesAdjusted,
    evaluate,
    make_stream,
)


def main() -> None:
    # Sample cost regime: interruptions are cheap, errors are priced at stakes.
    principal = HumanPrincipal(
        budget=10**9, interruption_cost=5.0, error_cost=1.0, accuracy=0.95
    )
    stream = make_stream(2000, seed=7)

    print(f"{'policy':22s} {'total cost':>12s} {'asks':>6s} {'unaudited errs':>14s}")
    best = None
    for pol in (
        AlwaysAsk(),
        NeverAsk(),
        FixedThreshold(0.70),
        FixedThreshold(0.90),
        StakesAdjusted(),
        BudgetAware(200),
    ):
        rep = evaluate(stream, principal, pol, seed=7)
        print(
            f"{rep.policy_name:22s} {rep.total_cost:12,.0f} "
            f"{rep.n_asks:6d} {rep.n_unaudited_errors:14d}"
        )
        if best is None or rep.total_cost < best[1]:
            best = (rep.policy_name, rep.total_cost)

    # The optimal fixed threshold is arithmetic: tau* = h - c_int/(s*c_err).
    # With heterogeneous stakes we report the median-stakes approximation.
    median_stakes = float(np.median(stream.stakes))
    tau_star = principal.accuracy - principal.interruption_cost / (
        median_stakes * principal.error_cost
    )
    print(f"\nmedian stakes        = {median_stakes:.0f}")
    print(f"optimal threshold    ~ {tau_star:.2f}  (h - c_int/(stakes*c_err))")
    print(f"cheapest policy      = {best[0]} ({best[1]:,.0f})")
    assert best[0] == "stakes-adjusted"


if __name__ == "__main__":
    main()
