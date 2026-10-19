# Leadership Insights — experiment results

Seed 7. All numbers from actual runs.

## (a) Metric accuracy vs ground truth

    team  true_mean_h  est_mean_h  rel_err
payments          8.6         9.9    0.150
checkout          8.3        10.1    0.217
  search          8.6        10.1    0.169
  mobile          7.6         9.9    0.295
platform         48.0        54.9    0.144
    data          6.9         8.4    0.213

Escalation rates: {'checkout-web esc_rate': 0.297, 'org esc_rate': 0.124}

## (b) Injected-issue recovery

- **bottleneck**: {'flagged': ['platform'], 'expected': ['platform'], 'hit': True, 'false_positives': []}
- **license_waste**: {'precision': 1.0, 'recall': 1.0, 'n_found': 20, 'n_truth': 20}
- **retention**: {'precision_at_k': 0.5, 'recall_at_k': 1.0, 'k': 10, 'n_true': 5}
- **escalation**: {'top_service': 'checkout-web', 'expected': 'checkout-web', 'hit': True, 'top_rate': 0.297}

## (c) Dollar quantification

- Reclaimable: $35,040/yr (expected $35,040/yr) — match=True

## (d) Siloed vs integrated

- Integrated finds 7 insights; siloed finds 1. Missed without joins (6):
  - Slow reviews do NOT explain change failures here
  - Speed/stability tradeoff by team
  - Idle licenses confirmed by engineering inactivity
  - Escalations concentrate where teams are stretched
  - Retention risk has a dollar value
  - Satisfaction/throughput link

## (e) Entity resolution

- {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'n_scored': 2153, 'fallback_accuracy': 1.0, 'fallback_n': 3}

## (f) Escalation predictor (client lens)

- train 400 / test 160, threshold=train base rate: {'precision': 0.16, 'recall': 0.267, 'f1': 0.2, 'n': 160, 'threshold': 0.138}

## Lens outputs

### DORA
          deploys_per_week  lead_time_p50_h  change_fail_rate  mttr_h  n_prs  n_incidents
team                                                                                     
checkout              7.85             12.4             0.564     2.7    204          148
data                  6.62             10.5             0.282     2.3    172           60
mobile                7.12             12.3             0.396     2.2    185          108
payments              7.92             12.4             0.418     2.8    206          101
platform              6.58             51.4             0.375     2.5    171           96
search                6.42             12.0             0.202     2.2    167           50

### License report
                   cost_per_mo  assigned  active  utilization  monthly_cost  wasted_monthly
license                                                                                    
ENTERPRISE_SUITE          95.0        60      52        0.867        5700.0           760.0
PREMIUM_ANALYTICS        180.0        20       7        0.350        3600.0          2340.0
DEV_TOOLKIT               45.0        54      54        1.000        2430.0             0.0

### CSAT drivers
- cd['corr_csat_logresolve']=-0.226, cd['corr_csat_escalated']=-0.314

### Top skill gaps
    skill  demand_share  supply_share    gap
       ml         0.104         0.150 -0.046
      ios         0.097         0.233 -0.136
   python         0.108         0.250 -0.142
       go         0.105         0.250 -0.145
terraform         0.097         0.283 -0.186
