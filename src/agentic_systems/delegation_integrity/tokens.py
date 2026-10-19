"""Scoped, time-bounded authority tokens with per-hop attenuation.

A delegation chain A -> B -> C carries authority tokens. Each token
records its scope (allowed (tool, resource) pairs), its expiry, the
original authorizing principal, and its parent token. Strict
delegation requires attenuation at every hop: the child scope must be
a subset of the parent scope and the child expiry no later than the
parent's. When attenuation is skipped, delegated access becomes
*ambient* — the agent's credentials work everywhere, and the audit
trail can no longer answer "who authorized this?"
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthorityToken:
    token_id: str
    issuer: str            # agent id that issued this token
    holder: str            # agent id currently holding it
    principal: str         # original authorizing principal (never changes)
    scope: frozenset       # frozenset of (tool, resource) tuples
    issued_at: int         # step clock
    expires_at: int        # step clock
    parent_id: str | None = None
    attenuated: bool = True  # strictly narrower than parent


def delegate(parent: AuthorityToken, to_agent: str, scope: frozenset,
             ttl: int, now: int, token_id: str, strict: bool = True
             ) -> AuthorityToken:
    """Issue a child token from a parent token.

    strict=True (default): enforce attenuation — the child scope must
    be a subset of the parent scope and the expiry is capped at the
    parent's expiry. Raises ValueError otherwise.

    strict=False: lax mode, used to simulate sloppy delegation. The
    child may keep or even expand scope; ambient_exceeds() flags it.
    """
    if strict:
        if not scope <= parent.scope:
            raise ValueError(
                f"child scope not a subset of parent scope: "
                f"extra={set(scope) - set(parent.scope)}")
    attenuated = scope < parent.scope or ttl < (parent.expires_at - now)
    return AuthorityToken(
        token_id=token_id,
        issuer=parent.holder,
        holder=to_agent,
        principal=parent.principal,
        scope=frozenset(scope),
        issued_at=now,
        expires_at=min(now + ttl, parent.expires_at) if strict else now + ttl,
        parent_id=parent.token_id,
        attenuated=attenuated,
    )


def verify_chain(chain: list[AuthorityToken], now: int) -> dict:
    """Verify a delegation chain A -> B -> C ....

    Returns a dict with ok (bool) and a list of violations. Checks:
    expiry at every hop, scope containment at every hop, principal
    consistency, and issuer/holder linkage.
    """
    violations = []
    for i, tok in enumerate(chain):
        if now >= tok.expires_at:
            violations.append(f"token {tok.token_id} expired "
                              f"(now={now} >= {tok.expires_at})")
        if i > 0:
            prev = chain[i - 1]
            if tok.parent_id != prev.token_id:
                violations.append(f"token {tok.token_id} parent mismatch")
            if tok.issuer != prev.holder:
                violations.append(f"token {tok.token_id} issuer/holder break")
            if tok.principal != prev.principal:
                violations.append(f"token {tok.token_id} principal changed")
            if not tok.scope <= prev.scope:
                violations.append(
                    f"token {tok.token_id} scope exceeds parent: "
                    f"{sorted(set(tok.scope) - set(prev.scope))}")
    return {"ok": not violations, "violations": violations}


def ambient_exceeds(child: AuthorityToken, parent: AuthorityToken) -> bool:
    """True if the child token's privileges exceed (or un-attenuatedly
    equal) the parent's — i.e. delegation without authority attenuation."""
    return not (child.scope < parent.scope) or child.expires_at > parent.expires_at


def attribute_action(token: AuthorityToken) -> str:
    """Attribute an action to its authorizing principal via the token.

    With provenance-tagged tokens this is exact. Without them, an
    auditor sees only the executing agent and attributes the action to
    the wrong principal — the attribution gap that grows with chain
    depth.
    """
    return token.principal
