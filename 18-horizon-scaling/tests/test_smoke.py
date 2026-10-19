"""Smoke tests for horizon-scaling."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.horizon_scaling import (
    TaskSpec, default_spec, mix_spec,
    run_baseline, run_checkpoints, run_hierarchy, run_recovery,
    run_voting, run_hierarchy_checkpoints,
    theoretical_per_step_q, theoretical_voting_per_step_q,
    fit_exponential_decay, summarize,
)


def test_baseline_matches_theory():
    spec = default_spec(20)
    reps = [run_baseline(spec, np.random.default_rng(100 + i))
            for i in range(2000)]
    emp = summarize(reps)["success_rate"]
    theory = theoretical_per_step_q(spec) ** 20
    assert abs(emp - theory) < 0.03, (emp, theory)


def test_voting_matches_binomial_theory():
    spec = default_spec(20)
    reps = [run_voting(spec, np.random.default_rng(200 + i), n=3)
            for i in range(2000)]
    emp = summarize(reps)["success_rate"]
    theory = theoretical_voting_per_step_q(spec, 3) ** 20
    assert abs(emp - theory) < 0.03, (emp, theory)


def test_decay_is_monotone():
    spec_fn = default_spec
    prev = 1.0
    for n in [5, 10, 20, 40]:
        spec = spec_fn(n)
        reps = [run_baseline(spec, np.random.default_rng(300 + i))
                for i in range(1000)]
        s = summarize(reps)["success_rate"]
        assert s <= prev + 0.02, (n, s, prev)
        prev = s


def test_mitigations_beat_baseline_long_horizon():
    spec = default_spec(40)
    base = summarize([run_baseline(spec, np.random.default_rng(400 + i))
                      for i in range(500)])["success_rate"]
    for name, fn in [("checkpoints", lambda s, r: run_checkpoints(s, r, k=5)),
                     ("hierarchy", lambda s, r: run_hierarchy(s, r, subtask_size=10)),
                     ("voting", lambda s, r: run_voting(s, r, n=3)),
                     ("recovery", lambda s, r: run_recovery(s, r, k=5))]:
        s = summarize([fn(spec, np.random.default_rng(500 + i))
                       for i in range(500)])["success_rate"]
        assert s > base + 0.2, (name, s, base)


def test_recovery_never_worse_than_checkpoints_much():
    # recovery adds diagnosis + retries on top of checkpoints; it should
    # not be dramatically worse (both share the core)
    spec = default_spec(40)
    c = summarize([run_checkpoints(spec, np.random.default_rng(600 + i), k=5)
                   for i in range(500)])["success_rate"]
    r = summarize([run_recovery(spec, np.random.default_rng(700 + i), k=5)
                   for i in range(500)])["success_rate"]
    assert r > c - 0.15, (r, c)


def test_checkpoint_sweep_has_interior_optimum():
    # very frequent verification wastes cost; very rare loses the task
    spec = default_spec(40)
    cps = {}
    for k in [2, 40]:
        reps = [run_checkpoints(spec, np.random.default_rng(800 + k + i), k=k)
                for i in range(500)]
        cps[k] = summarize(reps)["cost_per_success"]
    mid = summarize([run_checkpoints(spec, np.random.default_rng(900 + i), k=5)
                     for i in range(500)])["cost_per_success"]
    assert mid < cps[2] and mid < cps[40], (mid, cps)


def test_fatal_heavy_favors_rollback():
    # fatal errors are immediately visible, so verify-and-rollback
    # should shine in the fatal-heavy mix
    spec = mix_spec(40, "fatal-heavy")
    c = summarize([run_checkpoints(spec, np.random.default_rng(1000 + i), k=5)
                   for i in range(500)])["success_rate"]
    assert c > 0.85, c


def test_fit_recovers_theoretical_q():
    spec = default_spec(10)
    q = theoretical_per_step_q(spec)
    horizons = [5, 10, 20, 40]
    sr = []
    for n in horizons:
        s2 = TaskSpec(n_steps=n, p_fatal=spec.p_fatal, p_err=spec.p_err,
                      cascade=spec.cascade, detect_check=spec.detect_check)
        reps = [run_baseline(s2, np.random.default_rng(1100 + n * 10 + i))
                for i in range(1500)]
        sr.append(summarize(reps)["success_rate"])
    q_hat, r2 = fit_exponential_decay(horizons, sr)
    assert abs(q_hat - q) < 0.005, (q_hat, q)
    assert r2 > 0.99, r2


def test_no_forbidden_name():
    # user directive (2026-10-19): the old product name must not appear
    # anywhere; the literal is constructed so it never occurs in source
    forbidden = "dev" + "pulse"
    import agentic_systems.horizon_scaling as m
    import pathlib
    root = pathlib.Path(m.__file__).parent
    for p in list(root.rglob("*.py")) + [
            pathlib.Path(__file__).parent.parent / "README.md",
            pathlib.Path(__file__).parent.parent / "experiments" / "run_experiments.py"]:
        if p.exists():
            assert forbidden not in p.read_text().lower(), p
