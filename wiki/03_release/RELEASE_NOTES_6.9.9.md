# Moira 6.9.9 - Standard Defaults and Source Corrections

Release date: 2026-09-29. Upgrade path: 6.9.8 to 6.9.9.

Moira 6.9.9 repairs defects found by running consumer tools against 6.9.8:
three pattern routes that failed on every call, a composite default that
rejected every existing caller, and several routes that returned a confident
answer where the engine had not judged anything. It also makes each named
doctrine follow its own source by default, adopts the standard heliacal
phase names, and adds the almuten, hyleg, alcocoden and predominator
procedures of Lilly and Ptolemy.

## Key Changes

### Routes That Failed

- `/v1/patterns/coherence`, `/v1/patterns/chart-profile` and
  `/v1/patterns/network` work again (HTTP 500 in 6.9.8).
- A composite request without `reference_latitude` works again: the houses
  are cast at the mean latitude of the two birthplaces.
- Lunar-mansion requests with only a longitude work again (default tradition
  `agrippa`).
- Release Hardening now rejects undefined names, the class of error behind
  the pattern-route failures.

### Standard Defaults

- Lilly-named dignity scoring uses Lilly's own triplicity table and terms
  (Christian Astrology 1647, I ch. XVIII, p. 104); Lilly's perfection
  reception does too.
- Planetary years follow Lilly's printed table.
- Nine parts computes the seven Hermetic lots of Paulus by default; Necessity
  and Eros follow Paulus ch. 23.
- Synastry, composite and Davison aspects default to the five major aspects.
- The harmonic conjunction orb defaults to 12 degrees on the harmonic wheel
  (Hamblin).
- Lunar mansions use 28 equal divisions in every tradition, with each
  tradition's own Latin names and Agrippa's significations restored to II.33.

### Heliacal Phases

- The standard Ptolemy/Schoch names: heliacal rising (morning first),
  heliacal setting (evening last), evening first, morning last, acronychal
  rising and cosmical setting, for planets and fixed stars.
- `POST /v1/heliacal/phasis` finds the phases within a window around a date.
- The Moon's old crescent (morning last) under the Yallop criterion, and a
  true first-crescent search.
- Previous solar and lunar eclipse searches.

### Traditional Procedures

- Almuten of a degree and almuten of the figure (Lilly's own rule by
  default), the Lilly hyleg with its dominion step, and the alcocoden, which
  must behold the hyleg.
- Ptolemy's predominator (Tetrabiblos III.10) on `/v1/hellenistic/offices`.

### Honest Answers

- A superior planet's morning apparition that ends at opposition has no
  morning last visibility.
- The dark-sky limiting-magnitude criterion is not applied in daylight.
- Galactic chart positions default to geocentric.
- A draconic chart computed with an observer says it is topocentric.
- Lord of the turn reports placement as not judged when no house is given.
- Gauquelin plus zones are reported only for the five bodies with a
  published effect.
- The Huber intensity curve is opt-in and labelled editorial.
- Unsourced glosses (harmonic keywords, one-word lot meanings,
  lord-of-the-orb house meanings) are no longer emitted.
- Davison, decanate and midpoint requests reject settings they would have
  ignored; the facade almuten no longer skips unresolved rulers.

### Relationship Charts and Unknown Birth Times

- Synastry aspects and contacts, and one-way house overlays into a known
  chart, work when a birth time is unknown; routes that need the unknown
  person's houses say so by name.
- Composite and Davison aspects use one node and one Lilith, as synastry does.

### Solar Condition and Draconic Houses

- `solar_condition_at` follows the dignity scoring: combust within 8°30′
  (Lilly), the Moon evaluated like every other body, only the Sun excluded.
- The draconic route can return the natal cusps and angles rotated by the
  node, with the house system used.

## Compatibility Highlights

Many default results change in this release. Read
[COMPATIBILITY_NOTES_6.9.9.md](COMPATIBILITY_NOTES_6.9.9.md) before
upgrading, especially for:

- dignity scores (Lilly's terms and water triplicity);
- `heliacal_setting`, which now means evening last visibility;
- relationship aspects (send `tier` explicitly to keep minor aspects);
- the harmonic orb, lunar mansion indexes for `al_biruni`, and the nine
  parts.

## Install

```text
pip install --upgrade moira-astro==6.9.9
```

For the optional REST service:

```text
pip install --upgrade "moira-astro[server]==6.9.9"
```
