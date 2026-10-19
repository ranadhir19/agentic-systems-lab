# SkillBridge MCP experiment results

## Exp 1 — Portability (6 skills x 3 adapters)

| Skill | Mode | openai-style | anthropic-style | local-style | Mean | Worst | Std |
|---|---|---|---|---|---|---|
| invoice-extractor | skillbridge | 100% | 100% | 100% | 100% | 100% | 0.000 |
| invoice-extractor | raw | 100% | 100% | 100% | 100% | 100% | 0.000 |
| pii-redactor | skillbridge | 96% | 83% | 83% | 88% | 83% | 0.059 |
| pii-redactor | raw | 100% | 75% | 62% | 79% | 62% | 0.156 |
| sql-generator | skillbridge | 96% | 92% | 92% | 93% | 92% | 0.020 |
| sql-generator | raw | 88% | 79% | 58% | 75% | 58% | 0.123 |
| code-reviewer | skillbridge | 96% | 88% | 92% | 92% | 88% | 0.034 |
| code-reviewer | raw | 88% | 79% | 75% | 81% | 75% | 0.052 |
| meeting-summarizer | skillbridge | 92% | 100% | 79% | 90% | 79% | 0.086 |
| meeting-summarizer | raw | 83% | 96% | 62% | 81% | 62% | 0.137 |
| rag-answerer | skillbridge | 92% | 100% | 88% | 93% | 88% | 0.052 |
| rag-answerer | raw | 83% | 92% | 67% | 81% | 67% | 0.104 |

Mean cross-adapter std (skillbridge): 0.042

Mean cross-adapter std (raw): 0.095

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
