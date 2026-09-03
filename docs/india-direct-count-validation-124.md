# India direct-count qualification for issue #124

India is scientifically relevant because it is both a large share of the WUP evaluation
sample and materially influential in the 2020 persistence failure. It is not currently an
identified direct-count validation panel.

## Official-source assessment

The Census of India catalog publishes 2011 A-04 population-class tables with historical
town/urban-agglomeration populations for 1981, 1991, 2001, and 2011. Those four columns do
not by themselves create an origin-valid panel. The table is classified using the 2011
town and size-class frame. Treating its historical rows as the 1981 or 1991 denominator
would select on later urban status, survival, and size—the exact denominator error this
repository prohibits.

The 2001 and 2011 Primary Census Abstract and Location Code Directory materials can
support a historical transition and concordance-coverage audit. They provide only one
transition, however, so they cannot supply recent growth followed by future growth. That
exercise is permitted as historical data-quality work but cannot close #124 or independently
confirm H1.

Original 1981, 1991, 2001, and 2011 state town directories could eventually support two
forecast origins if origin cohorts are reconstructed separately. The binding missing input
is a registered, defensible official adjacent-wave concordance covering new towns,
declassifications, splits, mergers, name changes, and boundary changes. Name matching is not
an acceptable substitute.

India's next population census has a March 1, 2027 reference date (October 1, 2026 for
specified snow-bound areas). Locality outputs and crosswave concordances have not been
released, so Census 2027 is a future validation path rather than current evidence.

## Machine-readable decision

Run:

```bash
uv run --locked python scripts/run_construction_smoothing_124.py --pilot india
```

The runner writes `india_source_qualification.csv` and `india_benchmark_status.csv`.
The current decision is
`unresolved_no_origin_valid_multiwave_concorded_town_panel`, with both
`benchmark_estimable` and `h1_independent_confirmation` false.

The next useful action is not to regress the A-04 historical columns. It is to inventory and
digitize original town universes by wave, then quantify official concordance coverage against
each origin denominator. If that coverage cannot be made defensible, India should remain a
historical transition sensitivity and not be presented as validation.
