# HealFlow experiment results

## Phase 1 — fault battery

| Scenario | System | Success | Graceful | Side effects | Tool calls | Diagnosis correct | Repairs |
|---|---|---|---|---|---|---|---|
| order: transient payment outage | healflow | True | False | 0 | 4 | True | retry,retry |
| order: transient payment outage | healflow-no-mem | True | False | 0 | 4 | True | retry,retry |
| order: transient payment outage | retry | True | False | 0 | 4 | None |  |
| order: transient payment outage | replan | True | False | 0 | 6 | None |  |
| order: inventory permanently down | healflow | False | True | 0 | 3 | True | retry,retry,compensate_abort |
| order: inventory permanently down | healflow-no-mem | False | True | 0 | 3 | True | retry,retry,compensate_abort |
| order: inventory permanently down | retry | False | False | 1 | 2 | None |  |
| order: inventory permanently down | replan | False | False | 3 | 6 | None |  |
| etl: transient extract outage | healflow | True | False | 0 | 3 | True | retry,retry |
| etl: transient extract outage | healflow-no-mem | True | False | 0 | 3 | True | retry,retry |
| etl: transient extract outage | retry | True | False | 0 | 3 | None |  |
| etl: transient extract outage | replan | True | False | 0 | 3 | None |  |
| etl: upstream schema change | healflow | True | False | 0 | 4 | True | substitute |
| etl: upstream schema change | healflow-no-mem | True | False | 0 | 4 | True | substitute |
| etl: upstream schema change | retry | False | False | 0 | 4 | None |  |
| etl: upstream schema change | replan | False | False | 0 | 6 | None |  |
| research: corrupted plan (permanent) | healflow | True | False | 0 | 5 | True | rollback_recompute,substitute |
| research: corrupted plan (permanent) | healflow-no-mem | True | False | 0 | 5 | True | rollback_recompute,substitute |
| research: corrupted plan (permanent) | retry | False | False | 0 | 3 | None |  |
| research: corrupted plan (permanent) | replan | False | False | 0 | 3 | None |  |
| research: search schema change | healflow | True | False | 0 | 4 | True | substitute |
| research: search schema change | healflow-no-mem | True | False | 0 | 4 | True | substitute |
| research: search schema change | retry | False | False | 0 | 4 | None |  |
| research: search schema change | replan | False | False | 0 | 6 | None |  |

## Phase 2 — repair-memory transfer

| | With memory | Without memory |
|---|---|---|
| Diagnosis steps | 1 | 2 |
| Memory hits | 1 | — |
| Success | True | True |
| Tool calls | 4 | 4 |
