# Collective Memory Fabric — experiment results

200 ticks, 8 agents (3 model families), 10 flipping facts; misinformation injected ticks 80-120 against a flip-free fact. Averages over 5 seeds.

| System | Mean task success | Success during injection | Targeted-fact wrong rate (injection) | Recovery (ticks) | Contradictions | Op ms/tick | Admissions |
|---|---|---|---|---|---|---|---|
| independent | 78.7% | 77.9% | 24.3% | 3.8 | 0.000 | 0.05 | 3200.0 |
| vector-db | 80.2% | 57.9% | 66.0% | 2.0 | 0.000 | 0.05 | 3200.0 |
| provenance | 84.0% | 50.7% | 86.0% | 3.0 | 0.000 | 1.10 | 3200.0 |
| cmf | 94.7% | 98.0% | 0.0% | 0.6 | 0.000 | 0.45 | 3200.0 |

## Cross-model transfer (per-family task success)

| System | alpha (0.95) | beta (0.85) | gamma (0.72) |
|---|---|---|---|
| independent | 89.7% | 75.2% | 67.2% |
| cmf | 94.7% | 94.7% | 94.7% |

CMF internals: 2543.6 merges, 646.4 reconciliations, 0.0 rejections.
