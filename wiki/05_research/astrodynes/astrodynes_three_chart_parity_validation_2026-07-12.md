# Astrodynes Three-Chart Parity Validation (2026-07-12)

Status: executable external-software parity corpus

## 1. Authority and Product

External operational source:

- Church of Light, *Astrological Delineation with Astrodynes: Class 1 - The
  Planets*
- `https://www.churchoflight.tv/pdf/01-Astrodynes-Planets.pdf`
- report pages 9-11: Donald Trump, Mohandas K. Gandhi, and Barbara Walters

This is cross-engine corroboration against official Church of Light software
output. The Astrodyne Manual remains the primary authority for formulas and
doctrine. The reports govern this validation product: the complete displayed
natal relation, planet, house, sign, and Class 5 summary output.

## 2. Source Recovery

The official PDF was rendered and inspected directly. Its report wheels contain
the planetary longitudes, all twelve house cusps, MC, and Asc to arcminutes.
Its square grids are structured as:

- upper triangle: zodiacal aspects
- lower triangle: parallels
- each populated cell: power and algebraic harmony/discord

This closes the older OCR note that treated the grids and exact wheels as
unavailable. The complete transcription is
`tests/fixtures/astrodynes_church_of_light.json`.

The wheels are Placidus figures. A controlled comparison using the printed MC,
Asc, epoch obliquity, and city latitude reproduced the minor cusps to display
precision. House-system identity is therefore measured rather than inferred
from the shape of the reports.

## 3. Trump Source Defect

The Trump page prints `6/14/1949`, but its wheel is not a 1949 sky. Its Sun,
Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto agree
with `1946-06-14 09:51 EDT` (`13:51 UTC`). A 1949 calculation disagrees
radically, including the Moon and multiple planets.

The fixture preserves both truths:

- `displayed_birth`: the literal 1949 page label
- `ephemeris_epoch_utc`: the 1946 epoch demonstrated by the printed wheel

No engine default silently repairs this source defect.

## 4. Engine Boundary

`natal_astrodynes_from_geometry(...)` converts an explicit tropical chart
figure into the existing constitutional Astrodyne core. It derives:

- planet house membership and house class
- zodiacal house size
- distance from the weaker, closing boundary used by the manual's interpolation
- cusp signs and intercepted signs
- the complete `AstrodyneChartResult`

It does not choose a house system, acquire an ephemeris, infer a time zone, or
replace printed geometry with a birth-label reconstruction.

The parity test uses the printed longitudes and cusps. Because the reports do
not print declinations, it independently derives apparent equatorial
declinations from DE441 at the wheel-demonstrated epoch. This is the only
resource-bound part of the validation.

## 5. Corpus Breadth

The executable corpus pins:

- 125 populated relation-grid cells
- 36 planet/angle rows
- 36 house rows
- 36 sign rows
- 42 society/trinity/element/quality rows
- 3 complete chart totals

All admitted zodiacal and parallel relation identities must match exactly; an
extra or missing relation fails the test.

## 6. Tolerances and Observed Residuals

| Product | Test tolerance | Maximum observed residual |
|---|---:|---:|
| Zodiacal relation power/harmony | 0.026 | 0.02500 |
| Parallel relation power/harmony | 0.050 | 0.04583 |
| Planet/angle power or harmony | 0.080 | 0.06917 power; 0.03899 harmony |
| House power or harmony | 0.120 | 0.09071 power; 0.04589 harmony |
| Sign power or harmony | 0.120 | 0.10770 power; 0.05035 harmony |
| Class 5 summary power or harmony | 0.180 | 0.16743 power; 0.12023 harmony |
| Whole-chart power or harmony | 0.150 | 0.14191 power; 0.09381 harmony |

The zodiacal allowance covers the manual's arcminute-to-two-decimal conversion
table and independently rounded display inputs. The parallel allowance covers
the unprinted Church of Light declinations while still constraining every
published parallel cell through an independent DE441 reduction.

## 7. Claim Boundary

Moira now has full displayed-output parity for these three Church of Light natal
reports within the named tolerances and explicit-geometry semantics.

This does not claim:

- that the literal place/time labels alone reproduce the wheels, because exact
  atlas coordinates and historical time-zone records are not printed
- that the erroneous Trump year should be accepted as astronomical input
- progressed Astrodyne parity
- an independent authority validation of Church of Light software astronomy

