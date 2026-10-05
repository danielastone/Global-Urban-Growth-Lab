# Contributing

This repository is a pre-conclusion research program. Contributions are welcome, but
the priority is reproducible evidence—not feature volume or stronger-sounding claims.

## Before starting

1. Read the [implementation roadmap](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/33).
2. Search existing issues and pull requests before opening another.
3. For substantial work, open or claim one bounded issue before writing code.
4. Do not code around an issue marked **MANUAL BLOCK**. Attach the required source,
   licensing, governance, or methodological evidence to the issue first.

Work on synthetic tests and infrastructure may proceed while empirical inputs are
blocked, but it must not be presented as an empirical result.

## Development setup

This project uses Python 3.11 or later and locks dependencies with `uv`.

```bash
uv sync --locked --extra dev
uv run --locked --extra dev pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev urban-growth-sources verify-licenses
```

## Pull requests

- Keep one bounded issue per pull request.
- Link the issue and state which research or implementation gate the change advances.
- Use one analytic sample for estimator comparisons unless the specification explicitly
  requires otherwise.
- Add tests for code and machine-readable checks for data or metadata changes.
- Update documentation, expected manifests, and the claim status when results change.
- Report conflicting or null results. Do not select specifications by preferred sign.
- Separate generated artifacts from source data and document how to reproduce them.

A pull request is not complete merely because CI passes. Methodological judgment,
source rights, and empirical interpretation may still require review.

## Data and licensing

Apache-2.0 covers repository software only. Before acquiring or using a dataset:

1. Register the exact source and release in `data/sources.json`.
2. Record the intended uses and controlling terms in `data/licenses.json`.
3. Add acquired-file provenance and SHA-256 hashes to the local manifest.
4. Run the license checks for the intended operation.

Do not commit raw, restricted, employer-owned, personally identifiable, or
redistribution-uncertain data. See [THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md).

## Research claims

Treat every result as provisional until its inputs, geography, timing, sample,
estimator, and validation status are reproducible. A contribution that weakens a
headline claim is useful if it is correct. A contribution that hides a failed gate is
not acceptable.

## Review ownership

This is currently an owner-controlled repository. The owner authors and performs final
review of changes; the project does not claim independent review, peer review, or
segregation of duties. Requiring an approval would create false review theater because an
author cannot supply independent approval of their own pull request.

`CODEOWNERS` records decision ownership. Pull requests, the required CI check, current-
branch enforcement, resolved review threads, and the owner-attestation checklist reduce
accidental error, but none substitutes for an independent reviewer. If a qualified second
reviewer is added later, the branch rules must then require their approval and dismiss
stale approvals after new pushes.
