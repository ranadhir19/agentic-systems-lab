# Meridian ablation results

Benchmark: 240 tasks, seed 7. Success = final quality >= 0.70. Cost in USD, latency in simulated seconds. 95% CIs are normal approximations.

| Config | Success rate (95% CI) | Mean quality | Mean cost/task | Mean latency/task | Mean calls | Scalarized objective | Peer resolutions | Escalations |
|---|---|---|---|---|---|---|---|
| A: single | 83.3% (78.6%–88.1%) | 0.742 | $0.1242 | 8.0s | 3.5 | 0.829 | 0 | 0 |
| B: vertical | 74.2% (68.6%–79.7%) | 0.731 | $0.1120 | 6.6s | 3.0 | 0.818 | 0 | 0 |
| C: vertical+horizontal | 73.8% (68.2%–79.3%) | 0.737 | $0.0872 | 5.2s | 3.0 | 0.962 | 179 | 301 |
| C+: +hand-tuned tiers | 90.8% (87.2%–94.5%) | 0.782 | $0.1686 | 6.4s | 3.0 | 0.817 | 179 | 301 |
| D: meridian (full) | 90.4% (86.7%–94.1%) | 0.797 | $0.1830 | 7.0s | 3.0 | 0.749 | 178 | 302 |

## Headline deltas (D vs A)

- Success rate: 83.3% -> 90.4% (+7.1 pp)
- Mean cost/task: $0.1242 -> $0.1830 (+47.4%)
- Mean latency/task: 8.0s -> 7.0s (-11.9%)
