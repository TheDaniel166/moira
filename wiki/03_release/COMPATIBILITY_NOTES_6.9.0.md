# Compatibility Notes - Moira 6.9.0

## Upgrade Boundary

Moira 6.9.0 is a feature release from 6.8.2. Existing planetary, chart, house,
and predictive entry points remain available, but two previously permissive or
misnamed contracts have intentionally changed so their public meaning matches
the governing convention.

## Eclipse Saros Fields

- `EclipseData.saros_index` and the REST `saros_index` field now contain the
  conventional van den Bergh/NASA Saros-series number as `int | None`.
- `saros_series` is the preferred explicit name for the same value.
- `saros_lunation_number` contains the signed NASA/GSFC `Luna Num` used for
  assignment.
- `saros_cycle_position` preserves the former floating mean-month phase within
  a 223-month cycle.
- Non-eclipse snapshots return `None` for the catalog designation fields.

Consumers that previously displayed `saros_index` as a continuous value must
switch to `saros_cycle_position`. Consumers labeling it as a Saros series may
continue using `saros_index`, but should migrate to `saros_series` for clarity.

## Jones Chart-Shape Inputs

Jones chart-shape classification now accepts exactly the canonical ten bodies
from Sun through Pluto. Nodes and custom planet sets are not silently folded
into a Jones classification. The REST route returns HTTP 422 for those inputs.

This can change classifications near shape boundaries because Bucket,
Locomotive, Seesaw, Splay, and Splash now apply the rules and orbs documented
from Marc Edmund Jones's primary text.

## Lunar Orientation Resources

The new lunar-orientation API fails closed unless its pinned orientation
resources are installed and match the published size and SHA-256 identities:

- `moon_pa_de440_200625.bpc`
- `moon_de440_250416.tf`

Install them with:

```text
moira-download-kernels --lunar-orientation
```

The requested epoch must also be covered by the orientation PCK and the
applicable DE441/LE441 translation kernels.

## New Additive Surfaces

The aspect-pattern coherence, house-dynamics, polar-admissibility, expanded
primary-directions, and lunar-orientation Python and REST surfaces are
additive. Applications may adopt them independently.

## Recommended Migration Sequence

```text
pip install --upgrade moira-astro==6.9.0
```

For services running `moira_server`:

```text
pip install --upgrade "moira-astro[server]==6.9.0"
```

Restart long-running engine and API processes after upgrading so the new
native extension and transport schemas are loaded together.
