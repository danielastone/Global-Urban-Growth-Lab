"""Fail CI when repository-level governance controls regress."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION_USE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
PINNED_ACTION = re.compile(r"^[^/\s]+/[^@\s]+@[0-9a-f]{40}$")
EMPIRICAL_WORKFLOWS = {
    "ghsl-redteam-130.yml",
    "wup-contemporaneous-country.yml",
    "wup-h1-empirical.yml",
}
PROHIBITED_RELIABILITY_PATTERNS = {
    "legacy classifier entry point": "scripts/classify_reliability.py",
    "composite-score summation": "sum(scores.values())",
    "classifier output band": "band={band}",
    "classifier output score": "score={total}",
    "classifier output archetype": "archetype={archetype}",
}


def governance_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    if not workflows:
        return ["No GitHub Actions workflows found"]

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        if not re.search(r"^permissions:\n  contents: read\s*$", text, re.MULTILINE):
            errors.append(f"{workflow.relative_to(root)} lacks explicit contents: read permissions")
        for action in ACTION_USE.findall(text):
            if action.startswith(("./", "docker://")):
                continue
            if not PINNED_ACTION.fullmatch(action):
                errors.append(
                    f"{workflow.relative_to(root)} uses mutable action reference {action}"
                )
        if workflow.name in EMPIRICAL_WORKFLOWS and "sha256sum --check --strict" not in text:
            errors.append(f"{workflow.relative_to(root)} does not verify registered input hashes")

    searchable = [workflow_dir, root / "scripts"]
    for label, pattern in PROHIBITED_RELIABILITY_PATTERNS.items():
        for directory in searchable:
            for path in directory.rglob("*"):
                if (
                    path.is_file()
                    and pattern in path.read_text(encoding="utf-8", errors="ignore")
                ):
                    errors.append(f"{path.relative_to(root)} contains prohibited {label}")
    return errors


def main() -> None:
    errors = governance_errors()
    if errors:
        raise SystemExit("Repository governance validation failed:\n- " + "\n- ".join(errors))
    print("Repository governance controls validated")
