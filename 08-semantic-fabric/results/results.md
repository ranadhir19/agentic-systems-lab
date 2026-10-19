# Semantic Fabric experiment results

Seed 7; 10000 txns, 300 incidents, 400 tickets, 600 users.

## A — semantic compression (raw bytes : artifact bytes)

Raw transactions: 1974056 bytes; all semantic artifacts: 72495 bytes; overall compression **27.2:1**.

| Layer | Artifact bytes | Compression |
|---|---|---|
| L0 | 754 | 2618.1:1 |
| L1 | 1137 | 1736.2:1 |
| L2 | 13101 | 150.7:1 |
| L3 | 641 | 3079.7:1 |
| L4 | 397 | 4972.4:1 |
| L5 | 819 | 2410.3:1 |
| L6 | 55049 | 35.9:1 |
| L7 | 597 | 3306.6:1 |

## B — extraction quality vs ground truth

| Check | Result |
|---|---|
| L0_entities | {'recovered': ['server', 'txn', 'user'], 'expected': ['txn', 'user', 'server'], 'recall': 1.0} |
| L0_relations | {'n_found': 4, 'txn_user_found': True, 'txn_server_found': True} |
| L1_determinism | True |
| L1_amount_mean | 41.76 |
| L2_ARI | 0.546 |
| L3_hot_recall | 1.0 |
| L3_n_edges | 6 |
| L4_period_ok | True |
| L4_cascade_ok | True |
| L5_precision | 0.75 |
| L5_recall | 1.0 |
| L5_found | [('latency_ms', 'error'), ('queue_depth', 'latency_ms'), ('server_load', 'error'), ('server_load', 'queue_depth')] |
| L6_accuracy | 1.0 |
| L7_boundary_motif | True |
| L7_top_support | 110 |

## C — reasoning agreement (fabric vs raw data)

| Query | Fabric | Raw | Agree |
|---|---|---|---|
| impacting_servers | ['srv11', 'srv03'] | ['srv11', 'srv03'] | True |
| root_cause | queue_depth | queue_depth | True |
| what_if_sign | {'fabric_effect': 1.712, 'raw_effect': 1.905, 'agree': True} | — | True |
| markov_next | checkout | checkout | True |

Overall agreement: **1.0**

## D — freshness

False-positive rate on stationary stream (L1): **0.0**

| Shift (std) | Detection latency (batches) |
|---|---|
| 0.5 | 3 |
| 1.0 | 1 |
| 2.0 | 1 |
| 3.0 | 1 |

L2 behavior-change verdict: {'layer': 'L2', 'score': 0.35, 'threshold': 0.3, 'drifted': True}

## E — ablation (query accuracy)

| Configuration | Accuracy |
|---|---|
| full | 1.0 |
| no_L2 | 0.75 |
| no_L3 | 0.75 |
| no_L5 | 0.5 |
