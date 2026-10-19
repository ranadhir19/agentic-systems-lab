"""Preset task configurations: the default family and error-mix variants."""
from __future__ import annotations

from .tasks import TaskSpec


def default_spec(n_steps: int) -> TaskSpec:
    """Default task family: 1% fatal, 3% latent corruption per step."""
    return TaskSpec(n_steps=n_steps, p_fatal=0.01, p_err=0.03,
                    cascade=2.0, detect_check=0.8)


ERROR_MIXES = {
    # (p_fatal, p_err): total per-step error ~5% in each mix so the
    # baseline decay is comparable and the *composition* is the variable.
    "corruption-heavy": (0.01, 0.05),
    "balanced": (0.02, 0.03),
    "fatal-heavy": (0.045, 0.005),
}


def mix_spec(n_steps: int, mix: str) -> TaskSpec:
    pf, pe = ERROR_MIXES[mix]
    return TaskSpec(n_steps=n_steps, p_fatal=pf, p_err=pe,
                    cascade=2.0, detect_check=0.8)
