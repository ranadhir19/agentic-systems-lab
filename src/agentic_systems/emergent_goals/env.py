"""Resource-flow environment with agent metabolism and mortality.

A 2D grid world with continuously regenerating resource sources (the
"continuous data/resource flow"), diffusive resource spread, one home /
deposit zone, static obstacles, and per-agent energy dynamics. Energy
decays every step (metabolism); agents replenish it by eating carried
resources and earn extrinsic reward by depositing at home. Energy at
zero means death.
"""
from __future__ import annotations

from collections import deque

import numpy as np


class ResourceFlowEnv:
    def __init__(self, width=36, height=36, n_sources=4, seed=0):
        self.rng = np.random.default_rng(seed)
        self.W = width
        self.H = height
        self.obstacles = np.zeros((height, width), dtype=bool)
        self._place_obstacles()
        self.home = self._place_home()
        self.sources = self._place_sources(n_sources)
        self.res = np.zeros((height, width), dtype=float)
        self.source_cap = 20.0
        self.source_regen = 2.5
        self.diffusion = 0.05
        self.agents = []
        self.t = 0
        # empowerment proxy: reachable cells within K steps (static topology)
        self._reach = self._precompute_reachability(depth=4)

    # ---- world construction ------------------------------------------------
    def _place_obstacles(self):
        # a few wall segments; kept clear of borders so connectivity holds
        walls = [
            ((8, 8), (8, 16)),
            ((24, 20), (24, 30)),
            ((14, 26), (22, 26)),
        ]
        for (x0, y0), (x1, y1) in walls:
            for x in range(min(x0, x1), max(x0, x1) + 1):
                for y in range(min(y0, y1), max(y0, y1) + 1):
                    self.obstacles[y, x] = True

    def _place_home(self):
        # 4x4 home zone near bottom-left, on free cells
        hx, hy = 2, self.H - 6
        zone = [(hx + dx, hy + dy) for dx in range(4) for dy in range(4)]
        assert all(not self.obstacles[y, x] for x, y in zone)
        return zone

    def _place_sources(self, n):
        cands = [(30, 4), (6, 6), (30, 30), (16, 14)]
        srcs = []
        for x, y in cands[:n]:
            assert not self.obstacles[y, x]
            srcs.append((x, y))
        return srcs

    def _precompute_reachability(self, depth=4):
        """Reachable-cell counts within `depth` steps for every free cell.

        Static topology -> computed once. Used as the empowerment proxy:
        states with more reachable futures afford more options.
        """
        reach = np.zeros((self.H, self.W), dtype=float)
        for y in range(self.H):
            for x in range(self.W):
                if self.obstacles[y, x]:
                    continue
                seen = {(x, y)}
                frontier = deque([(x, y, 0)])
                while frontier:
                    cx, cy, d = frontier.popleft()
                    if d == depth:
                        continue
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < self.W and 0 <= ny < self.H
                                and not self.obstacles[ny, nx]
                                and (nx, ny) not in seen):
                            seen.add((nx, ny))
                            frontier.append((nx, ny, d + 1))
                reach[y, x] = len(seen)
        reach /= reach.max()
        return reach

    # ---- dynamics ----------------------------------------------------------
    def free(self, x, y):
        return (0 <= x < self.W and 0 <= y < self.H
                and not self.obstacles[y, x])

    def step_resources(self):
        for x, y in self.sources:
            self.res[y, x] = min(self.source_cap,
                                 self.res[y, x] + self.source_regen)
        # diffusive flow: a fraction spreads to von-Neumann neighbours
        r = self.res
        flow = np.zeros_like(r)
        flow[1:, :] += self.diffusion * r[:-1, :]
        flow[:-1, :] += self.diffusion * r[1:, :]
        flow[:, 1:] += self.diffusion * r[:, :-1]
        flow[:, :-1] += self.diffusion * r[:, 1:]
        kept = 1.0 - 4 * self.diffusion
        self.res = r * kept + flow
        self.res[self.obstacles] = 0.0

    def add_agent(self, agent):
        self.agents.append(agent)

    def alive_agents(self):
        return [a for a in self.agents if a.alive]

    def step(self):
        self.step_resources()
        self.t += 1
        for a in list(self.agents):
            if a.alive:
                a.step(self)

    def resource_in_view(self, x, y, radius=2):
        x0, x1 = max(0, x - radius), min(self.W, x + radius + 1)
        y0, y1 = max(0, y - radius), min(self.H, y + radius + 1)
        return self.res[y0:y1, x0:x1].sum()

    def nearest_source(self, x, y):
        d = [abs(x - sx) + abs(y - sy) for sx, sy in self.sources]
        return self.sources[int(np.argmin(d))]

    def at_home(self, x, y):
        return (x, y) in self.home
