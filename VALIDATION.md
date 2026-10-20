# Validation

Run the harness from the repo root:

```bash
python3 validate.py
```

It is deterministic, offline, and exits non-zero on any failure. The last
line is exactly `HARNESS GREEN` or `HARNESS RED: <stages>`.

## What the harness covers

1. **import-compile** — byte-compiles every `.py` file in the tree, then
   imports the package declared in `pyproject.toml` (src layout:
   `agentic_systems` under `src/`) **and every one of its subpackages** in a
   clean subprocess, so a broken subpackage cannot hide behind a lazy
   top-level `__init__`.
2. **tests** — the full existing test suite: `pytest` over the whole repo,
   which collects every system's `tests/` directory. It is run with
   `--import-mode=importlib` because all test files share the basename
   `test_smoke.py` (one per system, no `__init__.py`); pytest's default
   import mode cannot collect duplicate basenames. No test is skipped,
   deselected, or modified by the harness.
3. **reference-scan** — the owner's shared forbidden-reference scanner
   over the whole repo tree. The scanner lives outside this repo (repo
   files must themselves pass the scan) and the harness resolves it at
   runtime. The scanner only produces *candidates*; this stage fails on
   **any** candidate, because each one must be judged in context (real
   reference vs innocent substring) before anything is pushed. A green
   stage means zero candidates were found — not that candidates were
   waved through.
4. **docs-consistency** — cheap existence checks only: every local file
   linked from the root `README.md` and each per-system `README.md`
   resolves to a real file; every system has `experiments/run_experiments.py`,
   `results/results.md`, and `results/charts.png`; `examples/` holds one
   quickstart per system with matching numbering.

## What the harness does NOT cover (honest scope)

- **Measured numbers are not re-derived.** Stage 4 checks that results
  files *exist*, not that the numbers in them are correct or reproducible.
  Re-running the 21 experiment runners and comparing outputs is not part of
  this harness.
- **Three systems have no tests.** `02-sentinel-ledger`,
  `03-forge-inference`, and `04-skillbridge-mcp` have empty `tests/`
  directories. The test stage passes over 18 test files / the systems that
  have them; it provides **no test coverage at all** for those three
  systems beyond import/compile (stage 1) and docs checks (stage 4).
- **No coverage measurement.** There is no line/branch coverage gate; the
  smoke tests exercise core paths only, not edge cases, error paths, or the
  experiment runners end-to-end.
- **Examples are not executed.** Quickstarts are compile-checked (stage 1)
  and existence/numbering-checked (stage 4), but not run.
- **Docs site not validated.** `docs/` HTML is not link-checked or rendered;
  only Markdown READMEs are checked, and only for local file existence —
  external URLs are not fetched (the harness is offline).
- **Reference judgment is not automated.** Stage 3 detects candidates;
  deciding whether a candidate is a real forbidden reference remains a
  human/agent judgment, per the repo owner's gate policy.
- **No packaging/release checks.** Building the wheel/sdist, PyPI metadata,
  and the `PYPI_RELEASE.md` checklist are out of scope.
