# Physical Heliacal-Visibility Validation and Admission

Date: 2026-08-07
Status: local Phase 7 engine-release gate closed; no publication or deployment
Model: `clear_sky_naked_eye_point_source_v1`

## Scope

This document is the current validation authority for Moira's additive physical
point-source assessment and event model. It does not replace the separate
legacy arcus/limiting-magnitude, Yallop lunar-crescent, or
Krisciunas-Schaefer legacy-moonlight validation families.

The machine-checked inventories are:

- [physical capability matrix](PHYSICAL_HELIACAL_VISIBILITY_CAPABILITY_MATRIX.generated.md);
- [physical API inventory](PHYSICAL_HELIACAL_VISIBILITY_API_INVENTORY.generated.md);
- `tests/fixtures/physical_visibility_phase7_evidence_registry.json`; and
- `scripts/generate_physical_visibility_inventory.py --check`.

Each admitted claim below names its evidence class. A test snapshot or another
engine's output is never promoted to scientific authority merely because it
agrees.

## Admission summary

| Surface | Status | Named evidence classes | Qualification |
|---|---|---|---|
| Physical single-epoch assessment | admitted, opt-in | `primary_source_equation_validation`, `independent_libradtran_holdouts`, `modern_era_observational_comparison`, `property_and_invariant_testing`, `separated_numerical_tolerances` | Clear sky, unresolved steady point source, admitted observer protocol and exact pack domain. |
| Four-phase physical event search | admitted, opt-in | `external_ephemeris_event_goldens`, `property_and_invariant_testing`, `separated_numerical_tolerances` | Mars/Jupiter/Saturn/Sirius only; explicit first/last ownership and certified crossings. |
| Python/facade/REST/OpenAPI projection | admitted | `public_contract_and_openapi_parity`, `legacy_regression_fixtures` | Additive physical routes; legacy defaults and shapes remain exact. |
| External data pack 1.2.0 | admitted immutable resource | `independent_libradtran_holdouts`, `release_artifact_and_offline_install` | Separate CC BY-SA 4.0 artifact; never embedded or downloaded. |
| Two private Phase 6 kernels | admitted implementation detail | `native_python_differential` | Numerical differential/performance evidence only; no policy or doctrine ownership. |
| Historical apparition/Sothic cases | legacy corroboration only | `historical_event_corroboration` | Bounded windows or historical uncertainty; not exact physical-event goldens. |
| Site-specific experimental moonlight | quarantined research | `experimental_site_specific_moonlight_quarantine` | No runtime, API, packaged resource, release gate, or active-roadmap dependency. |

## Scientific evidence

### Primary equations

`tests/unit/test_visibility_physics.py` and
`tests/unit/test_visibility_spectral.py` retain source-level evaluations for
Kasten-Young relative air mass, the named Schaefer legacy component family,
Crumey/Blackwell point-source equations, CIE MES2 response composition, and
Tousey-Koomen Table I comparison values. Their purpose is equation and
component validation; they do not claim a universal atmosphere or observer.

### Independent libRadtran evidence

The versioned pack was produced in an external offline libRadtran 2.0.6 and
REPTRAN reference laboratory. Holdout coordinates and random seeds were kept
disjoint from training or representation selection. The admitted checkpoints
include:

- untouched radiance-response holdouts;
- untouched named-spectral direct-transmission holdouts;
- altitude, pressure, and joint interpolation holdouts; and
- Windows/Linux byte and validator parity.

The generator and runtime remain separate. libRadtran, REPTRAN data, and CIE
source tables do not enter the Python distribution or normal execution.

### Observational comparison

The admitted modern-era observational comparison is the Tousey-Koomen 1953
Table I twilight series. It is source bounded and enforces the declared
point-source/field relationship. It is not described as a contemporary
multi-site observer-population campaign.

### Astronomical and event goldens

The Phase 3 source-owned golden binds:

```text
tests/golden/physical_visibility_phase3_events.json
pack manifest:
  cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c
```

The independent oracle uses checksum-locked Horizons geometry for Jupiter and
the Sun, and Hipparcos/BSC5/CALSPEC/Astropy/PyERFA/IERS sources for Sirius. It
does not import Moira's event solver. The admitted residuals were:

| Case | Engine versus independent event | Oracle tolerance |
|---|---:|---:|
| Jupiter morning first rising | 1.2063503265 seconds | 60 seconds |
| Sirius morning first rising | 2.5644600391 seconds | 60 seconds |

These cases validate ephemeris geometry, target identity, event ownership,
crossing semantics, and exact pack use. They are not observed first-visibility
dates and do not quantify weather or observer-population uncertainty.

### Historical cases

Published planetary apparition windows and the Sirius/Sothic historical case
remain in the legacy validation family with their declared windows and
delegation tolerances. Phase 7 classifies them as corroboration only. It does
not fit the physical model to them, reinterpret them as exact timestamps, or
use engine agreement to erase calendrical, observational, site, or doctrine
uncertainty.

## Separated tolerance law

The pack's independent holdouts produced these numerical bounds:

| Error owner | Maximum | p95 or receipt law |
|---|---:|---:|
| Photopic response interpolation | 0.354270 mag | 0.287715 mag |
| Scotopic response interpolation | 0.252966 mag | 0.244817 mag |
| Direct-extinction interpolation | 0.0212954 mag | 0.00279149 mag |
| Binary32 storage | `9.487461198887104e-7` mag | retained separately |
| Source solver / Monte Carlo | per response cell | maximum contributing corner |

The runtime propagates the admitted numerical envelope through the photopic and
scotopic backgrounds and threshold to separate limiting-magnitude and
visibility-margin bounds. Input/scenario and model uncertainties that lack a
defensible numeric bound remain named and unquantified; they are not assigned
zero.

Event search separately records:

- scan step and recursion law;
- root-time tolerance;
- root-margin tolerance or non-applicability at a horizon boundary;
- actual residual and bracket;
- the Lipschitz zero-enclosure certificate and unresolved interval count; and
- deterministic event-time sensitivity under admitted atmosphere scenarios.

The numerical search tolerances do not become claims about human-observer or
weather accuracy. Moira publishes no aggregate tolerance and no probabilistic
confidence score.

## Property, invariant, and failure evidence

The focused property/invariant family covers:

- no extrapolation at pack axes or target photometry domains;
- exact regular-file inventory, checksums, compatibility, and symlink refusal;
- multiple hidden crossings, same-sign endpoints, tangencies, and near-zero
  intervals;
- fail-closed uncertified crossings;
- first/last guard-day ownership;
- horizon-owned versus margin-owned boundaries;
- polar day/night, circumpolar, never-rising, and missing-boundary states;
- deterministic repeated and concurrent execution;
- target-catalog and profile drift;
- no generic stellar color-index guessing; and
- no confidence or synthetic score fabrication.

`not_evaluable` is not treated as false visibility. `not_found` is used only
when a fully evaluable search contains no owned phase transition.

## Contract and compatibility evidence

Thirty-six physical symbols preserve object identity across
`moira.heliacal`, the curated `moira` root, `moira.facade`, and
`moira.sky.visibility`. Matching `Moira` methods forward the full policy. The
two dedicated REST operations preserve every engine policy/receipt field and
accept no client filesystem path.

The legacy assessment, tonight, and generalized heliacal event request and
response schemas remain exact. The current generated inventory is checked
against `create_app().openapi()` rather than copied from prose.

## Native differential evidence

Phase 6 admitted exactly two private kernels. The boundary-inclusive
differential contained 14,205 response cases, 2,001 direct-extinction cases,
and eight-thread determinism. Maximum observed absolute differences were:

| Quantity | Maximum | Admission tolerance |
|---|---:|---:|
| S/P ratio | `8.881784197001252e-16` | `5e-15` |
| Response weight | `1.734723475976807e-18` | `5e-18` |
| Response normalization | `1.1102230246251565e-16` | `2e-15` |
| Direct extinction | `0` | `2e-15` |
| Direct transmission | `0` | `2e-15` |

This is implementation evidence, not a second scientific oracle. Python's
numerical paths remain executable differential references.

## Release artifact and offline evidence

`scripts/validate_physical_visibility_phase7_release.py` performs the release
gate from a copied current source snapshot:

1. build a wheel and sdist with build isolation disabled;
2. inspect both for the release identity, compatibility contracts, and notice;
3. reject any embedded external `.f32le` payload;
4. clean-install the source-built wheel with `--no-index --no-deps`;
5. rebuild a wheel from the extracted sdist;
6. clean-install the sdist-built wheel;
7. import the native backend and both public physical functions; and
8. load the exact external pack under `MOIRA_NO_DOWNLOAD=1` and an active
   socket-deny guard.

The external pack release tool produces a deterministic 14-file archive:

```text
moira-physical-heliacal-visibility-1.2.0.tar.gz
SHA-256:
  0d2c98d0717c45416ad0f8f3e0b72ca28d3975f4f6c8080112ceb2bef8327d71
```

The final run is recorded in
`tests/artifacts/release/physical_visibility_phase7_release_validation_2026-08-07.json`.
That receipt proves only the exact local artifacts it names; it does not claim
that they were uploaded, tagged, published, installed downstream, or deployed.

## Closed exclusions and downstream boundary

Clouds, live weather, optical aids, extended objects, the Sun, lunar crescents
through this model, global site transfer, generic stellar profiles, observer
population probability, and synthetic confidence remain outside the model.

The Jones/Paranal experiment is quarantined and does not enter the assessment,
event, compatibility, or release contract. Website
documentation remains downstream of an actual engine and data-artifact
publication gate.
