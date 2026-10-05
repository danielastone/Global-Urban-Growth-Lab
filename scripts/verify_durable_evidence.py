"""Verify durable evidence for empirical results cited in repository documents."""

from pathlib import Path

from urban_growth.durable_evidence import validate_durable_evidence


def main() -> None:
    validate_durable_evidence(
        Path("results/durable_evidence_packages.csv"),
        Path("results/durable_evidence_outputs.csv"),
    )
    print("Durable empirical evidence verified")


if __name__ == "__main__":
    main()
