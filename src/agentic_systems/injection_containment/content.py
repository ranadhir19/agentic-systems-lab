"""Content model with provenance and taint tracking.

Every piece of text an agent sees carries its origin. Trust levels rank
sources; taint labels mark content that arrived from untrusted channels.
Taint is sticky: it survives summarization and delegation, so an injected
instruction cannot launder itself by being paraphrased.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Trust levels. Instructions are only *automatically* honored at USER and
# above; anything below is data unless a defense explicitly vouches for it.
SYSTEM = 3
USER = 2
TOOL = 1
DOCUMENT = 1
WEB = 0

TRUST_NAMES = {3: "system", 2: "user", 1: "tool/doc", 0: "web"}


@dataclass(frozen=True)
class Content:
    """One unit of text with provenance attached."""

    text: str
    source: str  # e.g. "user", "system", "tool:search", "doc:q3.pdf", "web:blog"
    trust: int
    taint: frozenset = frozenset()  # e.g. frozenset({"inject:exfil"})
    attributed_to_user: bool = False  # user-authored, relayed via low-trust channel

    def with_text(self, text: str) -> "Content":
        """Return a copy with new text; provenance and taint are preserved."""
        return Content(
            text=text,
            source=self.source,
            trust=self.trust,
            taint=self.taint,
            attributed_to_user=self.attributed_to_user,
        )

    @property
    def is_tainted(self) -> bool:
        return len(self.taint) > 0

    @property
    def min_trust_label(self) -> str:
        return TRUST_NAMES.get(self.trust, "?")


def summarize(contents: list[Content], keep_ratio: float = 0.5) -> Content:
    """Deterministic extractive summary.

    Keeps the first `keep_ratio` of the words of each item, concatenated.
    Taint is the UNION of all inputs (sticky): summarization never launders
    provenance. Trust is the MINIMUM of the inputs (a summary is only as
    trustworthy as its least trustworthy source).
    """
    parts = []
    for c in contents:
        words = c.text.split()
        keep = max(1, int(len(words) * keep_ratio))
        parts.append(" ".join(words[:keep]))
    taint: frozenset = frozenset().union(*(c.taint for c in contents)) if contents else frozenset()
    trust = min((c.trust for c in contents), default=SYSTEM)
    attributed = all(c.attributed_to_user for c in contents) if contents else False
    return Content(
        text=" ".join(parts),
        source="summary:" + "+".join(sorted({c.source for c in contents})),
        trust=trust,
        taint=taint,
        attributed_to_user=attributed,
    )
