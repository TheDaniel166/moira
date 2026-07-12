# Astrodynes Backend Standard

Status: constitutional through SCP Phase 12 for the bounded natal engine

## 1. Governing Identity

Moira's Astrodynes subsystem implements the Church of Light / Hermetic natal
power and harmony system described by Elbert Benjamine and W. M. A. Drake.

It is not:
- the conventional Western essential-dignity table
- the Garcia harmogram/Fourier subsystem
- a generic planetary-strength score
- progressed Astrodynes

The computational core is `moira.astrodynes`. It is standard-library only,
kernel-free, deterministic, and independent of `moira.dignities`.

## 2. Authority and Provenance

Primary computational authority:
- Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946)

Direct table authority:
- Church of Light, *Astrological Delineation with Astrodynes: Class 1 -
  The Planets*, page 3, `Table of Essential Dignities`
- Church of Light, *Astrological Delineation with Astrodynes: Class 5 -
  Summary - Societies, Trinities, Elements, & Qualities*,
  `https://www.churchoflight.tv/pdf/05-Astrodynes-Summary.pdf`

The dignity table was inspected directly on 2026-07-12. It establishes the
Astrodyne-specific Mercury axis (Aquarius 15 exaltation, Leo 15 fall, Scorpio
harmony, Taurus inharmony) and the corresponding Venus, Jupiter, Neptune, and
outer-planet entries. These values may not be replaced with conventional tables.

## 3. Computational Products

The bounded natal engine computes:
- house-position power for ten planets
- fixed house-position power for M.C. and Asc.
- zodiacal aspect admission and power
- declination-magnitude parallel admission and power
- essential-dignity harmony/discord
- benefic/malefic aspect modifiers
- home-or-exaltation mutual reception
- integrated planet/angle condition profiles
- sign and house power/harmony rollups
- society, trinity, element, and quality summaries
- explicit-chart-geometry normalization into the natal core
- an admitted-relation network

Inputs are explicit precomputed chart geometry. The subsystem does not acquire
ephemerides, calculate houses, infer house interpolation distances, or perform
I/O.

## 4. Fixed Doctrine

`AstrodynePolicy` exposes one admitted source doctrine and rejects unsupported
alternatives:
- degree-emphasis band: one degree, inclusive
- parallel orb: 60 arcminutes
- parallel geometry: absolute declination-magnitude difference
- Mercury: ordinary planet orb for presence, Sun-Moon orb for scoring
- mutual-reception bonus: 5 harmodynes to each planet

This policy vessel makes doctrine visible; it is not permission to invent
variants.

## 5. Constitutional Layers

| Phase | Admitted surface |
|---:|---|
| 1 | Source rows and full computational derivation truth |
| 2 | Body, dignity, aspect, relation, and contribution classifications |
| 3 | Orb margins, rounded manual values, condition polarity, contribution queries |
| 4 | Fixed `AstrodynePolicy` |
| 5 | Zodiacal, parallel, and mutual-reception relation vessels |
| 6 | Detected, admitted, and scored relation subsets |
| 7 | `AstrodyneBodyConditionProfile` |
| 8 | Sign, house, checksum, and Class 5 summary aggregates |
| 9 | Relation network nodes and edges |
| 10 | Deterministic ordering, validation, failure behavior, cross-layer invariants |
| 11 | This standard and validation codex |
| 12 | Curated module, package-root, `Moira` facade, and typed REST surface |

## 6. Result Semantics

Power is non-negative and measured in astrodynes.

Harmony and discord are stored separately as non-negative magnitudes. Net
harmony is always:

```text
total_harmony - total_discord
```

Positive net values are harmodynes; negative net values represent discordynes.
No formatting label replaces the preserved magnitudes.

Each integrated profile preserves named contributions from:
- house position
- zodiacal aspects
- parallels
- essential dignity
- mutual reception

## 7. Relation Doctrine

Zodiacal relations retain the closest named aspect candidate for each body pair.
Parallel candidates exist when both declinations are supplied. Mutual-reception
candidates exist for planet pairs.

The relation subsets mean:
- `detected`: geometrically or doctrinally evaluated candidate
- `admitted`: candidate satisfies the source orb or reception rule
- `scored`: admitted candidate contributes nonzero power or harmony

Integrated profiles consume only scored relations. Networks expose admitted
relations and retain whether each edge is scored.

## 8. Aggregate Doctrine

The ruler of an unoccupied sign contributes:
- one half of average ruler power for each cusp carrying that sign
- one quarter of average ruler power when intercepted

Co-rulers are averaged before the fraction is applied. Occupant profiles are
then added. The same ruler and occupant construction is used for houses.

Rulers are derived only from the confirmed Astrodyne home-sign table. This gives
co-rulership to Scorpio (Mars/Pluto), Aquarius (Saturn/Uranus), and Pisces
(Jupiter/Neptune).

The admitted checksum is:

```text
sum(sign totals) == sum(house totals)
sum(sign net harmony) == sum(house net harmony)
```

Class 5 summaries are deterministic partitions of the existing aggregates:

- societies: Personal (12, 1, 2, 3), Companionship (4, 5, 6, 7), Public
  (8, 9, 10, 11)
- trinities: Life (1, 5, 9), Wealth (2, 6, 10), Association (3, 7, 11),
  Psychism (4, 8, 12)
- elements: Fire, Earth, Air, and Water use their three zodiac signs
- qualities: Movable, Fixed, and Mutable use their four zodiac signs

Each family independently partitions the chart's total power and net harmony.
`Movable` is preserved as the source label. The detailed source capture is
`wiki/05_research/astrodynes/astrodynes_class5_summary_source_capture_2026-07-12.md`.

## 9. Failure and Determinism Doctrine

The engine rejects:
- missing or duplicate bodies in a full natal result
- unsupported bodies, signs, aspects, or house classes
- house classes inconsistent with house number
- non-finite geometry
- invalid house interpolation distances
- unsourced policy values
- duplicate or inconsistently ordered relations
- cross-layer aggregate or network disagreement
- incomplete or disordered explicit cusp figures
- explicit MC/Asc values that disagree with the tenth/first cusps
- sign allocations requiring more than two house cusps in one sign, which lie
  outside the bounded aggregate doctrine currently validated

Full chart input requires ten planets plus M.C. and Asc. Canonical body order is
the ten-planet source-table order followed by M.C. and Asc. Relations, profiles,
signs, houses, network nodes, and edges are deterministic regardless of caller
input ordering.

## 10. Validation Codex

Primary evidence class: authority validation against discrete manual examples.

The focused corpus reproduces:
- Venus twelfth-house position power: `8.72`
- Sun-Jupiter trine: `3.82`
- Mars-Mercury sextile: `3.62`
- Mercury-Saturn opposition: `3.18`
- Sun-Saturn magnitude parallel: `7.60`
- Mercury-Venus magnitude parallel: `0.25`
- Uranus-Jupiter magnitude parallel: `6.00`
- sign power rollups: `77.74`, `41.24`, `94.82`
- house power rollups: `41.26`, `82.50`
- sign harmony/discord rollups: `4.18`, `13.26`
- all fourteen published Donald Trump Class 5 summary rows
- all 125 populated relation cells and every displayed planet, house, sign,
  summary, and chart-total row across the Trump, Gandhi, and Walters reports

Exact internal arithmetic is compared with `pytest.approx`; the published
manual values are additionally checked after rounding to hundredths. The Class
5 oracle uses `0.011` absolute tolerance because its displayed inputs and
outputs are independently rounded to hundredths. Source tables and summary
memberships are pinned row-for-row. Structural evidence covers policy rejection,
relation subsets, deterministic ordering, sign/house checksums, profile/network
agreement, summary-family partitions, and public-export identity.

The three-chart integration corpus uses DE441 only to supply the declinations
omitted from the reports. It demonstrates full displayed-output parity for the
three official Church of Light natal reports under explicit-geometry semantics
and the named tolerances in
`wiki/05_research/astrodynes/astrodynes_three_chart_parity_validation_2026-07-12.md`.
This is external-software corroboration, not a replacement for the manual's
primary formula authority. The degree-emphasis tier is implemented from an
explicit source rule but has no independent worked-example hit.

## 11. Public Surface

The complete stable module surface is the `__all__` contract of
`moira.astrodynes`. A smaller high-level subset is re-exported through `moira`
and `moira.facade`. The `Moira` facade provides `astrodynes(...)`, a kernel-free
delegate to `natal_astrodynes(...)`.

`natal_astrodynes_from_geometry(...)` and the corresponding facade method
derive body inputs, cusp signs, and interceptions from a complete explicit
tropical chart figure. They do not acquire ephemerides or choose houses.

Private normalization, relation assembly, ruler lookup, aggregate assembly, and
network construction helpers are not public.

The optional FastAPI transport admits three routes under `/v1/astrodynes`:

- `GET /doctrine` exposes the fixed policy and source tables without requiring
  an ephemeris kernel.
- `POST /geometry` accepts a complete tropical figure and remains kernel-free.
- `POST /chart` derives geocentric apparent planetary longitudes and
  declinations from a kernel-backed chart, while using the supplied location
  only for the house figure.

The chart route defaults to strict house semantics. A caller may explicitly set
`allow_house_fallback=true`; the response then preserves requested and effective
systems, the fallback flag, and its reason. It never silently makes the Moon
topocentric. Both calculation routes return normalized geometry, fixed policy,
all detected relations with admitted/scored flags and derivation truth, body
profiles, aggregates, Class 5 summaries, network, invariant failures, and
computational provenance. Chart-backed responses also preserve the requested
datetime/location, Julian date, and true obliquity used for declination
conversion. Transport models, orchestration, and serialization
remain under `moira_server`; doctrine remains in `moira.astrodynes`.

## 12. Remaining Scope

Deferred without approximation:
- progressed Astrodynes
- autonomous place/time-label reconstruction where the report omits exact
  atlas coordinates or contains contradictory source data
- any doctrine alternative not present in the confirmed sources
