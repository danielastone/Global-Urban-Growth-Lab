import json
from pathlib import Path

from urban_growth.spi_evidence import (
    coverage_diagnostic,
    load_spi,
    pairwise_indicator_correlations,
    revision_diagnostic,
)


def main():
    raw = Path("data/raw/spi_166")
    out = Path("outputs/spi_166")
    out.mkdir(parents=True, exist_ok=True)
    cur = load_spi(raw / "SPI_data.csv", release="World Bank SPI December 2025")
    pre = load_spi(
        raw / "SPI_data_pre_release.csv", release="World Bank SPI pre-release 2025-12-04"
    )
    cur.to_csv(out / "spi_selected_long.csv", index=False)
    coverage_diagnostic(cur).to_csv(out / "coverage.csv", index=False)
    pairwise_indicator_correlations(cur).to_csv(out / "pairwise_correlations_2024.csv", index=False)
    (out / "revision_diagnostic.json").write_text(
        json.dumps(revision_diagnostic(cur, pre), indent=2) + "\n"
    )
    print(revision_diagnostic(cur, pre))


if __name__ == "__main__":
    main()
