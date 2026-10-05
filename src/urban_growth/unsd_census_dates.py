"""Fail-closed parsing for the UNSD census-dates and M49 HTML tables."""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser

REGION_PANES = {"Africa", "North", "South", "Asia", "Europe", "Oceania"}
ROUNDS = ("1990", "2000", "2010", "2020", "2030")
ASSERTION_STATUSES = {
    "observed_exact",
    "observed_interval",
    "observed_month",
    "observed_year",
    "planned_date",
    "planned_unconfirmed",
    "planned_decade",
    "no_census_or_plan",
    "blank",
    "unparsed",
}
CROSSWALK_STATUSES = {"matched", "unmatched", "ambiguous"}
ASSERTION_OUTPUT_FIELDS = [
    "region",
    "source_country_name",
    "country_id",
    "crosswalk_status",
    "census_round",
    "occurrence",
    "raw_text",
    "assertion_status",
    "date_start",
    "date_end",
    "date_precision",
    "footnotes_json",
    "source_links_json",
    "source_id",
    "source_release",
    "snapshot_id",
]

# Source-specific historical/abbreviated labels mapped to exact names in the pinned M49 page.
# UK constituent-country rows and dissolved areas are deliberately absent: mapping them to a
# present-day sovereign code would merge distinct source assertions.
UNSD_TO_M49_ALIASES = {
    "Bolivia": "Bolivia (Plurinational State of)",
    "Cape Verde": "Cabo Verde",
    "China - Hong Kong SAR": "China, Hong Kong Special Administrative Region",
    "China - Macao SAR": "China, Macao Special Administrative Region",
    "Korea, Democratic People's Republic of": "Democratic People's Republic of Korea",
    "Korea, Republic of": "Republic of Korea",
    "Libya Arab Jamahiriya": "Libya",
    "Netherlands": "Netherlands (Kingdom of the)",
    "Palestine, State of": "State of Palestine",
    "Saint Helena ex. dep.": "Saint Helena",
    "Saint-Martin": "Saint Martin (French Part)",
    "Sint Maarten": "Sint Maarten (Dutch part)",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Lucia": "Saint Lucia",
    "St. Pierre and Miquelon": "Saint Pierre and Miquelon",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "Turkey": "Türkiye",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "Venezuela": "Venezuela (Bolivarian Republic of)",
}

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
MONTH_OR_FULL = r"[A-Za-z]+\.?"


class UNSDParseError(ValueError):
    """Raised when captured UNSD evidence violates the parsing contract."""


def _space(value: str) -> str:
    return " ".join(value.split())


def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
    value = dict(attrs).get("class") or ""
    return set(value.split())


@dataclass(frozen=True)
class M49Country:
    country_name: str
    m49_code: str
    iso_alpha2: str
    iso_alpha3: str


@dataclass(frozen=True)
class RawCensusCell:
    region: str
    source_country_name: str
    census_round: str
    occurrence: int
    raw_text: str
    footnotes: tuple[str, ...]
    source_links: tuple[str, ...]


@dataclass(frozen=True)
class CensusDateAssertion:
    region: str
    source_country_name: str
    country_id: str | None
    crosswalk_status: str
    census_round: str
    occurrence: int
    raw_text: str
    assertion_status: str
    date_start: str | None
    date_end: str | None
    date_precision: str | None
    footnotes: tuple[str, ...]
    source_links: tuple[str, ...]


class _CensusHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.pane: str | None = None
        self.pane_depth: int | None = None
        self.row_depth: int | None = None
        self.cell_depth: int | None = None
        self.headline_depth: int | None = None
        self.sup_depth: int | None = None
        self.link: str | None = None
        self.cell_text: list[str] = []
        self.cell_footnotes: list[str] = []
        self.cell_links: list[str] = []
        self.row: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
        self.rows: list[tuple[str, list[tuple[str, tuple[str, ...], tuple[str, ...]]]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            self.div_depth += 1
            element_id = dict(attrs).get("id")
            if element_id in REGION_PANES and "tab-pane" in _classes(attrs):
                self.pane = element_id
                self.pane_depth = self.div_depth
            elif self.pane and self.row_depth is None and "row" in _classes(attrs):
                self.row_depth = self.div_depth
                self.row = []
            elif (
                self.row_depth is not None
                and self.cell_depth is None
                and self.div_depth == self.row_depth + 1
                and "col-md-2" in _classes(attrs)
            ):
                self.cell_depth = self.div_depth
                self.cell_text = []
                self.cell_footnotes = []
                self.cell_links = []
            elif self.cell_depth is not None and "headline" in _classes(attrs):
                self.headline_depth = self.div_depth
        elif tag == "sup" and self.cell_depth is not None:
            self.sup_depth = self.div_depth
        elif tag == "a" and self.cell_depth is not None:
            href = dict(attrs).get("href")
            if href:
                self.link = href
                self.cell_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            self.sup_depth = None
        elif tag == "a":
            self.link = None
        elif tag == "div":
            if self.headline_depth == self.div_depth:
                self.headline_depth = None
            if self.cell_depth == self.div_depth:
                self.row.append(
                    (
                        _space("".join(self.cell_text)),
                        tuple(self.cell_footnotes),
                        tuple(dict.fromkeys(self.cell_links)),
                    )
                )
                self.cell_depth = None
            if self.row_depth == self.div_depth:
                if self.row:
                    self.rows.append((self.pane or "", self.row))
                self.row_depth = None
            if self.pane_depth == self.div_depth:
                self.pane = None
                self.pane_depth = None
            self.div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.cell_depth is None or self.headline_depth is not None:
            return
        if self.sup_depth is not None:
            value = _space(data)
            if value:
                self.cell_footnotes.append(value)
        else:
            self.cell_text.append(data)


class _M49HTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.table_depth = 0
        self.in_body = False
        self.in_row = False
        self.in_cell = False
        self.cell_text: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and dict(attrs).get("id") == "downloadTableEN":
            self.in_table = True
            self.table_depth = 1
        elif self.in_table and tag == "table":
            self.table_depth += 1
        elif self.in_table and tag == "tbody":
            self.in_body = True
        elif self.in_body and tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag == "td":
            self.row.append(_space("".join(self.cell_text)))
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
        elif self.in_body and tag == "tbody":
            self.in_body = False
        elif self.in_table and tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_text.append(data)


def parse_m49_countries(html: str) -> list[M49Country]:
    parser = _M49HTMLParser()
    parser.feed(html)
    countries: list[M49Country] = []
    for row in parser.rows:
        if len(row) < 12:
            raise UNSDParseError("M49 English table row has fewer than 12 cells")
        country = M49Country(row[8], row[9], row[10], row[11])
        if not re.fullmatch(r"\d{3}", country.m49_code):
            raise UNSDParseError("M49 code must contain three digits")
        if not re.fullmatch(r"[A-Z]{3}", country.iso_alpha3):
            raise UNSDParseError("M49 country row lacks an ISO alpha-3 code")
        countries.append(country)
    if not countries:
        raise UNSDParseError("M49 English table was not found")
    if len({row.iso_alpha3 for row in countries}) != len(countries):
        raise UNSDParseError("M49 English table contains duplicate ISO alpha-3 codes")
    return countries


def parse_raw_census_cells(html: str) -> list[RawCensusCell]:
    parser = _CensusHTMLParser()
    parser.feed(html)
    output: list[RawCensusCell] = []
    current_country: dict[str, str] = {}
    current_country_footnotes: dict[str, tuple[str, ...]] = {}
    occurrences: dict[tuple[str, str], int] = {}
    for region, row in parser.rows:
        if not row:
            continue
        source_country = row[0][0]
        if source_country:
            current_country[region] = source_country
            current_country_footnotes[region] = row[0][1]
        elif region not in current_country:
            raise UNSDParseError(f"{region} contains a continuation row without a country")
        source_country = current_country[region]
        cells = row[1:6]
        cells.extend([("", (), ())] * (5 - len(cells)))
        for census_round, (raw_text, footnotes, links) in zip(ROUNDS, cells, strict=True):
            key = (source_country, census_round)
            occurrences[key] = occurrences.get(key, 0) + 1
            output.append(
                RawCensusCell(
                    region,
                    source_country,
                    census_round,
                    occurrences[key],
                    raw_text,
                    tuple(dict.fromkeys((*current_country_footnotes.get(region, ()), *footnotes))),
                    links,
                )
            )
    if not output:
        raise UNSDParseError("No regional census-date cells were found")
    return output


def _name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = normalized.replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).strip()


def build_country_crosswalk(
    source_names: list[str],
    m49: list[M49Country],
    *,
    aliases: dict[str, str] | None = None,
) -> dict[str, tuple[str | None, str]]:
    index: dict[str, set[str]] = {}
    for row in m49:
        index.setdefault(_name_key(row.country_name), set()).add(row.iso_alpha3)
    alias_keys = {_name_key(key): _name_key(value) for key, value in (aliases or {}).items()}
    result: dict[str, tuple[str | None, str]] = {}
    for source_name in source_names:
        key = alias_keys.get(_name_key(source_name), _name_key(source_name))
        matches = index.get(key, set())
        if len(matches) == 1:
            result[source_name] = (next(iter(matches)), "matched")
        elif len(matches) > 1:
            result[source_name] = (None, "ambiguous")
        else:
            result[source_name] = (None, "unmatched")
    return result


def _month(value: str) -> int:
    key = value.rstrip(".").casefold()
    if key not in MONTHS:
        raise ValueError(value)
    return MONTHS[key]


def _iso(year: str, month: str = "1", day: str = "1") -> str:
    return date(int(year), int(month), int(day)).isoformat()


def classify_date_text(raw_text: str) -> tuple[str, str | None, str | None, str | None]:
    """Classify one source cell without correcting or crashing on malformed source text."""
    try:
        return _classify_date_text(raw_text)
    except (ValueError, OverflowError):
        return "unparsed", None, None, None


def _classify_date_text(raw_text: str) -> tuple[str, str | None, str | None, str | None]:
    text = _space(raw_text)
    if not text:
        return "blank", None, None, None
    if text == "-":
        return "no_census_or_plan", None, None, None
    if text == "(...)":
        return "planned_decade", None, None, "decade"
    if re.fullmatch(r"\[\s*\d{4}\s*\]", text):
        return "planned_unconfirmed", None, None, "year"
    if text.startswith("(") and text.endswith(")"):
        inner = text[1:-1].strip()
        status, start, end, precision = _classify_date_text(inner)
        if status.startswith("observed_"):
            return "planned_date", start, end, precision
        return "unparsed", None, None, None
    exact = re.fullmatch(rf"(\d{{1,2}})\s+({MONTH_OR_FULL})\s*(\d{{4}})", text)
    if exact:
        day, month, year = exact.groups()
        value = _iso(year, str(_month(month)), day)
        return "observed_exact", value, value, "day"
    same_month = re.fullmatch(
        rf"(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+({MONTH_OR_FULL})\s+(\d{{4}})", text
    )
    if same_month:
        first, last, month, year = same_month.groups()
        return (
            "observed_interval",
            _iso(year, str(_month(month)), first),
            _iso(year, str(_month(month)), last),
            "day",
        )
    cross_month = re.fullmatch(
        rf"(\d{{1,2}})\s+({MONTH_OR_FULL})\s*-\s*(\d{{1,2}})\s+({MONTH_OR_FULL})\s+(\d{{4}})",
        text,
    )
    if cross_month:
        first, month1, last, month2, year = cross_month.groups()
        return (
            "observed_interval",
            _iso(year, str(_month(month1)), first),
            _iso(year, str(_month(month2)), last),
            "day",
        )
    cross_year = re.fullmatch(
        rf"(\d{{1,2}})\s+({MONTH_OR_FULL})\s*(\d{{4}})\s*-\s*"
        rf"(\d{{1,2}})\s+({MONTH_OR_FULL})\s*(\d{{4}})",
        text,
    )
    if cross_year:
        first, month1, year1, last, month2, year2 = cross_year.groups()
        return (
            "observed_interval",
            _iso(year1, str(_month(month1)), first),
            _iso(year2, str(_month(month2)), last),
            "day",
        )
    month_range = re.fullmatch(rf"({MONTH_OR_FULL})\s*-\s*({MONTH_OR_FULL})\s+(\d{{4}})", text)
    if month_range:
        month1, month2, year = month_range.groups()
        return (
            "observed_interval",
            _iso(year, str(_month(month1))),
            _iso(year, str(_month(month2))),
            "month",
        )
    month_only = re.fullmatch(rf"({MONTH_OR_FULL})\s+(\d{{4}})", text)
    if month_only:
        month, year = month_only.groups()
        value = _iso(year, str(_month(month)))
        return "observed_month", value, value, "month"
    year_range = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", text)
    if year_range:
        first, last = year_range.groups()
        return "observed_interval", _iso(first), _iso(last), "year"
    if re.fullmatch(r"\d{4}", text):
        value = _iso(text)
        return "observed_year", value, value, "year"
    return "unparsed", None, None, None


def build_census_assertions(
    cells: list[RawCensusCell], crosswalk: dict[str, tuple[str | None, str]]
) -> list[CensusDateAssertion]:
    assertions: list[CensusDateAssertion] = []
    for cell in cells:
        country_id, crosswalk_status = crosswalk.get(cell.source_country_name, (None, "unmatched"))
        status, start, end, precision = classify_date_text(cell.raw_text)
        assertions.append(
            CensusDateAssertion(
                cell.region,
                cell.source_country_name,
                country_id,
                crosswalk_status,
                cell.census_round,
                cell.occurrence,
                cell.raw_text,
                status,
                start,
                end,
                precision,
                cell.footnotes,
                cell.source_links,
            )
        )
    validate_census_assertions(assertions)
    return assertions


def validate_census_assertions(assertions: list[CensusDateAssertion]) -> None:
    identities: set[tuple[str, str, int]] = set()
    for row in assertions:
        if row.assertion_status not in ASSERTION_STATUSES:
            raise UNSDParseError("invalid assertion_status")
        if row.crosswalk_status not in CROSSWALK_STATUSES:
            raise UNSDParseError("invalid crosswalk_status")
        if (row.country_id is None) != (row.crosswalk_status != "matched"):
            raise UNSDParseError("country_id and crosswalk_status are inconsistent")
        if row.assertion_status.startswith("observed_") or row.assertion_status == "planned_date":
            if row.date_start is None or row.date_end is None or row.date_precision is None:
                raise UNSDParseError("dated assertion is missing interval bounds or precision")
            if date.fromisoformat(row.date_start) > date.fromisoformat(row.date_end):
                raise UNSDParseError("date interval is reversed")
        elif row.date_start is not None or row.date_end is not None:
            raise UNSDParseError("non-dated assertion cannot contain date bounds")
        identity = (row.source_country_name, row.census_round, row.occurrence)
        if identity in identities:
            raise UNSDParseError("duplicate source census cell")
        identities.add(identity)


def require_expected_exceptions(
    assertions: list[CensusDateAssertion],
    *,
    allowed_unmatched: set[str],
    allowed_unparsed: set[str],
) -> None:
    """Require an exact, reviewed exception set rather than accepting new source drift."""
    actual_unmatched = {
        row.source_country_name for row in assertions if row.crosswalk_status != "matched"
    }
    actual_unparsed = {row.raw_text for row in assertions if row.assertion_status == "unparsed"}
    if actual_unmatched != allowed_unmatched:
        raise UNSDParseError(
            f"unmatched country labels changed: expected={sorted(allowed_unmatched)!r}, "
            f"actual={sorted(actual_unmatched)!r}"
        )
    if actual_unparsed != allowed_unparsed:
        raise UNSDParseError(
            f"unparsed date cells changed: expected={sorted(allowed_unparsed)!r}, "
            f"actual={sorted(actual_unparsed)!r}"
        )


def census_assertions_csv_bytes(
    assertions: list[CensusDateAssertion],
    *,
    source_id: str,
    source_release: str,
    snapshot_id: str,
) -> bytes:
    """Serialize staging assertions as deterministic UTF-8 CSV bytes."""
    validate_census_assertions(assertions)
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=ASSERTION_OUTPUT_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in assertions:
        writer.writerow(
            {
                "region": row.region,
                "source_country_name": row.source_country_name,
                "country_id": row.country_id or "",
                "crosswalk_status": row.crosswalk_status,
                "census_round": row.census_round,
                "occurrence": row.occurrence,
                "raw_text": row.raw_text,
                "assertion_status": row.assertion_status,
                "date_start": row.date_start or "",
                "date_end": row.date_end or "",
                "date_precision": row.date_precision or "",
                "footnotes_json": json.dumps(
                    row.footnotes, ensure_ascii=False, separators=(",", ":")
                ),
                "source_links_json": json.dumps(
                    row.source_links, ensure_ascii=False, separators=(",", ":")
                ),
                "source_id": source_id,
                "source_release": source_release,
                "snapshot_id": snapshot_id,
            }
        )
    return handle.getvalue().encode("utf-8")
