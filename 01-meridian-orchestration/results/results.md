# Meridian ablation results

Benchmark: 240 tasks, seed 7. Success = final quality >= 0.70. Cost in USD, latency in simulated seconds. 95% CIs are normal approximations.

| Config | Success rate (95% CI) | Mean quality | Mean cost/task | Mean latency/task | Mean calls | Scalarized objective | Peer resolutions | Escalations |
|---|---|---|---|---|---|---|---|
| A: single | 80.4% (75.4%–85.4%) | 0.742 | $0.1244 | 8.1s | 3.5 | 0.794 | 0 | 0 |
| B: vertical | 70.8% (65.1%–76.6%) | 0.723 | $0.1125 | 6.8s | 3.0 | 0.768 | 0 | 0 |
| C: vertical+horizontal | 74.2% (68.6%–79.7%) | 0.732 | $0.0882 | 5.5s | 3.0 | 0.951 | 175 | 305 |
| C+: +hand-tuned tiers | 88.8% (84.7%–92.8%) | 0.779 | $0.1683 | 6.5s | 3.0 | 0.789 | 180 | 300 |
| D: meridian (full) | 89.6% (85.7%–93.5%) | 0.791 | $0.1794 | 7.0s | 3.0 | 0.749 | 177 | 303 |

## Headline deltas (D vs A)

- Success rate: 80.4% -> 89.6% (+9.2 pp)
- Mean cost/task: $0.1244 -> $0.1794 (+44.3%)
- Mean latency/task: 8.1s -> 7.0s (-13.4%)
