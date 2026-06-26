# AGENTS.md

Guidance for AI coding agents working in the **py_ez_wikidata** repository
(mapping for Wikidata — simplified / easy creation of Wikidata entries from dicts,
https://github.com/WolfgangFahl/py_ez_wikidata).

## PLAN AND ASK BEFORE DO

**CRITICAL: NEVER EVER DO ANY ACTION READING, MODIFYING OR RUNNING without explaining the plan.**

Each set of intended actions needs to be explained in the format:

> I understood that `<YOUR ANALYSIS>` so that I plan to `<GOALS YOU PURSUE>` by `<ACTIONS TO BE CONFIRMED>` estimating `<# of ITEMS>` `<ITEMS>` to be worked on. Confirm with go!

**YOU WILL NEVER PROCEED WITHOUT POSITIVE CONFIRMATION by go!**

## Efficiency

- Do NOT do unneeded file lookups based on guessing or assuming typos.
- Do NOT use TodoWrite for tasks with fewer than 4 steps.
- Do NOT read files you already have contents for.
- Keep summaries to 2-3 lines max unless asked for detail.
- Minimize tool calls. Batch parallel calls. Avoid redundant calls.

## Security

**CRITICAL: NEVER leak credentials, passwords, hashes, internal hostnames, IPs, or any infrastructure details to public platforms (GitHub, Discourse, etc.). Firing offense.**

## DMAIC

Follow the DMAIC principle (Define, Measure, Analyze, Improve, Control).
When called out, read AGENTS-DMAIC to look for known past problems to avoid
repetition:
- https://media.bitplan.com/index.php/AGENTS-DMAIC
- https://media.bitplan.com/index.php/Agents (wiki id: `media`)

## Project Overview

`py_ez_wikidata` (requires Python `>=3.10`) is a Python library providing a
mapping layer for Wikidata that allows simplified / easy creation of Wikidata
entries from dicts. Build system: **hatchling**. Version is sourced from
`ez_wikidata/__init__.py`. CLI entry point: `ezwd = ez_wikidata.ezwd_cmd:main`.

## Project Layout

- `ez_wikidata/` — Python package (source)
  - `wikidata.py` — core Wikidata access
  - `wdproperty.py` — Wikidata property handling
  - `wbquery.py` — Wikibase query support
  - `wdsearch.py` — Wikidata search
  - `trulytabular.py` — truly-tabular analysis
  - `__init__.py` — single source of truth for `__version__`
  - `version.py` — `Version` metadata
  - `resources/` — bundled resources
- `tests/` — test suite (`test_*.py`, plus `testTrulyTabular.py`)
- `scripts/` — dev/build/release shell scripts
- `docs/` / `site/` — mkdocs documentation sources and generated output
- `pyproject.toml` — build (hatchling) + project metadata

## Setup, Build & Test

Test framework is **Python `unittest`** (not pytest). Tests inherit from
`tests.basetest.BaseTest`, which extends `unittest.TestCase`.

```bash
scripts/install          # editable install
scripts/test             # python -m unittest discover (default)
scripts/test --green     # run with the green test runner
scripts/test --module    # run module-by-module
scripts/blackisort       # isort + black on ez_wikidata/ and tests/
scripts/doc              # build docs
scripts/release          # release pipeline
```

- Python `>=3.10`; supported: 3.10, 3.11, 3.12, 3.13.
- `BaseTest.inPublicCI()` — returns `True` on CI; skip slow/external (live
  Wikidata/SPARQL) tests there.
- Always run `scripts/test` before committing.

## Code Style

- **black** for formatting and **isort** for imports (run `scripts/blackisort`).
- Google-style docstrings with `Args:` / `Returns:` / `Raises:` sections.
- File-level module docstrings follow the pattern:
  ```python
  '''
  Created on YYYY-MM-DD

  @author: wf
  '''
  ```
- Keep changes minimal and consistent with the existing code.

## Open-source conformance: `checkos`

This project follows the WolfgangFahl open-source project conventions, verified
by the `checkos` tool:

```bash
checkos -p py_ez_wikidata -o WolfgangFahl --local -v    # verbose check
checkos -p py_ez_wikidata -o WolfgangFahl --local -v -d # with per-rule debug detail
checkos -p py_ez_wikidata -o WolfgangFahl -b            # emit standard README badge markup
```

After changes that affect CI workflows, README badges, or packaging,
**re-run `checkos` and resolve every `❌`** before finishing.

## Documentation

Daily / problem documentation goes to the MediaWiki at
https://media.bitplan.com (wiki id `media`) via the `wikipush` MCP, using
ISO-dated pages.

## Commit / PR conventions

- Do not commit, push, or open PRs unless explicitly requested.
- Stage only intended files; never commit secrets.
- Match the existing commit message style.
