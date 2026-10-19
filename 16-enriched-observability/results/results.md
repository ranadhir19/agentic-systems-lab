# Enriched Observability — experiment results

Seeds: [7, 11, 42, 0, 99]. Every number measured.

## (a) Cascade end-to-end
Mean detection delay per layer (min): {'infra': 0.8, 'platform': 17.0, 'application': 3.0, 'sre': 4.6, 'business': 1.6}
Mean chain link recall: 1.0
Mean onset MAE (min): 5.5
Mean pipeline wall time (s): 0.271

## (b) Anomaly detection: robust vs naive (per-minute P/R)

infra: robust P=0.963 R=0.909 | naive P=0.679 R=0.345
platform: robust P=0.579 R=0.413 | naive P=0.704 R=0.545
application: robust P=0.917 R=0.908 | naive P=0.105 R=0.448
sre: robust P=0.801 R=0.914 | naive P=0.0 R=0.0
business: robust P=0.725 R=0.368 | naive P=0.447 R=0.976

## (c) Forecasting time-to-breach (at onset+10)
n=16, MAE=3.4 min

## (d) Cross-layer links
Mean link recall: 1.0, mean spurious links: 0.0

## (e) Role-view relevance (rubric 0..1)
Enriched: {'cto': 1.0, 'sre_director': 1.0, 'devops_lead': 1.0, 'eng_manager': 1.0, 'engineer': 1.0}
Raw dump baseline: {'cto': 0.8, 'sre_director': 0.8, 'devops_lead': 0.8, 'eng_manager': 0.9, 'engineer': 0.8}

## (f) Triage proxy
Mean raw alerts: 18.2, mean enriched chain items: 5.0
