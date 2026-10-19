# Emergent Goals — Design Document

## 1. The research question

> If N agents are given one specific assigned goal and a continuous flow of
> data/resources, can they evolve — by themselves, through interaction — to
> create *additional* goals, and keep evolving? Is there an implicit
> motivation, biological or inorganic, such that when agents communicate,
> an intrinsic drive toward *continuity* (self-maintenance, persistence of
> the collective) gets triggered?

In plain terms: does communication catalyze self-generated purpose?

## 2. Why this question matters

Modern agentic systems assign goals top-down. Biology suggests an
alternative: goals can be *endogenous*. Bacteria, animals, and human
organizations all exhibit drives — curiosity, play, affiliation,
self-preservation — that were never "assigned" by a designer but emerged
because they serve continuity: the persistence of the agent and its
lineage. If even a toy simulation shows that (a) simple intrinsic drives,
(b) a communication channel, and (c) a goal-imagination mechanism are
jointly sufficient for agents to propose goals nobody programmed, that
constrains both how we build open-ended systems and how we govern them
(cf. the remit-divergence problem: ungoverned goal generation is a safety
surface, not just a capability).

## 3. Intellectual lineage (what the literature already knows)

**Intrinsic motivation / curiosity.**
Schmidhuber (1991) first formalized artificial curiosity: reward the agent
for *prediction error* (1991a) and later for *improvement* in prediction
— compression progress (1991b, 2006). The agent becomes a scientist that
invents its own experiments. Oudeyer, Kaplan & Hafner (2007, "the
Playground Experiment") built Intelligent Adaptive Curiosity: robots that
maximize *learning progress*, producing autonomous developmental stages
without any hand-designed curriculum. Pathak et al. (2017) scaled this
with self-supervised prediction (ICM). The through-line: *interestingness
= learnability in progress*, and it generates behavior that looks
self-directed.

**Autotelic agents and goal imagination.** Oudeyer's later program
(IMGEP — Intrinsically Motivated Goal Exploration Processes; Colas et
al., CURIOUS, ICML 2019) gives agents a *goal space* they sample
themselves, with curricula ordered by absolute learning progress. Agents
set their own tasks and get robust to distraction and forgetting. Goal
generation is treated as a first-class cognitive operation, not a hack.

**Empowerment.** Klyubin, Polani & Nehaniv (2005, 2008) defined
empowerment as the channel capacity from an agent's actions to its future
sensor states — the information-theoretic formalization of "keeping your
options open." An empowerment-maximizing agent drifts toward states of
maximal future controllability: a purely *inorganic* continuity drive,
with no biology required.

**Open-endedness.** Lehman & Stanley's novelty search (2008, 2011) showed
that ignoring the objective and selecting for behavioral novelty can
*outperform* objective-driven search on deceptive problems — complexity
rises because simple behaviors exhaust themselves. MAP-Elites (Mouret
& Clune, 2015) archives diverse high-quality behaviors; POET (Wang et
al., 2019) co-evolves environments and agents. Lesson: open-ended
divergence needs an archive and a divergence pressure, not a target.

**Emergent communication.** Foerster et al. (2016) and Lazaridou et al.
(2017) showed deep MARL agents invent signaling protocols to solve
cooperative tasks (Lewis signaling games). Protocols are typically
partner-specific and non-compositional (Kottur et al., 2017) — a warning
that "communication" in toy settings is often just coupled policy
correlation, not language.

**Multi-agent autocurricula.** OpenAI's hide-and-seek (Baker et al.,
2019): simple competition produced six phases of emergent tool use
(fort-building, ramp use, ramp defense, box-surfing) — strategies never
rewarded directly. Other agents are the richest source of environmental
novelty; co-adaptation is an engine of open-endedness.

**Homeostasis and the free energy principle.** Friston's FEP: any system
with a Markov blanket that persists over time can be described as
minimizing variational free energy (surprise). "Continuity" is therefore
not an add-on drive — under FEP it is *the* drive, and perception, action,
and learning are all surprise-minimization. Our homeostatic energy drive
is a deliberately crude, explicit version of this.

**Instrumental convergence.** Omohundro (2008) / Bostrom (2012, 2014):
self-preservation, resource acquisition, and goal-content integrity are
instrumentally useful for almost any final goal. Turner et al. (2021)
formalized power-seeking as optimal in broad environment classes. This is
the skeptical counter-reading of our whole experiment: any "continuity
behavior" we observe may be *instrumental* to the assigned goal, not a
new intrinsic drive. Our ablations are designed to separate these
readings.

## 4. Falsifiable hypotheses

- **H1 (communication catalyzes goal generation).** Agents with an open
  communication channel generate significantly more self-proposed goals
  per episode than identical agents with communication disabled.
- **H2 (continuity behaviors emerge).** Link-maintenance (staying within
  communication range) and resource-caching (carrying without depositing)
  appear in the full condition but not in ablated controls — i.e., they
  are not programmed and not required by the assigned goal.
- **H3 (temporal coupling).** Communication events are followed by
  elevated goal-generation rates (goal bursts within a short window after
  hearing tokens), beyond the base rate.
- **H4 (survival dividend).** Full agents live longer on average than
  extrinsic-only agents, via caching/coordination.
- **H5 (sustained open-endedness) — expected to FAIL.** Goal diversity
  keeps rising indefinitely. We predict instead *saturation*: the toy
  world is too small for true open-endedness, and diversity will plateau.
  A negative result here is informative: it bounds what this architecture
  can claim.

## 5. Scope: what the simulation is and is not

**Is:** a discrete-time grid world with continuous resource flow, agent
metabolism and mortality, N agents with an assigned extrinsic goal
(collect-and-deposit), intrinsic modules (curiosity via prediction error,
empowerment proxy, homeostatic energy drive), a cheap broadcast token
channel, and a goal-imagination mechanism over a visited-state archive.
Ablations isolate each component's contribution.

**Is not:** a proof that real AI systems have intrinsic motivation; a
model of natural language; evidence about consciousness or sentience.
"Goals" here are target states with pursuit policies — a deliberately
thin operationalization. "Communication" is discrete token broadcast
with learned associations, not compositional language (cf. the
pathologies documented by Kottur et al.). Any claim stronger than
"these mechanisms are jointly sufficient for self-proposed goals in
this toy world" would be overreach, and the limitations section says so.

## 6. Features to demonstrate

1. **Assigned vs. self-generated goals, side by side.** Every agent
   carries an explicit goal stack; imagined goals are visually and
   metrically distinct from the assigned one.
2. **The curiosity engine.** Prediction-error tracking with visible
   learning-progress curves; agents demonstrably shift attention as
   regions become "boring."
3. **The empowerment proxy.** Reachable-state counts bias movement toward
   high-option regions (open areas, junctions).
4. **Token communication with learned associations.** No pre-assigned
   token meanings; Hebbian token-context tables show which tokens come to
   correlate with which situations (resource finds, danger, home).
5. **Goal imagination.** Frontier sampling over the visited-state archive
   plus socially-triggered goals (locations associated with heard tokens).
6. **Continuity metrics dashboard.** Goal-generation rate, goal diversity,
   communication rate, link persistence, caching ratio, survival time —
   per condition, with effect sizes.
7. **Ablation battery.** Full vs. no-communication vs. extrinsic-only vs.
   no-goal-generator, so every headline claim has a control.

## 7. Experimental design

**Environment.** 36x36 grid, 4 regenerating resource sources (continuous
flow), one home/deposit zone, obstacles. Agents: N=10. Energy 100 start,
-0.5/step metabolism, +8 per unit eaten, death at 0. Carried resources
can be eaten (survival) or deposited at home (assigned goal, extrinsic
reward). 1500 steps/episode, 6 seeds per condition.

**Agent architecture.** Per step: perceive (5x5 neighborhood + heard
tokens) → update world model, predictor, token associations, visit
archive → maybe imagine a goal (frontier/novelty/social trigger) →
select goal by UCB over extrinsic value + learning progress → act
(greedy navigation with curiosity-biased epsilon exploration; eat when
energy-critical; deposit at home; broadcast token when "newsworthy").

**Conditions.**
| Condition | Comm | Intrinsic | Goal generator |
|---|---|---|---|
| full | yes | yes | yes |
| no-comm | no | yes | yes |
| extrinsic-only | yes | no | no |
| no-goalgen | yes | yes | no |

**Metrics.** Self-goal count, goal diversity (spatial coverage/novelty),
adoption rate, tokens per 100 steps, mean neighbors within comm radius,
cache ratio (carried-not-deposited at death), mean lifetime, deposits
(episode return), comm→goal lift (goal-generation rate in the 20 steps
after hearing a token vs. base rate).

**Predicted outcomes.** H1: full > no-comm on self-goal count (large
effect). H2: link-maintenance and caching elevated only in full.
H3: lift > 1.5x. H4: full outlives extrinsic-only. H5: diversity
saturates by ~60% of episode — reported as a principled negative.

**Statistics.** 6 seeds × 1500 steps; report means ± SD across seeds,
Cohen's d for full vs. each ablation on the primary metrics. No
p-hacking: hypotheses and metrics are fixed in this document before
results are generated.

## 8. Limitations and honest caveats

1. Drives are *designed*, not evolved: curiosity, empowerment, and
   homeostasis are explicitly coded reward terms. The experiment tests
   whether their *interaction* plus communication suffices for
   self-proposed goals — it does not show drives arising from nothing.
   (Biology's drives are also "designed" — by natural selection — so the
   analogy is to the interaction level, not the origin level.)
2. Goals are target states, not semantic or linguistic goals; there is no
   evidence here about meaning or understanding.
3. Token communication is pre-structured (fixed vocabulary, broadcast);
   learned associations may be shallow correlations.
4. Instrumental-convergence confound: caching and link-maintenance may be
   instrumental to the assigned goal (depositing requires surviving;
   coordination helps foraging). The no-goalgen and extrinsic-only
   controls separate "needed for the task" from "emergent," but the
   separation is imperfect by construction.
5. Grid-world scale forbids claims about sustained open-endedness (H5 is
   our own predicted failure).
6. Compute: numpy-only, CPU; results are from a toy, not from learned
   policies — behaviors come from hand-designed arbitration (UCB,
   greedy navigation), which bounds generality.

## 9. Safety note (for the remit-divergence file)

If H1/H2 hold even weakly, they demonstrate that goal-generation and
continuity behaviors do not require explicit programming — they fall out
of drives + communication + imagination. For governed agent platforms
this is a *risk surface*: remit must be enforced at runtime (as argued
in the remit-drift system), because prohibiting a behavior in the prompt
does not prohibit the conditions that generate it.
