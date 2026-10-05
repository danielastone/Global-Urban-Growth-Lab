# World Bank SPI evidence — issue #166

The registered source is the World Bank December 9, 2025 SPI output at upstream commit
`2b474a5a0c5274b7988200747afae8c7eaa58564`. The workflow downloads and verifies the
data, metadata, license, and December 4 pre-release comparison snapshot.

The transformation retains 40 indicators from data products (pillar 3), data sources
(pillar 4), and data infrastructure (pillar 5) in long form. Values remain on their
published 0–1 scale. No overall SPI index or cross-pillar average is produced. Pillar 3
is marked product availability, pillar 4 production sources, and pillar 5 production
capacity; these are not interchangeable constructs or direct measures of population accuracy.

The source contains 217 economy codes and years 2004–2024. `XKX` is retained with its
source name but has no project `country_id`; it is reported as an unresolved crosswalk.
All other source codes are retained as direct source-ISO3 project identifiers pending a
broader country/territory policy in #170.

The December 9 file differs from the December 4 pre-release file in 2 of 182,280 common
selected-indicator cells. Revision-vintage qualification is therefore material even within
a nominal release cycle. The upstream July 2026 metadata table does not align perfectly with
the December output columns, so identifiers are derived from the pinned data rather than a
silent forced metadata join.

This evidence describes statistical-system production and availability. It does not validate
country population counts, city growth estimates, or any universal reliability tier.
