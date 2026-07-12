# Progressed Astrodynes Manual Discrepancy Ledger

Status: primary-source publication discrepancies isolated from executable
Church of Light doctrine

Date inspected: 2026-07-12

## Authority and Method

The governing source is Elbert Benjamine and W. M. A. Drake, *The Astrodyne
Manual* (1946), printed pages 42-46, PDF pages 45-49 of the locally inspected
scan. Each entry below was checked against a rendered page. These are not OCR
transcription errors.

Moira implements the manual's declared formulas, aspect-polarity rules, planet
nature terms, and commercial half-up staging. A contradictory printed value is
preserved as publication evidence but is not substituted into the executable
calculation.

## Dated Relation Rows

| Relation | Published | Formula-derived | Evidence |
|---|---:|---:|---|
| Saturn inconjunct Sun r | 11.13 power | 11.14 power | `14.37 - round(14.37 * 27 / 120, 2) = 11.14` |
| Sun square Pluto r | 18.72 power, 15.72 discord | 18.73 power and discord | `25.83 - round(25.83 * 33 / 120, 2) = 18.73`; neither planet has a stated nature modifier |
| M.C. parallel Moon r | 19.94 power | 19.91 power | `34.62 - round(34.62 * 51 / 120, 2) = 19.91` |
| Mercury sesqui-square Uranus p | 13.58 power and discord | 13.59 power and discord | `20.13 - round(20.13 * 39 / 120, 2) = 13.59` |
| Jupiter semi-sextile Saturn r | 4.58 harmony | 4.88 harmony | harmonious base `4.88`; Jupiter `+1/2` and Saturn `-1/2` nature terms cancel |
| Jupiter square Uranus p | +8.87 harmony | 8.87 discord | discordant square offset by Jupiter's half-harmony remains net discord; the downstream house arithmetic treats it as discord |

The complete fixture contains all 27 printed dated rows. Twenty-one reproduce
exactly; the six above are asserted as named source exceptions rather than
being silently tolerated.

## Aggregate Arithmetic

### Seventh-house Jupiter line

The printed contributions are:

`49.52 + 88.82 + 51.12 + 46.51 + 55.71 + 7.32 + 26.61 + 14.15`

They total `339.86`, not the published `339.76`.

### Seventh-house Moon line

The printed contributions are:

`2.43 + 3.66 + 0.75 + 2.88 + 5.48 + 9.75 + 7.68 + 3.26 + 13.00 + 7.93`

They total `56.82`, not the published `61.87`. Several terms also disagree
with one-half of their corresponding dated relation rows, so the difference
cannot be resolved as a single rounding-stage choice.

### Ninth-house Sun line

The six printed dated powers are:

`15.96 + 33.01 + 59.21 + 11.13 + 18.72 + 25.83`

They total `163.86`, not `163.88`; half is `81.93`, not the published `81.94`.
Separately, one sentence prints the normal baseline as `51.32`, while the
established normal value and the stated final `133.76` total require `51.82`.

## Validation Policy

Moira reports two distinct evidence products:

1. **Doctrinal result** - calculated from the source's stated formulas and
   staged half-up arithmetic.
2. **Published witness** - the exact printed row or aggregate, retained with a
   discrepancy explanation and delta.

Doctrinal parity means the first product is reproduced throughout the engine.
Publication transcription parity means the second product is preserved
exactly. It does not mean publication errors are made executable.

Tracked fixtures:

- `tests/fixtures/progressed_astrodynes_benjamine_dated_1949.json`
- `tests/fixtures/progressed_astrodynes_benjamine_normal_1949.json`
- `tests/fixtures/progressed_astrodynes_church_of_light.json`

