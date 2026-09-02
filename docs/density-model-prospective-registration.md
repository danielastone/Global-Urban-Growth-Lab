# Density-model prospective-registration audit

## Status

The density-model candidate set, timing clocks, resampling unit and falsification rule were fixed
before any registered direct-count density outcome or real-data density-model result existed.
The original model registration landed in PR #153. PR #155 corrected the enforcement defects
identified before data acquisition and prospectively fixed the practical threshold described
below. These changes cannot be described as a pristine preregistration independent of all design
discussion, but they precede the outcome artifact and empirical run they govern.

## Practical improvement threshold

The primary comparison is relative RMSE improvement over the contemporaneous-country density
baseline on identical held-out rows. Passing requires the lower bound of the registered 95%
state/entidad-clustered interval to be at least 5%, with MAE no worse. The 5% floor was committed
in PR #155 before direct-count outcome registration. It is a prospective decision threshold, not
an effect-size estimate or a threshold selected after inspecting model performance.

## Timing limitation recorded before execution

For the 2010–2020 direct-count change outcome, the forecast origin is 2010. The registered
primary feature set available at that origin is limited to built-surface share, retrospectively
backcast time-invariant terrain slope, and GHSL land fraction. Open Buildings height begins in
2016 and cannot be moved backward to the 2010 origin. Any later height-enabled census design
requires a new dated registration and cannot revise the original 2010–2020 test.
