"""Conservative tabular readers for publisher workbooks and delimited files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class SourceSchemaError(ValueError):
    """Raised when an input does not match an explicitly declared schema."""


def read_table(path: str | Path, *, sheet_name: str | int = 0, **kwargs) -> pd.DataFrame:
    """Read CSV/XLSX data without guessing a publisher-specific schema."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source, **kwargs)
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(source, sheet_name=sheet_name, engine="openpyxl", **kwargs)
    if suffix == ".xls":
        return pd.read_excel(source, sheet_name=sheet_name, engine="xlrd", **kwargs)
    raise SourceSchemaError(f"Unsupported tabular format: {suffix}")


def require_columns(frame: pd.DataFrame, required: set[str], *, source_name: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise SourceSchemaError(f"{source_name} missing columns: {', '.join(missing)}")


def reject_duplicate_keys(frame: pd.DataFrame, keys: list[str], *, source_name: str) -> None:
    require_columns(frame, set(keys), source_name=source_name)
    if frame.duplicated(keys).any():
        raise SourceSchemaError(f"{source_name} contains duplicate keys: {', '.join(keys)}")
