# UNFPA Global Census Tracker qualification for issue #163

The UNFPA Global Census Tracker is now registered as a documentary reliability-evidence source,
but it is not yet admitted to an evidence transformation. Three exact ArcGIS REST responses
captured on 3 September 2026 are checksum-registered: the feature-service item metadata, the layer
schema, and an `OBJECTID ASC` query of all layer rows. The raw JSON remains outside Git because
the item has blank `licenseInfo` and `accessInformation` fields and the general UNFPA terms do not
establish redistribution rights.

## Provenance and vintage

The official UNFPA Data page links the Global Census Tracker. The tracker experience, owned by
UNFPA's Population Data Portal team, embeds three dashboards whose web maps all reference ArcGIS
item `e40524a0370f4eae8e50acd20ab5e431`, feature layer `census_joined`. The item belongs to UNFPA's
ArcGIS organization and is owned by `ahid@unfpa.org_UNFPAPDP`.

The layer data was last edited at `2023-02-28T20:54:22.794Z`. The containing ArcGIS item was
modified at `2024-03-12T18:20:36Z`. An item-metadata change does not refresh the data vintage.
Accordingly, this source is qualified as a pinned 2023 layer and must not be described as current
2026 census status merely because the live dashboard is still available.

## What the layer can and cannot establish

The layer can provide source-qualified assertions about planned and actual census timing,
previous census year, de jure/de facto reference basis, census-round type, collection method, and
reported COVID-19 impact. Each assertion must retain its source `OBJECTID`, original label, and
snapshot identity.

The layer does not establish results publication status, post-enumeration-survey status,
undercount, coverage adjustment, census quality, or incorporation into WPP, IDB, or another
estimate series. Missing or favorable operational fields must not be converted into any of those
claims.

## Row audit and fail-closed requirements

The ordered query contains 292 unique `OBJECTID` rows. Sixty-three have no `Country` or
`ISO3CD_1` tracker attributes, leaving 229 attributed rows and 217 unique country labels. Those 63
rows remain visible in attrition accounting; they cannot be silently dropped from the source
denominator.

Several country labels occur more than once. Some repetitions are identical, while Egypt,
Portugal, French Polynesia, the Russian Federation, Sudan, South Sudan, and Venezuela contain
conflicting evidence fields. An adapter must preserve these as separate source assertions rather
than select or merge a preferred row.

Two explicit tracker-code defects require reviewed aliases rather than automatic coercion:

- `OBJECTID 255` labels the Republic of the Marshall Islands with tracker code `RMI`, while the
  base geography code is `MHL`.
- `OBJECTID 279` labels the British Virgin Islands with tracker code `VG`, while the base
  geography code is `VGB`.

Before any transformation is registered, the adapter must verify all three input checksums,
preserve null and conflicting rows, declare the reviewed code exceptions, and emit no inferred
PES, undercount, adjustment, results-status, quality, or estimate-incorporation fields.
