# Track A bounded closure: relationship and locational forecasting

Date: 2026-08-10  
Scope: Moira engine and packaged `moira_server` only  
Status: implementation complete; focused validation recorded below

## Objective

Track A closes three high-value composition gaps without creating a second
ephemeris, aspect, return, house, or astrocartography authority:

1. exact predictive transits to composite and Davison charts;
2. fixed-star parity across the astrocartography line and subplanetary-point
   family;
3. relocated return charts and explicit-epoch dynamic astrocartography.

This work is calculation-only. It does not include Urania Workspace, the
public website, report prose, travel recommendations, or location rankings.

## Admission boundary

| Surface | Admitted contract | Delegated authority | Explicit exclusions |
|---|---|---|---|
| Relationship forecasting | Exact moving-body aspect perfections to immutable composite or Davison planet, node, angle, and cusp targets, with optional named aspect selection | `moira.synastry`, `moira.constants.ASPECT_TIERS`, and `moira.transits.find_transits` | Orb entry/exit windows, progressed composites, directed composites, interpretation |
| Fixed-star astrocartography | Source-resolved true-of-date star identity, RA/Dec, MC/IC/ASC/DSC lines, and zenith/nadir points | `moira.stars.star_at`, `moira.coordinates.ecliptic_to_equatorial`, `moira.astrocartography.acg_lines`, and `subplanetary_points` | Star ranking, place ranking, interpretation, duplicate canonical identity through aliases |
| Relocated returns | One canonical solar, lunar, or planetary return moment recast into source and relocated local house frames | `moira.transits` return solvers, `moira.chart.create_chart`, and `moira.chart.relocated_chart` | A second return solver, changed celestial positions between locations, interpretive relocation claims |
| Dynamic astrocartography | One to 128 caller-supplied, strictly increasing transit epochs with exact adjacent line displacement receipts | `moira.planets.sky_position_at` and `moira.astrocartography.acg_lines` | Progressed or directed cyclocartography, interpolation, scores, rankings, travel advice |

## Invariants

- Relationship chart identity is a stable SHA-256 receipt over chart kind, the
  complete authoritative composite or Davison construction truth, used epoch,
  correction/reference policy, and complete target geometry. Target or aspect
  selection does not change chart identity.
- Symmetric relationship aspects search both directional longitudes. A square,
  for example, searches both the positive and negative 90-degree branches.
- Relationship events are canonical `TransitEvent` results against static
  numeric longitude targets. No parallel aspect solver exists.
- Relationship search truth preserves the explicit/automatic step policy,
  policy override, solver tolerance, direction, motion, target set, aspect set,
  and canonical search count even when no event is found.
- Fixed-star requests require explicit UT1 and TT epochs. Star aliases that
  resolve to the same canonical identity fail closed.
- Fixed-star line geometry is equatorial; ecliptic star positions are converted
  with the true obliquity of date and retain the complete available star truth,
  classification, relation, catalog identity, and provenance receipt.
- A relocated return preserves the exact return epoch, planet snapshot, and
  node snapshot. Only the local house frame changes. The scalar return solvers'
  complete caller/default search policy is restored as typed result truth.
- Dynamic astrocartography accepts explicit epochs only. Adjacent results report
  signed meridian shifts or matched-latitude curve shifts, never a quality or
  destination score. Topocentric observer latitude and longitude are required;
  there is no hidden Greenwich/equator default.
- The implementation uses the Python standard library and existing Moira
  primitives. It introduces no NumPy dependency.

## Public contract parity

### Engine modules

- `moira.relationship_forecasting`
- `moira.astrocartography`
- `moira.locational_forecasting`

The same public types and functions are exported from `moira`, `moira.facade`,
and reader-bound `Moira` methods.

### Packaged REST routes

- `POST /v1/composite/transits`
- `POST /v1/davison/transits`
- `POST /v1/astrocartography/fixed-stars`
- `POST /v1/astrocartography/dynamic/transits`
- `POST /v1/returns/relocated`

The packaged server adds transport-only safety bounds: at most four moving
bodies per relationship request, at most 16 explicitly named target selectors,
at most 1,024 expanded canonical searches, at most approximately 500,000 scan
samples, at least a 0.01-day caller scan step, at least a 0.5-degree ACG
latitude step, at most 32 dynamic epochs, and at most four dynamic bodies.
These do not narrow the direct Python engine contracts.

## Validation receipt

Focused validation is intentionally separate from the repository-wide release
suite. Track A is not a tag or publication decision.

- [x] Relationship forecasting unit invariants
- [x] Fixed-star identity, frame, line, point, and alias-collision tests
- [x] Relocated-return and dynamic-line composition invariants
- [x] Root/facade/`Moira` public-surface parity
- [x] Server request validation, route discovery, search budget, reader/policy
      forwarding, and live fixed-star transport
- [x] Result-vessel tamper checks for complete relationship search expansion,
      exact per-subject line families, and adjacent dynamic transitions
- [x] Explicit ephemeris-reader and refraction parity through ACG chart and
      lunar-refinement paths
- [x] Existing astrocartography regression slice
- [x] Ruff on Track A modules and transport files
- [x] No `numpy` import in Track A source or tests

The final focused gate completed with 86 passing tests. Four additional legacy
small-body cases were separately observed to fail for the resource condition
described below and were excluded from the green Track A slice.

Four existing small-body astrocartography cases require local Ceres/Halley SPK
shards and fail in this isolated worktree when those resources are absent.
They are not Track A regressions and were not changed or waived. The planetary
and fixed-star Track A gates do not depend on those optional shards.

## Release boundary

This checkpoint does not authorize a commit, push, tag, package publication,
or deployment. Before a future release, run the repository's selected release
gates in the release worktree and assess any failures independently. Website or
Workspace adoption is a separate, later scope.
