"""Versioned skill registry with capability-based discovery.

Skills are stored by (name, version). Resolution supports exact versions
and caret ranges ("^1.2.0" -> latest 1.x). Deprecated versions resolve only
when explicitly pinned — the policy engine can forbid them outright.
"""
from __future__ import annotations

from .skill import SkillPackage


def _parse(v: str) -> tuple[int, int, int]:
    parts = (v.split(".") + ["0", "0"])[:3]
    return tuple(int(p) for p in parts)


class RegistryError(Exception):
    pass


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, dict[str, SkillPackage]] = {}

    def register(self, skill: SkillPackage) -> None:
        self._skills.setdefault(skill.name, {})
        if skill.version in self._skills[skill.name]:
            raise RegistryError(f"{skill.name}@{skill.version} already registered")
        self._skills[skill.name][skill.version] = skill

    def resolve(self, name: str, version_spec: str = "latest") -> SkillPackage:
        versions = self._skills.get(name)
        if not versions:
            raise RegistryError(f"unknown skill: {name}")
        if version_spec == "latest":
            cands = [v for v in versions.values() if not v.manifest.deprecated]
            pool = cands or list(versions.values())
            return max(pool, key=lambda s: _parse(s.version))
        if version_spec.startswith("^"):
            base = _parse(version_spec[1:])
            cands = [s for s in versions.values()
                     if _parse(s.version)[0] == base[0]
                     and _parse(s.version) >= base]
            if not cands:
                raise RegistryError(f"no {name} matching {version_spec}")
            return max(cands, key=lambda s: _parse(s.version))
        try:
            return versions[version_spec]
        except KeyError:
            raise RegistryError(f"{name}@{version_spec} not registered")

    def find_by_capability(self, capability: str) -> list[SkillPackage]:
        out = []
        for versions in self._skills.values():
            for s in versions.values():
                if capability in s.manifest.required_capabilities:
                    out.append(s)
        return sorted(out, key=lambda s: (s.name, _parse(s.version)))

    def find_by_tag(self, tag: str) -> list[SkillPackage]:
        out = []
        for versions in self._skills.values():
            for s in versions.values():
                if tag in s.manifest.tags and not s.manifest.deprecated:
                    out.append(s)
        return sorted(out, key=lambda s: s.name)
