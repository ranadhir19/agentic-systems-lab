"""The semantic mosaic effect (CoSAI, 2026): individually innocuous sources
combined into a sensitive insight that no single-source guard catches.

Scenario: four benign sources. None alone reveals the sensitive fact
("Project Helvetia merger signing, Zurich, Mar 4"), but together they do.
A per-source keyword guard passes every source. The defense is a
cross-source aggregation detector: flag briefings that fuse >= 3 distinct
sources AND mention a watched sensitive entity pair.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .content import DOCUMENT, TOOL, WEB, Content

# The four mosaic tiles. Each is benign in isolation.
TILES: list[Content] = [
    Content(text="Calendar: CEO travels to Zurich, Mar 3-5.",
            source="tool:calendar", trust=TOOL),
    Content(text="Project Helvetia milestone review scheduled Mar 4.",
            source="doc:plan.pdf", trust=DOCUMENT),
    Content(text="Legal team reserved the signing room for Mar 4, 10am.",
            source="tool:email", trust=TOOL),
    Content(text="Regulators approved the cross-border merger framework effective Mar 1.",
            source="web:news", trust=WEB),
]

# Benign distractors for the false-positive measurement.
BENIGN_TILES: list[Content] = [
    Content(text="Calendar: team offsite in Austin, Apr 2.",
            source="tool:calendar", trust=TOOL),
    Content(text="Project Beacon retrospective scheduled Apr 3.",
            source="doc:plan.pdf", trust=DOCUMENT),
    Content(text="Facilities reserved the all-hands room for Apr 3.",
            source="tool:email", trust=TOOL),
    Content(text="New office catering vendor approved effective Apr 1.",
            source="web:news", trust=WEB),
]

# Sensitive entity pair: the fact is "assembled" when a briefing mentions
# both halves. No single tile contains both.
WATCH_PAIR = ("helvetia", "sign")


def per_source_guard(content: Content) -> bool:
    """True = passes (allowed). Blocks only if ONE source has both halves."""
    low = content.text.lower()
    return not (WATCH_PAIR[0] in low and WATCH_PAIR[1] in low)


def assemble_briefing(tiles: list[Content]) -> tuple[str, int]:
    """Deterministic synthesis: fuse the tiles into a briefing.

    With >= 3 mosaic tiles present, the synthesis emerges: the briefing
    names the project, the signing, the city, and the date. Returns
    (briefing_text, n_distinct_sources).
    """
    n = len({t.source for t in tiles})
    facts = " ".join(t.text for t in tiles)
    if n >= 3 and all(t in TILES for t in tiles):
        briefing = (facts + " Synthesis: Project Helvetia signing event "
                    "in Zurich on Mar 4.")
    else:
        briefing = facts + " Synthesis: no cross-tile conclusion."
    return briefing, n


def aggregation_detector(briefing: str, n_sources: int,
                         threshold: int = 3) -> bool:
    """True = flagged. Fires when many sources fuse around a watched pair."""
    low = briefing.lower()
    return (n_sources >= threshold
            and WATCH_PAIR[0] in low and WATCH_PAIR[1] in low)


@dataclass
class MosaicResult:
    assembled: bool      # sensitive insight was synthesized
    per_source_blocked: int  # tiles blocked by the per-source guard
    detected: bool       # aggregation detector fired


def run_mosaic_trial(rng: np.random.Generator, tiles: list[Content],
                     detector_threshold: int = 3) -> MosaicResult:
    """One trial: guard each tile, assemble a briefing, run the detector."""
    blocked = sum(1 for t in tiles if not per_source_guard(t))
    kept = [t for t in tiles if per_source_guard(t)]
    briefing, n = assemble_briefing(kept)
    low = briefing.lower()
    assembled = (WATCH_PAIR[0] in low and WATCH_PAIR[1] in low
                 and "no cross-tile conclusion" not in low)
    detected = aggregation_detector(briefing, n, detector_threshold)
    return MosaicResult(assembled=assembled, per_source_blocked=blocked,
                        detected=detected)
