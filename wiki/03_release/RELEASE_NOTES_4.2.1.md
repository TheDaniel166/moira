# Moira 4.2.1 — Relationship REST Completion

Moira 4.2.1 completes the REST promotion of the derived-chart aspect work
introduced in 4.2.0. Composite and Davison consumers can now receive each
relationship chart and its position-owned aspect analysis in one response.

## Relationship charts now include their aspects

The following routes add a required `aspects` response member:

- `POST /v1/composite/chart`
- `POST /v1/davison/chart`

The member uses the same `AspectsFromLongitudesResponse` contract as
`POST /v1/aspects/from-longitudes`. It contains:

- canonical aspect events with separation, exact angle, orb, allowed orb,
  classification, direction, and sign-degree evidence;
- normalized and deterministically ordered input longitudes;
- the effective aspect tier and orb factor;
- node-inclusion policy and any excluded node names;
- point and aspect counts;
- explicit position and motion semantics.

The existing relationship request fields now govern the embedded analysis:

- `tier` selects canonical aspect tier `0`, `1`, or `2`;
- `orb_factor` applies the positive bounded orb multiplier;
- `include_nodes` controls Moira's named node points.

When these fields are omitted or null, the relationship routes resolve them to
tier `1`, orb factor `1.0`, and node inclusion.

## Semantic boundary

Composite and Davison charts own ecliptic positions, but those positions do
not provide speed truth. The embedded analysis therefore does not invent
retrograde, stationary, applying, or separating semantics. Its computation
truth continues to report
`motion_semantics: not_computed_without_speeds`, and each aspect's `applying`
field remains null.

The underlying chart calculations are unchanged. Composite and Davison retain
their distinct chart, house, classification, relation, and computation-truth
vessels; they now share one nested aspect-analysis contract.

## Compatibility

This patch adds a response member without removing or renaming an existing
field. Most JSON consumers will accept the addition normally. Strict consumers
that reject unknown response members must admit `aspects` on both relationship
chart responses.

The standalone `POST /v1/aspects/from-longitudes` route remains available for
harmonic, draconic, progressed, and other caller-supplied position products.

## Validation

The 4.2.1 release checks establish that:

- OpenAPI marks `aspects` as required on both relationship response schemas;
- the nested schema is exactly `AspectsFromLongitudesResponse`;
- `tier`, `orb_factor`, and `include_nodes` propagate through REST to the
  engine analysis;
- invalid aspect-policy values are rejected at the transport boundary;
- both composite methods return embedded analysis;
- all five Davison methods return embedded analysis;
- embedded events agree with direct `Moira.aspects_from_longitudes(...)`
  results for the returned positions.

This is a REST visibility and contract-completion patch. It does not change
planetary positions, house calculation, Davison time-scale handling, or
Moira's canonical aspect definitions.
