"""Sample skill catalog: 6 portable skills with deterministic tools,
transforms, adapter-modulated corruptors, and executable eval cases.

Conventions:
- Tool steps are deterministic: same inputs -> same outputs on every
  provider. Portability here is structural.
- Transform steps have a deterministic base + a corruptor applied with
  probability (1 - q_eff) * err_rate, where q_eff comes from the adapter.
  This models "the model flubbed the step" honestly: better adapters and
  the SkillBridge damping both reduce corruption.
- State is keyed by step name; each step sees prior outputs.
"""
from __future__ import annotations

import random
import re

from .capabilities import CapabilityBroker, CapabilityServer
from .registry import SkillRegistry
from .skill import EvalCase, SkillManifest, SkillPackage, Step


# ---------------------------------------------------------------------------
# Tool implementations (deterministic)
# ---------------------------------------------------------------------------
def extract_fields(document: str, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        m = re.search(rf"^{re.escape(f)}\s*:\s*(.+)$", document, re.M | re.I)
        out[f] = m.group(1).strip() if m else ""
    return out


def scan_pii(document: str) -> list[tuple[int, int]]:
    spans = []
    for pat in (r"[\w\.-]+@[\w\.-]+\.\w+",
                r"\b\d{3}[-.]\d{3}[-.]\d{4}\b"):
        for m in re.finditer(pat, document):
            spans.append((m.start(), m.end()))
    return sorted(set(spans))


def lint_code(diff: str) -> list[dict]:
    findings = []
    for i, line in enumerate(diff.splitlines(), 1):
        if len(line) > 100:
            findings.append({"line": i, "severity": "minor",
                             "msg": "line exceeds 100 chars"})
        if "TODO" in line or "FIXME" in line:
            findings.append({"line": i, "severity": "info",
                             "msg": "todo/fixme marker"})
    return findings


def make_retriever(corpus):
    def retrieve(question: str, top_k: int = 2) -> list[dict]:
        q = set(question.lower().split())
        ranked = sorted(corpus,
                        key=lambda d: -len(q & set(d[1].lower().split())))
        return [{"id": d[0], "text": d[1]} for d in ranked[:top_k]]
    return retrieve


# ---------------------------------------------------------------------------
# Transforms (deterministic base) + corruptors (adapter-modulated)
# ---------------------------------------------------------------------------
def t_redact(state, inputs, step, rng):
    doc, spans = inputs["document"], state["text.scan_pii"]
    out = doc
    for s, e in sorted(spans, reverse=True):
        out = out[:s] + "[REDACTED]" + out[e:]
    return {"redacted": out, "n_redacted": len(spans)}


def c_redact_skip_one(state, inputs, step, rng):
    doc, spans = inputs["document"], state["text.scan_pii"]
    skip = rng.randrange(len(spans)) if spans else None
    out = doc
    for i, (s, e) in enumerate(sorted(spans, reverse=True)):
        if len(spans) - 1 - i == skip:
            continue
        out = out[:s] + "[REDACTED]" + out[e:]
    return {"redacted": out, "n_redacted": len(spans) - (1 if skip is not None else 0)}


def t_compose_sql(state, inputs, step, rng):
    q = f"SELECT {inputs['agg']}({inputs['metric']}) FROM {inputs['table']}"
    if inputs.get("group_by"):
        q += f" GROUP BY {inputs['group_by']}"
    if inputs.get("where"):
        q += f" WHERE {inputs['where']}"
    return {"sql": q}


def c_sql_drop_where(state, inputs, step, rng):
    out = t_compose_sql(state, inputs, step, rng)
    out["sql"] = out["sql"].split(" WHERE ")[0]
    return out


def t_summarize_findings(state, inputs, step, rng):
    findings = state["code.lint"]
    lines = [f"[{f['severity']}] line {f['line']}: {f['msg']}" for f in findings]
    return {"report": "\n".join(lines), "n_findings": len(findings)}


def c_findings_drop_half(state, inputs, step, rng):
    findings = state["code.lint"]
    keep = findings[:max(1, len(findings) // 2)]
    lines = [f"[{f['severity']}] line {f['line']}: {f['msg']}" for f in keep]
    return {"report": "\n".join(lines), "n_findings": len(keep)}


def t_extract_points(state, inputs, step, rng):
    pts = [l.strip() for l in inputs["transcript"].splitlines()
           if l.strip().startswith(("DECISION:", "ACTION:"))]
    return {"points": pts}


def t_summarize_meeting(state, inputs, step, rng):
    pts = state["extract_points"]["points"]
    return {"summary": " | ".join(pts), "n_points": len(pts)}


def c_points_drop_one(state, inputs, step, rng):
    pts = list(state["extract_points"]["points"])
    if pts:
        pts.pop(rng.randrange(len(pts)))
    return {"summary": " | ".join(pts), "n_points": len(pts)}


def t_answer(state, inputs, step, rng):
    docs = state["kb.retrieve"]
    cites = " ".join(f"[{d['id']}]" for d in docs)
    return {"answer": f"{inputs['question']} -- see {cites}",
            "citations": [d["id"] for d in docs]}


def c_answer_drop_cites(state, inputs, step, rng):
    out = t_answer(state, inputs, step, rng)
    out["answer"] = inputs["question"] + " -- see sources"
    out["citations"] = []
    return out


TRANSFORMS = {
    "redact": (t_redact, c_redact_skip_one, 1.4),
    "compose_sql": (t_compose_sql, c_sql_drop_where, 1.2),
    "summarize_findings": (t_summarize_findings, c_findings_drop_half, 1.0),
    "extract_points": (t_extract_points, None, 0.0),
    "summarize_meeting": (t_summarize_meeting, c_points_drop_one, 1.0),
    "answer": (t_answer, c_answer_drop_cites, 1.2),
}


# ---------------------------------------------------------------------------
# Skill builders + eval cases
# ---------------------------------------------------------------------------
def _doc(vendor, amount, date):
    return f"Vendor: {vendor}\nAmount: {amount}\nDate: {date}\n"


def _skill_invoice():
    cases = []
    data = [("Acme Corp", "$12,400.00", "2026-09-01"),
            ("Globex", "$845.10", "2026-08-14"),
            ("Initech LLC", "$230,000.00", "2026-10-02"),
            ("Umbrella Co", "$59.99", "2026-07-30"),
            ("Hooli", "$1,200,000.00", "2026-01-15"),
            ("Stark Industries", "$77.77", "2026-11-11"),
            ("Wayne Enterprises", "$45,210.50", "2026-03-22"),
            ("Stark Labs", "$9.99", "2026-12-01"),
            ("Cyberdyne", "$3,333.33", "2026-05-17"),
            ("Tyrell Corp", "$88,000.00", "2026-02-28"),
            ("Aperture Science", "$1,042.00", "2026-06-09"),
            ("Blue Sun", "$610.25", "2026-09-19")]
    for i, (v, a, d) in enumerate(data):
        cases.append(EvalCase(
            f"invoice-{i}", {"document": _doc(v, a, d)},
            lambda out, exp, v=v, a=a, d=d: (
                out["text.extract"]["vendor"] == v
                and out["text.extract"]["amount"] == a
                and out["text.extract"]["date"] == d)))
    return SkillPackage(
        SkillManifest("invoice-extractor", "1.2.0",
                      "Extract vendor/amount/date from invoice text",
                      ("finance", "extraction"), ("text.extract",), "internal"),
        "Extract the requested fields from the invoice document.",
        [Step("tool", "text.extract", capability="text.extract",
              args={"fields": ["vendor", "amount", "date"]})],
        cases)


def _skill_pii():
    docs = [
        ("Contact alice@example.com or 415-555-0132 for access.", 2),
        ("Email bob.smith@corp.io; backup carol@corp.io.", 2),
        ("No personal data here, just a meeting at noon.", 0),
        ("Reach 212-555-0199 (Dave) or dave99@mail.com today.", 2),
        ("Priya's email priya@dev.org and phone 650-555-0117.", 2),
        ("Support: help@vendor.com, sales: sales@vendor.com, 800-555-0100.", 3),
        ("Call 312-555-0148 after emailing nina@startup.ai.", 2),
        ("Nothing sensitive in this quarter's summary.", 0),
        ("Ping zoe@design.co or 917-555-0163 re: mockups.", 2),
        ("Legal: counsel@firm.com, alt: counsel2@firm.com.", 2),
        ("On-call 408-555-0121, backup 408-555-0122.", 2),
        ("Send the report to finance-team@bigcorp.com.", 1),
        ("Email grace.hopper@navy.mil for the specs.", 1),
        ("Call 617-555-0188 or 617-555-0189 for support.", 2),
        ("No PII in this system status update.", 0),
        ("Contact wei.chen@example.org; phone 206-555-0177.", 2),
        ("HR: hr@company.com, payroll: pay@company.com.", 2),
        ("My number is 415.555.0166, email sam_jones@mail.net.", 2),
        ("Urgent: call 303-555-0145, not the old line.", 1),
        ("Visit us at 123 Main St; email visit@store.com.", 1),
        ("Two emails: a@b.co and c@d.io, no phones.", 2),
        ("Phone 2125550199 has no dashes, so no match.", 0),
        ("DM jordan_lee@chat.io or text 929-555-0114.", 2),
        ("Quarterly figures attached; no contacts listed.", 0),
    ]
    cases = []
    for i, (doc, n) in enumerate(docs):
        cases.append(EvalCase(
            f"pii-{i}", {"document": doc},
            lambda out, exp, n=n: (
                out["redact"]["n_redacted"] == n
                and not re.search(r"[\w\.-]+@[\w\.-]+\.\w+",
                                  out["redact"]["redacted"])
                and not re.search(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b",
                                  out["redact"]["redacted"]))))
    return SkillPackage(
        SkillManifest("pii-redactor", "2.0.1", "Scan and redact PII",
                      ("privacy",), ("text.scan_pii",), "confidential",
                      approved_tools=("text.scan_pii",)),
        "Find PII spans, then redact every one of them.",
        [Step("tool", "text.scan_pii", capability="text.scan_pii"),
         Step("transform", "redact", transform="redact")],
        cases)


def _skill_sql():
    specs = [
        ({"agg": "SUM", "metric": "revenue", "table": "orders",
          "group_by": "region", "where": "year = 2024"},
         ["SELECT", "SUM(revenue)", "orders", "GROUP BY region",
          "WHERE year = 2024"]),
        ({"agg": "COUNT", "metric": "*", "table": "users",
          "group_by": "", "where": "country = 'US'"},
         ["SELECT", "COUNT(*)", "users", "WHERE country = 'US'"]),
        ({"agg": "AVG", "metric": "latency_ms", "table": "events",
          "group_by": "service", "where": ""},
         ["SELECT", "AVG(latency_ms)", "events", "GROUP BY service"]),
        ({"agg": "SUM", "metric": "amount", "table": "refunds",
          "group_by": "", "where": "status = 'approved'"},
         ["SELECT", "SUM(amount)", "refunds", "WHERE status = 'approved'"]),
        ({"agg": "MAX", "metric": "score", "table": "leaderboard",
          "group_by": "league", "where": "season = 2026"},
         ["SELECT", "MAX(score)", "leaderboard", "GROUP BY league",
          "WHERE season = 2026"]),
        ({"agg": "MIN", "metric": "price", "table": "products",
          "group_by": "category", "where": ""},
         ["SELECT", "MIN(price)", "products", "GROUP BY category"]),
        ({"agg": "COUNT", "metric": "*", "table": "sessions",
          "group_by": "", "where": "device = 'mobile'"},
         ["SELECT", "COUNT(*)", "sessions", "WHERE device = 'mobile'"]),
        ({"agg": "AVG", "metric": "rating", "table": "reviews",
          "group_by": "product_id", "where": "verified = true"},
         ["SELECT", "AVG(rating)", "reviews", "GROUP BY product_id",
          "WHERE verified = true"]),
        ({"agg": "SUM", "metric": "quantity", "table": "line_items",
          "group_by": "sku", "where": ""},
         ["SELECT", "SUM(quantity)", "line_items", "GROUP BY sku"]),
        ({"agg": "MAX", "metric": "created_at", "table": "deployments",
          "group_by": "", "where": "env = 'prod'"},
         ["SELECT", "MAX(created_at)", "deployments", "WHERE env = 'prod'"]),
        ({"agg": "AVG", "metric": "duration_s", "table": "builds",
          "group_by": "", "where": "branch = 'main'"},
         ["SELECT", "AVG(duration_s)", "builds", "WHERE branch = 'main'"]),
        ({"agg": "SUM", "metric": "cost", "table": "invoices",
          "group_by": "vendor", "where": "paid = false"},
         ["SELECT", "SUM(cost)", "invoices", "GROUP BY vendor",
          "WHERE paid = false"]),
        ({"agg": "MIN", "metric": "age", "table": "employees",
          "group_by": "dept", "where": ""},
         ["SELECT", "MIN(age)", "employees", "GROUP BY dept"]),
        ({"agg": "SUM", "metric": "bytes", "table": "transfers",
          "group_by": "", "where": "day = '2026-10-01'"},
         ["SELECT", "SUM(bytes)", "transfers", "WHERE day = '2026-10-01'"]),
        ({"agg": "COUNT", "metric": "*", "table": "orders",
          "group_by": "status", "where": ""},
         ["SELECT", "COUNT(*)", "orders", "GROUP BY status"]),
        ({"agg": "AVG", "metric": "score", "table": "exams",
          "group_by": "", "where": "passed = true"},
         ["SELECT", "AVG(score)", "exams", "WHERE passed = true"]),
        ({"agg": "MAX", "metric": "temp_c", "table": "sensors",
          "group_by": "location", "where": "hour = 14"},
         ["SELECT", "MAX(temp_c)", "sensors", "GROUP BY location",
          "WHERE hour = 14"]),
        ({"agg": "SUM", "metric": "clicks", "table": "ads",
          "group_by": "campaign", "where": ""},
         ["SELECT", "SUM(clicks)", "ads", "GROUP BY campaign"]),
        ({"agg": "COUNT", "metric": "*", "table": "tickets",
          "group_by": "", "where": "priority = 'p1'"},
         ["SELECT", "COUNT(*)", "tickets", "WHERE priority = 'p1'"]),
        ({"agg": "AVG", "metric": "balance", "table": "accounts",
          "group_by": "tier", "where": "active = true"},
         ["SELECT", "AVG(balance)", "accounts", "GROUP BY tier",
          "WHERE active = true"]),
        ({"agg": "MIN", "metric": "started_at", "table": "jobs",
          "group_by": "", "where": ""},
         ["SELECT", "MIN(started_at)", "jobs"]),
        ({"agg": "SUM", "metric": "revenue", "table": "subscriptions",
          "group_by": "plan", "where": "churned = false"},
         ["SELECT", "SUM(revenue)", "subscriptions", "GROUP BY plan",
          "WHERE churned = false"]),
        ({"agg": "MAX", "metric": "version", "table": "releases",
          "group_by": "", "where": "channel = 'stable'"},
         ["SELECT", "MAX(version)", "releases", "WHERE channel = 'stable'"]),
        ({"agg": "AVG", "metric": "cpu", "table": "hosts",
          "group_by": "datacenter", "where": ""},
         ["SELECT", "AVG(cpu)", "hosts", "GROUP BY datacenter"]),
    ]
    cases = []
    for i, (inp, toks) in enumerate(specs):
        cases.append(EvalCase(
            f"sql-{i}", inp,
            lambda out, exp, toks=toks: all(t in out["compose_sql"]["sql"]
                                            for t in toks)))
    return SkillPackage(
        SkillManifest("sql-generator", "1.0.0",
                      "Compose analytical SQL from a spec",
                      ("data", "code"), (), "internal"),
        "Compose the SQL exactly from the given spec; never drop the WHERE clause.",
        [Step("transform", "compose_sql", transform="compose_sql")],
        cases)


def _gen_diff(n_long: int, n_todo: int, seed_i: int) -> tuple[str, int]:
    """Build a diff with exactly n_long over-100-char lines and n_todo
    TODO/FIXME markers (kept on separate short lines so each counts once)."""
    rng = random.Random(1000 + seed_i)
    lines = []
    for j in range(n_long):
        lines.append('data_%d = "%s"' % (j, "x" * 105))
    for j in range(n_todo):
        marker = rng.choice(["TODO", "FIXME"])
        lines.append(f"# {marker}: item {j}")
    lines.append("clean = True")
    rng.shuffle(lines)
    return "\n".join(lines) + "\n", n_long + n_todo


def _skill_review():
    plan = [(0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (3, 0),
            (0, 3), (2, 2), (4, 1), (1, 4), (3, 3), (2, 0),
            (1, 1), (0, 2), (5, 0), (0, 5), (2, 3), (3, 2),
            (4, 4), (6, 0), (0, 4), (2, 5), (5, 2), (1, 3)]
    cases = []
    for i, (nl, nt) in enumerate(plan):
        diff, n = _gen_diff(nl, nt, i)
        cases.append(EvalCase(
            f"review-{i}", {"diff": diff},
            lambda out, exp, n=n: out["summarize_findings"]["n_findings"] == n))
    return SkillPackage(
        SkillManifest("code-reviewer", "1.4.0", "Lint and summarize a diff",
                      ("code",), ("code.lint",), "internal"),
        "Report every lint finding with its severity.",
        [Step("tool", "code.lint", capability="code.lint"),
         Step("transform", "summarize_findings",
              transform="summarize_findings")],
        cases)


_DECISIONS = [
    "DECISION: launch in Q1",
    "DECISION: freeze the API",
    "DECISION: migrate to postgres",
    "DECISION: hire two engineers",
    "DECISION: sunset v1 endpoints",
    "DECISION: adopt the new pricing",
    "DECISION: pause the beta",
    "DECISION: fund the pilot",
]
_ACTIONS = [
    "ACTION: Priya to draft plan",
    "ACTION: Tom to fix build",
    "ACTION: Ana to notify customers",
    "ACTION: Lee to update docs",
    "ACTION: Sam to run load tests",
    "ACTION: Kim to schedule review",
    "ACTION: Jo to file the ticket",
    "ACTION: Max to ping legal",
]
_FILLER = [
    "Small talk about the weather.",
    "Discussed the roadmap briefly.",
    "Coffee break.",
    "Reviewed last week's notes.",
    "Open Q&A session.",
]


def _skill_meeting():
    rng = random.Random(2026)
    plan = [(2, 1), (1, 2), (3, 0), (0, 3), (2, 2), (1, 1),
            (4, 1), (1, 3), (0, 0), (2, 0), (0, 2), (0, 0),
            (3, 2), (2, 3), (1, 0), (0, 1), (5, 0), (0, 4),
            (2, 4), (4, 2), (1, 5), (0, 0), (3, 3), (2, 1)]
    cases = []
    for i, (kd, ka) in enumerate(plan):
        pts = rng.sample(_DECISIONS, kd) + rng.sample(_ACTIONS, ka)
        rng.shuffle(pts)
        lines = []
        for p in pts:
            lines.append(p)
            if rng.random() < 0.5:
                lines.append(rng.choice(_FILLER))
        if not pts:
            lines = [rng.choice(_FILLER), rng.choice(_FILLER)]
        transcript = "\n".join(lines) + "\n"
        cases.append(EvalCase(
            f"meeting-{i}", {"transcript": transcript},
            lambda out, exp, pts=pts: all(p in out["summarize_meeting"]["summary"]
                                          for p in pts)
            and out["summarize_meeting"]["n_points"] == len(pts)))
    return SkillPackage(
        SkillManifest("meeting-summarizer", "0.9.0",
                      "Extract decisions and actions from a transcript",
                      ("productivity",), (), "internal"),
        "Capture every DECISION and ACTION line; drop nothing.",
        [Step("transform", "extract_points", transform="extract_points"),
         Step("transform", "summarize_meeting", transform="summarize_meeting")],
        cases)


_CORPUS = [
    ("kb-1", "refunds are processed within five business days"),
    ("kb-2", "the enterprise plan includes SSO and audit logs"),
    ("kb-3", "latency SLO is 200ms p99 for the search API"),
    ("kb-4", "data retention for logs is thirteen months"),
    ("kb-5", "password resets require email verification within ten minutes"),
    ("kb-6", "the mobile app supports offline mode and biometric login"),
    ("kb-7", "invoices are issued on the first day of each month"),
    ("kb-8", "webhooks retry failed deliveries with exponential backoff"),
]


def _skill_rag():
    # expected ids are the retriever's verified top-2 for each question
    qs = [
        ("how long do refunds take to process", ["kb-1", "kb-2"]),
        ("does the enterprise plan include SSO and audit logs", ["kb-2", "kb-6"]),
        ("what is the latency SLO for the search API", ["kb-3", "kb-4"]),
        ("how long are logs retained for data retention", ["kb-4", "kb-1"]),
        ("how do password resets work with email verification", ["kb-5", "kb-8"]),
        ("does the mobile app support offline mode", ["kb-6", "kb-2"]),
        ("when are invoices issued each month", ["kb-7", "kb-1"]),
        ("how do webhooks handle failed deliveries", ["kb-8", "kb-1"]),
        ("refund processing time in business days", ["kb-1", "kb-2"]),
        ("enterprise SSO and audit log features", ["kb-2", "kb-6"]),
        ("search API p99 latency requirement", ["kb-3", "kb-1"]),
        ("biometric login in the mobile app", ["kb-6", "kb-2"]),
        ("how are refunds processed", ["kb-1", "kb-7"]),
        ("audit logs in the enterprise plan", ["kb-2", "kb-3"]),
        ("200ms p99 search SLO", ["kb-3", "kb-1"]),
        ("thirteen month log retention", ["kb-4", "kb-7"]),
        ("email verification for password resets", ["kb-5", "kb-3"]),
        ("offline mode and biometric login", ["kb-6", "kb-2"]),
        ("first day of the month invoices", ["kb-7", "kb-2"]),
        ("exponential backoff for webhooks", ["kb-8", "kb-3"]),
        ("business days for refund processing", ["kb-1", "kb-3"]),
        ("SSO included in enterprise", ["kb-2", "kb-1"]),
        ("search API latency", ["kb-3", "kb-1"]),
        ("data retention months for logs", ["kb-4", "kb-2"]),
    ]
    cases = []
    for i, (q, ids) in enumerate(qs):
        cases.append(EvalCase(
            f"rag-{i}", {"question": q},
            lambda out, exp, ids=ids: all(d in out["answer"]["citations"]
                                          for d in ids)))
    return SkillPackage(
        SkillManifest("rag-answerer", "2.3.0",
                      "Answer from the knowledge base with citations",
                      ("knowledge",), ("kb.retrieve",), "internal"),
        "Answer only from retrieved passages and cite every source used.",
        [Step("tool", "kb.retrieve", capability="kb.retrieve",
              args={"top_k": 2}),
         Step("transform", "answer", transform="answer")],
        cases)


def build_catalog():
    registry = SkillRegistry()
    broker = CapabilityBroker()
    broker.register_server(CapabilityServer("text-tools", {
        "text.extract": lambda document, fields: extract_fields(document, fields),
        "text.scan_pii": lambda document: scan_pii(document),
    }))
    broker.register_server(CapabilityServer("dev-tools", {
        "code.lint": lambda diff: lint_code(diff),
    }))
    broker.register_server(CapabilityServer("kb-server", {
        "kb.retrieve": lambda question, top_k=2: make_retriever(_CORPUS)(question, top_k),
    }))
    # high-sensitivity server used only by governance tests
    broker.register_server(CapabilityServer(
        "ops-tools", {"data.export": lambda query: "exported"},
        sensitivity={"data.export": "high"}))
    for build in (_skill_invoice, _skill_pii, _skill_sql,
                  _skill_review, _skill_meeting, _skill_rag):
        registry.register(build())
    # a deprecated version, for governance tests
    old = _skill_sql()
    old.manifest = SkillManifest(
        old.manifest.name, "0.5.0", old.manifest.description,
        old.manifest.tags, old.manifest.required_capabilities,
        old.manifest.data_classification, deprecated=True)
    registry.register(old)
    return registry, broker
