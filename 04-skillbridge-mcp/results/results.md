# SkillBridge MCP experiment results

## Exp 1 — Portability (6 skills x 3 adapters)

| Skill | Mode | openai-style | anthropic-style | local-style | Mean | Worst | Std |
|---|---|---|---|---|---|---|
| invoice-extractor | skillbridge | 100% | 100% | 100% | 100% | 100% | 0.000 |
| invoice-extractor | raw | 100% | 100% | 100% | 100% | 100% | 0.000 |
| pii-redactor | skillbridge | 96% | 96% | 75% | 89% | 75% | 0.098 |
| pii-redactor | raw | 92% | 71% | 62% | 75% | 62% | 0.123 |
| sql-generator | skillbridge | 100% | 88% | 79% | 89% | 79% | 0.086 |
| sql-generator | raw | 96% | 83% | 62% | 81% | 62% | 0.137 |
| code-reviewer | skillbridge | 96% | 100% | 100% | 99% | 96% | 0.020 |
| code-reviewer | raw | 92% | 92% | 75% | 86% | 75% | 0.079 |
| meeting-summarizer | skillbridge | 92% | 92% | 96% | 93% | 92% | 0.020 |
| meeting-summarizer | raw | 88% | 92% | 92% | 90% | 88% | 0.020 |
| rag-answerer | skillbridge | 92% | 100% | 88% | 93% | 88% | 0.052 |
| rag-answerer | raw | 83% | 83% | 62% | 76% | 62% | 0.098 |

Mean cross-adapter std (skillbridge): 0.046

Mean cross-adapter std (raw): 0.076

## Exp 2 — Reuse economics (dev-days)

| Models | Per-provider rebuild | SkillBridge | Saved |
|---|---|---|---|
| 1 | 100 | 123 | -23 |
| 2 | 200 | 131 | 69 |
| 3 | 300 | 139 | 161 |
| 4 | 400 | 147 | 253 |
| 5 | 500 | 155 | 345 |
| 6 | 600 | 163 | 437 |
| 7 | 700 | 171 | 529 |
| 8 | 800 | 179 | 621 |

## Exp 3 — Governance

Adversarial runs denied: 3/3; clean runs allowed: 20/20.

- unlisted tool: DENIED — capability 'text.scan_pii' not in approved_tools
- high-sensitivity w/o approval: DENIED — capability 'data.export' is high-sensitivity: approval required
- high-sensitivity WITH approval: ALLOWED — 
- deprecated version: DENIED — sql-generator@0.5.0 is deprecated
