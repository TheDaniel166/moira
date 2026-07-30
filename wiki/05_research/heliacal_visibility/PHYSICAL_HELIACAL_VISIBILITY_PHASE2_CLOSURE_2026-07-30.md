# Physical Heliacal Visibility Phase 2 Closure

Date: 2026-07-30
Status: complete

Governing roadmap:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

## Closure Boundary

Phase 2 closes Python spectral single-epoch truth for the first admitted
planetary targets. It does not activate:

- the Phase 3 physical visibility-event solver;
- Phase 4 moonlight, airglow, directional horizon, or local-environment
  expansion;
- Phase 5 root, facade, serializer, REST, or OpenAPI parity;
- native acceleration or native parity;
- automatic acquisition or network access;
- a new default visibility policy;
- a package, tag, release, or website deployment.

The legacy Schaefer/arcus event path remains the default and retains its
existing identifiers and behavior.

## Admitted Runtime Contract

`physical_visibility_assessment()` is an additive owning-module surface. It
requires:

- an explicit caller-supplied local data-pack directory;
- one versioned `PhysicalVisibilityPolicy`;
- one complete atmosphere input matching the pack;
- exactly one admitted directional background authority; and
- an admitted Mercury, Venus, Mars, Jupiter, or Saturn identity.

The runtime does not search for, download, regenerate, or silently replace a
pack. Missing, corrupt, incompatible, incomplete, and out-of-source-domain
inputs return typed non-evaluable results.

Pack version 1.0 remains loadable for its Phase 1 atmosphere tables. It has no
planetary target profiles, so the Phase 2 public assessment returns
`target_spectral_profile_missing`. Pack version 1.1 adds the source-locked
planetary profiles required for evaluation.

The public assessment has no caller-supplied planetary spectral-profile
parameter. Apparent V magnitude, phase angle, and Saturn effective ring
sub-latitude are resolved from one engine-owned ephemeris context. The
validated pack then resolves the matching response integrands and color law.

## Exact Data-Pack Receipt

```text
pack_id:
  moira-physical-heliacal-visibility
version:
  1.1.0
compatibility_id:
  moira-physical-heliacal-visibility-data-pack-v1.1
manifest_sha256:
  f594fd12058cc7f5c7bc9de7f2b06652bef3c0604ef7b0a05a069e54e4026c87
target_profile_sha256:
  40f4362aca22e329ad25916efa8476fee7a86eb1a6b0dfc1cf1b6c88f64531a0
generation_fingerprint:
  281b3fdaa1910d81ebf9ec616cbed0784eed5a33f05bbdc682baee34b4db8848
payload_file_count:
  12
```

The admitted external artifact is:

```text
/home/nilad/.cache/moira/visibility-reference-lab/data-packs/
moira-physical-heliacal-visibility-1.1.0-v3
```

A clean second build at the `v4` path produced the same 13 root files,
byte-for-byte, including the root manifest. Neither build modified the
admitted Phase 1 pack.

The `v1` and `v2` construction attempts are preserved as rejected forensic
artifacts. `v1` had not yet narrowed the Payne source spectra to the admitted
positive visible subset. `v2` omitted explicit empty `limitations` arrays
required by the strict color-model schema. Neither is admitted.

## Planetary Profile Authority

The 1.1 pack owns 400-bin, 380-779 nm photopic and scotopic response
integrands for:

- Mercury;
- Venus;
- Mars;
- Jupiter; and
- Saturn.

The base spectral shapes derive from the versioned Payne et al. planetary
geometric-albedo spectra multiplied by the locked extraterrestrial solar
spectrum and integrated against the exact CIE photopic and scotopic response
data.

Mallama et al. 2017 supplies the source-domain broadband color behavior:

- Mercury: constant-color/gray treatment over phase 2-170 degrees;
- Venus: UBVRI phase-polynomial color over phase 2-165 degrees;
- Mars: UBVRI phase-polynomial color over phase 0-50 degrees;
- Jupiter: UBVRI phase-polynomial color over phase 0-12 degrees; and
- Saturn: UBVRI phase and effective ring-sub-latitude treatment over phase
  0-6 degrees and ring sub-latitude 0-27 degrees.

The runtime uses a named piecewise-linear Johnson-Cousins differential
magnitude warp, normalizes both response paths independently, and updates the
S/P ratio consistently. It never extrapolates a color law beyond its source
domain.

The compact source and numerical receipt is:

```text
tests/artifacts/visibility_reference_lab/
phase2_planetary_target_profiles_checkpoint_2026-07-30.json
```

## Numerical Truth

The admitted compositor includes:

- exact Phase 1 pack identity and no-extrapolation interpolation;
- response-weighted photopic and scotopic direct transmission;
- measured-total background precedence;
- modeled twilight plus a source-owned dark-sky anchor;
- qualified SQM transformation;
- visibly coarse explicit Bortle fallback;
- CIE MES2 adaptation with a bounded same-equation fallback;
- Crumey equations 28 and 34 with fixed field factor `F=2`;
- visibility margin
  `limiting_magnitude - conditioned_target_magnitude`; and
- a typed declared data-pack numerical-error envelope; and
- eight exact component receipts for an evaluated result.

The observer protocol remains:

```text
known_location_directed_averted_observation_v1
```

It is a known-location, deliberately directed, peripheral/averted task. It is
not claimed as a central/foveal threshold.

## Independent Validation

`scripts/validate_visibility_phase2_data_pack.py` is read-only and imports
neither the builder nor the Moira engine. From explicit local paths it:

- verifies every declared source byte count and SHA-256;
- validates the complete 1.1 root inventory and `SHA256SUMS`;
- proves the seven inherited Phase 1 payloads are byte-identical;
- independently parses and interpolates the Payne, solar, and CIE inputs;
- independently rederives all five response profiles;
- compares the canonical target payload byte-for-byte;
- verifies the specification, compatibility, builder, provenance, and
  generation receipts; and
- records that no network was used.

Windows independent validation accepted the exact v3 pack. The same pack also
loads through the engine with its pinned root manifest.

The end-to-end Venus smoke at JD `2451545.7291666665`, latitude `0`, longitude
`0` returned:

```text
status: evaluated
evidence_state: evaluated_clear_sky
target_true_altitude_deg: 30.953318182797634
solar_center_true_altitude_deg: -7.73651006224335
phase_angle_deg: 58.618037322862044
visibility_margin_magnitude: 7.126526684691916
component_receipt_count: 8
spectral_profile_id: payne_2026_venus_cie_response_v1
color_model_id: mallama_2017_ubvri_phase_color_v1
solver_relative_standard_error_multiplier: 1.0
visibility_margin_data_pack_envelope_lower_magnitude: 6.810345248615479
visibility_margin_data_pack_envelope_upper_magnitude: 7.455362567961965
visibility_margin_data_pack_envelope_maximum_deviation_magnitude: 0.32883588327004887
visibility_classification_within_data_pack_envelope: visible
error_budget_method_id: phase2_data_pack_declared_numerical_error_envelope_v1
```

## Numerical-Error Propagation

The nominal Venus margin is unchanged. The added error-budget receipt closes
the Phase 1 handoff that assigned limiting-magnitude propagation to Phase 2.
It includes:

- plus or minus one maximum-contributing per-cell solver relative standard
  error;
- maximum photopic and scotopic interpolation error;
- direct-extinction maximum interpolation error; and
- separately recorded binary32 storage error.

Modeled-twilight bounds perturb the twilight term only, hold the supplied
dark-sky anchor nominal, and evaluate CIE MES2 plus the Crumey threshold at all
four photopic/scotopic bound corners. The target bound combines the
direct-extinction maximum interpolation and storage errors. The final receipt
reports lower and upper limiting-magnitude and visibility-margin envelope
limits and a
`visible`, `not_visible`, or `indeterminate` classification within those
data-pack numerical terms.

Measured-total backgrounds carry no fabricated pack-owned background error.
Their input uncertainty is named as unquantified, and only the direct-
extinction pack error is propagated. P95 interpolation values remain
diagnostics rather than maximum bounds.

The solver term is not claimed as a hard maximum, and this is not a
scientific-confidence interval. Dark-sky or measured-background
input error, planetary photometry and spectral-source uncertainty, CIE and
threshold model-form uncertainty, observer-population variance, and actual
atmospheric variability remain explicitly unquantified.

## Failure Containment

The Phase 2 tests cover:

- absent and corrupt packs;
- incompatible semantic versions and compatibility receipts;
- unsafe or mismatched inventories;
- malformed provenance and notices;
- checksum, byte-count, and nonfinite table failures;
- interpolation nodes, off-grid values, and every declared boundary;
- missing target profiles;
- missing Saturn ring context;
- source phase and ring-domain violations;
- changed color-coefficient shapes;
- silently non-normalized response weights;
- background conflicts and double counting;
- nonfinite engine photometry;
- authenticated relative-standard-error values at or above one;
- authenticated P95 values above their declared maxima;
- zero-error envelope collapse and increasing-error envelope widening;
- measured-total propagation without invented measurement error;
- nominal margins that become indeterminate inside the pack error envelope;
- atmosphere and local-horizon boundaries;
- evaluated, missing-dependency, out-of-domain, and not-applicable truth;
- immutable pickle round trip; and
- finite JSON-safe structural round trip without activating transport.

No caller can relabel engine photometry or inject substitute planetary
response weights.

The focused Phase 2 loader, compositor, target-profile, serialization, and
error-envelope gate collected and passed 88 tests. The combined Phase 2 plus
legacy visibility gate collected 585 tests, passed 584, and skipped the one
pre-existing empty optional enumeration; nothing was deselected.

## Legacy Regression Gate

Three incomplete fixture boundaries found during the checkpoint were repaired
only
at their resource boundaries:

- the mocked Yallop event fixture now supplies the later assessment geometry,
  photometry, and crescent detail dependencies;
- the fixed-star not-found fixture now supplies its mocked twilight boundary
  rather than falling through to live `sky_position_at`; and
- the two KS1991 assessment cases now pin their mocked phase and signed
  elongation inputs rather than falling through to live ephemeris geometry.

The focused legacy gate collected 497 tests. It passed 496 and skipped one
pre-existing empty optional enumeration. No failure was deselected. The gate
covers legacy heliacal policy, planetary and fixed-star heliacal behavior,
visibility physics, adversarial public behavior, validation corpora, and the
existing server visibility route.

The apparent-magnitude reference suite also passes all 23 cases after the
internal photometry-context refactor.

## Phase 2 Exit Gate

- [x] Every result names its effective component models and data identity.
- [x] Every unsupported or incomplete case fails closed.
- [x] Independent reference cases pass the Phase 1 error budget, and its
  downstream numerical inputs are propagated through the single-epoch margin.
- [x] Existing Schaefer, Kasten-Young, Krisciunas-Schaefer, Crumey, Yallop,
  and legacy defaults retain their frozen behavior.
- [x] The Phase 2 closure receipt is source-controlled and linked from the
  roadmap.

## Next Authorized Work

Phase 3, the physical visibility-event solver, is the next authorized phase.
It must find physical visibility-margin crossings without changing any legacy
event search or activating later facade/REST/native work.
