# Astrodynes SCP Phase 1 Truth Preservation (2026-07-12)

Status: complete for the bounded natal computational core

Follow-up: the bounded natal subsystem subsequently completed SCP Phases 2-12.
The frozen architecture and validation doctrine are recorded in
`wiki/02_standards/ASTRODYNES_BACKEND_STANDARD.md`.

## 1. Constitutional Boundary

This increment implements Phase 1 (truth preservation) of the Moira Subsystem
Constitutional Process for Church of Light natal Astrodynes.

It admits:
- the source-owned natal computational core
- immutable source-table rows
- result vessels that preserve inputs, intermediate derivation, and output

It does not admit:
- Phase 2 classification
- Phase 3 inspectability helpers
- Phase 4 doctrine alternatives or policy knobs
- Phase 5-6 mutual-reception relation vessels
- Phase 7 integrated planetary conditions
- Phase 8 sign, house, or chart-wide aggregates
- Phase 9 network intelligence
- Phase 10-11 constitutional freeze
- Phase 12 package-root, facade, or REST exposure

## 2. Governing Sources

Primary computational authority:
- Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946)

Direct table authority:
- Church of Light, *Astrological Delineation with Astrodynes: Class 1 -
  The Planets*, page 3, `Table of Essential Dignities`

The embedded page-3 table was rendered directly on 2026-07-12 and checked
against a clearer image of the same table supplied in-thread. The inspection
resolved the earlier Mercury/Virgo transcription error and corrected additional
Venus, Jupiter, and Neptune entries.

This is a distinct Hermetic dignity doctrine. It must not delegate to or alter
the conventional Western tables in `moira.dignities`.

## 3. Confirmed Essential-Dignity Table

| Planet | Home | Detriment | Exaltation | Degree | Fall | Degree | Harmony | Inharmony |
|---|---|---|---|---:|---|---:|---|---|
| Sun | Leo | Aquarius | Aries | 19 | Libra | 19 | Sagittarius | Gemini |
| Moon | Cancer | Capricorn | Taurus | 3 | Scorpio | 3 | Pisces | Virgo |
| Mercury | Gemini, Virgo | Sagittarius, Pisces | Aquarius | 15 | Leo | 15 | Scorpio | Taurus |
| Venus | Taurus, Libra | Aries, Scorpio | Pisces | 27 | Virgo | 27 | Aquarius | Leo |
| Mars | Aries, Scorpio | Taurus, Libra | Capricorn | 28 | Cancer | 28 | Leo | Aquarius |
| Jupiter | Sagittarius, Pisces | Gemini, Virgo | Cancer | 15 | Capricorn | 15 | Taurus | Scorpio |
| Saturn | Capricorn, Aquarius | Cancer, Leo | Libra | 21 | Aries | 21 | Virgo | Pisces |
| Uranus | Aquarius | Leo | Gemini | 7 | Sagittarius | 7 | Libra | Aries |
| Neptune | Pisces | Virgo | Sagittarius | 18 | Gemini | 18 | Cancer | Capricorn |
| Pluto | Scorpio | Taurus | Leo | 17 | Aquarius | 17 | Aries | Libra |

Scoring preserved from the manual:
- degree of exaltation `+4`
- exaltation `+3`
- home `+2`
- harmony `+1`
- degree of fall `-4`
- fall `-3`
- detriment `-2`
- inharmony `-1`

The degree tier applies within one degree of the tabulated degree, inclusive.
This rule is explicit in the source but still lacks an independent worked
numeric example; Phase 1 therefore preserves both its derivation and that
validation limitation.

## 4. Implemented Core

`moira.astrodynes` now owns:
- all ten dignity rows
- all twelve house-position power rows
- all nine zodiacal aspect-orb rows
- the fixed one-degree parallel orb
- the fixed M.C./Asc. house-position power of 15.00
- house-position interpolation truth
- zodiacal aspect admission and scoring truth
- Mercury's ordinary presence orb plus Sun-Moon scoring orb
- magnitude-parallel truth using absolute declination magnitudes, including
  opposite-hemisphere inputs
- essential-dignity match and contribution truth
- aspect-family and planetary-nature harmony/discord truth

No kernel, ephemeris, native extension, external dependency, or conventional
dignity engine is used by this core.

## 5. Validation Evidence

`tests/unit/test_astrodynes.py` pins the source tables row-for-row and reproduces:
- Venus in the twelfth house: `8.72` astrodynes after source rounding
- Sun-Jupiter trine: `3.82`
- Mars-Mercury sextile: `3.62`
- Mercury-Saturn opposition: ordinary presence orb `12`, scoring orb `15`,
  result `3.18`
- Sun-Saturn magnitude parallel: `7.60`
- Mercury-Venus magnitude parallel: `0.25`
- Uranus-Jupiter magnitude parallel: `6.00`

The tests also prove that Mercury in Aquarius receives the Church of Light
exaltation contribution and Mercury in Virgo receives home, not exaltation.

## 6. Remaining Validation Boundary

Phase 1 does not claim full-chart parity. The three captured Church of Light
charts remain later end-to-end targets because their exact house cusps and
aspect grids are not fully captured. The manual's discrete worked examples are
the authority exercised by this increment.
