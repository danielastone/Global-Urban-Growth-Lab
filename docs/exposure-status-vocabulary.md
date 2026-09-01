# Exposure status controlled vocabulary

`truncation_exposure` and `survivorship_exposure` are headline-gating evidence, not free-form notes.

Accepted values are limited to:

- `none`
- `low`
- `material`
- `unknown`

`none` and `low` can satisfy the generic headline exposure gate. `material` and `unknown` block headline eligibility. Blank values remain separately identified as missing evidence.

Any other value is treated as unrecognized/unknown evidence and fails headline eligibility with an explicit reason. This prevents typos, novel adapter labels, or source-specific phrases such as `moderate` or `not_applicable` from silently being interpreted as acceptable exposure.

Source-specific adapters that need a different exposure concept should map it deliberately into the common vocabulary or keep it in a separate descriptive field rather than expanding the common gate implicitly.