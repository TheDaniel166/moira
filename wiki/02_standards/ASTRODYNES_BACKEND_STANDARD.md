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
| 8 | Sign, house, and checksum aggregates |
| 9 | Relation network nodes and edges |
| 10 | Deterministic ordering, validation, failure behavior, cross-layer invariants |
| 11 | This standard and validation codex |
| 12 | Curated module, package-root, and `Moira` facade surface |

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

Society, trinity, element, and quality summary columns are not admitted because
their exact source assembly rules have not yet been captured. They must not be
reconstructed from labels or output totals.

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

Exact internal arithmetic is compared with `pytest.approx`; the published
manual values are additionally checked after rounding to hundredths. Source
tables are pinned row-for-row. Structural evidence covers policy rejection,
relation subsets, deterministic ordering, sign/house checksums, profile/network
agreement, and public-export identity.

No external numerical engine is used. No full-chart Church of Light parity is
claimed. The degree-emphasis tier is implemented from an explicit source rule
but has no independent worked-example hit.

## 11. Public Surface

The complete stable module surface is the `__all__` contract of
`moira.astrodynes`. A smaller high-level subset is re-exported through `moira`
and `moira.facade`. The `Moira` facade provides `astrodynes(...)`, a kernel-free
delegate to `natal_astrodynes(...)`.

Private normalization, relation assembly, ruler lookup, aggregate assembly, and
network construction helpers are not public.

REST is not admitted by this standard. Transport requires a separate evaluation
of request geometry, payload size, serialization, and website product needs.

## 12. Remaining Scope

Deferred without approximation:
- progressed Astrodynes
- complete full-chart parity against Church of Light output
- society, trinity, element, and quality rollups
- any doctrine alternative not present in the confirmed sources
