# SRE-Observability — experiment results

Seeds 0-4; one simulated day (1440 min) per seed; 8 intra-layer + 3 cascading incidents per day.

## (a) The boundary problem, quantified

| layer | segment recall | F1 | mean time-to-detect (min) |
|---|---|---|---|
| infra | 1.00 +/- 0.00 | 0.89 +/- 0.04 | 1.8 +/- 1.6 |
| network | 1.00 +/- 0.00 | 0.87 +/- 0.05 | 1.4 +/- 0.4 |
| platform | 0.96 +/- 0.08 | 0.82 +/- 0.09 | 1.5 +/- 1.0 |
| app | 0.96 +/- 0.08 | 0.77 +/- 0.02 | 1.4 +/- 0.4 |
| service | 0.95 +/- 0.10 | 0.84 +/- 0.12 | 1.1 +/- 0.1 |
| product | 0.60 +/- 0.37 | 0.44 +/- 0.30 | 7.0 +/- 5.8 |

| boundary | crossing-link recall | F1 | mean link time (min) |
|---|---|---|---|
| infra->network | 1.00 +/- 0.00 | 0.73 +/- 0.33 | 10.8 +/- 3.0 |
| network->platform | 1.00 +/- 0.00 | 0.83 +/- 0.21 | 14.2 +/- 2.3 |
| platform->app | 1.00 +/- 0.00 | 0.85 +/- 0.18 | 12.7 +/- 2.3 |
| app->service | 0.90 +/- 0.20 | 0.73 +/- 0.23 | 13.7 +/- 3.6 |
| service->product | 0.00 +/- 0.00 | 0.00 +/- 0.00 | n/a (never linked) |

Mean intra-layer recall 0.91 vs mean boundary crossing-link recall 0.78. Intra-layer detection is fast (~1-2 min); boundary links lag (8-30 min) when they exist at all.

## (b) Weakest boundary identified from telemetry alone

| rank | boundary | gap (1 - F1) |
|---|---|---|
| 1 | service->product | 1.00 |
| 2 | infra->network | 0.67 |
| 3 | app->service | 0.50 |
| 4 | network->platform | 0.43 |
| 5 | platform->app | 0.40 |

## (c) Closed loop: targeted fix at the weakest boundary

service->product recall 0.00 -> 1.00; F1 0.00 -> 0.40. The fix (near-raw cross-layer stream, 2-min delay) turns the blind boundary into a leading indicator (link time -3.0 min, negative = visible before downstream onset).

## (d) Cascading incidents: siloed vs unified MAS response (n=15)

| mode | detection (min) | correct runbook | MTTR (min) |
|---|---|---|---|
| siloed | 0.9 +/- 0.3 | 73% | 102 +/- 24 |
| unified | 0.8 +/- 0.4 | 100% | 78 +/- 13 |

Siloed observers fragment cascades into partial contexts and pick layer-local runbooks; the unified context recognizes the cascade, chooses the cascade runbook, and triages faster.

## (e) Strategy bridge: reliability vs innovation frontier (budget $100k)

| reliability | innovation | initiatives |
|---|---|---|
| 11 | 20 | auto_remediation_runbooks, checkout_flow_revamp, ml_recommendations |
| 14 | 18 | auto_remediation_runbooks, developer_platform_upgrade, checkout_flow_revamp |
| 19 | 14 | boundary_observability_modules, auto_remediation_runbooks, checkout_flow_revamp |
| 27 | 6 | boundary_observability_modules, auto_remediation_runbooks, multiregion_failover |

Balanced recommendation (w=0.5): boundary_observability_modules, auto_remediation_runbooks, checkout_flow_revamp at $95k.

| scorecard | baseline quarter | with recommendation |
|---|---|---|
| downtime (min/qtr) | 320 | 80 |
| MTTR (min) | 58 | 23 |
| incident cost ($M) | 1.40 | 0.35 |
| strategic ROI | 1.00x | 2.26x |
| delivery velocity | 100 | 146 |
