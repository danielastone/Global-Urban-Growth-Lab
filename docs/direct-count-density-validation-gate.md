# Direct-count density validation gate

Status: implementation complete; empirical execution blocked as of 2 September 2026.

## Why no result is registered

The repository has a U.S. Census place acquisition and concordance pipeline, but no acquired
U.S. pilot result is registered. The Mexico acquisition remains explicitly blocked. Neither
pilot currently supplies an accepted same-support relationship between directly enumerated
population and the fixed polygon used to aggregate GHSL built surface, built volume and
GHS-POP.

A whole-place or whole-locality census count cannot be divided by a UCDB urban-centre
denominator merely because the two features overlap or share a name. That would assign a
numerator and denominator from different geographic supports and falsely label the result
lineage-clean. Execution therefore fails unless `census_population_support_id` exactly equals
`denominator_support_id`, the count is marked `direct_enumeration`, and geography is stable or
supported by an official crosswalk.

## Implemented analysis

`urban_growth.density_validation` provides:

- log census and GHS-POP densities over built surface and built volume;
- mandatory density-registry identifiers on every downstream density column;
- the identity `log(GHS-POP density) - log(census density) = log(GHS-POP / census)`, making
  clear that the discrepancy itself is denominator-invariant when supports match;
- discrepancy distributions overall, by census size and by built-surface-growth tercile;
- percentile intervals from resampling complete pilot-region clusters;
- raw and denominator-partialled density correlations; and
- leave-one-pilot-region-out C3 comparisons of prior surface growth, prior volume/surface and
  an intercept-only baseline.

## Locked demotion rule

For either shared-denominator density family, denominator-driven correlation is declared when
the absolute partial correlation is below 0.20 and falls by at least 0.30 from the absolute raw
correlation. If this occurs in the overall matched sample, all GHS-POP-based density metrics
remain or are demoted to `construction_sensitive_robustness`; they cannot enter headline C1 or
C3 results. This matches the evidentiary treatment of GHSL persistence in issue #125.

## Evidence required to unblock

1. Acquired and checksum-registered direct census counts for at least one pilot.
2. Fixed population support for each census year.
3. Built and GHS-POP rasters aggregated to that exact support, or an accepted non-built-weighted
   population crosswalk into the analysis polygon with uncertainty retained.
4. At least two pilot-region clusters and adequate support within reported strata.
5. A prior form interval ending at the census-density forecast origin for the clean C3 test.

Synthetic tests validate the calculations and failure rules. They are not empirical evidence
and no result table or expected-output manifest is created from them.
