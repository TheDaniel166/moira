# Compatibility Notes - Moira 5.2.2

Date: 2026-07-25

Moira 5.2.2 preserves the public result vessels and existing positional call
forms, but it intentionally changes several lunar-point longitudes and
asteroid-family memberships to repair hidden frame and catalog semantics.
Consumers that freeze exact node values or assume one exclusive asteroid
family should review the changes below.

## True-node longitude correction

`true_node(jd_ut, reader=None)` retains its signature and `NodeData` result.
Its longitude now comes from a common-frame osculating-plane/ecliptic-plane
intersection.

The numerical correction depends on epoch and grows away from J2000 in the
previous implementation. Representative defects repaired by this release
include approximately +39.3 arcseconds in 1967, -29.2 arcseconds in 2026, and
+139 arcseconds in the shipped 1625 comparison case.

Applications with saved true-node charts, exact aspect boundaries, transit
times, or draconic charts should regenerate affected results.

## Mean-node and Mean-Lilith default frame

The signatures are now:

```python
mean_node(jd_ut, *, nutation=True)
mean_lilith(jd_ut, *, nutation=True)
```

The default `True` value expresses the analytical mean orbital point in the
true ecliptic and equinox of date, matching the rest of a default Moira chart.
This shifts prior default longitudes by nutation in longitude, generally by a
few arcseconds and up to roughly 19 arcseconds over the tested historical and
modern interval.

Use `nutation=False` when a raw mean-equinox-of-date analytical longitude is
required. The mean-node polynomial itself is now the IERS 2003 expression, so
`nutation=False` is the correct frame-compatible replacement but is not a
promise of bit-for-bit reproduction of the older duplicated coefficients.

`NodeData.speed` for the mean node is the derivative of the governing IERS
mean argument. It deliberately excludes the short-period derivative of
nutation even when the longitude is returned in the true frame.

## Chart reduction response

Each entry in `reduction.node_reductions` now includes:

- `nutation: true`
- `frame: "true_ecliptic_and_equinox_of_date"`

Mean-node and mean-Lilith stage sequences also include the IAU 2000A nutation
conversion. Strict response consumers must admit these two additive fields.

## Asteroid-family catalog behavior

The family catalog is now a many-to-many Proper25/PDS product. Consumers must
not interpret `family` as exclusive physical membership.

- Use the complete `families` collection when grouping or constructing
  resonance networks.
- Treat the display-primary `family` value as a deterministic compatibility
  selection only.
- Expect memberships, family sizes, and aliases to differ from the earlier
  legacy catalog.
- A null or absent family remains meaningful: it means the numbered asteroid
  is absent from the admitted Proper25/PDS catalogs, not that the asteroid has
  been proven to have no family.

The aliases `Koronis(2)`, `RJ`, and `UV209` resolve to the normalized family
identifiers without duplicating membership rows.

## Upgrade action

Pin and install:

```text
moira-astro==5.2.2
```

Restart every process that imports Moira, regenerate cached charts containing
lunar nodes or Mean Lilith, and refresh any derived asteroid-family grouping
or resonance artifacts.
