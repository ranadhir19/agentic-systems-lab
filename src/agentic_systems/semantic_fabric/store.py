"""Versioned semantic store.

The store persists semantic *artifacts* — never raw data. Each artifact is
content-addressed (sha256 of canonical JSON) and versioned: a new version
is minted only when the content hash changes. Raw data is discardable
after extraction; the store is the system of record.
"""
from __future__ import annotations

import hashlib
import json


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str)


def content_hash(artifact):
    return hashlib.sha256(canonical(artifact).encode()).hexdigest()[:16]


class SemanticStore:
    """put(layer, source, artifact) -> (version, hash, changed).

    Versions are per (layer, source). Identical content re-put is a
    no-op returning the current version with changed=False.
    """

    def __init__(self):
        self._versions = {}   # (layer, source) -> list of entries
        self._latest = {}     # (layer, source) -> entry

    def put(self, layer, source, artifact, meta=None):
        h = content_hash(artifact)
        key = (layer, source)
        prev = self._latest.get(key)
        if prev is not None and prev["hash"] == h:
            return prev["version"], h, False
        version = (prev["version"] + 1) if prev else 1
        entry = {"layer": layer, "source": source, "version": version,
                 "hash": h, "artifact": artifact, "meta": meta or {}}
        self._versions.setdefault(key, []).append(entry)
        self._latest[key] = entry
        return version, h, True

    def get(self, layer, source, version=None):
        key = (layer, source)
        if version is None:
            return self._latest[key]
        for e in self._versions[key]:
            if e["version"] == version:
                return e
        raise KeyError(f"no version {version} for {key}")

    def history(self, layer, source):
        return list(self._versions.get((layer, source), []))

    def layers(self):
        return sorted({layer for layer, _ in self._latest})

    def sources(self):
        return sorted({src for _, src in self._latest})

    def total_bytes(self):
        return sum(len(canonical(e["artifact"]).encode())
                   for e in self._latest.values())

    def bytes_by_layer(self):
        out = {}
        for (layer, _), e in self._latest.items():
            out[layer] = out.get(layer, 0) + len(
                canonical(e["artifact"]).encode())
        return out
