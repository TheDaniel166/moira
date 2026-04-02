# Primary Directions Truth Card -- Fixed Stars

## Current Admitted Surface

Moira now admits one narrow fixed-star branch in runtime:

- sovereign catalog-backed fixed-star promissors
- projected through the ordinary primary-direction speculum
- admitted against **angle and planet significators**
- currently realized as plain conjunction-style directional points

This branch is intentionally narrow.


## Governing Law

The current fixed-star law is:

1. resolve the star through Moira's sovereign registry
2. compute its true geocentric longitude/latitude at `jd_tt`
3. build a `SpeculumEntry` for that explicit point
4. measure the direction through the chosen method's existing conjunction law

So the branch stands on explicit substrate:

- [stars.py](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
- [primary_direction_fixed_stars.py](c:/Users/nilad/OneDrive/Desktop/Moira/moira/primary_direction_fixed_stars.py)
- [primary_directions.py](c:/Users/nilad/OneDrive/Desktop/Moira/moira/primary_directions.py)


## Current Policy Boundary

Admitted now:

- sovereign catalog-backed named stars
- explicit service-supplied fixed-star targets
- angle significators only

Not admitted yet:

- fixed-star opposition
- zodiacal aspect doctrine for stars
- wider mundane-star doctrine
- consumer-facing folklore star menus


## Validation State

The current branch is validated by:

- sovereign name-resolution tests
- direct point-resolution tests against `star_at(...)`
- end-to-end runtime proof on the admitted angle branch
- fixture-backed angle examples preserving exact star coordinates and exact arc
  results on:
  - `Meridian` mundane (`Sirius -> ASC`)
  - `Ptolemy / semi-arc` zodiacal (`Algol -> MC`)
- fixture-backed planet examples preserving exact star coordinates and exact arc
  results on:
  - `Meridian` mundane (`Sirius -> Venus`)
  - `Ptolemy / semi-arc` zodiacal (`Algol -> Sun`)

The caller-facing path is now also hardened through
`primary_directions_policy_preset(...)`, which can thread explicit
`fixed_star_targets` into the documented method branches.


## Present Declaration

Moira now has a first mathematically explicit fixed-star branch.

It should be described as:

> catalog-backed fixed-star conjunction to angles and planets

and not yet as a complete fixed-star family.

