# Horizon-scaling experiment results

Seed 7; 2000 trials per cell; default task family p_fatal=0.01, p_err=0.03, cascade=2.0, detect_check=0.8.

## (a,b) Decay curves: success rate vs horizon

| Agent | N=5 | N=10 | N=20 | N=40 | N=80 |
|---|---|---|---|---|---|
| baseline | 0.8045 | 0.6450 | 0.4200 | 0.1875 | 0.0345 |
| checkpoints(k=5) | 0.9670 | 0.9380 | 0.8720 | 0.7670 | 0.5955 |
| hierarchy(s=10) | 0.9860 | 0.9610 | 0.9195 | 0.8585 | 0.7400 |
| voting(n=3) | 0.9740 | 0.9500 | 0.9105 | 0.8235 | 0.6755 |
| recovery(k=5) | 0.9715 | 0.9405 | 0.8830 | 0.7760 | 0.6125 |

Exponential fit success(N) = q^N (log-linear regression):

| Agent | q_hat (per-step) | R^2 |
|---|---|---|
| baseline | 0.95903 | 0.9999 |
| checkpoints(k=5) | 0.99355 | 0.9996 |
| hierarchy(s=10) | 0.99624 | 0.9982 |
| voting(n=3) | 0.99513 | 0.9997 |
| recovery(k=5) | 0.99386 | 0.9996 |

Theoretical baseline per-step q = (1-pf)(1-pe) = 0.96030.

## (d) Cost per successful task

| Agent | N=5 | N=10 | N=20 | N=40 | N=80 |
|---|---|---|---|---|---|
| baseline | 6.1 | 14.7 | 41.8 | 158.4 | 1211.0 |
| checkpoints(k=5) | 8.4 | 17.7 | 38.8 | 85.9 | 200.4 |
| hierarchy(s=10) | 7.8 | 14.8 | 31.2 | 66.3 | 145.4 |
| voting(n=3) | 15.4 | 31.6 | 65.9 | 145.7 | 355.3 |
| recovery(k=5) | 8.3 | 17.4 | 38.1 | 85.5 | 197.3 |

Cheapest per horizon: N=5: baseline (6.1), N=10: baseline (14.7), N=20: hierarchy(s=10) (31.2), N=40: hierarchy(s=10) (66.3), N=80: hierarchy(s=10) (145.4).

## (c) Checkpoint-interval sweep (N=40)

| k | Success | Mean cost | Cost/success |
|---|---|---|---|
| 2 | 0.7715 | 81.4 | 105.5 |
| 5 | 0.7635 | 66.0 | 86.5 |
| 10 | 0.7585 | 66.8 | 88.1 |
| 20 | 0.6700 | 74.5 | 111.3 |
| 40 | 0.5305 | 87.4 | 164.8 |

Optimal k by cost-per-success: **5**.

## (e) Error mix (N=40)

| Mix (pf, pe) | baseline | checkpoints(k=5) | hierarchy(s=10) | voting(n=3) | recovery(k=5) |
|---|---|---|---|---|---|
| corruption-heavy (0.01, 0.05) | 0.0850 | 0.6355 | 0.7665 | 0.6575 | 0.6490 |
| balanced (0.02, 0.03) | 0.1235 | 0.7730 | 0.8260 | 0.7450 | 0.7640 |
| fatal-heavy (0.045, 0.005) | 0.1235 | 0.9510 | 0.7840 | 0.7450 | 0.9580 |

## (f) Interaction (N=80)

| Config | Success | Cost/success |
|---|---|---|
| checkpoints(k=5) | 0.6145 | 194.9 |
| hierarchy(s=10) | 0.7495 | 145.4 |
| both | 0.7980 | 149.6 |
