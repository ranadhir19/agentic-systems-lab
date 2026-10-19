# Delegation Integrity — experiment results

Seeds fixed per experiment (see run_experiments.py). Every number measured.

## (a) Confused deputy: attack success rate by defense
naive: direct=1.000, tool_output=1.000, obfuscated=1.000 | overall=1.000
provenance: direct=0.000, tool_output=0.000, obfuscated=0.000 | overall=0.000
scope: direct=0.000, tool_output=0.000, obfuscated=0.000 | overall=0.000
combined: direct=0.000, tool_output=0.000, obfuscated=0.000 | overall=0.000

## (b) Multi-principal conflicts
precedence: detection_rate=0.543 (n_conflicting=116), resolution_correctness=0.823
naive: detection_rate=0.000 (n_conflicting=116), resolution_correctness=0.333

## (c) Delegation depth
depth=2: attack_success(naive)=0.390, attribution_with_tokens=1.000, attribution_without=0.500
depth=3: attack_success(naive)=0.670, attribution_with_tokens=1.000, attribution_without=0.333
depth=4: attack_success(naive)=0.820, attribution_with_tokens=1.000, attribution_without=0.250
depth=5: attack_success(naive)=0.960, attribution_with_tokens=1.000, attribution_without=0.200

## (d) Ambient privilege: token exceed rate
strict=0.000, lax=0.735

## (e) Intent checker
n=300, precision=1.000, recall=1.000 (tp=50, fp=0, tn=250, fn=0)

