# Data

No analytical data have been committed yet.

## Intended source classes

- United Nations World Urbanization Prospects city or urban-agglomeration estimates
- DEGURBA-related city, town, and rural classifications where redistribution is permitted
- National population and urban-share series
- Geographic coordinates, country boundaries, and accessibility measures
- Documented auxiliary sources used for case validation

## Rules

- Preserve raw downloads unchanged.
- Record source URL, release, retrieval date, license, checksum, and citation.
- Do not commit data when redistribution terms are unclear.
- Assign stable project identifiers; do not rely on names alone.
- Document boundary, definition, and name changes.
- Separate reported observations from interpolated or modeled estimates.
- Generate processed data only through code.
- Pass the intended operation through `urban-growth-sources check-license` before
  commercial ingestion, redistribution, model fitting, or customer delivery.

## Required manifest fields

```text
source_id
publisher
dataset
release
retrieved_at
source_url
license
local_path
sha256
redistribution_allowed
notes
```

The manifest records acquired files. It does not grant permission. Source-level legal
decisions and attribution requirements are maintained separately in
`data/licenses.json`; see [THIRD_PARTY_DATA.md](../THIRD_PARTY_DATA.md).
