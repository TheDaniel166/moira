# Church of Light Progression Geometry

Status: implemented chart-backed adapter with primary-source worked-example
validation and modern JPL-kernel corroboration

Date: 2026-07-12

## 1. Governing Product

`moira.progressed_astrodynes_chart` derives the astronomical geometry required
by the fixed doctrine in `moira.progressed_astrodynes`. It is a separate,
kernel-backed product. It does not treat similarly named generic progression
functions as proof of Church of Light semantics.

The adapter accepts a timezone-aware natal datetime, target datetime, observer
latitude/longitude, house system, and explicit fallback policy. Its result
retains time-key derivation, house-system truth, four terminal tiers, and the
complete progressed Astrodyne calculation.

## 2. Primary Sources

The source-derived time and angle rules were checked against the Church of
Light Serial Lessons:

- [The Hermetic System of Progressions](https://www.light.org/HermeticSystemofProgressions-SL019.cfm)
- [Major Progressions of Sun and Angles](https://www.light.org/Major-Progression-Sun-andAngles-SL111.cfm)
- [Minor Progressions of Sun and Angles](https://www.light.org/Minor-Progressions-Sun-andAngles-SL114.cfm)
- [Minor Progressions of Moon and Planets](https://www.light.org/Minor-Progressions-of-Moon-and-Planets-SL115.cfm)
- Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946), local
  source `C:\Users\nilad\Downloads\Astrodyne-Manual.pdf`

These sources govern the astrological time keys. JPL DE441 governs modern
planetary-position computation; it is corroboration for the historical worked
positions, not the authority for the progression doctrine.

## 3. Declared Derivation

### 3.1 Limiting Date

The interval between Greenwich noon and the natal EGMT is converted with:

- two birth-time hours to one symbolic month
- four birth-time minutes to one symbolic day
- 30-day symbolic months

The signed interval is applied oppositely to the birth date. The result is an
explicit `ChurchOfLightSymbolicDate`; it is not collapsed into an ordinary
Gregorian date before major progression arithmetic.

### 3.2 Major Ephemeris Date

One completed life year advances one ephemeris day from the Limiting Date.
Within the current life year, one calendar month advances two ephemeris hours
and one calendar day advances four ephemeris minutes. The adapter records both
the calendar offset and resulting EGMT interval.

### 3.3 Minor Ephemeris Date

The Solar Constant is the natal Sun minus natal Moon longitude. At the target
date, the transit Sun minus this constant defines the required minor Moon
longitude. The approximate date advances 27.3 ephemeris days per life year;
the admitted root solve then finds the nearby ephemeris instant where the Moon
reaches the required longitude. The selected root and target longitude are
both retained.

### 3.4 Angles and Terminal Frame

The Midheaven Constant is the natal M.C.-Sun relationship. The major progressed
M.C. is therefore the natal M.C. plus the major solar arc. The progressed
Ascendant is reconstructed from that M.C., the natal latitude, obliquity, and
the selected house method. Radical, major, minor, and transit terminals are all
assigned to the natal house figure for practical distribution.

Planetary longitudes and declinations use Moira's geocentric apparent
planetary path. Requested and effective house systems and any explicitly
permitted fallback remain visible.

## 4. Worked-Example Validation

The Benjamine example uses:

- natal EGMT: 1882-12-12 12:11:26 UTC
- target: 1949-08-29 12:00:00 UTC
- latitude: 41 degrees 37 minutes north
- longitude: 94 degrees west

Pinned witnesses:

| Product | Printed witness | Modern reconstruction | Tolerance |
|---|---:|---:|---:|
| Limiting Date | 1882-12-09 plus 3h24m | 1882-12-09.141666... | exact symbolic arithmetic |
| Major ephemeris date | 1883-02-17 near -6h42 EGMT | 1883-02-17 near -6h40.6 | source rounding boundary |
| Major Sun | 328.25 deg | 328.24584 deg | 0.02 deg |
| Minor ephemeris date | 1887-12-09 | 1887-12-09 | date witness |
| Minor Moon | 178.70 deg | 178.69752 deg | 0.02 deg |
| Minor Mercury | 236.58333 deg | 236.58277 deg | 0.02 deg |
| Minor Neptune | 58.16667 deg | 58.17392 deg | 0.02 deg |
| Transit Neptune | 193.51667 deg | 193.50936 deg | 0.02 deg |

This is a named, bounded comparison. It does not claim that a modern kernel and
modern house implementation reproduce every printed historical chart value.
The source manual's internally inconsistent dated rows and aggregate statements
remain recorded in
`progressed_astrodynes_manual_discrepancies_2026-07-12.md`; those publication
errors are not Moira compatibility targets.

## 5. Public Surfaces

- `church_of_light_progression_geometry(...)`
- `church_of_light_progressed_astrodynes_chart(...)`
- `Moira.progressed_astrodynes_geometry(...)`
- `Moira.progressed_astrodynes_chart(...)`
- `POST /v1/astrodynes/progressed/chart`

The REST response exposes full geometry, natal result, normal progressed
horoscope, major/minor/transit relations, reenforcements, practical totals, and
provenance. Scalar and explicit-geometry routes remain kernel-free.

## 6. Search and Variable-Rate Extension

`moira.progressed_astrodynes_search` now admits the deferred bounded products:

- one-degree entry and exit chronology
- exact perfection or explicitly named closest approach
- minor reenforcement peaks against a named major relation
- composite-trapezoid integration of actual ephemeris-varying instantaneous
  power, harmony, and discord

The source governs the one-degree threshold and instantaneous power curve.
Numerical bracketing, minimization, and quadrature are labeled as Moira methods.
Every result exposes its numerical policy and keeps the manual's conditional
constant-rate total as a comparator.

Arbitrary prediction/advice, unbounded sweeps, and hidden automatic aspect
discovery remain outside this product.
