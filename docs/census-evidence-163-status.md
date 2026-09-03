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

This snapshot establishes documentary census-date assertions only. Parsing remains open because
the table contains date ranges, multiple dates, parenthesized planned dates, dashes, ellipses,
symbols, and footnotes that cannot be coerced safely into one exact reference date.

Issue #163 is not empirically complete. Required PES, undercount, coverage-adjustment,
results-status, and WPP/IDB incorporation evidence is distributed across country reports and
publisher notes. The UNFPA, WPP, and IDB artifacts still need release-specific capture,
checksums, licenses, crosswalks, and transformation lineage. A global census-date capture alone
satisfies only part of one field and must not be presented as completion.
