from pathlib import Path

from urban_growth.repository_governance import governance_errors


def test_repository_governance_controls() -> None:
    assert governance_errors(Path(".")) == []


def _write_workflow(root: Path, name: str, body: str) -> None:
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / name).write_text(body, encoding="utf-8")
    (root / "scripts").mkdir(exist_ok=True)


def test_governance_rejects_mutable_action_and_inherited_permissions(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "tests.yml",
        "name: tests\nsteps:\n  - uses: actions/checkout@v7\n",
    )
    errors = governance_errors(tmp_path)
    assert any("lacks explicit contents: read" in error for error in errors)
    assert any("mutable action reference actions/checkout@v7" in error for error in errors)


def test_governance_rejects_empirical_workflow_without_hash_gate(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "wup-h1-empirical.yml",
        "name: empirical\npermissions:\n  contents: read\nsteps: []\n",
    )
    assert any("does not verify registered input hashes" in error for error in governance_errors(tmp_path))


def test_governance_rejects_legacy_classifier(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "tests.yml",
        "name: tests\npermissions:\n  contents: read\nsteps: []\n",
    )
    (tmp_path / "scripts" / "legacy.py").write_text(
        "total = sum(scores.values())\n", encoding="utf-8"
    )
    assert any("composite-score summation" in error for error in governance_errors(tmp_path))
