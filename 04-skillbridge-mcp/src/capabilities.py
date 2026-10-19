"""MCP-style capability broker.

Servers register the capabilities they offer (this mirrors MCP servers
exposing tools/resources). Skills declare required capabilities; the broker
binds each requirement to a concrete server at run time. A skill is only
runnable when every required capability resolves — portability means the
*capability contract* is stable even as servers and models change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CapabilityServer:
    name: str                                   # e.g. "text-tools-mcp"
    capabilities: dict[str, Callable[..., Any]] # capability -> implementation
    sensitivity: dict[str, str] = field(default_factory=dict)  # cap -> low|high


class BrokerError(Exception):
    pass


class CapabilityBroker:
    def __init__(self):
        self._servers: list[CapabilityServer] = []

    def register_server(self, server: CapabilityServer) -> None:
        self._servers.append(server)

    def resolve(self, skill) -> dict[str, tuple[CapabilityServer, Callable]]:
        """Bind every required capability to (server, implementation)."""
        bound = {}
        missing = []
        for cap in skill.manifest.required_capabilities:
            hit = None
            for srv in self._servers:
                if cap in srv.capabilities:
                    hit = (srv, srv.capabilities[cap])
                    break
            if hit is None:
                missing.append(cap)
            else:
                bound[cap] = hit
        if missing:
            raise BrokerError(f"unresolved capabilities for {skill.name}: {missing}")
        return bound

    def sensitivity_of(self, capability: str) -> str:
        for srv in self._servers:
            if capability in srv.sensitivity:
                return srv.sensitivity[capability]
        return "low"
