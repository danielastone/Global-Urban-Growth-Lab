import csv
import io

import pytest

from urban_growth.unsd_census_dates import (
    UNSD_TO_M49_ALIASES,
    UNSDParseError,
    build_census_assertions,
    build_country_crosswalk,
    census_assertions_csv_bytes,
    classify_date_text,
    parse_m49_countries,
    parse_raw_census_cells,
    require_expected_exceptions,
)

CENSUS_HTML = """
<div class="tab-pane" id="North">
  <div class="row">
    <div class="col-md-2"><div class="headline">Countries or areas</div>United States of America<sup>(C)</sup></div>
    <div class="col-md-2"><div class="headline">1990 round</div><sup>(17)</sup> 1 April 1990</div>
    <div class="col-md-2"><div class="headline">2000 round</div>1-15 April 2000</div>
    <div class="col-md-2"><div class="headline">2010 round</div>-</div>
    <div class="col-md-2"><div class="headline">2020 round</div>[2020]</div>
    <div class="col-md-2"><div class="headline">2030 round</div>(1 April 2030)</div>
  </div>
  <div class="row">
    <div class="col-md-2"></div><div class="col-md-2"></div>
    <div class="col-md-2"><a href="https://example.test">9 Jan. - 20 Feb. 2001</a></div>
    <div class="col-md-2"></div><div class="col-md-2"></div><div class="col-md-2">(...)</div>
  </div>
</div>
"""

M49_HTML = """
<table id="downloadTableEN"><tbody><tr>
<td>001</td><td>World</td><td>019</td><td>Americas</td><td>021</td><td>Northern America</td>
<td></td><td></td><td>United States of America</td><td>840</td><td>US</td><td>USA</td>
</tr></tbody></table>
"""


def test_parser_preserves_continuation_rows_footnotes_and_links():
    cells = parse_raw_census_cells(CENSUS_HTML)
    assert len(cells) == 10
    first = cells[0]
    assert first.source_country_name == "United States of America"
    assert first.raw_text == "1 April 1990"
    assert first.footnotes == ("(C)", "(17)")
    continuation = cells[6]
    assert continuation.occurrence == 2
    assert continuation.footnotes == ("(C)",)
    assert continuation.source_links == ("https://example.test",)


def test_m49_crosswalk_and_assertions_do_not_invent_country_codes():
    m49 = parse_m49_countries(M49_HTML)
    crosswalk = build_country_crosswalk(
        ["United States of America", "Unknown place"],
        m49,
        aliases=UNSD_TO_M49_ALIASES,
    )
    assert crosswalk["United States of America"] == ("USA", "matched")
    assert crosswalk["Unknown place"] == (None, "unmatched")
    assertions = build_census_assertions(parse_raw_census_cells(CENSUS_HTML), crosswalk)
    assert assertions[0].country_id == "USA"
    assert assertions[0].assertion_status == "observed_exact"
    assert assertions[0].date_start == "1990-04-01"


def test_symbol_states_remain_distinct():
    expected = {
        "": "blank",
        "-": "no_census_or_plan",
        "(...)": "planned_decade",
        "[2023]": "planned_unconfirmed",
        "(1 April 2030)": "planned_date",
        "1 April 2020": "observed_exact",
        "16-30 April 2008": "observed_interval",
        "9 Jan. - 20 Feb. 2011": "observed_interval",
        "23 Oct. 2011-23 Jan. 2012": "observed_interval",
        "31 Dec.2011-31 Mar.2012": "observed_interval",
        "June - July 2004": "observed_interval",
        "Jan.-Mar. 1986": "observed_interval",
        "December 2012": "observed_month",
        "1985-1989": "observed_interval",
        "1 Octoer 2011": "unparsed",
        "not a date": "unparsed",
    }
    for raw, status in expected.items():
        assert classify_date_text(raw)[0] == status


def test_exception_gate_requires_exact_reviewed_sets():
    m49 = parse_m49_countries(M49_HTML)
    crosswalk = build_country_crosswalk(["United States of America"], m49)
    assertions = build_census_assertions(parse_raw_census_cells(CENSUS_HTML), crosswalk)
    require_expected_exceptions(assertions, allowed_unmatched=set(), allowed_unparsed=set())
    with pytest.raises(UNSDParseError, match="unmatched country labels changed"):
        require_expected_exceptions(
            assertions,
            allowed_unmatched={"invented exception"},
            allowed_unparsed=set(),
        )


def test_csv_serialization_is_deterministic_and_keeps_source_snapshot():
    m49 = parse_m49_countries(M49_HTML)
    crosswalk = build_country_crosswalk(["United States of America"], m49)
    assertions = build_census_assertions(parse_raw_census_cells(CENSUS_HTML), crosswalk)
    kwargs = {
        "source_id": "unsd_dates",
        "source_release": "release",
        "snapshot_id": "snapshot:abc",
    }
    first = census_assertions_csv_bytes(assertions, **kwargs)
    assert first == census_assertions_csv_bytes(assertions, **kwargs)
    rows = list(csv.DictReader(io.StringIO(first.decode("utf-8"))))
    assert rows[0]["snapshot_id"] == "snapshot:abc"
    assert rows[0]["footnotes_json"] == '["(C)","(17)"]'
