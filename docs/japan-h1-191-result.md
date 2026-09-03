# Japan direct-count H1 hierarchy — issue 191

## Decision

The preregistered strict-stability result supports H1 for a narrow Japan DID sample. Raw
persistence beats both the prior-origin mean and size-only models under the 5% RMSE/95%-lower-bound
gate, with MAE also improving. The high-coverage dynamic-identity diagnostic does not pass the same
uncertainty gate. The result is therefore boundary-selection-sensitive and cannot be generalized to
all Japanese DIDs or universal H1.

## Design

The source panel extends the registered MLIT A16 DID archive set backward to 1990 and 1995, yielding
seven direct census waves through 2020. The 94 added prefectural archives have registered SHA-256
digests. Multipart source features are dissolved by official vintage DID identifier before cohort
construction.

The 25,000–100,000 cohort is defined independently at every forecast origin before concordance.
The first eligible origin supplies training data; 2000, 2005, 2010, and 2015 are chronological test
origins. For each test origin, models use only earlier origin outcomes. All models are scored on
identical rows.

Models:

- prior-origin mean;
- size-only linear model using log origin population;
- raw persistence, predicting future growth with observed recent growth;
- fitted recent-growth linear model.

The registered primary forecast is raw persistence. Uncertainty resamples both connected DID
lineages and the four test origins. The gate requires at least 5% RMSE improvement with the 95%
lower bound at or above 5%, plus non-worsening MAE. Four origin clusters are the minimum accepted
for this gate.

## Primary strict-stability result

The strict 99.5%-overlap denominator contains 1,706 forecast-origin DIDs, of which 122 (7.2%) have
eligible three-wave histories. The chronological test set contains 100 rows in 40 connected
lineages across four test origins.

| Baseline | RMSE improvement | 95% interval | MAE improvement | Gate |
|---|---:|---:|---:|---|
| Prior-origin mean | 39.4% | 19.8% to 62.9% | 0.479 pp | Pass |
| Size only | 40.3% | 18.4% to 64.8% | 0.480 pp | Pass |

All threshold-band sensitivities pass against both baselines after excluding 47,500–52,500,
45,000–55,000, or 40,000–60,000 origin populations. Test samples range from 86 to 98 rows and the
lower RMSE bounds remain above 20% in the reported bootstrap draws.

## Dynamic-identity diagnostic

Dynamic identity retains 1,415 of 1,706 denominator rows (82.9%) and produces 1,161 chronological
test rows. Persistence point estimates improve RMSE by 8.5% versus the prior-origin mean and 8.3%
versus size only, while MAE improves by about 0.14 percentage points. The two-way 95% lower bounds
are negative, so neither comparison passes. None of the threshold-band exclusions changes that
decision.

The fitted recent-growth model improves the dynamic point estimate, but it also fails the registered
5% lower-bound rule. On the strict sample, fitting attenuates performance relative to raw
persistence and fails the gate. The favorable primary result is specifically a stable-geography
persistence result, not generic evidence that estimating a recent-growth coefficient improves
forecasting.

## Interpretation

The result upgrades H1 from “source-sensitive and universally unsupported” to “supported for a
strict, selected Japanese fixed-geography sample.” It does not rescue universal H1. The strict
sample loses 92.8% of the origin denominator, while the high-coverage changing-boundary diagnostic
does not clear uncertainty. This is a real finding, but a narrow one: persistence is commercially
useful where geographic identity is exceptionally stable, and its broader transfer remains
unconfirmed.
