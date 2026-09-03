"""Acquire the pinned World Bank SPI current and pre-release revision files."""

from pathlib import Path
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/worldbank/SPI"
FILES = {
    "LICENSE": ("2b474a5a0c5274b7988200747afae8c7eaa58564", "LICENSE"),
    "SPI_data.csv": ("2b474a5a0c5274b7988200747afae8c7eaa58564", "03_output_data/SPI_data.csv"),
    "SPI_data_pre_release.csv": (
        "89570498fc3a5de2e599115443841e242c39a040",
        "03_output_data/SPI_data.csv",
    ),
    "SPI_full_metadata.csv": (
        "2b474a5a0c5274b7988200747afae8c7eaa58564",
        "01_raw_data/metadata/SPI_full_metadata.csv",
    ),
}


def main():
    out = Path("data/raw/spi_166")
    out.mkdir(parents=True, exist_ok=True)
    for name, (commit, path) in FILES.items():
        target = out / name
        target.write_bytes(urlopen(f"{BASE}/{commit}/{path}", timeout=120).read())
        print(target)


if __name__ == "__main__":
    main()
