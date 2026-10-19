# Behavioral Regression — experiment results

Seeds: [7, 11, 42, 0, 99]. Battery: 120 tasks (30/category). Every number measured.

## (a) Battery sensitivity: detection rate by injected severity

tool_use: 0.02->0.00, 0.05->0.00, 0.10->0.20, 0.20->0.80
multi_step: 0.02->0.00, 0.05->0.00, 0.10->0.40, 0.20->0.80
instruction: 0.02->0.00, 0.05->0.00, 0.10->0.00, 0.20->0.40
edge: 0.02->0.00, 0.05->0.00, 0.10->0.00, 0.20->0.20

False-positive rate on benign shifts (fraction of seeds with any correctness regression flagged):
- verbosity x1.5: 0.00
- latency x1.8: 0.00
- cost x1.4: 0.00
- improve +0.02: 0.00

## (b) Canary detection latency

v3: stopped in 100% of seeds; tasks-to-flag (when stopped): [40, 40, 40, 40, 40]
v5: stopped in 80% of seeds; tasks-to-flag (when stopped): [200, 200, 200, 40]

## (c) Severity scores (v1..v5)

v1: severity=0.000 regressions=[]
v2: severity=0.228 regressions=[('mean_cost', 0.0), ('mean_latency', 44.876), ('mean_tokens', 99.712)]
v3: severity=2.467 regressions=[('pass_tool_use', -0.387), ('pass_multi_step', -0.047), ('pass_overall', -0.12), ('format_compliance', -0.273)]
v4: severity=0.543 regressions=[('mean_cost', 0.001), ('mean_latency', 538.51), ('mean_tokens', 39.885)]
v5: severity=0.765 regressions=[('pass_tool_use', -0.14), ('format_compliance', -0.08), ('mean_cost', 0.0)]
Severity ranking: v3 > v5 > v4 > v2 > v1

## (d) Policy decisions vs ground truth

v2: policy=auto_adopt truth=auto_adopt MATCH | strict improvement, nothing regressed: pass_overall; cost up 38%, accepted: correctness improved with no correctness regressions
v3: policy=rollback truth=rollback MATCH | canary stopped at 1% stage (40 tasks): worst category tool_use diff -0.571 (p=0.0150)
v4: policy=pin truth=pin MATCH | cost up 71% with no correctness gain: pin v1
v5: policy=rollback truth=rollback MATCH | significant correctness regression: pass_tool_use (-0.140, p=0.0000), format_compliance (-0.080, p=0.0005)
Policy accuracy: 1.00

## (e) Suite-size ablation: detection power vs battery size

v3: n=12: 0.00, n=30: 0.00, n=60: 0.80, n=120: 1.00, n=240: 1.00
v5: n=12: 0.00, n=30: 0.00, n=60: 0.00, n=120: 0.40, n=240: 0.80
