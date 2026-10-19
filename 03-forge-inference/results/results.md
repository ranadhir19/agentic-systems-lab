# Forge experiment results

1500 requests per cell, seed 42. Times in ms.

| Load | Policy | Mean e2e | p99 e2e | Mean TTFT | Throughput | KV util |
|---|---|---|---|---|---|---|
| low (0.8 rps) | static-fcfs | 2973 | 6192 | 1070 | 0.76 | 7% |
| low (0.8 rps) | continuous | 2017 | 4219 | 18 | 0.76 | 9% |
| low (0.8 rps) | continuous-srpt | 2017 | 4219 | 18 | 0.76 | 9% |
| medium (2 rps) | static-fcfs | 8308 | 20144 | 5642 | 1.88 | 21% |
| medium (2 rps) | continuous | 2857 | 6633 | 28 | 1.89 | 22% |
| medium (2 rps) | continuous-srpt | 2857 | 6633 | 28 | 1.89 | 22% |
| high (4 rps) | static-fcfs | 189503 | 369406 | 186770 | 1.95 | 23% |
| high (4 rps) | continuous | 20607 | 44399 | 14431 | 3.47 | 98% |
| high (4 rps) | continuous-srpt | 13652 | 178710 | 7506 | 3.46 | 96% |
