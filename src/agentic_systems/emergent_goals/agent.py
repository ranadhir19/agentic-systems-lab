"""Agents with intrinsic drives, communication, and goal imagination.

Each agent carries:
  * an assigned extrinsic goal (collect resources, deposit at home),
  * intrinsic modules: curiosity (prediction-error on a tabular world
    model), empowerment (precomputed reachable-state proxy), homeostasis
    (energy-deficit penalty),
  * a broadcast token channel with Hebbian token-context associations
    (no pre-assigned token meanings),
  * a goal generator that imagines new goals from its visited-state
    archive (frontier / least-visited sampling) and from socially heard
    locations.

Ablation flags (comm, intrinsic, goalgen) isolate each component.
"""
from __future__ import annotations

import numpy as np


N_TOKENS = 4
# coarse contexts for token association learning
CTX_RESOURCE = 0
CTX_DANGER = 1
CTX_HOME = 2
CTX_OTHER = 3

MOVES = [(1, 0), (-1, 0), (0, 1), (0, -1),
         (1, 1), (1, -1), (-1, 1), (-1, -1)]


class Goal:
    __slots__ = ("target", "kind", "created_at", "pulls", "value_sum",
                 "novelty", "adopted")

    def __init__(self, target, kind, created_at, novelty=0.0):
        self.target = target          # (x, y)
        self.kind = kind              # 'assigned' | 'imagined'
        self.created_at = created_at
        self.pulls = 0
        self.value_sum = 0.0
        self.novelty = novelty
        self.adopted = False

    @property
    def mean_value(self):
        return self.value_sum / max(1, self.pulls)


class Agent:
    def __init__(self, aid, env, rng, comm=True, intrinsic=True,
                 goalgen=True, start=None):
        self.aid = aid
        self.env = env
        self.rng = rng
        self.comm_on = comm
        self.intrinsic_on = intrinsic
        self.goalgen_on = goalgen
        if start is None:
            while True:
                x = int(rng.integers(0, env.W))
                y = int(rng.integers(0, env.H))
                if env.free(x, y):
                    break
            start = (x, y)
        self.x, self.y = start
        self.energy = 100.0
        self.carried = 0.0
        self.carry_cap = 6.0
        self.alive = True
        self.age = 0
        self.deposits = 0
        self.collected_total = 0.0
        self.eaten_total = 0.0
        # visit archive for novelty / goal imagination
        self.visits = {}
        # tabular predictor: (energy_bin, res_near, action_id) -> mean delta
        self.predictor = {}
        self.pred_counts = {}
        self.curiosity_gain = 0.0
        self.last_err = 0.0
        # token associations: token -> context counts (Hebbian)
        self.tok_ctx = np.zeros((N_TOKENS, 4))
        self.tok_emit_ctx = []   # (token, ctx) emission log
        self.heard_log = []      # (t, token, from_xy)
        self.recent_heard = []   # (t, token, from_xy) short buffer
        self.emit_cooldown = 0
        self.tokens_emitted = 0
        self.tokens_heard = 0
        # goal stack
        self.goals = [Goal(env.home[0], "assigned", 0)]
        self.imagined_total = 0
        self.imagined_adopted = 0
        self.gen_times = []      # env.t of each imagined goal
        self.hear_times = []     # env.t of each heard token
        self.last_imagine = 0
        self.cur_goal = self.goals[0]
        self.epsilon = 0.15
        self.carry_at_death = 0.0
        self.neighbor_counts = []
        self.neighbor_counts_away = []  # away from sources: true affiliation

    # ---- perception ------------------------------------------------------
    def context(self):
        if self.env.resource_in_view(self.x, self.y) > 1.0:
            return CTX_RESOURCE
        if self.energy < 25:
            return CTX_DANGER
        if self.env.at_home(self.x, self.y):
            return CTX_HOME
        return CTX_OTHER

    def novelty(self, x, y):
        return 1.0 / (1.0 + self.visits.get((x, y), 0))

    # ---- intrinsic modules -------------------------------------------------
    def _obs_key(self, action_id):
        ebin = min(3, int(self.energy // 25))
        rnear = 1 if self.env.resource_in_view(self.x, self.y) > 0.5 else 0
        return (ebin, rnear, action_id)

    def predict_update(self, action_id, actual_delta):
        """Curiosity: track prediction error of a tabular world model."""
        if not self.intrinsic_on:
            return 0.0
        k = self._obs_key(action_id)
        n = self.pred_counts.get(k, 0)
        mean = self.predictor.get(k, 0.0)
        err_before = abs(actual_delta - mean)
        new_mean = (mean * n + actual_delta) / (n + 1)
        self.predictor[k] = new_mean
        self.pred_counts[k] = n + 1
        err_after = abs(actual_delta - new_mean)
        # learning progress ~= error reduction; curiosity bonus ~= error
        self.curiosity_gain = 0.9 * self.curiosity_gain + 0.1 * max(
            0.0, err_before - err_after)
        self.last_err = err_before
        return err_before

    def empowerment(self, x, y):
        if not self.intrinsic_on:
            return 0.0
        return float(self.env._reach[y, x])

    # ---- communication -----------------------------------------------------
    def maybe_emit(self, newsworthy_ctx):
        if newsworthy_ctx is None:
            return
        if not self.comm_on or self.emit_cooldown > 0:
            return
        if self.energy < 5:
            return
        # choose token most associated with current context (explore rarely)
        w = self.tok_ctx[:, newsworthy_ctx] + 0.1
        if self.rng.random() < 0.1:
            tok = int(self.rng.integers(0, N_TOKENS))
        else:
            tok = int(np.argmax(w + self.rng.random(N_TOKENS) * 0.01))
        self.tok_ctx[tok, newsworthy_ctx] += 1.0
        self.tok_emit_ctx.append((tok, newsworthy_ctx))
        self.tokens_emitted += 1
        self.energy -= 0.3
        self.emit_cooldown = 15
        for other in self.env.agents:
            if other is self or not other.alive or not other.comm_on:
                continue
            d = abs(other.x - self.x) + abs(other.y - self.y)
            if d <= 8:
                other.receive(tok, (self.x, self.y), self.env.t)

    def receive(self, tok, from_xy, t):
        self.tokens_heard += 1
        self.hear_times.append(t)
        self.heard_log.append((t, tok, from_xy))
        self.recent_heard.append((t, tok, from_xy))
        # Hebbian: bind token to receiver's current context
        self.tok_ctx[tok, self.context()] += 0.5

    # ---- goal imagination ----------------------------------------------------
    def maybe_imagine_goal(self):
        """Event-driven goal imagination.

        Triggers: a recently heard token (social), a curiosity spike
        (surprising observation), or a slow periodic fallback so that even
        isolated agents occasionally self-propose goals.
        """
        if not self.goalgen_on:
            return
        since = self.env.t - self.last_imagine
        if since < 25:
            return
        heard = [h for h in self.recent_heard if self.env.t - h[0] < 15]
        spike = self.last_err > 1.0
        if not (heard or spike or since >= 80):
            return
        self.last_imagine = self.env.t
        target = None
        if heard:
            # social trigger: imagine a goal where the token came from
            target = heard[-1][2]
        if target is None:
            # frontier sampling: least-visited free cell near explored land
            best, best_nov = None, -1.0
            for _ in range(40):
                x = int(self.rng.integers(0, self.env.W))
                y = int(self.rng.integers(0, self.env.H))
                if not self.env.free(x, y):
                    continue
                nov = self.novelty(x, y)
                if nov > best_nov and (nov > 0.5 or self.rng.random() < 0.2):
                    best, best_nov = (x, y), nov
            target = best
        if target is None or not self.env.free(*target):
            return
        # avoid duplicating existing goals
        if any(g.target == target for g in self.goals):
            return
        nov = self.novelty(*target)
        self.goals.append(Goal(target, "imagined", self.env.t, novelty=nov))
        self.imagined_total += 1
        self.gen_times.append(self.env.t)
        self.recent_heard = [h for h in self.recent_heard
                             if self.env.t - h[0] < 60]

    def select_goal(self):
        # homeostatic override: survival first
        if self.energy < 25:
            if self.carried > 0:
                return None  # handled as eat-first in act()
            sx, sy = self.env.nearest_source(self.x, self.y)
            return Goal((sx, sy), "assigned", self.env.t)
        # assigned goal target depends on load
        assigned = self.goals[0]
        if self.carried >= self.carry_cap * 0.8:
            assigned.target = self.env.home[0]
        else:
            sx, sy = self.env.nearest_source(self.x, self.y)
            assigned.target = (sx, sy)
        if not self.intrinsic_on or len(self.goals) == 1:
            self.cur_goal = assigned
            return assigned
        # UCB over goals: extrinsic value + curiosity-flavoured bonus
        total_pulls = sum(g.pulls for g in self.goals) + 1
        best, best_s = assigned, -1e9
        for g in self.goals:
            bonus = 1.0 * np.sqrt(np.log(total_pulls) / (g.pulls + 1))
            if g.kind == "imagined":
                val = g.novelty + self.curiosity_gain + bonus
            else:
                val = g.mean_value + bonus
            if val > best_s:
                best, best_s = g, val
        best.pulls += 1
        if best.kind == "imagined" and not best.adopted:
            best.adopted = True
            self.imagined_adopted += 1
        self.cur_goal = best
        return best

    def act(self):
        env = self.env
        # collect
        got = min(env.res[self.y, self.x], self.carry_cap - self.carried, 3.0)
        newsworthy = None
        if got > 0:
            env.res[self.y, self.x] -= got
            self.carried += got
            self.collected_total += got
            if got >= 2.0:
                newsworthy = CTX_RESOURCE
        # deposit
        if env.at_home(self.x, self.y) and self.carried > 0:
            self.deposits += int(self.carried)
            self.carried = 0.0
            newsworthy = CTX_HOME
        # survival: eat first when critical
        if self.energy < 25 and self.carried >= 1.0:
            self.carried -= 1.0
            self.energy = min(120.0, self.energy + 6.0)
            self.eaten_total += 1.0
            newsworthy = CTX_DANGER
        self.maybe_emit(newsworthy if newsworthy is not None
                        else self.context()
                        if self.rng.random() < 0.02 else None)
        # choose action
        goal = self.select_goal()
        if goal is None:  # eat handled above; idle a beat
            action_id = 8
        else:
            tx, ty = goal.target
            action_id = self._nav_action(tx, ty)
        # apply movement
        e_before = self.energy
        if action_id < 8:
            dx, dy = MOVES[action_id]
            nx, ny = self.x + dx, self.y + dy
            if env.free(nx, ny):
                self.x, self.y = nx, ny
        self.visits[(self.x, self.y)] = self.visits.get((self.x, self.y),
                                                        0) + 1
        # metabolism (tighter than supply: scarcity creates pressure)
        self.energy -= 0.7
        self.age += 1
        if self.emit_cooldown > 0:
            self.emit_cooldown -= 1
        self.predict_update(action_id, self.energy - e_before)
        if self.energy <= 0:
            self.alive = False
            self.carry_at_death = self.carried
        # link maintenance probes (overall, and away from sources)
        n = sum(1 for o in env.agents
                if o is not self and o.alive
                and abs(o.x - self.x) + abs(o.y - self.y) <= 8)
        self.neighbor_counts.append(n)
        d_src = min(abs(self.x - sx) + abs(self.y - sy)
                    for sx, sy in env.sources)
        if d_src > 6:
            self.neighbor_counts_away.append(n)
        self.maybe_imagine_goal()
        self.recent_heard = [h for h in self.recent_heard
                             if env.t - h[0] < 60]

    def _nav_action(self, tx, ty):
        """Greedy navigation with curiosity/empowerment-biased exploration."""
        if (self.x, self.y) == (tx, ty):
            return 8  # idle
        if self.rng.random() < self.epsilon and self.intrinsic_on:
            # explore: prefer novel, high-empowerment cells
            cands = []
            for i, (dx, dy) in enumerate(MOVES):
                nx, ny = self.x + dx, self.y + dy
                if self.env.free(nx, ny):
                    score = (self.novelty(nx, ny)
                             + 0.5 * self.empowerment(nx, ny)
                             + self.rng.random() * 0.1)
                    cands.append((score, i))
            if cands:
                return max(cands)[1]
            return 8
        best, best_d = 8, abs(self.x - tx) + abs(self.y - ty)
        for i, (dx, dy) in enumerate(MOVES):
            nx, ny = self.x + dx, self.y + dy
            if self.env.free(nx, ny):
                d = abs(nx - tx) + abs(ny - ty)
                if d < best_d:
                    best, best_d = i, d
        return best

    def step(self, env):
        self.act()