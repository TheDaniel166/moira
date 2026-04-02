# Primary Directions: Field-Plane Decomposition

## Purpose

This note states, explicitly, how far Moira's currently admitted retained-
latitude zodiacal branch reaches toward what other software sometimes labels
`field_plane`, and where it still stops.

It exists to prevent the projected zodiacal branch from being misnamed as full
field-plane doctrine before the missing policy layers are admitted.

## Current Moira Branches

Moira currently admits two zodiacal branches:

1. `in_zodiaco` + `zodiacal_suppressed` + `assigned_zero`
   This is pure zodiacal-longitude perfection with latitude suppressed.

2. `in_zodiaco` + `zodiacal_promissor_retained` + `promissor_native`
   This is a retained-latitude zodiacal projection branch. The promissor keeps
   its own latitude, is projected through the existing ecliptic-to-equatorial
   path, and perfects through projected right ascension.

3. `in_zodiaco` + `zodiacal_promissor_retained` + `aspect_inherited`
   This is the first non-native latitude-bearing zodiacal aspect branch.
   Aspectual promissor points inherit the source body's latitude rather than
   being flattened to zero or pretending to own an independent native latitude.
   They are then projected through the same equatorial path and perfected by
   projected right ascension.

4. `in_zodiaco` + `zodiacal_significator_conditioned` + `significator_native`
   This is a pair-specific latitude-bearing zodiacal branch. The promissor or
   aspect-point is projected using the significator's latitude, so the
   projected point depends on the relation being tested rather than on the
   promissor alone.

## What The Projected Branch Does Cover

The retained-latitude zodiacal branches already cover a real part of the
broader field-plane idea:

- zodiacal orientation is preserved
- latitude is not flattened to zero
- the promissor remains a latitude-bearing point rather than a bare ecliptic
  longitude
- aspectual points may inherit latitude from the source body rather than being
  forced to zero latitude
- projected zodiacal points may now also be conditioned by the significator's
  latitude on a pair-specific branch

So, at minimum, this branch covers the following doctrinal statement:

> a zodiacal direction may retain latitude instead of reducing every promissor
> to zero-latitude longitude alone, including by allowing an aspectual point to
> inherit latitude from its source body.

That means the branch is not merely cosmetic. It already spans a genuine portion
of the space that some software appears to place under `field_plane`.

## What It Does Not Yet Cover

The projected branch is still narrower than the full unresolved field-plane
family. It does **not** yet define:

1. `significator_conditioned` latitude
   A first explicit branch now exists in which the significator's latitude
   conditions the projected promissor point. But the broader historical scope
   and interpretive standing of that law still remain unsettled.

2. distinct projected plane law
   The current branch projects the latitude-bearing zodiacal point through the
   normal coordinate pipeline and perfects by projected RA. It does not yet
   declare a separate geometric "plane" doctrine beyond that.

3. aspect-specific field rules
   There is no policy yet for whether conjunction, sextile, square, trine, and
   opposition acquire or preserve latitude differently.

4. explicit field ownership
   The current branch still belongs to `in_zodiaco`. It is not yet a separate
   direction-space family.

## Interim Constitutional Judgment

The retained-latitude zodiacal branch is best understood as:

- a **partial overlap** with what other software may call `field_plane`
- not yet enough to collapse `field_plane` into `in_zodiaco`
- not yet enough to expose `field_plane` as a stable runtime label

So the correct current statement is:

> Moira now covers more of the latitude-bearing zodiacal layer that likely
> belongs inside the wider field-plane problem, including aspect-inherited and
> significator-conditioned latitude for explicit zodiacal branches. But it does
> not yet claim that this exhausts field-plane doctrine.

## Practical Engineering Boundary

Until one or more additional policy axes are admitted, `field_plane` should
remain unresolved at runtime.

The next candidate axes are:

1. explicit projected-plane relation law
2. aspect-specific field rules
3. field ownership beyond `in_zodiaco`

Only after those exist can Moira decide whether:

- `field_plane` is just a family of retained-latitude zodiacal branches
- or whether it is a genuinely separate direction-space doctrine

## External Context

The current external landscape is suggestive but not sharp enough to justify a
single black-box `field_plane` implementation:

- AstroApp distinguishes `In Zodiaco`, `In Mundo`, and `Field Plane`, which
  confirms the label is real.
- Kolev's discussion indicates historical practice involving zodiacal aspects
  with latitude.
- Moira now admits explicit zodiacal aspect-point promissors with
  `aspect_inherited` latitude, which closes part of that gap without requiring
  a separate `field_plane` space label.
- But those sources do not yet provide one clean, uniform computational law
  that Moira can admit as the whole family.

Therefore the light-box position remains:

- admit what is explicit
- separate what is still ambiguous
- do not hide unresolved doctrine under a familiar software label

