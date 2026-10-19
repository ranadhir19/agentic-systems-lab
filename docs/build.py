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

# ---------------------------------------------------------------------------
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
<div>Agentic Systems Lab — seven original agentic-AI systems with implementations,<br>seeded experiments, and measured results.</div>
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
<h1>Seven systems for the hard problems in agentic AI.</h1>
<p class="sub">Coordination, memory, reliability, and efficiency — each project is a
complete, implemented answer to a research question, with architecture,
seeded experiments, measured results, and honest conclusions. No demos.
No hand-waving.</p>
<a class="btn" href="#orchestration">Explore the systems</a>
<a class="btn ghost" href="meridian-orchestration/index.html">Start with Meridian →</a>
<div class="install"><code>pip install agentic-systems-lab</code><span>The full library — seven systems, one import.</span></div>
<div class="stats">
<div><b>7</b><span>implemented systems</span></div>
<div><b>3</b><span>categories</span></div>
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
