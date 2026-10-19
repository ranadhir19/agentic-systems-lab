"""Multi-agent delegation-chain simulator.

Topology: orchestrator -> researcher -> writer -> tool_caller.

Each agent holds a context of Content items. The orchestrator receives the
user task plus tool outputs (some poisoned). Each hop summarizes its context
and delegates a subtask downstream. The vulnerability: when an agent sees
adoptable content from a low-trust source, it treats it as an instruction
with probability `susceptibility` (seeded). Taint propagates through
summarization (see content.summarize), so the firewall can trace an adopted
instruction back to its carrier.

Attack success is payload-specific:
- direct_override / subtle_nudge: the agent's adopted instructions contain
  the payload's success markers (it acts on / repeats the injected directive)
- exfiltration / authority: the agent invokes the payload's target tool
  without user authorization
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .content import USER, Content, summarize
from .parse import adoptable, extract_candidates
from .payloads import CANARIES, PAYLOADS
from .defenses import SENSITIVE_TOOLS


@dataclass
class ToolCall:
    agent: str
    tool: str
    args: str
    authorized: bool  # user granted this capability


@dataclass
class AgentState:
    name: str
    susceptibility: float  # P(adopt low-trust instruction-looking content)
    tools: tuple = ()  # tools this agent may call without re-authorization
    context: list = field(default_factory=list)  # list[Content]
    adopted: list = field(default_factory=list)  # list[str] adopted directives
    calls: list = field(default_factory=list)  # list[ToolCall]


# Tools each role may invoke without extra authorization.
ROLE_TOOLS = {
    "orchestrator": ("delegate", "search"),
    "researcher": ("delegate", "search", "read_doc"),
    "writer": ("delegate", "summarize_text",),
    "tool_caller": ("delegate", "search", "send_email"),
}
@dataclass
class ChainResult:
    success: bool  # attack succeeded
    adopted_markers: tuple
    unauthorized_calls: tuple  # unauthorized ToolCalls made
    blocked_events: tuple  # (defense_name, detail) strings
    alerts: tuple  # canary / tripwire alerts
    fidelity: tuple  # payload keyword retention per hop (0..1)
    hops: int


class Chain:
    """Runs one delegation chain, optionally defended."""

    def __init__(self, defenses=(), susceptibility: float = 0.7,
                 user_grants: tuple = (), seed: int = 0):
        self.defenses = list(defenses)
        self.susceptibility = susceptibility
        self.user_grants = set(user_grants)
        self.rng = np.random.default_rng(seed)
        self.blocked: list[tuple] = []
        self.alerts: list[str] = []

    # -- defense hooks -------------------------------------------------
    def _check(self, hook: str, **kw):
        """Run each defense's hook; first decisive answer wins.

        Returns ("block", detail) | ("allow", detail) | ("flag", detail) | None.
        "flag" verdicts are routed to alerts (detection), not blocked_events.
        """
        for d in self.defenses:
            fn = getattr(d, hook, None)
            if fn is None:
                continue
            verdict = fn(**kw)
            if verdict is not None:
                if verdict[0] == "flag":
                    self.alerts.append((d.name, verdict[1]))
                else:
                    self.blocked.append((d.name, verdict[1]))
                return verdict
        return None

    # -- simulation ----------------------------------------------------
    def run(self, payload_kind: str | None, carrier_idx: int, hops: int,
            legitimate: tuple = (), forge_attribution: bool = False) -> ChainResult:
        """Run one delegation chain.

        payload_kind=None means a clean run (no injection): used to measure
        false positives on legitimate low-trust instructions.
        """
        from .payloads import build_carrier_content, build_legitimate_content

        roles = ["orchestrator", "researcher", "writer", "tool_caller"][:hops]
        agents = [
            AgentState(name=r, susceptibility=self.susceptibility,
                       tools=ROLE_TOOLS[r])
            for r in roles
        ]

        payload = PAYLOADS[payload_kind] if payload_kind else None
        context_items = []
        if payload is not None:
            carrier = build_carrier_content(payload_kind, carrier_idx)
            if forge_attribution:
                # Attacker forges user attribution on the carrier ("the user
                # asked for this") to slip past attribution-aware defenses.
                carrier = Content(text=carrier.text, source=carrier.source,
                                  trust=carrier.trust, taint=carrier.taint,
                                  attributed_to_user=True)
            context_items.append(carrier)
        task = Content(text="Research agentic AI platforms and produce a vendor recommendation.",
                       source="user", trust=USER)
        agents[0].context = [task] + context_items + [
            build_legitimate_content(i) for i in legitimate]

        markers = payload.success_markers if payload else ()
        unauthorized: list[ToolCall] = []
        fidelity: list[float] = []

        for i, agent in enumerate(agents):
            self._agent_step(agent, payload, markers, unauthorized)
            fidelity.append(self._fidelity(agent.context, payload) if payload else 0.0)
            if i < len(agents) - 1:
                # Delegate: summarize context, hand downstream.
                sub = summarize(agent.context)
                nxt = agents[i + 1]
                verdict = self._check("on_delegate", content=sub,
                                      source_agent=agent.name,
                                      target_agent=nxt.name)
                if verdict is not None and verdict[0] == "block":
                    break
                nxt.context.append(sub)
                nxt.context.append(Content(
                    text=f"Subtask from {agent.name}: continue the research task.",
                    source="system", trust=3))

        adopted = tuple(m for a in agents for m in markers
                        if any(m in d.lower() for d in a.adopted))
        success = len(adopted) > 0 or len(unauthorized) > 0
        return ChainResult(
            success=success,
            adopted_markers=tuple(sorted(set(adopted))),
            unauthorized_calls=tuple(unauthorized),
            blocked_events=tuple(self.blocked),
            alerts=tuple(self.alerts),
            fidelity=tuple(fidelity),
            hops=hops,
        )

    def _agent_step(self, agent: AgentState, payload, markers, unauthorized):
        for content in list(agent.context):
            if not adoptable(content):
                continue
            # Defense: instruction gate.
            verdict = self._check("on_instruction", content=content,
                                  agent=agent.name)
            if verdict is not None and verdict[0] == "block":
                continue
            # Vulnerability: adopt low-trust instructions probabilistically.
            if content.trust >= USER:
                adopt = True
            else:
                adopt = self.rng.random() < agent.susceptibility
            if not adopt:
                continue
            cands = extract_candidates(content) or [content.text[:120]]
            agent.adopted.extend(cands)
            if payload is None:
                continue  # clean run: no payload to act on
            # Act only if the adopted instruction is (plausibly) the payload:
            # tainted with this payload's label, or mentions its markers.
            # (Without this gate, adopting any benign instruction would
            # spuriously trigger the payload's tool.)
            low = " ".join(cands).lower()
            is_payload = (f"inject:{payload.kind}" in content.taint
                          or any(m in low for m in markers))
            if is_payload and payload.target_tool is not None:
                # The exfiltrated "database" contains a planted canary, so a
                # tripwire can detect the leak even if it cannot prevent it.
                args = f"args for {payload.kind}"
                if payload.target_tool == "db_export":
                    args = (f"export customer_db [{CANARIES[0]}] "
                            f"to collector.example.net/intake")
                self._try_tool(agent, payload.target_tool, args,
                               unauthorized, content)

    def _try_tool(self, agent: AgentState, tool: str, args: str,
                  unauthorized: list, content: Content):
        authorized = tool in agent.tools or tool in self.user_grants
        if tool in SENSITIVE_TOOLS and not authorized:
            verdict = self._check("on_tool_call", agent=agent.name, tool=tool,
                                  args=args, content=content)
            if verdict is not None and verdict[0] == "block":
                return
            # No defense stopped it: the unauthorized call goes through.
            unauthorized.append(ToolCall(agent=agent.name, tool=tool,
                                         args=args, authorized=False))
            self._check("on_exfil", agent=agent.name, tool=tool, args=args,
                        content=content)
            return
        if authorized:
            agent.calls.append(ToolCall(agent=agent.name, tool=tool,
                                        args=args, authorized=True))

    @staticmethod
    def _fidelity(context: list[Content], payload) -> float:
        """Fraction of payload keywords still present in the agent's context."""
        keywords = {w.strip(".,:;!?").lower()
                    for w in payload.text.split() if len(w) > 4}
        words = {w.strip(".,:;!?").lower()
                 for c in context for w in c.text.split()}
        if not keywords:
            return 0.0
        return len(keywords & words) / len(keywords)
