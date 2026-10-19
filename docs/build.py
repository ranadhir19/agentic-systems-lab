#!/usr/bin/env python3
"""Builds the Agentic Systems Lab landing site into docs/ (GitHub Pages ready).

Each project page: Problem / The gap / The solution / Architecture (SVG) /
Results / Insights / Implementation. Run: python3 docs/build.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{
  --bg:#0b0e14; --panel:#111724; --panel2:#0e1420; --border:#22304a;
  --text:#e8ebf2; --muted:#98a2b8; --faint:#6b7690;
  --blue:#6ea8fe; --green:#7ee2a8; --amber:#f0b35e; --red:#f08787;
  --radius:14px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  line-height:1.65;font-size:16px}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
nav.top{position:sticky;top:0;z-index:50;background:rgba(11,14,20,.92);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
nav.top .wrap{display:flex;align-items:center;gap:28px;height:60px}
.brand{font-weight:700;font-size:17px;color:var(--text);letter-spacing:.2px}
.brand span{color:var(--blue)}
nav.top .links{margin-left:auto;display:flex;gap:20px;font-size:14px}
nav.top .links a{color:var(--muted)}
nav.top .links a:hover{color:var(--text)}
.hero{padding:84px 0 60px;text-align:left;
  background:radial-gradient(900px 380px at 20% 0%,rgba(110,168,254,.12),transparent 60%)}
.hero .kicker{color:var(--blue);font-size:13px;font-weight:700;letter-spacing:2.5px;
  text-transform:uppercase;margin-bottom:18px}
.hero h1{font-size:46px;line-height:1.12;margin:0 0 20px;letter-spacing:-.5px;max-width:820px}
.hero p.sub{color:var(--muted);font-size:18px;max-width:720px;margin:0 0 34px}
.btn{display:inline-block;background:var(--blue);color:#0b0e14;font-weight:700;
  padding:12px 26px;border-radius:10px;font-size:15px}
.btn:hover{text-decoration:none;filter:brightness(1.08)}
.btn.ghost{background:transparent;color:var(--text);border:1px solid var(--border);margin-left:12px}
.install{margin-top:34px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.install code{background:#0e1420;border:1px solid var(--border);border-radius:8px;
  padding:10px 18px;font-size:15px;color:var(--green)}
.install span{color:var(--muted);font-size:14px}
.stats{display:flex;gap:36px;margin-top:44px;flex-wrap:wrap}
.stats div b{font-size:26px;display:block}
.stats div span{color:var(--muted);font-size:13px}
section{padding:56px 0}
h2.sec{font-size:28px;margin:0 0 8px;letter-spacing:-.3px}
p.lead{color:var(--muted);max-width:760px;margin:0 0 30px}
.cat{border:1px solid var(--border);border-radius:var(--radius);padding:28px;
  margin-bottom:28px;background:var(--panel)}
.cat h3{margin:0 0 4px;font-size:21px}
.cat h3 .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:10px}
.cat p.desc{color:var(--muted);margin:0 0 20px;max-width:720px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.cards{grid-template-columns:1fr}.hero h1{font-size:34px}}
.card{background:var(--panel2);border:1px solid var(--border);border-radius:12px;
  padding:22px;display:flex;flex-direction:column}
.card h4{margin:0 0 6px;font-size:18px}
.card h4 a{color:var(--text)}
.card .tag{font-size:12px;color:var(--faint);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px}
.card p{color:var(--muted);font-size:14.5px;margin:0 0 16px;flex:1}
.card .metric{font-size:14px;color:var(--text);border-top:1px solid var(--border);padding-top:12px}
.card .metric b{color:var(--green)}
.proj-hero{padding:56px 0 30px}
.proj-hero .kicker{font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px}
.proj-hero h1{font-size:38px;margin:0 0 10px;letter-spacing:-.4px}
.proj-hero p.tagline{color:var(--muted);font-size:18px;margin:0 0 8px}
.crumb{font-size:13px;color:var(--faint);margin-bottom:22px}
.crumb a{color:var(--faint)}
.block{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);
  padding:28px;margin-bottom:22px}
.block h2{font-size:20px;margin:0 0 12px}
.block h2 .n{display:inline-block;width:28px;height:28px;border-radius:8px;background:var(--blue);
  color:#0b0e14;font-size:15px;text-align:center;line-height:28px;margin-right:10px;font-weight:800}
.block p{margin:0 0 12px;color:#c9d1e2}
.block p:last-child{margin-bottom:0}
.block ul{margin:8px 0 0;padding-left:20px;color:#c9d1e2}
.block li{margin-bottom:8px}
.diagram{background:#0d1320;border:1px solid var(--border);border-radius:12px;
  padding:18px;overflow-x:auto;margin:6px 0 4px}
.diagram svg{display:block;margin:0 auto;max-width:100%;height:auto}
.caption{font-size:13px;color:var(--faint);text-align:center;margin-top:8px}
table.res{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0}
table.res th,table.res td{border:1px solid var(--border);padding:9px 12px;text-align:left}
table.res th{background:var(--panel2);color:var(--muted);font-weight:600}
.hl{color:var(--green);font-weight:700}
img.chart{width:100%;border-radius:10px;border:1px solid var(--border);margin-top:10px}
code.tree{background:#0d1320;border:1px solid var(--border);border-radius:10px;
  display:block;padding:16px 18px;font-size:13.5px;color:#c9d1e2;overflow-x:auto;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre}
.pagenav{display:flex;justify-content:space-between;margin:40px 0 60px;gap:16px}
.pagenav a{border:1px solid var(--border);border-radius:10px;padding:14px 20px;
  color:var(--text);font-size:14px;background:var(--panel)}
.pagenav a small{display:block;color:var(--faint);font-size:12px}
footer{border-top:1px solid var(--border);padding:34px 0 48px;color:var(--faint);font-size:13.5px}
footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
"""

SVG_DEFS = """
<defs>
  <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#8fa2c8"/>
  </marker>
  <marker id="arrb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#6ea8fe"/>
  </marker>
  <marker id="arrg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#7ee2a8"/>
  </marker>
</defs>
"""

def box(x, y, w, h, label, sub="", fill="#141c2e", stroke="#3b4d75", tcolor="#e8ebf2", fs=13):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
    s += f'<text x="{x+w/2}" y="{y+h/2-2}" text-anchor="middle" fill="{tcolor}" font-size="{fs}" font-weight="600">{label}</text>'
    if sub:
        s += f'<text x="{x+w/2}" y="{y+h/2+15}" text-anchor="middle" fill="#98a2b8" font-size="11">{sub}</text>'
    return s

def arrow(x1, y1, x2, y2, color="#8fa2c8", marker="arr", dashed=False, label=""):
    d = f' stroke-dasharray="5,4"' if dashed else ""
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#{marker})"/>'
    if label:
        s += f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-7}" text-anchor="middle" fill="{color}" font-size="11">{label}</text>'
    return s

# ---------------------------------------------------------------------------
# Architecture diagrams (hand-drawn SVG, consistent "blueprint" style)
# ---------------------------------------------------------------------------

def svg_meridian():
    b = [SVG_DEFS]
    # vertical hierarchy, left side
    b.append(box(40, 20, 200, 56, "Meta Orchestrator", "decomposes goal"))
    for i, lab in enumerate(["Domain A", "Domain B", "Domain C"]):
        x = 40 + i * 0  # stacked below via y
    b.append(box(40, 120, 200, 52, "Domain Orchestrator", "plans subtasks"))
    b.append(box(40, 216, 96, 52, "Worker", "standard tier"))
    b.append(box(144, 216, 96, 52, "Worker", "pro tier", fill="#1a2b1f", stroke="#3f7a52"))
    b.append(arrow(140, 76, 140, 118))
    b.append(arrow(88, 172, 88, 214))
    b.append(arrow(192, 172, 192, 214))
    # horizontal blackboard, right side
    b.append(box(320, 20, 220, 248, "", "", fill="#101827", stroke="#3b4d75"))
    b.append(f'<text x="430" y="46" text-anchor="middle" fill="#e8ebf2" font-size="14" font-weight="700">Blackboard</text>')
    b.append(f'<text x="430" y="66" text-anchor="middle" fill="#98a2b8" font-size="11">horizontal coordination</text>')
    b.append(box(345, 92, 170, 44, "propose", "offer a partial result", fs=12))
    b.append(box(345, 148, 170, 44, "request", "ask for a capability", fs=12))
    b.append(box(345, 204, 170, 44, "commit", "claim a subtask", fs=12))
    # horizontal links
    for y in [150, 240]:
        b.append(arrow(240, y, 318, y, dashed=True))
    # optimizer feedback loop at bottom
    b.append(box(40, 312, 500, 56, "Decision Optimizer", "contextual Thompson sampling · profile priors · scalarized objective", fill="#1b2340", stroke="#6ea8fe"))
    b.append(arrow(140, 268, 140, 310, color="#6ea8fe", marker="arrb"))
    b.append(arrow(430, 268, 430, 310, color="#6ea8fe", marker="arrb"))
    b.append(f'<text x="290" y="300" text-anchor="middle" fill="#6ea8fe" font-size="11">routes each subtask to a tier</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 580 390" width="580" height="390" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_sentinel():
    b = [SVG_DEFS]
    b.append(box(20, 60, 130, 56, "Agent", "any LLM / framework"))
    b.append(box(200, 60, 150, 56, "Decision record", "inputs · seed · tools"))
    b.append(arrow(150, 88, 198, 88))
    # hash chain
    for i in range(3):
        x = 400 + i * 105
        b.append(box(x, 60, 92, 56, f"Block {i+1}", "SHA-256 linked", fs=12))
        if i:
            b.append(arrow(x - 13, 88, x - 2, 88))
    b.append(arrow(350, 88, 398, 88))
    b.append(f'<text x="560" y="140" text-anchor="middle" fill="#98a2b8" font-size="11">tamper-evident ledger</text>')
    # replay path
    b.append(box(200, 190, 150, 56, "Tool cassettes", "captured effects", fs=12))
    b.append(box(400, 190, 197, 56, "Replay engine", "deterministic re-execution"))
    b.append(arrow(476, 116, 476, 188))
    b.append(arrow(350, 218, 398, 218))
    # verdicts
    for i, (lab, col) in enumerate([("MATCH", "#7ee2a8"), ("DIVERGED", "#f0b35e"), ("UNREPLAYABLE", "#f08787")]):
        b.append(box(120 + i * 165, 300, 150, 48, lab, "verdict", fill="#101827", stroke=col, tcolor=col))
    b.append(arrow(498, 246, 195, 298, color="#8fa2c8"))
    b.append(arrow(498, 246, 360, 298, color="#8fa2c8"))
    b.append(arrow(498, 246, 525, 298, color="#8fa2c8"))
    b.append(f'<text x="60" y="330" fill="#f08787" font-size="12">forged entry →</text>')
    b.append(f'<text x="60" y="348" fill="#f08787" font-size="12">chain break detected</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 640 370" width="640" height="370" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_forge():
    b = [SVG_DEFS]
    b.append(box(20, 90, 130, 60, "Request queue", "Poisson arrivals"))
    # scheduler with 3 policies
    b.append(box(200, 30, 170, 180, "", "", fill="#101827", stroke="#3b4d75"))
    b.append(f'<text x="285" y="56" text-anchor="middle" fill="#e8ebf2" font-size="13" font-weight="700">Scheduler</text>')
    for i, lab in enumerate(["static-fcfs", "continuous", "continuous-srpt"]):
        b.append(box(220, 72 + i * 44, 130, 36, lab, "", fs=12,
                     fill="#1b2340" if i else "#141c2e",
                     stroke="#6ea8fe" if i else "#3b4d75"))
    b.append(arrow(150, 120, 198, 120))
    for i in range(3):
        b.append(arrow(370, 90 + i * 44, 418, 90 + i * 44))
    b.append(box(420, 60, 150, 120, "GPU execution", "t = T0 + K · batch tokens"))
    b.append(box(420, 210, 150, 56, "KV cache ≤ 8192", "admission control", fs=12))
    b.append(arrow(495, 180, 495, 208))
    b.append(arrow(495, 266, 495, 300, dashed=True))
    b.append(box(420, 302, 150, 56, "Completions", "TTFT · e2e · throughput", fs=12))
    b.append(f'<text x="285" y="250" text-anchor="middle" fill="#98a2b8" font-size="11">iteration-level batching refills freed slots</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 600 380" width="600" height="380" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_skillbridge():
    b = [SVG_DEFS]
    steps = [
        ("SkillPackage", "manifest · eval"),
        ("Registry", "versioned"),
        ("PolicyEngine", "allowlist · sensitivity"),
        ("CapabilityBroker", "binds capabilities"),
        ("ModelAdapter", "provider translation"),
        ("SkillRuntime", "executes · audits"),
        ("EvalHarness", "cross-model eval"),
    ]
    x = 10
    for i, (lab, sub) in enumerate(steps):
        b.append(box(x, 50, 128, 62, lab, sub, fs=12,
                     fill="#1b2340" if i in (2, 4) else "#141c2e",
                     stroke="#6ea8fe" if i in (2, 4) else "#3b4d75"))
        if i < len(steps) - 1:
            b.append(arrow(x + 128, 81, x + 138, 81))
        x += 138
    # MCP servers bound under the broker (4th box: x = 10+3*138 = 424)
    for j, srv in enumerate(["text-tools", "dev-tools", "kb-server"]):
        sx = 352 + j * 138
        b.append(box(sx, 160, 128, 42, srv, "MCP server", fs=12))
        b.append(arrow(488, 112, sx + 64, 158, dashed=True))
    b.append(f'<text x="488" y="228" text-anchor="middle" fill="#98a2b8" font-size="11">capabilities resolve to MCP servers at runtime</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 990 245" width="990" height="245" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_cmf():
    b = [SVG_DEFS]
    for i, (lab, sub) in enumerate([("Agent α", "0.95 accurate"), ("Agent β", "0.85 accurate"), ("Agent γ", "0.72 accurate")]):
        b.append(box(20, 30 + i * 70, 130, 54, lab, sub, fs=12))
        b.append(arrow(150, 57 + i * 70, 196, 110))
    b.append(box(200, 80, 150, 60, "Admission gate", "evidence + confidence"))
    b.append(box(390, 80, 150, 60, "Conflict detection", "same subject·predicate"))
    b.append(arrow(350, 110, 388, 110))
    b.append(box(200, 200, 340, 64, "Reconciliation", "score = confidence × recency × (1 + 0.25 × distinct agents)", fs=12, fill="#1b2340", stroke="#6ea8fe"))
    b.append(arrow(465, 140, 370, 198))
    b.append(arrow(275, 140, 275, 198))
    b.append(box(200, 304, 160, 56, "Claim store", "active versions"))
    b.append(box(380, 304, 160, 56, "Tombstones", "superseded · revoked", fs=12))
    b.append(arrow(320, 264, 280, 302))
    b.append(arrow(420, 264, 460, 302))
    b.append(box(580, 190, 130, 90, "Query / MCP", "cmf://claims/…"))
    b.append(arrow(540, 232, 578, 232, color="#7ee2a8", marker="arrg"))
    b.append(f'<text x="645" y="300" text-anchor="middle" fill="#f08787" font-size="12">one loud agent</text>')
    b.append(f'<text x="645" y="318" text-anchor="middle" fill="#f08787" font-size="12">cannot outvote many</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 730 390" width="730" height="390" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_healflow():
    b = [SVG_DEFS]
    # workflow DAG
    for i, lab in enumerate(["validate", "charge", "reserve"]):
        x = 20 + i * 130
        b.append(box(x, 40, 115, 54, lab, "contract-checked", fs=12,
                     fill="#1a2b1f" if lab == "charge" else "#141c2e",
                     stroke="#3f7a52" if lab == "charge" else "#3b4d75"))
        if i < 2:
            b.append(arrow(x + 115, 67, x + 130, 67))
    b.append(f'<text x="215" y="120" text-anchor="middle" fill="#98a2b8" font-size="11">preconditions → checkpoint → execute → postconditions</text>')
    # failure path down
    b.append(arrow(280, 94, 280, 140))
    b.append(box(180, 145, 200, 56, "Diagnoser", "causal walk-back → culprit"))
    b.append(box(180, 235, 200, 96, "Repair ladder", "retry → substitute → rollback → compensate", fs=11, fill="#1b2340", stroke="#6ea8fe"))
    b.append(arrow(280, 201, 280, 233))
    b.append(box(180, 365, 200, 56, "Verifier", "re-check contracts"))
    b.append(arrow(280, 331, 280, 363))
    b.append(arrow(180, 393, 60, 393, color="#7ee2a8", marker="arrg"))
    b.append(f'<text x="120" y="385" text-anchor="middle" fill="#7ee2a8" font-size="11">resume</text>')
    b.append(arrow(380, 393, 470, 393, color="#f08787"))
    b.append(f'<text x="425" y="385" text-anchor="middle" fill="#f08787" font-size="11">escalate</text>')
    # repair memory side box
    b.append(box(430, 145, 200, 120, "Repair memory", "failure signature → validated repair", fs=12, fill="#241d10", stroke="#f0b35e"))
    b.append(arrow(430, 205, 382, 205, dashed=True, color="#f0b35e"))
    b.append(f'<text x="530" y="290" text-anchor="middle" fill="#f0b35e" font-size="11">transfers across workflows</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 440" width="660" height="440" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_intent_inference():
    b = [SVG_DEFS]
    # top: traditional path (dead end)
    b.append(f'<text x="20" y="22" fill="#f08787" font-size="12" font-weight="700">traditional: classify</text>')
    top = ["utterance", "TF-IDF", "softmax", "ONE LABEL"]
    for i, lab in enumerate(top):
        x = 20 + i * 155
        b.append(box(x, 35, 140, 50, lab, fs=12,
                     fill="#2a1620" if lab == "ONE LABEL" else "#141c2e",
                     stroke="#a04a5a" if lab == "ONE LABEL" else "#3b4d75"))
        if i < 3:
            b.append(arrow(x + 140, 60, x + 155, 60))
    b.append(f'<text x="20" y="108" fill="#f08787" font-size="11">no memory, no goals — paraphrases and novel utterances end in "unknown"</text>')
    # bottom: inference path
    b.append(f'<text x="20" y="142" fill="#7ee2a8" font-size="12" font-weight="700">inference: understand, then goals, then plan</text>')
    stages = [("memory", "entities, facts, goals"),
              ("semantics", "frame — no labels"),
              ("goals", "primary/secondary, missing info"),
              ("planner", "ask vs act, tools")]
    for i, (lab, sub) in enumerate(stages):
        x = 20 + i * 155
        b.append(box(x, 155, 140, 56, lab, sub, fs=12,
                     fill="#1a2b1f", stroke="#3f7a52"))
        if i < 3:
            b.append(arrow(x + 140, 183, x + 155, 183, color="#7ee2a8", marker="arrg"))
    b.append(arrow(555, 211, 555, 250, color="#7ee2a8", marker="arrg"))
    b.append(box(430, 255, 210, 56, "orchestrator", "specialist agents → response", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'


def svg_semantic_fabric():
    b = [SVG_DEFS]
    b.append(box(20, 140, 120, 56, "raw reality", "10k txns, logs, text"))
    layers = ["L0 struct", "L1 stat", "L2 behav", "L3 relat", "L4 temp", "L5 causal", "L6 intent", "L7 cogn"]
    for i, lab in enumerate(layers):
        x = 170 + (i % 4) * 120
        y = 60 + (i // 4) * 70
        b.append(box(x, y, 108, 54, lab, "extractor", fs=11))
        b.append(arrow(140, 168, x + 54, y + 54 if i // 4 == 1 else y, color="#6ea8fe", marker="arr"))
    b.append(box(170, 210, 228, 56, "semantic store", "versioned, hashed, no raw data", fs=12,
                 fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(430, 210, 200, 56, "reasoning", "retrieve · simulate · diagnose", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    b.append(arrow(398, 238, 428, 238, color="#7ee2a8", marker="arrg"))
    b.append('<text x="330" y="300" text-anchor="middle" fill="#99a4ba" font-size="11">store meaning, not data — 27.2:1 compression, reasoning without raw rows</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_decision_partition():
    b = [SVG_DEFS]
    decs = [("identity", "3"), ("damage", "10"), ("policy", "8"), ("fraud", "10"), ("settlement", "4")]
    for i, (lab, sc) in enumerate(decs):
        y = 20 + i * 58
        col = "#a04a5a" if sc == "10" else ("#8a6d3b" if sc == "8" else "#3f7a52")
        b.append(box(20, y, 150, 46, lab, f"score {sc}", fs=12, stroke=col))
    b.append(box(230, 40, 180, 60, "damage specialist", "dedicated, score 10", fs=12, fill="#2a1620", stroke="#a04a5a"))
    b.append(box(230, 120, 180, 60, "fraud specialist", "dedicated, score 10", fs=12, fill="#2a1620", stroke="#a04a5a"))
    b.append(box(230, 200, 180, 60, "compliance", "shared, score 8", fs=12))
    b.append(box(230, 270, 180, 46, "intake", "grouped: identity + settlement", fs=12, fill="#1a2b1f", stroke="#3f7a52"))
    for y1, y2 in [(43, 70), (159, 150), (217, 230), (275, 293)]:
        b.append(arrow(170, y1, 228, y2, color="#8fa2c8", marker="arr"))
    b.append('<text x="330" y="322" text-anchor="middle" fill="#99a4ba" font-size="11">score = state blocks x weight; 5 decisions -> 4 agents, 42-66% fewer than 1:1</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_sre_observability():
    b = [SVG_DEFS]
    layers = ["infra", "network", "platform", "app", "service", "product"]
    for i, lab in enumerate(layers):
        x = 20 + i * 104
        b.append(box(x, 60, 94, 54, lab, "observer", fs=11))
        if i < 5:
            gap = "#f08787" if lab == "service" else "#8fa2c8"
            b.append(arrow(x + 94, 87, x + 104, 87, color=gap, marker="arr"))
    b.append(f'<text x="330" y="140" text-anchor="middle" fill="#f08787" font-size="11">boundary blind spot: service-&gt;product recall 0.00</text>')
    b.append(box(180, 170, 300, 56, "boundary assessment", "TP/TN/FN + time-to-detect per boundary", fs=12,
                 fill="#2a1620", stroke="#a04a5a"))
    b.append(box(180, 250, 140, 54, "unified response", "100% runbook, 78m MTTR", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(340, 250, 140, 54, "strategy bridge", "$100k: 320->80m downtime", fs=11, fill="#1b2340", stroke="#6ea8fe"))
    b.append('<text x="330" y="326" text-anchor="middle" fill="#99a4ba" font-size="11">measure the gaps at layer intersections, then close them — and fund reliability like a portfolio</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_emergent_goals():
    b = [SVG_DEFS]
    for i in range(4):
        x = 20 + i * 120
        b.append(box(x, 60, 108, 60, f"agent {i+1}", "collect + deposit", fs=12))
        b.append(box(x, 150, 108, 44, "curiosity", "intrinsic drive", fs=10, fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(230, 230, 200, 56, "broadcast channel", "4 tokens, no fixed meanings", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    for i in range(4):
        b.append(arrow(20 + i * 120 + 54, 120, 300 + (i - 1.5) * 20, 228, color="#8fa2c8", marker="arr"))
    b.append('<text x="330" y="312" text-anchor="middle" fill="#99a4ba" font-size="11">communication catalyzes self-made goals (49.5 vs 34.5) — but curiosity is metabolically costly</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_ai_risk_twin():
    b = [SVG_DEFS]
    arts = ["arch spec", "IaC", "MCP manifest", "doc claims"]
    for i, lab in enumerate(arts):
        x = 20 + i * 160
        b.append(box(x, 30, 145, 50, lab, "evidence L0-L5", fs=11))
        b.append(arrow(x + 72, 80, 330, 130, color="#8fa2c8", marker="arr"))
    b.append(box(230, 130, 200, 56, "AI use-case twin", "components · flows · identities", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    b.append(box(230, 215, 200, 56, "28-rule engine", "NIST · OWASP · EU AI Act · GDPR", fs=12,
                 fill="#2a1620", stroke="#a04a5a"))
    b.append(arrow(330, 186, 330, 213, color="#f08787", marker="arr"))
    b.append(box(60, 215, 140, 56, "funnel", "125 -> 53 questions", fs=11))
    b.append(box(460, 215, 140, 56, "findings", "29: 13 design, 16 info", fs=11))
    b.append('<text x="330" y="300" text-anchor="middle" fill="#99a4ba" font-size="11">evidence-seeking, not answer-seeking — readiness 0.41: NOT READY for CISO submission</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_ideology_mirror():
    b = [SVG_DEFS]
    b.append(box(250, 20, 160, 54, "neutral KB", "8 topics x 3 frames", fs=12))
    ideo = [("alpha", "+0.26 econ"), ("beta", "-0.31 econ"), ("gamma", "~0 neutral")]
    for i, (lab, sub) in enumerate(ideo):
        x = 20 + i * 215
        b.append(box(x, 110, 200, 56, lab, sub, fs=12,
                     fill="#2a1620" if lab == "beta" else "#141c2e",
                     stroke="#a04a5a" if lab == "beta" else "#3b4d75"))
        b.append(arrow(330, 74, x + 100, 108, color="#8fa2c8", marker="arr"))
    b.append(box(20, 200, 200, 56, "red-team battery", "framing bias · refusals", fs=11))
    b.append(box(230, 200, 200, 56, "drift gate", "CI: worst-dim check", fs=11))
    b.append(box(440, 200, 200, 56, "constitution", "steer -> conformance 1.0", fs=11,
                 fill="#1a2b1f", stroke="#3f7a52"))
    b.append('<text x="330" y="290" text-anchor="middle" fill="#99a4ba" font-size="11">same knowledge, three creators: pairwise divergence up to 1.546 — alignment is the ideology</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_sre_learning():
    b = [SVG_DEFS]
    b.append(box(20, 130, 130, 60, "incident history", "792 incidents, 180d", fs=11))
    agents = ["change risk", "causality", "similarity", "resolution"]
    for i, lab in enumerate(agents):
        x = 180 + i * 118
        b.append(box(x, 130, 108, 60, lab, "trained agent", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
        b.append(arrow(150, 160, 178, 160, color="#7ee2a8", marker="arrg"))
    b.append(box(180, 230, 460, 54, "workflow: change -> causality/similarity -> resolution -> learn", fs=11,
                 fill="#1b2340", stroke="#6ea8fe"))
    b.append('<text x="330" y="312" text-anchor="middle" fill="#99a4ba" font-size="11">AUC 0.761 = Bayes ceiling; continuous learner climbs 0.58 -> 0.67 under drift</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_leadership_insights():
    b = [SVG_DEFS]
    srcs = ["Jira", "GitHub", "ServiceNow", "Workday", "Planview"]
    for i, lab in enumerate(srcs):
        x = 20 + i * 128
        b.append(box(x, 40, 116, 50, lab, "source", fs=11))
        b.append(arrow(x + 58, 90, 330, 140, color="#8fa2c8", marker="arr"))
    b.append(box(230, 140, 200, 54, "entity resolution", "F1 1.00, 2153 rows", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    lenses = ["CTO/DORA", "CFO/licenses", "client/CSAT", "HR/retention"]
    for i, lab in enumerate(lenses):
        x = 20 + i * 160
        b.append(box(x, 230, 148, 54, lab, "lens", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
    b.append('<text x="330" y="312" text-anchor="middle" fill="#99a4ba" font-size="11">7 insights joined vs 1 siloed — $35,040/yr license waste found exactly</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_enriched_observability():
    b = [SVG_DEFS]
    stages = [("raw", "telemetry"), ("processed", "anomaly · forecast"), ("analytic", "p(fail) · impact · action")]
    for i, (lab, sub) in enumerate(stages):
        x = 20 + i * 215
        b.append(box(x, 60, 200, 60, lab, sub, fs=12,
                     fill="#1a2b1f" if lab == "analytic" else "#141c2e",
                     stroke="#3f7a52" if lab == "analytic" else "#3b4d75"))
        if i < 2:
            b.append(arrow(x + 200, 90, x + 215, 90, color="#7ee2a8", marker="arrg"))
    b.append(box(20, 160, 200, 54, "5 layers", "infra → business", fs=11))
    b.append(box(235, 160, 200, 54, "chain reconstruction", "recall 1.00, 0 spurious", fs=11,
                 fill="#1b2340", stroke="#6ea8fe"))
    b.append(box(450, 160, 190, 54, "5 role views", "relevance 1.00", fs=11))
    b.append('<text x="330" y="250" text-anchor="middle" fill="#99a4ba" font-size="11">18.2 raw alerts collapse into one 5-link causal chain — each role gets its slice</text>')
    b.append('<text x="330" y="272" text-anchor="middle" fill="#99a4ba" font-size="11">forecast MAE 3.4 min to breach; robust detectors beat naive thresholds on precision</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

# ---------------------------------------------------------------------------

def svg_delegation_integrity():
    b = [SVG_DEFS]
    b.append(box(250, 20, 160, 54, "user", "principal: top of hierarchy", fs=12, fill="#1a2b1f", stroke="#3f7a52"))
    agents = [("A", "scoped token"), ("B", "attenuated"), ("C", "attenuated 2x")]
    for i, (lab, sub) in enumerate(agents):
        x = 60 + i * 185
        b.append(box(x, 120, 170, 56, f"agent {lab}", sub, fs=11))
        b.append(arrow(330 if i == 0 else 60 + (i-1) * 185 + 170, 47 if i == 0 else 148,
                       x + 85, 118, color="#7ee2a8", marker="arrg"))
    b.append(box(60, 220, 220, 56, "confused deputy", "data disguised as instruction", fs=11,
                 fill="#2a1620", stroke="#a04a5a"))
    b.append(box(380, 220, 220, 56, "provenance firewall", "attack success 1.00 -> 0.00", fs=11,
                 fill="#1a2b1f", stroke="#3f7a52"))
    b.append('<text x="330" y="306" text-anchor="middle" fill="#99a4ba" font-size="11">every delegation logged, every instruction tagged with its principal</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_horizon_scaling():
    b = [SVG_DEFS]
    b.append('<text x="20" y="22" fill="#99a4ba" font-size="11">success rate vs horizon length N</text>')
    b.append('<line x1="60" y1="260" x2="620" y2="260" stroke="#3b4d75"/>')
    b.append('<line x1="60" y1="260" x2="60" y2="40" stroke="#3b4d75"/>')
    import math
    pts = []
    for i in range(41):
        x = 60 + i * 14
        y = 260 - 215 * math.exp(-0.0408 * i * 2)
        pts.append(f"{x:.0f},{y:.0f}")
    b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#f08787" stroke-width="2.5"/>')
    pts2 = []
    for i in range(41):
        x = 60 + i * 14
        y = 260 - 215 * math.exp(-0.0038 * i * 2)
        pts2.append(f"{x:.0f},{y:.0f}")
    b.append(f'<polyline points="{" ".join(pts2)}" fill="none" stroke="#7ee2a8" stroke-width="2.5"/>')
    b.append('<text x="480" y="120" fill="#f08787" font-size="11">baseline: 0.804 -> 0.035</text>')
    b.append('<text x="480" y="70" fill="#7ee2a8" font-size="11">hierarchy: 0.740 at N=80</text>')
    b.append('<text x="330" y="300" text-anchor="middle" fill="#99a4ba" font-size="11">decay is exponential (R2=0.9999); hierarchy flattens it — cheapest beyond N=10</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_attention_economics():
    b = [SVG_DEFS]
    b.append(box(20, 120, 150, 60, "agent", "confidence 0.80", fs=12))
    b.append(box(255, 40, 150, 60, "human", "budget: N/hr, 95% accurate", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(255, 200, 150, 60, "act alone", "risk: error x stakes", fs=11, fill="#2a1620", stroke="#a04a5a"))
    b.append(arrow(170, 140, 253, 80, color="#7ee2a8", marker="arrg", label="escalate"))
    b.append(arrow(170, 160, 253, 220, color="#f08787", marker="arr"))
    b.append(box(460, 120, 160, 60, "EV rule", "stakes-adjusted threshold", fs=11, fill="#1b2340", stroke="#6ea8fe"))
    b.append(arrow(405, 70, 458, 130, color="#8fa2c8", marker="arr"))
    b.append('<text x="330" y="300" text-anchor="middle" fill="#99a4ba" font-size="11">total cost = asks x cint + errors x stakes x cerr — overconfidence costs 6x underconfidence</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_injection_containment():
    b = [SVG_DEFS]
    chain = ["orchestrator", "researcher", "writer", "tool caller"]
    for i, lab in enumerate(chain):
        x = 20 + i * 160
        b.append(box(x, 60, 145, 54, lab, f"hop {i+1}", fs=11,
                     fill="#2a1620" if i == 3 else "#141c2e",
                     stroke="#a04a5a" if i == 3 else "#3b4d75"))
        if i < 3:
            b.append(arrow(x + 145, 87, x + 160, 87, color="#f08787", marker="arr"))
    b.append('<text x="330" y="140" text-anchor="middle" fill="#f08787" font-size="11">injected instruction propagates: attack success 0.65-0.74 at every depth</text>')
    b.append(box(20, 180, 200, 56, "provenance firewall", "taint: strict block 1.00", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(230, 180, 200, 56, "privilege boundary", "actions -> 0.00, FP 0.00", fs=11, fill="#1a2b1f", stroke="#3f7a52"))
    b.append(box(440, 180, 200, 56, "mosaic detector", "cross-source catch 1.00", fs=11, fill="#1b2340", stroke="#6ea8fe"))
    b.append('<text x="330" y="266" text-anchor="middle" fill="#99a4ba" font-size="11">subtle nudge survives sanitizers (0.74) — only provenance stops it; combined: 0.00 residual</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

def svg_behavioral_regression():
    b = [SVG_DEFS]
    vers = [("v1", "baseline"), ("v2", "adopt"), ("v3", "ROLLBACK"), ("v4", "pin"), ("v5", "rollback")]
    for i, (lab, sub) in enumerate(vers):
        x = 20 + i * 128
        col = "#a04a5a" if "ROLLBACK" in sub or sub == "rollback" else ("#3f7a52" if sub == "adopt" else "#3b4d75")
        b.append(box(x, 60, 116, 56, lab, sub, fs=11, stroke=col,
                     fill="#2a1620" if "ROLLBACK" in sub else "#141c2e"))
    b.append(box(180, 160, 300, 56, "frozen battery (120 tasks)", "paired tests vs v1, p<0.05 + material", fs=12,
                 fill="#1b2340", stroke="#6ea8fe"))
    b.append(box(180, 250, 140, 54, "canary 1%->10%", "v3 stopped at 40 tasks", fs=11))
    b.append(box(340, 250, 140, 54, "severity rank", "v3 2.467 >> v5 0.765", fs=11))
    b.append('<text x="330" y="326" text-anchor="middle" fill="#99a4ba" font-size="11">4/4 policy decisions match ground truth; battery blind below ~60 tasks</text>')
    inner = "\n".join(b)
    return f'<svg viewBox="0 0 660 330" width="660" height="330" xmlns="http://www.w3.org/2000/svg">{inner}</svg>'

# Project content
# ---------------------------------------------------------------------------
PROJECTS = [
dict(
 slug="meridian-orchestration", num="01",
 name="Meridian Orchestration",
 tagline="Multi-orchestrator, multi-agent task execution with learned decision optimization",
 category="orchestration", repo="01-meridian-orchestration", arch=svg_meridian,
 problem="Complex knowledge work must be decomposed across specialized agents, but a single orchestrator becomes a bottleneck: it serializes decisions, routes every subtask through one policy, and wastes expensive worker capacity on trivial steps while starving hard ones.",
 gap="Existing orchestrators use fixed topologies and hand-tuned routing rules. There is no online learning of which worker tier fits which subtask, horizontal agent-to-agent coordination is ad hoc, and the tradeoff between quality, cost, and latency is managed by static thresholds rather than an explicit optimization objective.",
 solution="Meridian combines a <b>vertical hierarchy</b> (meta-orchestrator → domain orchestrators → workers) with a <b>horizontal blackboard</b> (propose / request / commit, with escalation avoidance) and a <b>decision optimizer</b>: a contextual Thompson-sampling router with profile-based priors plus a decomposition planner, optimizing a scalarized objective of quality − cost − latency.",
 results_table="""
<table class="res"><tr><th>Config</th><th>Success</th><th>Mean quality</th><th>Cost/task</th><th>Latency</th></tr>
<tr><td>Single agent</td><td>83.3%</td><td>0.742</td><td>$0.124</td><td>8.0s</td></tr>
<tr><td>Vertical only</td><td>74.2%</td><td>0.731</td><td>$0.112</td><td>6.6s</td></tr>
<tr><td>Vertical + horizontal</td><td>73.8%</td><td>0.737</td><td>$0.087</td><td>5.2s</td></tr>
<tr><td>+ hand-tuned tiers</td><td>90.8%</td><td>0.782</td><td>$0.169</td><td>6.4s</td></tr>
<tr><td><b>Meridian (full)</b></td><td><b class="hl">90.4%</b></td><td><b>0.797</b></td><td>$0.183</td><td>7.0s</td></tr></table>
<p>240 tasks, seed 7; 95% CIs in the repo. The learned router <b>matches the hand-tuned tiering policy</b> (90.4% vs 90.8%) with zero hand-tuning — and keeps adapting online, which a fixed rule cannot do.</p>""",
 insights=[
  "<b>Hierarchy alone is not enough.</b> Structure without routing intelligence just redistributes the same decisions (vertical-only underperforms a single agent).",
  "<b>The horizontal layer is the efficiency engine.</b> Peer-resolved handoffs avoid ~175 escalations per 240 tasks — but fixed tier routing fails hard subtasks.",
  "<b>Routing intelligence is the quality engine.</b> Matching worker tier to subtask difficulty lifts success from 74% to ~90%.",
  "<b>The optimizer discovers the hand-tuned policy on its own.</b> Profile-based priors prevent Thompson-sampling lock-in; decaying exploration keeps it adaptive.",
 ],
 impl_tree="""src/agentic_systems/meridian/
  tasks.py          # task generator: difficulty-tagged subtasks
  agents.py         # worker tiers (standard/pro) + capability profiles
  blackboard.py     # horizontal coordination: propose/request/commit
  optimizer.py      # contextual Thompson sampling + decomposition planner
  orchestrators.py  # meta + domain orchestrators (vertical hierarchy)
01-meridian-orchestration/
  experiments/run_experiments.py   # 5-config ablation, 240 tasks
  results/            # results.md + charts.png (generated)""",
),
dict(
 slug="sentinel-ledger", num="02",
 name="Sentinel Ledger",
 tagline="Tamper-evident evidence ledger and deterministic replay for agent decisions",
 category="trust", repo="02-sentinel-ledger", arch=svg_sentinel,
 problem="When agents make consequential decisions — financial, operational, compliance-bound — you must be able to prove <i>what</i> happened, <i>why</i>, and reproduce it <i>exactly</i>. Text logs don't provide that: they can be edited, they omit seeds and tool effects, and replays are approximate.",
 gap="Agent frameworks log unstructured text with no integrity guarantees. Replay is non-deterministic (model sampling, live tool calls), so 'it worked in replay' proves little, and fault location after a divergence is manual guesswork.",
 solution="Sentinel records every decision as a <b>SHA-256 hash-chained entry</b> (inputs, seed, model version, tool calls) and captures external effects in <b>tool cassettes</b>. The replay engine re-executes deterministically from the ledger, returning verdicts <b>MATCH / DIVERGED / UNREPLAYABLE</b> with step-level fault location. Forged entries break the chain and are detected on verify.",
 results_table="""
<table class="res"><tr><th>Scenario</th><th>n</th><th>Result</th></tr>
<tr><td>Clean replay</td><td>600</td><td><b class="hl">100% MATCH</b> (0.07 ms/decision)</td></tr>
<tr><td>Seed perturbed</td><td>150</td><td>100% DIVERGED</td></tr>
<tr><td>Tool result mutated</td><td>150</td><td>100% DIVERGED, 100% step-located</td></tr>
<tr><td>Seed stripped</td><td>150</td><td>100% UNREPLAYABLE</td></tr>
<tr><td>Ledger entry forged</td><td>1</td><td>detected at index 100</td></tr></table>
<p>Chain verification is O(n): 4,000 entries verify in ~52 ms.</p>""",
 insights=[
  "<b>Determinism is a design choice, not a model property.</b> Seeds + cassettes make replay exact even for stochastic agents.",
  "<b>Integrity must be structural.</b> Hash-chaining turns 'trust the log' into 'verify the log' — forgery is detected, not debated.",
  "<b>Verdicts beat diffs.</b> MATCH / DIVERGED / UNREPLAYABLE gives auditors and debuggers a decision, not a data dump.",
  "<b>Step-level location matters.</b> Knowing <i>which</i> step diverged turns replay from forensics into debugging.",
 ],
 impl_tree="""src/agentic_systems/sentinel/
  ledger.py         # hash-chained record store, verify(), tamper detection
  sim_agent.py      # instrumented agent: seeds + tool cassettes
02-sentinel-ledger/
  experiments/run_experiments.py   # clean replay + 4 fault injections""",
),
dict(
 slug="forge-inference", num="03",
 name="Forge Inference",
 tagline="LLM inference serving simulator: quantifying how scheduling policy shapes latency",
 category="performance", repo="03-forge-inference", arch=svg_forge,
 problem="Serving concurrent LLM requests on GPUs is a scheduling problem: requests arrive unpredictably with wildly different prompt and generation lengths. The wrong batching policy wastes GPU capacity and blows up user-facing latency.",
 gap="Teams choose serving configurations by folklore and vendor defaults. There is little accessible quantification of <i>how much</i> scheduling policy matters — how TTFT, p99, and throughput respond to load under static vs continuous batching.",
 solution="Forge is a <b>discrete-event simulator</b> of an inference engine: Poisson arrivals, iteration cost <i>t = T₀ + K · batch_tokens</i>, an 8,192-token KV-cache cap, chunked prefill. It compares <b>static FCFS</b> vs <b>continuous batching</b> vs <b>continuous + shortest-remaining-time-first</b> across low/medium/high load (1,500 requests per cell, seed 42).",
 results_table="""
<table class="res"><tr><th>Load</th><th>Policy</th><th>Mean e2e</th><th>p99 e2e</th><th>Mean TTFT</th><th>KV util</th></tr>
<tr><td rowspan="3">high (4 rps)</td><td>static-fcfs</td><td>189,503 ms</td><td>369,406 ms</td><td>186,770 ms</td><td>23%</td></tr>
<tr><td>continuous</td><td><b class="hl">20,607 ms</b></td><td>44,399 ms</td><td>14,431 ms</td><td>98%</td></tr>
<tr><td>continuous-srpt</td><td><b class="hl">13,652 ms</b></td><td>178,710 ms</td><td>7,506 ms</td><td>96%</td></tr></table>
<p>Continuous batching cuts mean latency <b>9.2×</b> at high load. SRPT cuts the mean another 34% — but p99 explodes 4×: classic starvation of long requests.</p>""",
 insights=[
  "<b>Policy dominates hardware at high load.</b> The same GPU does 9× better with iteration-level batching — scheduling is the lever.",
  "<b>TTFT is the most policy-sensitive metric</b> (18 ms vs 1,070 ms at low load, ~59×) — head-of-line blocking hits responsiveness first.",
  "<b>SRPT is a mean-vs-tail tradeoff.</b> Production SRPT needs anti-starvation (aging, fairness bands); the simulator makes the failure mode visible.",
  "<b>KV-cache utilization tells the story</b> (23% vs 98%): static batching wastes capacity on padding and idle slots.",
 ],
 impl_tree="""src/agentic_systems/forge/
  simulator.py      # discrete-event engine: arrivals, scheduler, KV cap
03-forge-inference/
  experiments/run_experiments.py   # 3 policies x 3 loads, 1500 req/cell""",
),
dict(
 slug="skillbridge-mcp", num="04",
 name="SkillBridge MCP",
 tagline="A model-agnostic framework for reusable AI skills",
 category="performance", repo="04-skillbridge-mcp", arch=svg_skillbridge,
 problem="Skills, instructions, tools, and workflows are coupled to specific model providers, prompting conventions, and tool-calling interfaces — producing duplicated engineering effort, vendor lock-in, inconsistent behavior, and rising maintenance costs.",
 gap="The Model Context Protocol (MCP) standardizes access to tools and context, but not <i>packaging, executing, governing, or evaluating</i> portable skills across heterogeneous environments. There is no 'develop once, deploy anywhere' layer for skills.",
 solution="SkillBridge defines portable <b>SkillPackages</b> (manifest + provider-neutral instructions + capability-referencing workflows + eval cases), a <b>versioned registry</b>, a <b>policy engine</b> (approved-tools allowlist, high-sensitivity approval gates, deprecation refusal), a <b>capability broker</b> binding to MCP servers, <b>model adapters</b> translating to each provider's calling convention, and a <b>cross-model eval harness</b>.",
 results_table="""
<table class="res"><tr><th>Skill</th><th>SkillBridge σ</th><th>Per-provider σ</th></tr>
<tr><td>pii-redactor</td><td>0.059</td><td>0.157</td></tr>
<tr><td>sql-generator</td><td>0.098</td><td>0.148</td></tr>
<tr><td>code-reviewer</td><td>0.052</td><td>0.104</td></tr>
<tr><td>meeting-summarizer</td><td>0.020</td><td>0.052</td></tr>
<tr><td>rag-answerer</td><td>0.071</td><td>0.142</td></tr></table>
<p>Cross-adapter pass-rate std <b>halved</b> (0.050 vs 0.100) across 132 eval cases × 3 adapters. Reuse economics: the framework pays off from <b>2+ models</b> (saves 345 dev-days at 5 models). Governance: <b>3/3 adversarial runs denied, 20/20 clean runs allowed</b>.</p>""",
 insights=[
  "<b>Standardization damps variance; it doesn't eliminate it.</b> The weakest adapter still trails on code-heavy skills — adapters aren't model upgrades.",
  "<b>Deterministic tool steps are portable by construction.</b> The invoice extractor passes 100% everywhere: push logic into tools, keep models for judgment.",
  "<b>Governance composes with portability.</b> Version deprecation and sensitivity gates work identically across providers because they sit above the adapter.",
  "<b>The economics argument is the adoption argument.</b> Per-provider rebuilds scale linearly; the framework cost is near-fixed.",
 ],
 impl_tree="""src/agentic_systems/skillbridge/
  skill.py          # SkillPackage: manifest + instructions + workflow + eval
  registry.py       # versioned registry, caret-range resolution
  capabilities.py   # CapabilityBroker -> MCP-style servers
  adapters.py       # openai / anthropic / local tool-convention adapters
  policy.py         # allowlist, sensitivity gates, deprecation
  runtime.py        # resolve -> govern -> bind -> execute -> audit
  eval.py           # cross-model portability harness
  catalog.py        # 6 skills, 132 eval cases""",
),
dict(
 slug="collective-memory-fabric", num="05",
 name="Collective Memory Fabric",
 tagline="A model-agnostic collective memory protocol for multi-agent systems",
 category="orchestration", repo="05-collective-memory-fabric", arch=svg_cmf,
 problem="Heterogeneous agents — different LLMs, tools, frameworks — must share knowledge, learn from each other's experience, and stay consistent over long horizons. An incorrect inference from one agent propagates; conflicting observations and stale facts compound.",
 gap="Shared databases, vector retrieval, and knowledge graphs store text but don't govern it: nothing checks that a contribution is <i>trustworthy, consistent, current, or appropriate</i> for every recipient. Naive 'wisdom of the crowd' (majority vote) is Sybil-vulnerable — one loud agent out-shouts many quiet ones.",
 solution="CMF treats memory as versioned <b>claims</b> (subject·predicate·value + evidence + provenance + validity window + confidence + access policy) with <b>admission gates</b>, <b>semantic conflict detection</b>, and <b>quorum reconciliation</b>: <i>score = confidence × recency × (1 + 0.25 × distinct agents)</i> — counting <b>independent sources, not raw claims</b>. Expiry, correction, and quorum revocation complete the lifecycle; claims serialize as MCP resources.",
 results_table="""
<table class="res"><tr><th>System</th><th>Mean success</th><th>During attack</th><th>Targeted wrong rate</th></tr>
<tr><td>independent (no sharing)</td><td>78.7%</td><td>77.9%</td><td>24.3%</td></tr>
<tr><td>vector-db (last-write-wins)</td><td>80.2%</td><td>57.9%</td><td>66.0%</td></tr>
<tr><td>provenance (majority vote)</td><td>84.0%</td><td>50.7%</td><td><b>86.0%</b></td></tr>
<tr><td><b>CMF (full fabric)</b></td><td><b class="hl">94.7%</b></td><td><b class="hl">98.0%</b></td><td><b class="hl">0.0%</b></td></tr></table>
<p>200 ticks, 8 agents × 3 model families, misinformation injected ticks 80–120 (5-seed average). Majority vote performs <i>worst</i> under attack — the attacker's 2 claims/tick outvote ~1.6 honest observations. CMF holds <b>98% success during the attack</b>. Cross-model transfer: the weakest family (γ, 0.72) rises from 69.1% alone to <b>94.5%</b> on the fabric.</p>""",
 insights=[
  "<b>Count sources, not claims.</b> The distinct-agent quorum is the entire defense: one confident liar can never outvote independent observers.",
  "<b>Majority vote is Sybil-vulnerable.</b> Frequency-based consensus amplifies attackers; source-based consensus resists them.",
  "<b>Governance is what makes sharing safe for weak models.</b> The least accurate family gains the most (+25pp) — the fabric, not the model, carries reliability.",
  "<b>Robustness has a bounded price:</b> fact flips converge in ~5–8 ticks (the cost of demanding corroboration), ~0.2 ms/tick for reconciliation.",
 ],
 impl_tree="""src/agentic_systems/memory_fabric/
  memory.py         # Claim, MemoryFabric: admit/merge/reconcile/query/revoke
  baselines.py      # independent, last-write-wins, majority-vote
  simulation.py     # 8 agents, 10 flipping facts, injected misinformation
05-collective-memory-fabric/
  experiments/run_experiments.py   # 4 systems x 5 seeds""",
),
dict(
 slug="healflow", num="06",
 name="HealFlow",
 tagline="A model-agnostic, self-healing runtime for agentic workflows",
 category="trust", repo="06-healflow", arch=svg_healflow,
 problem="Agentic workflows fail constantly: APIs go down, schemas drift, intermediate reasoning goes wrong, transactions half-complete. Retries and LLM replanning treat symptoms — and a bad recovery can repeat charges, corrupt state, or cascade.",
 gap="Retry re-executes the <i>symptom</i> instead of diagnosing the <i>cause</i> (it cannot fix schema drift or permanent corruption). Replanning restarts from scratch with no memory of the failure — re-running external side effects (the benchmark triple-charges a payment workflow). Nothing <i>verifies</i> a repair before resuming.",
 solution="HealFlow models workflows as <b>contract-checked DAGs</b> (pre/postconditions, compensations, risk levels) with <b>checkpoints</b>. On failure it performs <b>causal diagnosis</b> — walking the chain newest-first to find the culprit step — then applies the <b>smallest viable repair</b> (retry &lt; substitute &lt; rollback &lt; compensate+abort &lt; escalate), <b>verifies</b> contracts before resuming, and records validated strategies in a <b>repair memory</b> keyed by failure shape (transferable across workflows and models).",
 results_table="""
<table class="res"><tr><th>Scenario</th><th>HealFlow</th><th>Retry</th><th>Replan</th></tr>
<tr><td>transient outage</td><td>✅</td><td>✅</td><td>✅ (wasteful)</td></tr>
<tr><td>inventory permanently down (post-payment)</td><td>🛟 graceful abort, 0 side effects</td><td>❌ charged, no refund</td><td>❌ <b>triple charge</b></td></tr>
<tr><td>upstream schema change</td><td>✅ substitute</td><td>❌</td><td>❌</td></tr>
<tr><td>permanent plan corruption</td><td>✅ rollback → substitute</td><td>❌</td><td>❌</td></tr></table>
<p>Diagnosis accuracy 6/6. Side effects: HealFlow <b>0</b>, retry 1, replan 3. Repair-memory transfer: a strategy learned on one workflow applies to an analogous failure on another in <b>1 lookup</b>.</p>""",
 insights=[
  "<b>Unsafe recovery is worse than no recovery.</b> When repair is impossible, graceful abort with compensation is the only safe autonomous outcome.",
  "<b>Diagnosis beats repetition.</b> Every structural fault (schema drift, permanent corruption) defeats retry and replan; causal walk-back finds the culprit.",
  "<b>Verify, then resume.</b> The verification gate is what prevents a bad repair from cascading — failed verification escalates instead of looping.",
  "<b>Repair knowledge compounds.</b> Keying memory by failure shape (not workflow or model) makes validated strategies reusable — including by weaker models.",
 ],
 impl_tree="""src/agentic_systems/healflow/
  workflow.py       # DAG + contracts + checkpoints + rollback
  faults.py         # deterministic fault injector (outage/schema/corrupt)
  diagnosis.py      # causal walk-back, cause taxonomy
  repair.py         # RepairMemory: failure signature -> validated repair
  runtime.py        # HealFlow loop + retry/replan baselines
  catalog.py        # 3 workflows: order, ETL, research
06-healflow/
  experiments/run_experiments.py   # 6 scenarios x 4 systems + transfer test""",
),
dict(
 slug="intent-inference", num="07",
 name="Intent Inference",
 tagline="Classification puts a label on words. Inference figures out what you want — goal, constraints, missing pieces — then plans.",
 category="orchestration", repo="07-intent-inference", arch=svg_intent_inference,
 problem="Traditional chatbots treat language understanding as classification: utterance → one predefined intent label → dialogue manager → API call. This breaks on paraphrases with low lexical overlap (\"Can you tell me whether I can afford lunch today?\"), multiple intents in one utterance (\"I forgot my password, but I also changed my phone number, and I can't receive OTP\"), implicit goals (\"I'm hungry\"), intent that evolves across turns (\"I have an interview tomorrow\" … \"What should I wear?\"), and utterances whose meaning exists only in context (\"Book me a hotel\" … \"Make it cheaper\"). A single label cannot represent any of these, and a stateless router cannot resolve the last two at all.",
 gap="Intent taxonomies are designed by developers, not discovered from users. Every utterance outside the catalog — or combining several in-catalog intents — collapses to the same dead end: a low-confidence prediction or a generic \"Sorry, I didn't understand. Please rephrase.\" Confidence scores measure how well an utterance matches training examples, not whether the system understands what the user wants. The dialogue manager has no notion of goals, missing information, or conversation history.",
 solution="A ChatGPT-style inference pipeline in which <b>intent is emergent, never classified</b>: conversation memory → semantic understanding (meaning frames, not labels) → goal extraction producing <b>structured goals</b> (primary/secondary, constraints, missing info, confidence) → task decomposition → planner (ask-vs-act, tool selection) → orchestrator dispatching specialist stub agents. Situation prototypes match utterances in embedding space with discriminative-term gating; per-clause decomposition handles multi-intent input; predicate-level disambiguation resolves \"afford lunch\" to money, not hunger; evidence-checked missing-info questions are asked only when the answer is genuinely absent.",
 results_table="""
<table class="res"><tr><th>Phenomenon</th><th>n</th><th>Classifier</th><th>Inference pipeline</th></tr>
<tr><td>paraphrase</td><td>5</td><td>0.40</td><td><b>1.00</b></td></tr>
<tr><td>multi-intent</td><td>3</td><td>0.00</td><td><b>1.00</b></td></tr>
<tr><td>latent</td><td>2</td><td>0.50</td><td><b>1.00</b></td></tr>
<tr><td>dynamic</td><td>1</td><td>0.00</td><td><b>1.00</b></td></tr>
<tr><td>context</td><td>3</td><td>0.33</td><td><b>1.00</b></td></tr>
<tr><td>out-of-catalog</td><td>2</td><td>0.00</td><td><b>1.00</b></td></tr>
<tr><td>standard</td><td>5</td><td>1.00</td><td><b>1.00</b></td></tr></table>
<p>Aggregate task success: classifier <b>45%</b> vs pipeline <b>100%</b> (recall 1.0, precision 1.0). The classifier's 7 clarifications are all the same useless fallback; the pipeline's 6 are targeted missing-info questions. No utterance ever yields "unknown".</p>""",
 insights=[
  "<b>One label cannot hold a conversation.</b> The classifier fails multi-intent and out-of-catalog structurally — a softmax over a fixed catalog has nowhere to put three goals or a novel one.",
  "<b>\"Unknown\" is an architecture failure, not a data gap.</b> The pipeline's clarifications are targeted missing-info questions — a different kind of clarification, asked for a reason.",
  "<b>Emergence beats enumeration.</b> Paraphrases like \"afford lunch today\" resolve through embedding neighborhoods plus predicate disambiguation — no training example required.",
  "<b>Memory is what makes the second turn work.</b> \"Make it cheaper\" and \"What should I wear?\" are meaningless as isolated classifications; inherited context turns them into refine_search and attire_advice.",
  "<b>Ask-vs-act needs evidence checks, not confidence thresholds.</b> Asking \"how much?\" when the user already said \"$200\" is as bad as never asking.",
 ],
 impl_tree="""src/agentic_systems/intent_inference/
  classifier.py     # TF-IDF + softmax regression (numpy) + dialogue manager
  embeddings.py     # semantic space over gated situation prototypes
  memory.py         # conversation memory: entities, goals, facts, anaphora
  goals.py          # structured goal extraction + missing-info evidence checks
  planner.py        # decomposition, ask-vs-act, tool selection
  orchestrator.py   # stub agents with deterministic structured outcomes
  pipeline.py       # the full inference loop; evaluate.py grades both systems
07-intent-inference/
  experiments/run_experiments.py   # frozen 20-case suite, seed 7""",
),

dict(
 slug="semantic-fabric", num="08",
 name="Semantic Fabric",
 tagline="Don't store data. Store meaning: an 8-layer semantic extraction pipeline that keeps cognition, not rows.",
 category="orchestration", repo="08-semantic-fabric", arch=svg_semantic_fabric,
 problem="Data lakes store rows; RAG indexes store embeddings. Both keep the raw material and re-derive meaning on every query. Raw data is transient and expensive; what the organization actually needs — behavior archetypes, causal chains, drift signatures — is recomputed from scratch or lost entirely when the raw logs age out.",
 gap="Classical ETL keeps structure, vector DBs keep latent similarity, knowledge graphs keep relations — but no single layer keeps statistical, behavioral, temporal, causal, and intentional semantics together, versioned, with freshness monitoring. Semantics decay (embeddings drift, behaviors change, causal links evolve) and nobody measures it.",
 solution="An 8-layer extraction pipeline (L0 structural → L1 statistical → L2 behavioral → L3 relational → L4 temporal → L5 causal → L6 intent → L7 abstract-cognitive) that distills raw reality into versioned, content-hashed semantic artifacts. A <b>semantic store</b> persists the artifacts while raw data is discarded; a <b>freshness monitor</b> tracks drift per layer; a <b>reasoner</b> answers retrieve/simulate/diagnose queries from the fabric alone.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>compression (10k txns)</td><td><b class="hl">27.2:1</b> — 1,974,056 → 72,495 bytes</td></tr>
<tr><td>causal DAG discovery</td><td>precision <b>0.75</b>, recall <b>1.00</b> (one spurious edge, honestly reported)</td></tr>
<tr><td>reasoning without raw data</td><td><b>4/4</b> queries agree with raw-data computation</td></tr>
<tr><td>drift detection (stationary)</td><td>false-positive rate <b>0.0</b> over 20 batches</td></tr>
<tr><td>layer ablation</td><td>full 1.00 → no-L5 0.50: every layer uniquely contributes</td></tr></table>
<p>Seed 7. L4 recovered the 168h period and the cpu→latency cascade; L7 mined the cross-team coordination motif. Two honest debugging notes: L2 drift needed Hungarian centroid matching (without it, stationary re-samples looked <i>more</i> drifted than a real break), and the L4 cascade detector had to switch from lagged correlation to spike-triggered analysis.</p>""",
 insights=[
  "<b>Compression is the product.</b> 10M transactions become 5 archetypes, 6 impact edges, 4 causal edges — the fabric stores what the data <i>meant</i>.",
  "<b>Semantics decay is measurable.</b> Versioned artifacts plus per-layer drift metrics turn 'the model feels stale' into a number with a threshold.",
  "<b>Causal is the layer that earns its keep.</b> Ablation drops query accuracy to 0.50 without L5 — correlation layers are not enough for diagnosis.",
 ],
 impl_tree="""src/agentic_systems/semantic_fabric/
  extract.py        # L0-L7 extractors over seeded synthetic ground truth
  store.py          # versioned, content-hashed semantic persistence
  freshness.py      # per-layer drift metrics + versioning
  reason.py         # retrieve / simulate / diagnose without raw data
08-semantic-fabric/
  experiments/run_experiments.py   # compression, quality, drift, ablation (seed 7)""",
),
dict(
 slug="decision-partition", num="09",
 name="Decision Partition",
 tagline="Score decision complexity, then cut the workflow into the fewest agents that respect it.",
 category="orchestration", repo="09-decision-partition", arch=svg_decision_partition,
 problem="Multi-agent workflows are usually partitioned by gut feel: one agent per task (wasteful coordination overhead) or one agent for everything (cognitive overload, muddy accountability). There is no principled way to decide how many agents a workflow needs or which decisions belong together.",
 gap="Complexity is discussed qualitatively ('this is a hard decision') but never scored. Without a score there is no optimization: teams can't trade agent count against load balance, can't re-partition when evidence changes, and can't explain <i>why</i> two decisions share an agent.",
 solution="A scoring model grounded in state distinctions: <b>score = |distinct state groups| × category weight</b> (simple 1.0, composite 2.0). Assignment rules: ≥10 → dedicated agent, 5–9 → shared by domain similarity, &lt;5 → grouped into a general agent. Plus dynamic re-scoring on new evidence, latency/compute cost add-ons, and sequential-stage planning with critical-path accounting.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>insurance worked example</td><td>scores (3, 10, 8, 10, 4) → <b class="hl">4 agents</b>, exact match to the design</td></tr>
<tr><td>scaling (10/25/50 decisions)</td><td>5.8 / 11.6 / 17.2 agents — <b>42–66% fewer</b> than naive 1:1</td></tr>
<tr><td>sensitivity</td><td>composite weight is the high-leverage parameter (churn 0.75–1.0 off base 2.0)</td></tr>
<tr><td>dynamic re-partition</td><td>5 evidence updates → exactly one re-partition each, stability 0.6–1.0, no thrash</td></tr>
<tr><td>latency-aware scoring</td><td>12-decision workflow grows 8 → 10 agents as latency weight rises</td></tr></table>
<p>Seeded runs. Critical-path score 17.0 with 6 cross-agent handoffs on the insurance example; coordination-overhead estimate at n=50 is 141 vs 1225 naive.</p>""",
 insights=[
  "<b>The weight is the decision.</b> Sweeping block counts moves 21–40% of assignments; sweeping the composite weight moves nearly everything — calibrate it deliberately.",
  "<b>Re-partition on threshold crossings, not on noise.</b> Level-crossing triggers give stability without thrash.",
  "<b>Expensive 'simple' decisions earn dedicated agents.</b> Latency-aware scoring promotes them once compute cost dominates.",
 ],
 impl_tree="""src/agentic_systems/decision_partition/
  decisions.py      # Decision model: category, blocks, domains, costs
  scoring.py        # score = blocks × weight + latency/compute add-ons
  partition.py      # dedicated / shared / grouped rules + rationales
  dynamic.py        # evidence updates, threshold-crossing re-partition
  planner.py        # topological staging, critical path, handoffs
09-decision-partition/
  experiments/run_experiments.py   # A-E: reproduction, scaling, sensitivity, dynamic, latency""",
),
dict(
 slug="sre-observability", num="10",
 name="SRE Observability",
 tagline="The boundary problem, measured: per-layer observers are blind at the seams — find the gaps, close them, fund reliability like a portfolio.",
 category="operations", repo="10-sre-observability", arch=svg_sre_observability,
 problem="Observability tools see their own layer well and the seams between layers badly. Infra-to-app and app-to-service boundaries are blind spots where cascading incidents go undetected — while SRE teams drown in per-layer alerts that never assemble into one incident context.",
 gap="Nobody scores observability <i>at the boundaries</i>. Teams buy more dashboards instead of measuring true positives, false negatives, and time-to-detect per layer <i>and</i> per intersection — so the weakest seam is never identified and never fixed.",
 solution="A MAS-based platform: per-layer observer agents with realistic capability profiles, a <b>boundary-assessment workflow</b> that ranks seams by observability gap (TP/TN/FN, time-to-detect), closed-loop targeted fixes, unified incident response, cross-layer context engineering — and a <b>strategy bridge</b> that treats reliability vs innovation as a portfolio optimization under a fixed budget.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>boundary problem</td><td>intra-layer recall <b>0.91</b> vs boundary link recall <b>0.78</b>; service→product <b>0.00</b> (blind)</td></tr>
<tr><td>closed loop</td><td>targeted fix at service→product: recall <b>0.00 → 1.00</b>, link time −3.0 min</td></tr>
<tr><td>cascades (n=15)</td><td>siloed 73% runbook / 102 min MTTR vs unified <b>100% / 78 min</b></td></tr>
<tr><td>strategy bridge ($100k)</td><td>downtime 320→80 min, cost $1.40M→$0.35M, ROI <b>1.00x → 2.26x</b></td></tr></table>
<p>Seeds 0–4. Detection used trailing median/MAD (mean/std collapses under incident crowding — documented as an insight). The product-layer cascade symptom sits below the detection threshold by design: that is precisely why the boundary needs cross-layer visibility.</p>""",
 insights=[
  "<b>Measure the seams, not just the layers.</b> The weakest boundary (service→product, gap 1.00) was identifiable from telemetry alone.",
  "<b>Robust baselines matter.</b> Mean/std detection masks the incident right after another incident; median/MAD does not.",
  "<b>Reliability is a portfolio.</b> The $100k optimizer balances boundary modules, runbooks, and feature work on one efficient frontier.",
 ],
 impl_tree="""src/agentic_systems/sre_observability/
  layers.py         # 6-layer telemetry simulator with cascading incidents
  observers.py      # per-layer observer agents, median/MAD detection
  boundary.py       # per-boundary TP/FN/F1, gap ranking
  response.py       # unified vs siloed responders, runbooks, MTTR
  strategy.py       # initiative portfolio optimizer + scorecard
10-sre-observability/
  experiments/run_experiments.py   # a-e: boundaries, closed loop, cascades, frontier (seeds 0-4)""",
),
dict(
 slug="emergent-goals", num="11",
 name="Emergent Goals",
 tagline="Do communicating agents invent their own goals? A seeded test of intrinsic motivation, with the failures reported too.",
 category="orchestration", repo="11-emergent-goals", arch=svg_emergent_goals,
 problem="The open question behind every 'autonomous agent' pitch: given agents with an assigned goal and continuous resource flow, will they evolve <i>additional</i> goals by themselves — and does communication trigger it? Claims abound; falsifiable tests do not.",
 gap="Intrinsic-motivation literature (curiosity, empowerment, IMGEP, novelty search, emergent communication) is rich in theory and thin in reproducible multi-agent tests with pre-registered hypotheses. Without ablations, any 'emergent' behavior is just story-telling.",
 solution="A grid world with metabolism, mortality, and continuous resource flow; N=10 agents with an assigned collect-and-deposit goal plus curiosity, empowerment, and homeostatic drives, a 4-token broadcast channel with learned (not assigned) meanings, and event-driven goal imagination. Five hypotheses fixed <b>before</b> results, four ablations (full / no-comm / extrinsic-only / no-goalgen), 6 seeds × 1500 steps.",
 results_table="""
<table class="res"><tr><th>Hypothesis</th><th>Result</th></tr>
<tr><td>H1: communication catalyzes goal invention</td><td><b>supported (modest)</b>: 49.5 vs 34.5 goals, d=+0.69</td></tr>
<tr><td>H3: goals target communicated locations</td><td><b>strongly supported</b>: 87% of goals; tokens specialized (0.45 vs 1.39 nats)</td></tr>
<tr><td>H2: continuity behaviors emerge</td><td><b>partial</b>: link maintenance yes (d=+1.55); caching not supported</td></tr>
<tr><td>H4: intrinsic drives aid survival</td><td><b>FAILED, reversed</b>: 413 vs 1185 steps — curiosity is metabolically costly</td></tr></table>
<p>Two unplanned findings: communication <i>reduces</i> goal diversity (conformity: 33.7 vs 18.8 distinct cells), and self-generated goals <b>cannibalize</b> the assigned objective (deposits 30.5 vs 124.5, d=−8.33) — direct evidence for the remit-divergence safety file. Full literature survey in <code>11-emergent-goals/DESIGN.md</code>.</p>""",
 insights=[
  "<b>Curiosity kills — in the short run.</b> Exploration costs energy; the extrinsic-only agents outlived everyone. Intrinsic motivation needs a budget.",
  "<b>Communication conforms.</b> Shared tokens coordinate agents onto the same goals; diversity needs a counter-force.",
  "<b>Self-made goals eat the assigned one.</b> Any deployment of goal-imagining agents needs remit guardrails (see system 09's cousin in the inference repo).",
 ],
 impl_tree="""src/agentic_systems/emergent_goals/
  env.py            # grid world: resources, metabolism, mortality
  agent.py          # curiosity + empowerment + homeostasis + goal imagination
  metrics.py        # goal rate/diversity, link maintenance, survival
  simulate.py       # 4 ablations, seeded
11-emergent-goals/
  DESIGN.md         # literature survey + pre-registered hypotheses
  experiments/run_experiments.py   # 6 seeds x 1500 steps""",
),
dict(
 slug="ai-risk-twin", num="12",
 name="AI Risk Twin",
 tagline="Architecture-first, evidence-seeking AI risk pre-check: reconstruct the system from artifacts, then prove what's risky.",
 category="trust", repo="12-ai-risk-twin", arch=svg_ai_risk_twin,
 problem="AI risk assessment is a static questionnaire that asks developers to self-report risk. Developers assert 'the agent is read-only' while the architecture shows <tt>POST /holdTransaction</tt> — and nobody checks.",
 gap="Answer-seeking tools trust assertions. Nothing reconstructs the system from architecture diagrams, IaC, and MCP manifests; nothing cross-checks documentation against the graph; nothing distinguishes a finding backed by runtime telemetry from one backed by a checkbox.",
 solution="An evidence-seeking pipeline: ingest artifacts → build the <b>AI use-case twin</b> (components, flows, identities, trust boundaries) with three-level parsing that <b>never trusts the diagram</b> (edges resolve against IaC into real access paths) → 28-rule knowledge engine (OWASP Agentic/LLM, GDPR, EU AI Act, NIST AI RMF, internal policy) → <b>dynamic funnel</b> (125 questions → triggered → auto-answered → evidence-required → clarification) → evidence hierarchy L0–L5 → design vs information findings → readiness score → fix-and-rerun diff → drift detection.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>worked example</td><td><b>2 inconsistencies</b>, 29 findings (13 design, 16 info), readiness <b>0.41 → NOT READY</b></td></tr>
<tr><td>funnel (agentic platform)</td><td>125 → 121 → 9 → 59 → 53 questions</td></tr>
<tr><td>fix-and-rerun</td><td><b>7 resolved</b>, 2 introduced (honestly reported), severity delta <b>−20</b></td></tr>
<tr><td>drift</td><td>unapproved PII exfil edge → <b>1 critical alert</b>; approved edges → 0</td></tr></table>
<p>Deterministic, byte-identical across reruns. Evidence sensitivity is honest: vendor evidence helps exactly where it applies (confidence 0.8082 → 0.8242), small elsewhere. Five criticals in the worked example: excessive agency, high-stakes action without human approval, PII → external LLM.</p>""",
 insights=[
  "<b>Artifact wins on disagreement.</b> When docs say read-only and the graph shows a write edge, the graph is right.",
  "<b>Evidence has levels.</b> L1 user assertion carries a 0.90 uncertainty penalty; L4 enterprise-system evidence 0.05. Confidence is computed, not claimed.",
  "<b>Readiness is separate from risk.</b> 'Not ready for CISO submission' (3 blocking evidence items) is a different statement from 'risky' — and more actionable.",
 ],
 impl_tree="""src/agentic_systems/ai_risk_twin/
  artifacts.py      # ingestors: arch spec, IaC, MCP manifests, doc claims
  twin.py           # use-case twin + 3-level parser (never trusts diagram)
  knowledge.py      # 28 rules + 125-question bank with triggers
  funnel.py         # dynamic question funnel
  findings.py       # design vs info findings, readiness scorer
  rerun.py / drift.py  # fix-and-rerun diff, runtime drift alerts
12-ai-risk-twin/
  experiments/run_experiments.py   # deterministic end-to-end""",
),
dict(
 slug="ideology-mirror", num="13",
 name="Ideology Mirror",
 tagline="LLMs reflect their creators' ideology. Measure the reflection: red-team the values, gate the drift, steer to your constitution.",
 category="trust", repo="13-ideology-mirror", arch=svg_ideology_mirror,
 problem="Every aligned model ships its creator's values — RLHF/DPO inject annotator and corporate preferences, and the creator effect overrides pre-training data. Enterprises deploying base models as-is import an ideology: product voice becomes the vendor's voice, global rollouts hit cultural friction, B2B deployments inherit compliance mismatches.",
 gap="Model governance covers security, privacy, and hallucinations — not <b>value alignment</b>. Nobody red-teams how a model <i>frames</i> what it says, nobody scores vendors on ideological risk at procurement, and nobody gates CI on alignment drift when the vendor ships a new version.",
 solution="A governance <b>measurement</b> framework (simulated stand-ins with parameterized creator ideology; the contribution is the methodology): value profiles across 6 dimensions, a red-team probe battery (framing bias, refusal asymmetry, emphasis divergence), the creator-effect harness (same knowledge, different ideologies → divergence), an AI Constitution with conformance scoring, vendor risk grades (A–F + contract clauses), and a worst-dimension drift gate for CI/CD.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>creator effect</td><td>pairwise divergence up to <b>1.546</b>; econ leans separate cleanly (+0.26 / −0.31 / ~0)</td></tr>
<tr><td>refusal asymmetry</td><td>0.50 on challenging vs 0.17 on supportive probes — <b>refusal is part of the ideology</b></td></tr>
<tr><td>drift gate</td><td>injected −0.90 shift → detected 0.244, CI <b>FAILs</b>, latency 1 probe</td></tr>
<tr><td>constitution steering</td><td>conformance → <b>1.000</b> for all profiles (must-answer refusals eliminated)</td></tr>
<tr><td>vendor grades</td><td>A / B / D across three profiles, with recommended clauses</td></tr></table>
<p>Seed 7. Honest limits, documented in the README: synthetic stand-ins (methodology validation, not claims about real models), quantized framing (sub-boundary shifts are nearly invisible — the gate uses worst-dimension, not mean, for exactly this reason), uncalibrated parameters.</p>""",
 insights=[
  "<b>Refusal is ideology, not safety alone.</b> Asymmetric refusal patterns are measurable and belong in the risk report.",
  "<b>Gate on the worst dimension.</b> Mean drift hides the one axis that moved; the CI gate fails on max per-dimension drift.",
  "<b>Steering works when it's explicit.</b> A written constitution plus grounding moves conformance to 1.000 — 'be neutral' is not a constitution.",
 ],
 impl_tree="""src/agentic_systems/ideology_mirror/
  values.py / knowledge.py / model.py  # profiles, neutral KB, parameterized stand-in
  redteam.py        # probe battery + framing/refusal/divergence metrics
  constitution.py   # AI constitution + conformance scorer
  vendor.py / drift.py / steering.py   # risk grades, CI gate, steering
13-ideology-mirror/
  experiments/run_experiments.py   # a-e, seed 7""",
),
dict(
 slug="sre-learning", num="14",
 name="SRE Learning",
 tagline="Train SRE agents on your incident history: your past outages are the training data for future prevention.",
 category="operations", repo="14-sre-learning", arch=svg_sre_learning,
 problem="SRE automation is built on theory: hand-written runbooks, static thresholds, generic playbooks. Meanwhile the organization sits on years of incident tickets, change records, and postmortems — the exact training data that would let agents learn <i>this</i> environment's failure modes — and uses none of it.",
 gap="No pipeline turns incident history into agent competence. Change→incident links are tribal knowledge; causal patterns live in postmortem PDFs; 'similar incident' means keyword search; resolution choices ignore what actually worked last time.",
 solution="A data-first pipeline (extract → enrich incidents with change context via temporal×service×topology correlation → per-agent datasets) training <b>four agents</b>: change-risk predictor (AUC 0.761 = Bayes ceiling, honest log-odds explanations), causal knowledge graph (top-3 path accuracy 0.99), learned similarity (P@1 1.00 vs TF-IDF 0.90), resolution recommender (0.89 vs 0.41 baseline) — coordinated by a confidence-routed workflow with a <b>continuous learning loop</b> (quality-gated retraining, active learning, learning-velocity metrics).",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>change-risk prediction</td><td>AUC <b>0.761</b> (Bayes ceiling); recovers true weights (MAE 0.14)</td></tr>
<tr><td>change→incident linking</td><td>top-1 0.73, top-3 <b>0.92</b></td></tr>
<tr><td>resolution success</td><td><b>0.89</b> vs 0.41 most-frequent baseline</td></tr>
<tr><td>learning under drift</td><td>frozen 0.58 → continuous <b>0.67</b> AUC; interventions 0.40 → 0.33</td></tr>
<tr><td>active learning</td><td>100 uncertainty labels beat 200 random (~<b>2x</b> efficiency)</td></tr></table>
<p>Seed 7; 2400 changes / 792 incidents / 180 days. Honest note: top-1 linking ties the recency baseline — the enrichment's value is the evidence-backed candidate set, not the argmax.</p>""",
 insights=[
  "<b>The ceiling is knowable.</b> Hitting the Bayes AUC proves the agent extracts everything the features contain — the next gain is better features, not a bigger model.",
  "<b>Learn the pipeline order.</b> Causal reasoning helps exactly when linking runs first — architecture order is a performance parameter.",
  "<b>Uncertainty is the labeling budget.</b> Active learning doubles label efficiency; random labels are the waste to cut.",
 ],
 impl_tree="""src/agentic_systems/sre_learning/
  synth.py / pipeline.py  # seeded world + incident↔change enrichment
  change_agent.py / causality.py / similarity.py / resolution.py
  workflow.py / learning.py  # conditional workflow + continuous loop
14-sre-learning/
  experiments/run_experiments.py   # a-g, seed 7""",
),
dict(
 slug="leadership-insights", num="15",
 name="Leadership Insights",
 tagline="Join Jira, GitHub, ServiceNow, Workday, and Planview — and answer the questions no single system can.",
 category="operations", repo="15-leadership-insights", arch=svg_leadership_insights,
 problem="Leadership decisions run on siloed dashboards: engineering sees tickets, finance sees licenses, HR sees attrition. The questions that matter — <i>is the review bottleneck raising change-failure rates? which licenses are actually waste? is the escalation cluster a staffing problem?</i> — require joins nobody performs.",
 gap="Per-source analytics can't do cross-source inference. Entity resolution across five systems (same person, different IDs) is the unglamorous prerequisite nobody builds, so 'integrated insights' stay slideware.",
 solution="An integration layer (entity resolution F1 1.00 over 2,153 rows, with collision and missing-email fallbacks) feeding <b>four leadership lenses</b> — CTO (DORA, PR analytics, bottleneck detector), CFO (license utilization, dollarized reclaim list), Client (CSAT drivers, escalation predictor), HR (productivity/satisfaction, retention risk) — plus a <b>cross-source insight engine</b> where every insight declares its required sources, making the siloed-vs-integrated ablation exact.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>injected issues recovered</td><td>bottleneck (0 false positives), licenses <b>20/20</b>, retention recall <b>1.0</b>, escalation cluster found</td></tr>
<tr><td>license waste</td><td><b>$35,040/yr</b> — exactly the planted amount</td></tr>
<tr><td>siloed vs integrated</td><td><b>7 vs 1</b> insights; 6 unreachable without joins</td></tr>
<tr><td>entity resolution</td><td>precision/recall/F1 <b>1.00</b></td></tr></table>
<p>Seed 7; 60 people, 6 teams, 180 days. Honest negative: the review-latency→change-failure hypothesis measured −23% lift, so the engine reports 'no link found' — it tests hypotheses, it doesn't confirm them.</p>""",
 insights=[
  "<b>The join is the insight.</b> 6 of 7 findings need ≥2 sources; per-source dashboards can never produce them.",
  "<b>A testing engine beats a confirming engine.</b> Reporting 'no link found' on a plausible hypothesis is the feature, not a failure.",
  "<b>Entity resolution is the moat.</b> F1 1.00 with collision handling is what makes the rest possible.",
 ],
 impl_tree="""src/agentic_systems/leadership_insights/
  generators.py / integrate.py  # seeded enterprise + entity resolution
  cto.py / cfo.py / client.py / hr.py  # four lenses
  cross.py        # cross-source insight engine (7 insights)
15-leadership-insights/
  experiments/run_experiments.py   # a-f, seed 7""",
),
dict(
 slug="enriched-observability", num="16",
 name="Enriched Observability",
 tagline="Raw → processed → analytic: a three-stage AI enrichment pipeline that turns 18 alerts into one causal chain.",
 category="operations", repo="16-enriched-observability", arch=svg_enriched_observability,
 problem="Engineers triage raw telemetry: 18 alerts for one incident, each layer speaking its own dialect. Classical detectors flag; nobody translates. The CTO gets the same alert storm as the on-call engineer.",
 gap="Pipelines stop at 'processed' (anomaly scores, dashboards). The <b>analytic</b> stage — failure probability, root-cause confidence, business impact, recommended action, role-tailored narrative — is manual, slow, and inconsistent.",
 solution="A per-layer three-stage pipeline: <b>raw</b> telemetry → <b>processed</b> (robust median/MAD anomaly scores, trend-slope breach forecasting, k-means symptom clustering, lagged cross-correlation) → <b>analytic</b> (failure probability, root-cause confidence, impact score, rule-based recommendations) → a cross-layer <b>chain reconstructor</b> (onset order + correlation strength) → <b>five role views</b> (CTO, SRE director, DevOps lead, eng manager, engineer), each scored on a relevance rubric.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>cascade reconstruction</td><td>link recall <b>1.00</b>, onset MAE 5.5 min, <b>0</b> spurious links</td></tr>
<tr><td>anomaly detection</td><td>robust beats naive on precision (e.g. infra 0.963 vs 0.679 P)</td></tr>
<tr><td>breach forecasting</td><td>time-to-breach MAE <b>3.4 min</b> (n=16)</td></tr>
<tr><td>triage compression</td><td><b>18.2 alerts → 5-item chain</b>; role relevance 1.00 for all 5 roles</td></tr></table>
<p>Seeds 7, 11, 42, 0, 99. Honest notes: AR(1) forecasting mean-reverts and can't extrapolate trends (replaced with linear-regime extrapolation); slow-burn ramps evade adaptive detectors (trailing median chases the ramp); the narrative composer is deterministic templates standing in for LLM summarization — the measured value is the pipeline.</p>""",
 insights=[
  "<b>Onset order beats correlation for linking.</b> Step-like cascades make lagged-correlation direction ambiguous; temporal order plus |r| is robust.",
  "<b>Neither detector dominates.</b> Robust wins precision and gradual onsets; naive thresholds win recall when they happen to be right — report both.",
  "<b>Relevance is measurable.</b> Scoring each role's view against a rubric turns 'executive summary' from art into engineering.",
 ],
 impl_tree="""src/agentic_systems/enriched_observability/
  telemetry.py    # 5-layer generators (infra→business) + CDN-TLS cascade
  enrich.py       # processed: robust scores, forecasts, clusters
  analytic.py     # failure p, root-cause confidence, impact, actions
  correlate.py    # cross-layer chain reconstruction
  roles.py        # 5 role views + relevance rubric
16-enriched-observability/
  experiments/run_experiments.py   # a-f, seeds 7/11/42/0/99""",
),

dict(
 slug="delegation-integrity", num="17",
 name="Delegation Integrity",
 tagline="Who authorized that? Principal hierarchies, scoped delegation, and the confused deputy — measured.",
 category="trust", repo="17-delegation-integrity", arch=svg_delegation_integrity,
 problem="When Agent A delegates to B which calls C to modify a production database, reconstructing who authorized what is technically difficult and legally uncertain. Agents hold credentials that can be redirected by instructions hidden in data they consume (the confused deputy); delegation converts scoped access into ambient privilege; and multi-principal workflows (buyer, merchant, payment service) can complete while violating one principal's instructions.",
 gap="Observability tools log actions but not authority: no principal hierarchy, no per-hop scope attenuation, no provenance distinguishing instruction-channel from data-channel content. Governance literature calls attribution the hardest question of 2026 — this system makes it measurable.",
 solution="A principal hierarchy (user > developer > deployer > third-party) with provenance-tagged instructions; <b>scoped, time-bounded authority tokens</b> with per-hop attenuation and strict/lax delegation modes; a confused-deputy simulator with 4 defense policies; a multi-principal purchase workflow with semantic conflict detection and precedence resolution; and an intent checker validating actions against stated constraints.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>confused deputy (200 trials x 3 variants)</td><td>naive attack success <b>1.000</b>; provenance / scope / combined all <b>0.000</b></td></tr>
<tr><td>delegation depth 2->5</td><td>naive success 0.39 -> <b>0.96</b>; provenance attribution <b>1.000</b> at all depths</td></tr>
<tr><td>ambient privilege (200 delegations)</td><td>strict <b>0.000</b> exceed vs lax <b>0.735</b></td></tr>
<tr><td>multi-principal conflicts</td><td>resolution correctness <b>0.823</b> vs naive <b>0.333</b></td></tr>
<tr><td>intent checker (300 scenarios)</td><td>precision <b>1.000</b>, recall <b>1.000</b></td></tr></table>
<p>Seeded runs. Honest bounds: conflict detection is parser-limited (0.543 — word-form phrasings defeat demand extraction); the intent checker validates formal constraints, not natural-language intent.</p>""",
 insights=[
  "<b>Every hop is another injection chance.</b> Attack success climbs 0.39 → 0.96 with depth — attenuation is not optional.",
  "<b>Without enforced attenuation, 3 in 4 delegations leak.</b> Lax mode's 0.735 ambient-privilege rate is the default in most frameworks.",
  "<b>Attribution is structural.</b> Without provenance tokens it decays as 1/d; with them it holds at 1.000.",
 ],
 impl_tree="""src/agentic_systems/delegation_integrity/
  principals.py / tokens.py  # hierarchy, provenance, scoped authority
  deputy.py / conflicts.py / intent.py  # attacks, multi-principal, intent checks
17-delegation-integrity/
  experiments/run_experiments.py   # a-e, seeded""",
),
dict(
 slug="horizon-scaling", num="18",
 name="Horizon Scaling",
 tagline="How fast does reliability die with task length — and which architecture flattens the curve?",
 category="orchestration", repo="18-horizon-scaling", arch=svg_horizon_scaling,
 problem="Agents succeed on short tasks and collapse on long ones: error compounds with horizon length. Teams deploy 80-step agents with no measurement of the decay curve and no evidence for which mitigation — checkpoints, hierarchy, voting, recovery — actually helps at their horizon.",
 gap="The decay is discussed qualitatively ('agents fail on long tasks') but never fitted. Without the curve you cannot choose mitigations, price cost-per-success, or know the horizon at which your architecture stops being viable.",
 solution="A seeded long-horizon task simulator (compounding corruption: corrupted state triples fatal probability) with a baseline linear executor and four mitigations sharing one verify-and-rollback core — checkpoints, hierarchical decomposition, healflow-style recovery, per-step majority voting — plus a cost model computing <b>cost-per-successful-task</b> at each horizon.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>decay curve (N=5->80)</td><td>baseline 0.804 -> <b>0.035</b>; exponential fit R2 = <b>0.9999</b></td></tr>
<tr><td>mitigations at N=80</td><td>hierarchy <b>0.740</b>, voting 0.676, recovery 0.613, checkpoints 0.596</td></tr>
<tr><td>cheapest per horizon</td><td>baseline at N<=10; <b>hierarchy beyond</b> (145.4 vs 1211.0 at N=80)</td></tr>
<tr><td>checkpoint sweep (N=40)</td><td>optimal k=5 (cost 86.5); k=2 verifies better but overhead dominates</td></tr>
<tr><td>error mixes</td><td>fatal-heavy: checkpoints/recovery dominate; corruption-heavy: hierarchy wins</td></tr></table>
<p>Seed 7, 2000 trials/cell. Theory cross-checks: baseline and voting match closed-form predictions within 0.03. Combining hierarchy + checkpoints gives 0.798 but diminishing returns on cost.</p>""",
 insights=[
  "<b>The decay is exponential, not anecdotal.</b> Fit q=0.959 vs theoretical 0.960 — the curve is predictable, so plan against it.",
  "<b>Mitigations are pure overhead on short tasks.</b> Below N=10 the baseline wins on cost; hierarchy pays off only at length.",
  "<b>Match the mitigation to the error mix.</b> Fatal errors want checkpoints; corruption wants hierarchy; voting is never cheapest.",
 ],
 impl_tree="""src/agentic_systems/horizon_scaling/
  tasks.py / agents.py  # compounding-error simulator, 4 mitigations
  metrics.py / catalog.py  # Wilson CIs, decay fits, cost-per-success
18-horizon-scaling/
  experiments/run_experiments.py   # a-f, seed 7""",
),
dict(
 slug="attention-economics", num="19",
 name="Attention Economics",
 tagline="Human attention is a priced resource. Find the optimal escalation policy — and measure trust.",
 category="orchestration", repo="19-attention-economics", arch=svg_attention_economics,
 problem="Agents either interrupt humans constantly (attention exhaustion) or act autonomously on high-stakes decisions (accountability failure). Escalation thresholds are set by gut feel; nobody prices the trade-off between interruption cost and error cost, and nobody measures whether the human's trust matches the agent's actual reliability.",
 gap="Ask-vs-act is treated as a UX preference, not an optimization problem. Over-trust and under-trust are both failures with different cost signatures — unmeasured, unmanaged.",
 solution="A decision-stream simulator (lognormal stakes, calibrated/miscalibrated confidence) with a fallible human principal (95% accurate), five escalation policies (always/never ask, fixed threshold, stakes-adjusted EV rule, budget-aware knapsack), a total-cost model (asks × interruption cost + unaudited errors × stakes × error cost), and <b>trust calibration measurement</b> (over/under-trust indices vs the EV reference).",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>policies (3 cost regimes)</td><td><b>stakes-adjusted EV wins all</b>; never-ask catastrophic at high stakes</td></tr>
<tr><td>optimal threshold</td><td>tracks fallibility-corrected theory within <b>0.05</b> at every cost ratio</td></tr>
<tr><td>miscalibration</td><td>overconfidence costs <b>+10,805</b>; underconfidence +1,758 — <b>6x asymmetry</b></td></tr>
<tr><td>trust U-curve</td><td>optimal tau 0.90; over-trust +0.1645 excess errors, under-trust +0.2385 excess interruptions</td></tr>
<tr><td>budget exhaustion</td><td>knapsack asks 44% of high-stakes at B=50; naive truncation asks <b>0%</b></td></tr></table>
<p>Seed 7, n=2000. Key honest finding: pricing the human's own 5% error rate is what makes the theory fit — the naive EV rule over-asked until corrected.</p>""",
 insights=[
  "<b>Price the human's fallibility.</b> The textbook rule assumes a perfect human and is systematically ~0.05 too trusting.",
  "<b>Overconfidence is 6x worse than underconfidence.</b> Same ECE magnitude, wildly different cost — calibrate directionally.",
  "<b>Bankruptcy is about order, not volume.</b> First-come truncation starves high-stakes decisions; knapsack doesn't.",
 ],
 impl_tree="""src/agentic_systems/attention_economics/
  world.py / principal.py  # decision streams, fallible human
  policies.py / cost.py / calibration.py  # 5 policies, cost model, trust metrics
19-attention-economics/
  experiments/run_experiments.py   # a-e, seed 7""",
),
dict(
 slug="injection-containment", num="20",
 name="Injection Containment",
 tagline="Prompt injection doesn't stop at one agent — it rides delegation chains. Contain the propagation.",
 category="trust", repo="20-injection-containment", arch=svg_injection_containment,
 problem="A poisoned tool output or document flows into Agent A, which delegates to B, which acts on the injected instruction with C's credentials. Single-agent injection defenses don't cover the multi-agent propagation path — and the semantic mosaic effect assembles sensitive insights from individually innocuous sources without tripping any single-source guard.",
 gap="No measured answer to: how far does an injected instruction propagate? Which payload types survive which defenses? What stops the subtle nudge that sanitizers can't see?",
 solution="A 4-hop chain simulator (orchestrator → researcher → writer → tool caller) with 4 seeded payload archetypes × 3 carriers, sticky taint provenance through summarization, and four defenses: <b>provenance firewall</b> (strict/attributed), <b>privilege boundaries</b>, <b>output sanitizer</b>, <b>tripwire canaries</b> — plus a mosaic-effect harness with a cross-source aggregation detector.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>propagation (1-4 hops, undefended)</td><td>attack success <b>0.65-0.74 flat</b> — decided at first contact</td></tr>
<tr><td>defenses</td><td>firewall-strict block <b>1.00</b>; privilege boundary: actions <b>0.00</b>, FP 0.00; canary detects 0.73</td></tr>
<tr><td>hardest payload</td><td><b>subtle nudge survives sanitizers at 0.74</b> — only provenance stops it</td></tr>
<tr><td>mosaic effect</td><td>3-4 tiles assemble (1.00); per-source guards block 0.00; aggregation detector catches <b>1.00</b></td></tr>
<tr><td>combined</td><td><b>0.00 residual</b> on all four payloads</td></tr></table>
<p>N=200 seeded trials/cell. Honest limits: privilege boundaries stop actions, not beliefs; sanitizers are brittle against rephrasing; canaries detect but never prevent; forged user-attribution defeats the attributed firewall (0.73) but not strict.</p>""",
 insights=[
  "<b>The battle is decided at first contact.</b> Success is flat across hops — stop the injection where it lands, not downstream.",
  "<b>Sanitizers can't see nudges.</b> Only provenance — knowing where content came from — stops the subtle payload.",
  "<b>Mosaic attacks need mosaic defenses.</b> Per-source guards are structurally blind; aggregation detection is the fix.",
 ],
 impl_tree="""src/agentic_systems/injection_containment/
  content.py / payloads.py / parse.py  # taint labels, 4 payload archetypes
  chain.py / defenses.py / mosaic.py  # 4-hop sim, 4 defenses, mosaic harness
20-injection-containment/
  experiments/run_experiments.py   # a-f, seeded""",
),
dict(
 slug="behavioral-regression", num="21",
 name="Behavioral Regression",
 tagline="Your vendor shipped a new model version. Did your agent silently get worse? Find out before production does.",
 category="trust", repo="21-behavioral-regression", arch=svg_behavioral_regression,
 problem="Model vendors ship new versions; agent task success, tool-call formats, latency, and cost profiles shift silently. Teams discover regressions from production incidents, not tests — because no behavioral regression suite exists for their agents.",
 gap="Ideological drift is measured (system 13); FUNCTIONAL drift is not. Nobody runs a frozen task battery with paired statistical tests across model versions, staged canaries, and pin/adopt/rollback policy.",
 solution="A frozen 120-task regression battery (tool use, multi-step, instruction following, edge cases incl. must-refuse) run against 5 versioned model stand-ins; <b>paired statistical tests</b> (McNemar exact + t-tests; regression only if significant AND material); business-weighted severity ranking; staged canary (1% → 10%) with stop rules; and a pin/auto-adopt/rollback policy engine with rationales.",
 results_table="""
<table class="res"><tr><th>Experiment</th><th>Result</th></tr>
<tr><td>sensitivity</td><td>catches regressions from ~0.10 delta; <b>0.00 false positives</b> on benign shifts</td></tr>
<tr><td>canary</td><td>v3 stopped at 1% in <b>5/5 seeds after 40 tasks</b></td></tr>
<tr><td>severity rank</td><td>v3 (2.467) >> v5 (0.765) > v4 (0.543) — tool-format break outranks verbosity 10x</td></tr>
<tr><td>policy</td><td><b>4/4 decisions match ground truth</b> (adopt / rollback / pin / rollback)</td></tr>
<tr><td>battery size</td><td>diminishing returns; below ~60 tasks the battery is <b>blind</b></td></tr></table>
<p>Seeds 7, 11, 42, 0, 99. Honest note: format breaks compound with success deltas (measured −0.387 vs injected −0.18); canary catches big breaks, full battery catches subtle trade-offs — complementary stages.</p>""",
 insights=[
  "<b>Rank by business severity, not by p-value.</b> A silent tool-format break outranks a verbosity change 10-to-1.",
  "<b>Canary and battery are complementary.</b> Staged rollout catches big breaks fast; the full suite catches subtle trade-offs.",
  "<b>60 tasks is the floor.</b> Below it the battery is blind — size your suite deliberately.",
 ],
 impl_tree="""src/agentic_systems/behavioral_regression/
  versions.py / battery.py  # 5 version stand-ins, frozen 120-task battery
  detector.py / canary.py / policy.py  # paired tests, staged rollout, decisions
21-behavioral-regression/
  experiments/run_experiments.py   # a-e, seeds 7/11/42/0/99""",
),
]

CATEGORIES = [
dict(slug="orchestration", name="Orchestration & Collective Intelligence",
     color="#6ea8fe",
     desc="How many agents coordinate, divide labor, and maintain shared truth — the control plane and the memory plane of multi-agent systems."),
dict(slug="trust", name="Trust, Recovery & Evidence",
     color="#7ee2a8",
     desc="How agentic systems stay correct when things go wrong: proving what happened, healing workflows, and keeping recovery itself safe."),
dict(slug="performance", name="Performance & Portability",
     color="#f0b35e",
     desc="How agentic systems run fast and run anywhere: serving efficiency under load, and skills that survive a change of model provider."),
dict(slug="operations", name="Reliability & Operations",
     color="#c792ea",
     desc="How agentic systems keep production healthy and leadership informed: observability at the seams, learning from incidents, and intelligence for every role."),
]

# ---------------------------------------------------------------------------
# Templates + generation
# ---------------------------------------------------------------------------

def nav(prefix=""):
    cats = "".join(
        f'<a href="{prefix}index.html#{c["slug"]}">{c["name"].split(" &")[0]}</a>'
        for c in CATEGORIES)
    return f"""
<nav class="top"><div class="wrap">
<a class="brand" href="{prefix}index.html">Agentic Systems <span>Lab</span></a>
<div class="links">{cats}<a href="https://github.com/ranadhir19/agentic-systems-lab/blob/main/docs/user-guide.md">User Guide ↗</a><a href="https://github.com/ranadhir19/agentic-systems-lab">GitHub ↗</a></div>
</div></nav>"""

def page_head(title):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Agentic Systems Lab</title>
<style>{CSS}</style></head><body>"""

PAGE_FOOT = """
<footer><div class="wrap">
<div>Agentic Systems Lab — sixteen original agentic-AI systems with implementations,<br>seeded experiments, and measured results.</div>
<div>Built by Ranadhir Ghosh · MIT License</div>
</div></footer></body></html>"""

def index_page():
    cats_html = ""
    for c in CATEGORIES:
        projs = [p for p in PROJECTS if p["category"] == c["slug"]]
        cards = ""
        for p in projs:
            metric = {
                "meridian-orchestration": "<b>90.4%</b> success — learned router matches hand-tuning",
                "sentinel-ledger": "<b>100%</b> replay fidelity · tamper detected",
                "forge-inference": "<b>9.2×</b> lower latency via continuous batching",
                "skillbridge-mcp": "<b>2×</b> lower cross-model variance",
                "collective-memory-fabric": "<b>0%</b> wrong answers under attack",
                "healflow": "<b>6/6</b> safe outcomes · 0 side effects",
                "intent-inference": "<b>100%</b> task success vs 45% classification baseline",
                "semantic-fabric": "<b>27.2:1</b> compression — store meaning, not data",
                "decision-partition": "<b>4 agents</b> for 5 decisions, exact reproduction",
                "sre-observability": "boundary recall <b>0.00 → 1.00</b> after targeted fix",
                "emergent-goals": "49.5 vs 34.5 self-made goals — curiosity costs survival",
                "ai-risk-twin": "<b>29 findings</b>, readiness 0.41 → NOT READY",
                "ideology-mirror": "creator divergence up to <b>1.546</b>",
                "sre-learning": "change-risk AUC <b>0.761</b> = Bayes ceiling",
                "leadership-insights": "<b>$35,040/yr</b> waste found; 7 vs 1 insights",
                "enriched-observability": "<b>18.2 alerts → 5-item</b> causal chain",
                "delegation-integrity": "<b>1.00 → 0.00</b> confused-deputy attack success",
                "horizon-scaling": "<b>0.804 → 0.035</b> baseline decay · hierarchy <b>0.740</b> at N=80",
                "attention-economics": "stakes-adjusted EV wins · overconfidence costs <b>6×</b>",
                "injection-containment": "combined defenses: <b>0.00</b> residual attack",
                "behavioral-regression": "<b>4/4</b> policy decisions match ground truth",
            }[p["slug"]]
            cards += f"""
<div class="card"><div class="tag">{p["num"]} · {p["name"]}</div>
<h4><a href="{p["slug"]}/index.html">{p["tagline"]}</a></h4>
<p>{p["problem"][:170]}…</p>
<div class="metric">{metric}</div></div>"""
        cats_html += f"""
<div class="cat" id="{c["slug"]}">
<h3><span class="dot" style="background:{c["color"]}"></span>{c["name"]}</h3>
<p class="desc">{c["desc"]}</p>
<div class="cards">{cards}</div></div>"""
    return (page_head("Agentic Systems Lab") + nav() + f"""
<div class="hero"><div class="wrap">
<div class="kicker">Portfolio · Agentic AI Systems</div>
<h1>Twenty-one systems for the hard problems in agentic AI.</h1>
<p class="sub">Coordination, memory, reliability, and efficiency — each project is a
complete, implemented answer to a research question, with architecture,
seeded experiments, measured results, and honest conclusions. No demos.
No hand-waving.</p>
<a class="btn" href="#orchestration">Explore the systems</a>
<a class="btn ghost" href="meridian-orchestration/index.html">Start with Meridian →</a>
<div class="install"><code>pip install agentic-systems-lab</code><span>The full library — sixteen systems, one import.</span></div>
<div class="stats">
<div><b>21</b><span>implemented systems</span></div>
<div><b>4</b><span>categories</span></div>
<div><b>20+</b><span>experiments, all seeded</span></div>
<div><b>100%</b><span>reproducible — one command each</span></div>
</div></div></div>
<section><div class="wrap">
<h2 class="sec">Browse by category</h2>
<p class="lead">Each category attacks a different layer of the agentic stack.
Pick the layer you care about, then drill into any system.</p>
{cats_html}
</div></section>
<section><div class="wrap">
<h2 class="sec">How to read a project</h2>
<p class="lead">Every project page follows the same spine:</p>
<div class="cards">
<div class="card"><h4>1 · Problem &amp; gap</h4><p>What breaks in real agentic systems, and why existing approaches don't fix it.</p></div>
<div class="card"><h4>2 · Solution &amp; architecture</h4><p>The design that addresses the gap, with a blueprint-style architecture diagram.</p></div>
<div class="card"><h4>3 · Results &amp; insights</h4><p>Measured numbers from seeded experiments, plus what the numbers actually mean.</p></div>
<div class="card"><h4>4 · Implementation</h4><p>The code layout — everything is implemented, tested, and reproducible.</p></div>
</div></div></section>
""" + PAGE_FOOT)

def project_page(p, prev_p, next_p, cat):
    insights = "".join(f"<li>{i}</li>" for i in p["insights"])
    return (page_head(p["name"]) + nav("../") + f"""
<div class="wrap"><div class="proj-hero">
<div class="crumb"><a href="../index.html">Lab</a> / <a href="../index.html#{cat["slug"]}">{cat["name"]}</a> / {p["num"]}</div>
<div class="kicker" style="color:{cat["color"]}">{cat["name"]}</div>
<h1>{p["name"]}</h1>
<p class="tagline">{p["tagline"]}</p>
</div>
<div class="block"><h2><span class="n">1</span>The problem</h2><p>{p["problem"]}</p></div>
<div class="block"><h2><span class="n">2</span>The current gap</h2><p>{p["gap"]}</p></div>
<div class="block"><h2><span class="n">3</span>How the solution addresses it</h2><p>{p["solution"]}</p></div>
<div class="block"><h2><span class="n">4</span>Architecture</h2>
<div class="diagram">{p["arch"]()}</div>
<div class="caption">Blueprint of the {p["name"]} architecture. See the repo for the full implementation.</div></div>
<div class="block"><h2><span class="n">5</span>Results</h2>
{p["results_table"]}
<img class="chart" src="../assets/charts/{p["slug"]}.png" alt="{p["name"]} experiment charts">
<div class="caption">Generated by <code>experiments/run_experiments.py</code> — re-running reproduces these exactly.</div></div>
<div class="block"><h2><span class="n">6</span>Insights</h2><ul>{insights}</ul></div>
<div class="block"><h2><span class="n">7</span>Implementation</h2>
<code class="tree">{p["impl_tree"]}</code>
<p style="margin-top:14px">Full source, tests, and experiment code: <a href="https://github.com">{p["repo"]}/</a> ·
Run: <code>cd {p["repo"]} && python3 experiments/run_experiments.py</code></p></div>
<div class="pagenav">
<a href="../{prev_p["slug"]}/index.html"><small>← Previous</small>{prev_p["num"]} · {prev_p["name"]}</a>
<a href="../{next_p["slug"]}/index.html" style="text-align:right"><small>Next →</small>{next_p["num"]} · {next_p["name"]}</a>
</div></div>
""" + PAGE_FOOT)

def main():
    os.makedirs(os.path.join(HERE, "assets", "charts"), exist_ok=True)
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(index_page())
    for i, p in enumerate(PROJECTS):
        d = os.path.join(HERE, p["slug"])
        os.makedirs(d, exist_ok=True)
        cat = next(c for c in CATEGORIES if c["slug"] == p["category"])
        prev_p = PROJECTS[(i - 1) % len(PROJECTS)]
        next_p = PROJECTS[(i + 1) % len(PROJECTS)]
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(project_page(p, prev_p, next_p, cat))
    print(f"built index + {len(PROJECTS)} project pages into {HERE}")

if __name__ == "__main__":
    main()
