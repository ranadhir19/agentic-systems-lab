#!/usr/bin/env python3
"""Uniform validation harness for agentic-systems-lab.

Run from anywhere:  python3 validate.py
Runs from the repo root (the directory containing this file), offline and
deterministically. Exits 0 only if every stage passes.

Stages, in order:
  1. import-compile     compileall over the source tree + import of the
                        package(s) declared via pyproject.toml (src layout).
  2. tests              the full existing pytest suite over the whole repo
                        (every system's tests/) via subprocess.
  3. reference-scan     Forbidden-reference scan of the repo tree with the
                        owner's shared scanner, which lives outside this
                        repo and is resolved at runtime. Any candidate hit
                        fails this stage: candidates must be judged in
                        context by a human/agent before a push (the gate is
                        scan + judge, never scan + ignore).
  4. docs-consistency   cheap existence checks: every local file linked
                        from the root README and each per-system README
                        exists; every system has its experiment runner,
                        results files, README, and a quickstart example.
                        Also validates deployment configs wherever they
                        exist (render.yaml, vercel.json, Procfile,
                        Dockerfile, docker-compose*.yml,
                        .github/workflows/*): syntax parses and
                        platform-required keys/values are schema-valid.
                        A broken deploy config fails this stage.

Final line is exactly "HARNESS GREEN" or "HARNESS RED: <stage, ...>".
See VALIDATION.md for the honest scope of what this does NOT cover.
"""

from __future__ import annotations

import compileall
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
def _find_reference_scanner() -> str | None:
    """Locate the owner's shared reference scanner outside this repo.

    Resolved at runtime (env override, then a sibling-tooling glob) so no
    repo file has to name it: repo files must themselves pass the scan.
    """
    env = os.environ.get("REFERENCE_SCANNER")
    if env and os.path.isfile(env):
        return env
    import glob as _glob
    hits = sorted(_glob.glob(os.path.expanduser("~/workspace/github-*-watch/*_scan.py")))
    return hits[0] if hits else None

FAILED: list[str] = []


def report(stage: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {stage}"
    if detail:
        line += f": {detail}"
    print(line, flush=True)
    if not ok:
        FAILED.append(stage)
    return ok


# ---------------------------------------------------------------- stage 1
def stage_import_compile() -> bool:
    stage = "import-compile"
    # 1a. Byte-compile every .py file in the tree (excluding .git).
    ok = True
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in files:
            if fn.endswith(".py"):
                path = os.path.join(root, fn)
                if not compileall.compile_file(path, quiet=2, force=False):
                    print(f"  compile failed: {os.path.relpath(path, REPO)}")
                    ok = False
    if not ok:
        return report(stage, False, "compileall failures (see above)")

    # 1b. Import the package(s) declared in pyproject.toml. This repo uses a
    # src layout ([tool.setuptools.packages.find] where = ["src"]), so the
    # importable top-level packages are the dirs with __init__.py under src/.
    src = os.path.join(REPO, "src")
    if not os.path.isdir(src):
        return report(stage, False, "src/ layout expected by pyproject.toml is missing")
    top_pkgs = sorted(
        d for d in os.listdir(src)
        if os.path.isfile(os.path.join(src, d, "__init__.py"))
    )
    if not top_pkgs:
        return report(stage, False, "no importable package found under src/")
    code = (
        "import sys; sys.path.insert(0, {src!r})\n"
        "import importlib, pkgutil\n"
        "for name in {pkgs!r}:\n"
        "    mod = importlib.import_module(name)\n"
        "    # import every subpackage too, so a broken subpackage cannot\n"
        "    # hide behind a lazy top-level __init__\n"
        "    for info in pkgutil.walk_packages(mod.__path__, prefix=name + '.'):\n"
        "        importlib.import_module(info.name)\n"
        "print('imported:', ', '.join({pkgs!r}))\n"
    ).format(src=src, pkgs=top_pkgs)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        return report(stage, False, f"import failed for {top_pkgs}")
    return report(stage, True, r.stdout.strip() or f"compiled + imported {top_pkgs}")


# ---------------------------------------------------------------- stage 2
def stage_tests() -> bool:
    stage = "tests"
    # All 18 test files share the basename test_smoke.py (one per system,
    # no __init__.py), so pytest's default prepend import mode collides.
    # --import-mode=importlib collects them correctly without renaming or
    # modifying any test.
    cmd = [sys.executable, "-m", "pytest", REPO,
           "--import-mode=importlib", "-q", "-p", "no:cacheprovider"]
    print(f"  running: {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    tail = (r.stdout + r.stderr).strip().splitlines()
    for line in tail[-15:]:
        print(f"  {line}")
    if r.returncode != 0:
        return report(stage, False, f"pytest exited {r.returncode} (tail above)")
    summary = tail[-1] if tail else "pytest ok"
    return report(stage, True, summary)


# ---------------------------------------------------------------- stage 3
def stage_reference_scan() -> bool:
    stage = "reference-scan"
    scanner = _find_reference_scanner()
    if not scanner:
        return report(stage, False, "shared reference scanner not found "
                                    "(set REFERENCE_SCANNER)")
    r = subprocess.run([sys.executable, scanner, REPO],
                       capture_output=True, text=True)
    candidates = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError:
                candidates.append({"file": "?", "text": line})
    if candidates:
        for c in candidates:
            print(f"  candidate: {c.get('file')}:{c.get('line')} "
                  f"[{c.get('pattern')}] {c.get('text', '')[:160]}")
        return report(stage, False,
                      f"{len(candidates)} reference candidate(s) require in-context "
                      "judgment; a REAL forbidden reference blocks any push")
    return report(stage, True, "0 reference candidates in repo tree")


# ---------------------------------------------------------------- stage 4
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def stage_docs_consistency() -> bool:
    stage = "docs-consistency"
    problems: list[str] = []

    # 4a. Every local file linked from the root README and per-system
    # READMEs must exist (relative to the README's own directory).
    readmes = [os.path.join(REPO, "README.md")]
    systems = sorted(
        d for d in os.listdir(REPO)
        if re.fullmatch(r"\d{2}-.+", d) and os.path.isdir(os.path.join(REPO, d))
    )
    for s in systems:
        readmes.append(os.path.join(REPO, s, "README.md"))
    checked = 0
    for readme in readmes:
        if not os.path.isfile(readme):
            problems.append(f"missing README: {os.path.relpath(readme, REPO)}")
            continue
        base = os.path.dirname(readme)
        text = open(readme, encoding="utf-8").read()
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = target.split("#")[0]
            if not target:
                continue
            checked += 1
            if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                problems.append(
                    f"{os.path.relpath(readme, REPO)} links missing file: {target}")

    # 4b. Per-system entry points and generated results must exist.
    for s in systems:
        for rel in ("experiments/run_experiments.py",
                    "results/results.md", "results/charts.png"):
            if not os.path.isfile(os.path.join(REPO, s, rel)):
                problems.append(f"{s}: missing {rel}")

    # 4c. One runnable quickstart example per system, numbered to match.
    examples = os.path.join(REPO, "examples")
    quickstarts = sorted(f for f in os.listdir(examples) if f.endswith(".py")) \
        if os.path.isdir(examples) else []
    if len(quickstarts) != len(systems):
        problems.append(
            f"examples/ has {len(quickstarts)} quickstarts for {len(systems)} systems")
    else:
        for s, q in zip(systems, quickstarts):
            if s[:2] != q[:2]:
                problems.append(f"quickstart numbering mismatch: {s} vs {q}")

    # 4d. Deployment-config validation (wherever such files exist).
    deploy_checked = validate_deploy_configs(problems)

    if problems:
        for p in problems:
            print(f"  {p}")
        return report(stage, False, f"{len(problems)} problem(s), {checked} links checked")
    return report(stage, True,
                  f"{checked} README links resolve; {len(systems)} systems have "
                  f"runner + results + matching quickstart; {deploy_checked}")


# ------------------------------------------------------- deploy configs
RENDER_SERVICE_TYPES = {"web", "worker", "cron", "pserv", "keyvalue"}
RENDER_ENVS = {"docker", "elixir", "go", "node", "python", "ruby", "rust",
               "static", "image"}


def _load_yaml(path: str, problems: list[str]):
    try:
        import yaml
    except ImportError:
        problems.append(f"{path}: PyYAML unavailable, cannot validate YAML")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as exc:
        problems.append(f"{path}: YAML does not parse: {exc}")
        return None


def validate_deploy_configs(problems: list[str]) -> str:
    """Validate deployment configs if present; a broken one appends a
    problem (=> stage FAIL). Returns a short summary for the PASS line."""
    found: list[str] = []

    def rel(p: str) -> str:
        return os.path.relpath(p, REPO)

    # Render blueprint (render.yaml / render.yml, repo root).
    for name in ("render.yaml", "render.yml"):
        p = os.path.join(REPO, name)
        if not os.path.isfile(p):
            continue
        found.append(name)
        doc = _load_yaml(p, problems)
        if doc is None:
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("services"), list) \
                or not doc["services"]:
            problems.append(f"{name}: top level must define a non-empty 'services' list")
            continue
        for svc in doc["services"]:
            if not isinstance(svc, dict):
                problems.append(f"{name}: each service must be a mapping")
                continue
            for key in ("type", "name"):
                if key not in svc:
                    problems.append(f"{name}: service missing required key '{key}'")
            stype = svc.get("type")
            if stype is not None and stype not in RENDER_SERVICE_TYPES:
                problems.append(
                    f"{name}: service '{svc.get('name')}': invalid type {stype!r} "
                    f"(valid: {sorted(RENDER_SERVICE_TYPES)}); a static site is "
                    "type: web with env: static — there is no 'static' type")
            env = svc.get("env")
            if env is not None and env not in RENDER_ENVS:
                problems.append(
                    f"{name}: service '{svc.get('name')}': invalid env {env!r} "
                    f"(valid: {sorted(RENDER_ENVS)})")
            if env == "static" and stype != "web":
                problems.append(
                    f"{name}: service '{svc.get('name')}': env: static requires "
                    "type: web")

    # Vercel (vercel.json, repo root).
    p = os.path.join(REPO, "vercel.json")
    if os.path.isfile(p):
        found.append("vercel.json")
        try:
            doc = json.load(open(p, encoding="utf-8"))
            if not isinstance(doc, dict):
                problems.append("vercel.json: top level must be a JSON object")
        except Exception as exc:
            problems.append(f"vercel.json: JSON does not parse: {exc}")

    # Procfile: every non-empty, non-comment line is 'name: command'.
    p = os.path.join(REPO, "Procfile")
    if os.path.isfile(p):
        found.append("Procfile")
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            line = line.strip()
            if line and not line.startswith("#") \
                    and not re.fullmatch(r"[A-Za-z0-9_-]+:\s*\S.*", line):
                problems.append(f"Procfile:{i}: expected 'name: command', got {line!r}")

    # Dockerfile*: must contain a FROM instruction.
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in files:
            if fn == "Dockerfile" or fn.startswith("Dockerfile."):
                dp = os.path.join(root, fn)
                found.append(rel(dp))
                body = [ln.strip() for ln in open(dp, encoding="utf-8")
                        if ln.strip() and not ln.strip().startswith("#")]
                if not any(ln.upper().startswith(("FROM ", "ARG ")) for ln in body[:1]) \
                        or not any(ln.upper().startswith("FROM ") for ln in body):
                    problems.append(f"{rel(dp)}: no FROM instruction found")

    # docker-compose*.yml/yaml: parses; 'services' mapping; each service
    # defines image or build.
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in files:
            if re.fullmatch(r"docker-compose.*\.ya?ml", fn):
                dp = os.path.join(root, fn)
                found.append(rel(dp))
                doc = _load_yaml(dp, problems)
                if isinstance(doc, dict):
                    svcs = doc.get("services")
                    if not isinstance(svcs, dict) or not svcs:
                        problems.append(f"{rel(dp)}: 'services' must be a non-empty mapping")
                    else:
                        for sname, svc in svcs.items():
                            if isinstance(svc, dict) and "image" not in svc and "build" not in svc:
                                problems.append(
                                    f"{rel(dp)}: service '{sname}' has neither 'image' nor 'build'")

    # GitHub Actions workflows: parse; 'on' + 'jobs' with runs-on + steps.
    wf_dir = os.path.join(REPO, ".github", "workflows")
    if os.path.isdir(wf_dir):
        for fn in sorted(os.listdir(wf_dir)):
            if fn.endswith((".yml", ".yaml")):
                wp = os.path.join(wf_dir, fn)
                found.append(rel(wp))
                doc = _load_yaml(wp, problems)
                if isinstance(doc, dict):
                    # PyYAML (YAML 1.1) parses the key `on` as boolean True.
                    if "on" not in doc and True not in doc:
                        problems.append(f"{rel(wp)}: missing 'on' trigger")
                    jobs = doc.get("jobs")
                    if not isinstance(jobs, dict) or not jobs:
                        problems.append(f"{rel(wp)}: 'jobs' must be a non-empty mapping")
                    else:
                        for jname, job in jobs.items():
                            if not isinstance(job, dict) or "runs-on" not in job \
                                    or not isinstance(job.get("steps"), list):
                                problems.append(
                                    f"{rel(wp)}: job '{jname}' needs 'runs-on' and a 'steps' list")

    if not found:
        print("  deploy configs: none present — nothing to validate")
        return "no deployment configs present"
    print(f"  deploy configs validated: {', '.join(found)}")
    return f"deploy configs OK ({len(found)}: {', '.join(found)})"


STAGES = [
    ("import-compile", stage_import_compile),
    ("tests", stage_tests),
    ("reference-scan", stage_reference_scan),
    ("docs-consistency", stage_docs_consistency),
]


def main() -> int:
    print(f"validate.py — agentic-systems-lab harness (repo: {REPO})", flush=True)
    for _name, fn in STAGES:
        try:
            fn()
        except Exception as exc:  # a harness error is a failure, never a pass
            report(_name, False, f"harness error: {exc!r}")
    if FAILED:
        print(f"HARNESS RED: {', '.join(FAILED)}")
        return 1
    print("HARNESS GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
