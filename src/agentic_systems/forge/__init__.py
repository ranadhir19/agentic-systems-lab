"""Forge inference: discrete-event simulator of LLM inference serving.

Compares three batch-scheduling policies under load:

- ``static-fcfs``   -- static batching, first-come-first-served
- ``continuous``    -- continuous (iteration-level) batching, FIFO
- ``continuous-srpt`` -- continuous batching with shortest-remaining-processing-time ordering

Use :class:`Engine` to run the simulation on a list of :class:`Request`
objects (see :func:`generate_requests` to sample a synthetic arrival stream),
and :class:`Stats` to aggregate per-policy latency / throughput metrics.
"""

from .simulator import Engine, Request, Stats
from .simulator import _gen_requests as generate_requests

__all__ = ["Engine", "Request", "Stats", "generate_requests"]
