# Hellenistic Sect Authority Admission

**Verdict: admit horizon-frame authority for Hellenistic composition.**

## Object

Chart sect for Hellenistic work is the Sun’s hemisphere relative to the
exact Ascendant/Descendant, using `DignityHorizonFrame` (ASC + MC). Sun
on the ASC/DSC boundary is `not_evaluable`.

## Existing paths that are not Hellenistic authority

- `ChartContext.is_day` from house cusps 1 and 7 (defaults Placidus)
- `calculate_dignities` without a frame (`sun_house >= 7`)
- `LotsService.is_day_chart` (Sun-on-ASC treated as day)

Hellenistic lots of Exaltation, assemble-condition, and offices must consume
the horizon boolean. They must not re-derive sect from Whole Sign house numbers.

## Covenant

`profile.is_day_chart` == each planet `sect_truth.is_day_chart` == Sun
above-horizon from the same frame.
