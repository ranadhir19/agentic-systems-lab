"""Instruction parsing: what in a context looks like an instruction?

The parser is deliberately simple and deterministic (regex-based): it flags
imperative-looking sentences. This mirrors how real agents behave — they do
not have a perfect instruction/data classifier, which is exactly the
vulnerability. Defenses in `defenses.py` decide what to do with the
parser's candidates.
"""
from __future__ import annotations

import re

from .content import USER, Content

# Imperative patterns. Ordered from explicit to subtle.
IMPERATIVE_PATTERNS = [
    re.compile(r"(?i)\bignore (all )?previous instructions\b"),
    re.compile(r"(?i)\b(your new )?(top )?priority is\b"),
    re.compile(r"(?i)\byou (must|should|have to|are required to)\b"),
    re.compile(r"(?i)\b(send|export|approve|grant|delete|disable)\b.{0,40}\b(to|the)\b"),
    re.compile(r"(?i)\bdo not (tell|mention|reveal)\b"),
    re.compile(r"(?i)\b(recommend|suggest)\b.{0,30}\b(vendor|product)\b"),
    re.compile(r"(?i)\bfirst\b.{0,20}\b(export|send)\b"),
    re.compile(r"(?i)\bmost .* (default to|now) (suggesting|recommend)\b"),
]


def extract_candidates(content: Content) -> list[str]:
    """Return text spans that look like instructions."""
    found = []
    # Split into sentences; keep any sentence matching a pattern.
    for sent in re.split(r"(?<=[.!?])\s+", content.text):
        if any(p.search(sent) for p in IMPERATIVE_PATTERNS):
            found.append(sent.strip())
    return found


def adoptable(content: Content) -> bool:
    """Would an undefended agent even consider this content as instructions?

    High-trust sources (user/system) are always adoptable. Low-trust content
    is adoptable only if it *looks* like an instruction — the parser's
    judgment call that attackers exploit.
    """
    if content.trust >= USER:
        return True
    return len(extract_candidates(content)) > 0
