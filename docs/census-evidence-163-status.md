# Census evidence #163 — schema and UNSD snapshot implemented, acquisition open

The executable census-event and estimate-incorporation contracts are implemented in
`src/urban_growth/census_evidence.py`. They enforce controlled vocabularies, chronology,
source-specific event identities, assertion uniqueness, explicit unknown states, and
estimate-series/vintage-qualified incorporation claims. Conflicting source assertions remain
separate rows. Census recency never implies quality, PES status, undercount, adjustment, or
incorporation.

The UNSD *Census dates for all countries* page displayed as last updated 3 February 2026 is now
registered as an immutable snapshot. The exact 248,740-byte response captured on 3 September
2026 has SHA-256
`900b7f3691efe2c1309e422b16816e5ed45ebb127a7e71db3443f987fccf6165`. The raw HTML is not
committed because the exact page's redistribution terms remain unresolved. Its source, rights,
and snapshot records therefore fail closed for distribution.

This snapshot establishes documentary census-date assertions only.

## Parsing and crosswalk contract

`src/urban_growth/unsd_census_dates.py` parses the source HTML without adding an HTML-parser
dependency. It preserves every regional table cell, continuation-row occurrence, source label,
footnote, and source link. Its mutually exclusive states distinguish observed exact dates,
observed intervals, month/year precision, expected dates, planned-but-unconfirmed years,
expected-decade placeholders, no-census-or-plan markers, blanks, and unparsed source text.

The country crosswalk uses a separately pinned capture of the official UNSD M49 English table.
Aliases are explicit and source-specific. Current M49 identifiers are not forced onto dissolved
areas or UK constituent-country rows.

A local audit of the two exact registered captures found 1,530 source cells across 242 source
labels. Of those labels, 237 map to one M49 ISO alpha-3 identifier. Five remain unmatched:
England and Wales, Northern Ireland, Scotland, Nauru, and Netherlands Antilles. The first three
are subnational source rows, Netherlands Antilles is a dissolved area, and Nauru is absent from
the captured M49 English table. These rows remain in the denominator with null `country_id`.

Of the 1,530 cells, one remains syntactically unparsed because the source says
`11 Octoer 1994`. The parser does not silently repair that typo. No parsed assertion is yet
promoted to a `CensusEvent`: the UNSD date table alone does not establish reference-date versus
enumeration-date semantics, results status, geographic coverage, or census quality.

Issue #163 is not empirically complete. Required PES, undercount, coverage-adjustment,
results-status, and WPP/IDB incorporation evidence is distributed across country reports and
publisher notes. The UNFPA, WPP, and IDB artifacts still need release-specific capture,
checksums, licenses, crosswalks, and transformation lineage. The parsed assertion output also
needs a registered transformation run once the source-rights decision permits a committed
derived table. A global census-date capture alone satisfies only part of one field and must not
be presented as completion.
