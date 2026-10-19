# PyPI release checklist — agentic-systems-lab

Distribution name: `agentic-systems-lab` (verified available on PyPI).
Import name: `agentic_systems`. Version: `0.1.0`. License: MIT.

The actual publish is done by the repo owner. Do NOT publish from automation.

## 1. One-time setup

- [ ] Create a PyPI account at https://pypi.org/account/register/
- [ ] In account settings, create an API token (scope: entire account for the
      first upload, or scope it to the `agentic-systems-lab` project after it
      exists). Copy it now — PyPI shows it only once.
- [ ] Store the token in a password manager. It looks like
      `pypi-AgEIcHlwaS5vcmc...`. The username for token auth is always
      `__token__`.

## 2. Build the distribution (from the repo root)

Requires Python 3.10+ and the `build` package:

```bash
pip install build
python -m build
```

This produces `dist/agentic-systems-lab-0.1.0.tar.gz` (sdist) and
`dist/agentic_systems_lab-0.1.0-py3-none-any.whl` (wheel). Both should exist.

Sanity checks before upload:

```bash
pip install twine
twine check dist/*
# then install the wheel into a CLEAN virtualenv and smoke-test:
python -m venv /tmp/pkgtest && /tmp/pkgtest/bin/pip install dist/agentic_systems_lab-0.1.0-py3-none-any.whl
/tmp/pkgtest/bin/python -c "import agentic_systems; print(agentic_systems.__version__)"
/tmp/pkgtest/bin/python -c "from agentic_systems.meridian import MeridianSystem; from agentic_systems.healflow import HealFlowRuntime; print('imports ok')"
```

## 3. Upload

```bash
twine upload dist/*
# username: __token__
# password: <the pypi- API token>
```

First upload registers the project name. If the name is somehow taken at
upload time, rename the `name` field in `pyproject.toml`, rebuild, and retry.

## 4. After release

- [ ] Confirm the project page renders at
      https://pypi.org/project/agentic-systems-lab/ (README renders as the
      long description).
- [ ] `pip install agentic-systems-lab` in a fresh environment as a final check.
- [ ] Tag the release in git: `git tag v0.1.0 && git push origin v0.1.0`
- [ ] Optional: add a GitHub Release pointing at the tag with the changelog.

## 5. Releasing a new version later

- [ ] Bump `version` in `pyproject.toml` AND `__version__` in
      `src/agentic_systems/__init__.py` (keep them in sync).
- [ ] Re-run all six experiment suites; confirm results still match.
- [ ] Rebuild, re-check with twine, upload, tag.
