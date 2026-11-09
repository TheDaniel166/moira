# Release Notes - Moira 6.13.0

**Release date:** 9 November 2026.

This minor release follows published 6.12.1. It adds five house systems, grades
nearly every aspect pattern, gives patterns adjustable orbs and names generated
harmonic layouts. It also corrects the Zariel house system; read the
[compatibility notes](COMPATIBILITY_NOTES_6.13.0.md) before upgrading. The full
itemised record is in the changelog.

## House systems

Alova-Topocentric (`AT`), Makransky Sunshine (`MS`), Sripati (`SP`), Savard-A
(`SA`) and Porphyry with a 5-degree prespan (`P5`) bring the registry to 27.

Zariel now starts house 1 at RAMC + 90 degrees in right ascension, as its 1935
description places it. Its cusps were previously anchored at the Ascendant's
right ascension, which is the construction Carter uses.

## Pattern grading

Coherence policy `moira.pattern_coherence.qualitative.v2-draft` grades 36 of the
37 named patterns, up from six, along with every generated harmonic layout.
Required links are mapped per pattern and tested against each detector. The
reference table now holds the catalog default orb of every aspect except
Conjunction. Bands, aggregation, motion qualifiers and the six original
templates are unchanged, so an existing grade does not move. Stelliums and
caller-supplied templates remain not assessed.

## Adjustable pattern orbs

Pattern detection now has a default and three adjustments. The most specific
setting wins:

1. `pattern_orbs` sets one exact limit for every aspect in a pattern, and a
   Stellium's spread.
2. `orbs` sets an exact limit for an aspect in every pattern. As with regular
   aspects, passing it ignores `orb_factor`.
3. `orb_factor` scales every default.

Default limits are unchanged. The aspect search widens to reach an explicit
limit, and each result reports the limits it used in
`detection_truth.applied_orbs`. Grades keep their fixed references, so a link
admitted past its reference grades Marginal. `pattern_default_orbs()` and
`GET /v1/patterns/default-orbs` publish the defaults, and the coherence surface
is now exported through `moira` and `moira.facade`.

## Harmonic layout names

Generated layouts are named after the catalog aspect that is 1/H of the circle,
such as `Novile Triangle 1-2-3`, and rectangles count their sides on the grid.
H13, H32, H36 and H40 keep their number. The 21 layouts that match a registered
pattern take its name and apex.

## Native planetary routing

Planetary queries refuse a warmed cache whose reader or kernel pool has closed.
Longitude-rate samples use the canonical reader when native planning detects an
SPK segment change, and emission epochs apply the reader's coverage and overlap
priority.
