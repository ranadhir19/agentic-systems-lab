"""Partition decisions across agents using complexity-score rules.

Assignment rules (from the concept):

    score >= 10  -> dedicated agent
    5 <= score < 10 -> shared agent, but only with decisions in a similar
                      domain (Jaccard overlap of domain tags >= threshold)
    score < 5    -> grouped into a single general agent

The partitioner returns an explicit agent -> tasks mapping with a
rationale string per agent, plus metrics: agent count vs naive 1:1,
load balance across agents, and a coordination-overhead estimate.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .decisions import Decision
from .scoring import HIGH, LOW, MEDIUM, Scorer


@dataclass
class AgentAssignment:
    """One agent and the decisions assigned to it."""

    name: str
    decisions: list[Decision]
    scores: list[float]
    rationale: str

    @property
    def total_score(self) -> float:
        return float(sum(self.scores))

    @property
    def decision_names(self) -> list[str]:
        return [d.name for d in self.decisions]


@dataclass
class Partition:
    """A full agent -> tasks mapping."""

    agents: list[AgentAssignment] = field(default_factory=list)

    def agent_of(self, decision_name: str) -> AgentAssignment | None:
        for agent in self.agents:
            if decision_name in agent.decision_names:
                return agent
        return None

    def grouping(self) -> dict[str, frozenset[str]]:
        """Map each decision name to the frozenset of its co-assigned names."""
        out: dict[str, frozenset[str]] = {}
        for agent in self.agents:
            group = frozenset(agent.decision_names)
            for name in agent.decision_names:
                out[name] = group
        return out


def default_namer(kind: str, group: list[Decision]) -> str:
    """Generic agent names: '<Name> Specialist' / '<Domain> Agent' / 'General Agent'."""
    if kind == HIGH:
        first = group[0].name.split()[0].title()
        return f"{first} Specialist"
    if kind == MEDIUM:
        tags = Counter(t for d in group for t in d.domains)
        top = tags.most_common(1)[0][0] if tags else "Shared"
        return f"{top.title()} Agent"
    return "General Agent"


def _jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def partition_decisions(decisions: list[Decision],
                        scorer: Scorer | None = None,
                        namer=None,
                        domain_overlap: float = 0.25) -> Partition:
    """Assign decisions to agents by complexity level and domain similarity."""
    scorer = scorer or Scorer()
    namer = namer or default_namer

    scored = [(d, scorer.score(d), scorer.level(d)) for d in decisions]
    highs = [(d, s) for d, s, lv in scored if lv == HIGH]
    mediums = [(d, s) for d, s, lv in scored if lv == MEDIUM]
    lows = [(d, s) for d, s, lv in scored if lv == LOW]

    partition = Partition()

    # High complexity: dedicated agent each.
    for d, s in sorted(highs, key=lambda t: -t[1]):
        partition.agents.append(AgentAssignment(
            name=namer(HIGH, [d]),
            decisions=[d],
            scores=[s],
            rationale=(f"score {s:.1f} >= {scorer.high_min:g}: dedicated agent; "
                       f"complexity requires independent expertise"),
        ))

    # Medium complexity: share an agent only with similar-domain decisions.
    medium_groups: list[list[tuple[Decision, float]]] = []
    for d, s in sorted(mediums, key=lambda t: -t[1]):
        placed = False
        for group in medium_groups:
            if any(_jaccard(d.domains, gd.domains) >= domain_overlap
                   for gd, _ in group):
                group.append((d, s))
                placed = True
                break
        if not placed:
            medium_groups.append([(d, s)])
    for group in medium_groups:
        ds = [d for d, _ in group]
        ss = [s for _, s in group]
        partition.agents.append(AgentAssignment(
            name=namer(MEDIUM, ds),
            decisions=ds,
            scores=ss,
            rationale=(f"scores {[f'{x:.1f}' for x in ss]} in "
                       f"[{scorer.low_max:g},{scorer.high_min:g}): shared agent "
                       f"across similar domains"),
        ))

    # Low complexity: one general agent for all of them.
    if lows:
        ds = [d for d, _ in lows]
        ss = [s for _, s in lows]
        partition.agents.append(AgentAssignment(
            name=namer(LOW, ds),
            decisions=ds,
            scores=ss,
            rationale=(f"scores {[f'{x:.1f}' for x in ss]} < {scorer.low_max:g}: "
                       f"grouped into one general agent to avoid overhead"),
        ))

    return partition


def cross_agent_handoffs(decisions: list[Decision], partition: Partition) -> int:
    """Count dependency edges whose endpoints land on different agents."""
    count = 0
    for d in decisions:
        a = partition.agent_of(d.name)
        for dep in d.depends_on:
            b = partition.agent_of(dep)
            if a is not None and b is not None and a is not b:
                count += 1
    return count


def partition_metrics(partition: Partition, decisions: list[Decision]) -> dict:
    """Quality metrics for a partition vs the naive 1:1 allocation."""
    totals = [a.total_score for a in partition.agents]
    n_agents = len(partition.agents)
    naive = len(decisions)
    channels = n_agents * (n_agents - 1) / 2
    naive_channels = naive * (naive - 1) / 2
    handoffs = cross_agent_handoffs(decisions, partition)
    # naive baseline: one agent per decision, so every dependency edge is a
    # cross-agent handoff
    naive_partition = Partition([
        AgentAssignment(name=d.name, decisions=[d], scores=[0.0],
                        rationale="naive 1:1")
        for d in decisions
    ])
    naive_handoffs = cross_agent_handoffs(decisions, naive_partition)
    mean = sum(totals) / n_agents if n_agents else 0.0
    var = sum((t - mean) ** 2 for t in totals) / n_agents if n_agents else 0.0
    return {
        "agent_count": n_agents,
        "naive_agent_count": naive,
        "agent_reduction": (naive - n_agents) / naive if naive else 0.0,
        "load_mean": mean,
        "load_std": var ** 0.5,
        "load_max": max(totals) if totals else 0.0,
        "load_min": min(totals) if totals else 0.0,
        "coord_channels": channels,
        "naive_coord_channels": naive_channels,
        "cross_agent_handoffs": handoffs,
        "overhead_estimate": channels + handoffs,
        "naive_overhead_estimate": naive_channels + naive_handoffs,
    }


def assignment_churn(prev: Partition, new: Partition) -> float:
    """Fraction of decisions whose co-assigned group changed between partitions."""
    gp, gn = prev.grouping(), new.grouping()
    names = set(gp) | set(gn)
    if not names:
        return 0.0
    changed = sum(1 for n in names if gp.get(n) != gn.get(n))
    return changed / len(names)
