# Astrodynes Class 5 Summary Source Capture (2026-07-12)

Status: admitted source packet for natal summary aggregation

## 1. Source

Official Church of Light instructional handout:

- *Astrological Delineation with Astrodynes: Class 5 - Summary - Societies,
  Trinities, Elements, & Qualities*
- `https://www.churchoflight.tv/pdf/05-Astrodynes-Summary.pdf`
- 14 pages, inspected directly on 2026-07-12

This handout is an official Church of Light operational source. It extends the
1946 manual's natal sign/house totals into four named summary families without
changing the underlying power or harmony arithmetic.

## 2. Society Groups

Societies sum house aggregates:

| Society | Houses |
|---|---|
| Personal | 12, 1, 2, 3 |
| Companionship | 4, 5, 6, 7 |
| Public | 8, 9, 10, 11 |

## 3. Trinity Groups

Trinities sum house aggregates:

| Trinity | Houses |
|---|---|
| Life | 1, 5, 9 |
| Wealth | 2, 6, 10 |
| Association | 3, 7, 11 |
| Psychism | 4, 8, 12 |

The Padre Pio page title contains a visible `4, 8, & 10` typo, but the body text
on the same page explicitly gives Fourth, Eighth, and Twelfth, consistent with
the complete four-trinity partition and every worked total.

## 4. Element Groups

Elements sum sign aggregates:

| Element | Signs |
|---|---|
| Fire | Aries, Leo, Sagittarius |
| Earth | Taurus, Virgo, Capricorn |
| Air | Gemini, Libra, Aquarius |
| Water | Cancer, Scorpio, Pisces |

## 5. Quality Groups

Qualities sum sign aggregates:

| Quality | Signs |
|---|---|
| Movable | Aries, Cancer, Libra, Capricorn |
| Fixed | Taurus, Leo, Scorpio, Aquarius |
| Mutable | Gemini, Virgo, Sagittarius, Pisces |

`Movable` is the Church of Light label for the cardinal quality and is preserved
as source terminology.

## 6. Output Semantics

Each summary row exposes:

- power: sum of member house or sign power
- percentage: row power divided by the common chart summary total
- harmony: algebraic sum of member net harmony/discord

Within each family, member rows partition the complete twelve houses or signs.
Therefore every family must sum to the same total power, and its percentages
must sum to 100 subject to display rounding.

## 7. Official Trump Oracle

The handout's Donald Trump page publishes:

| Family | Group | Power | % | Harmony |
|---|---|---:|---:|---:|
| Society | Personal | 345.93 | 44.1 | 72.31 |
| Society | Companionship | 145.15 | 18.5 | 20.83 |
| Society | Public | 292.97 | 37.4 | 13.08 |
| Trinity | Life | 233.86 | 29.8 | 41.38 |
| Trinity | Wealth | 106.89 | 13.6 | -10.76 |
| Trinity | Association | 274.09 | 35.0 | 60.52 |
| Trinity | Psychism | 169.21 | 21.6 | 15.09 |
| Element | Fire | 271.94 | 34.7 | 35.95 |
| Element | Earth | 87.97 | 11.2 | -3.77 |
| Element | Air | 264.26 | 33.7 | 54.64 |
| Element | Water | 159.88 | 20.4 | 19.40 |
| Quality | Movable | 226.15 | 28.8 | 56.88 |
| Quality | Fixed | 265.07 | 33.8 | 16.97 |
| Quality | Mutable | 292.83 | 37.3 | 32.37 |

The previously captured Trump house and sign rows reproduce every displayed
percentage and reproduce summary power and harmony within `0.01`. A handful of
cells differ by one hundredth because the handout publishes both its inputs and
outputs only to two decimal places; the hidden pre-display precision is not
recoverable from the PDF. The tests therefore use this as a direct external
operational oracle with an explicit `0.011` absolute display-rounding tolerance.

## 8. Scope Decision

Admitted:

- deterministic society, trinity, element, and quality summaries derived from
  an existing `AstrodyneChartAggregate`
- raw power, separate harmony/discord magnitudes, algebraic net harmony, and
  percentage
- dominant-entry inspection within each family

Still deferred:

- autonomous reconstruction from incomplete place/time labels; the exact
  wheels and grids are now captured and executable, but the reports do not
  publish atlas coordinates and the Trump page contains a contradictory year
- progressed summary calculations
