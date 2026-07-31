# Physical Heliacal Visibility Phase 4 Background-Composition Checkpoint

Date: 2026-07-31
Status: implemented and locally verified; Phase 4 remains open

## Scope

This checkpoint closes the background-authority and double-counting contract
for separately modeled sky components. It adds no built-in airglow, zodiacal,
integrated-starlight, artificial-light, or moonlight numerical model.

The admitted input is a caller-supplied, response-integrated directional
model output. Measured total background remains the highest authority, and the
existing twilight-plus-dark-anchor path remains unchanged when no separate
component is supplied.

## Typed Component Contract

`PhysicalModeledBackgroundComponent` admits exactly one of:

- `airglow`;
- `zodiacal_light`;
- `integrated_starlight`; or
- `artificial_light`.

Every component must provide:

- positive photopic and scotopic directional luminance in `cd m-2`;
- a model identifier;
- one or more source identifiers;
- a lowercase SHA-256 source receipt;
- spatial, temporal, and directional applicability identifiers;
- a validity-domain identifier; and
- an uncertainty-authority identifier.

These qualifiers describe caller-supplied evidence. Moira does not infer the
site, epoch, direction, domain, or uncertainty treatment.

## Composition Law

The compositor applies these fail-closed rules:

1. A measured total background cannot be combined with twilight, a dark-sky
   anchor, or any separately modeled component.
2. Separately modeled components require a dark-sky anchor whose
   `component_inventory_complete` flag is true.
3. No component kind may appear both in that anchor's exhaustive
   `component_ids` and as a separately modeled component.
4. No modeled component kind may be supplied twice.
5. Solar twilight remains pack owned and cannot also appear in the anchor.
6. Accepted modeled components are sorted by canonical component identity
   before summation and receipt construction.

The complete directional background is summed with `math.fsum`. A distinct
authority identifier,
`modeled_twilight_plus_declared_background_components_v1`, prevents this
composition from being confused with the unchanged
`modeled_twilight_plus_measured_dark_sky_v1` path.

## Receipts and Error Boundary

Each accepted component becomes its own
`modeled_background_component` receipt containing its kind, model, sources,
source SHA-256, two luminances, and every applicability/domain/uncertainty
qualifier.

`PhysicalBackgroundReceipt` also records whether the anchor inventory was
complete and how many separate modeled components entered the result.

No caller-model uncertainty is fabricated or folded into the data-pack
numerical envelope. Each component appears in
`unquantified_error_sources` until an independently admitted sensitivity
contract states how its uncertainty propagates.

## ESO, PALACE, and Global-Default Boundary

The ESO Advanced Cerro Paranal Sky Model and PALACE remain site-bound
comparison and validation references. This checkpoint copies no GPL code or
tables, admits no Paranal-derived global profile, and gives neither source a
runtime default. A future source-specific implementation must retain its site
and validity domain in the component receipt and pass independent numerical
validation.

## Compatibility

All additions are optional and appended to existing dataclasses. Existing
callers that provide only a measured total, a dark-sky anchor, an SQM input,
or a coarse Bortle anchor keep their prior calculation path and authority
identifier.

The new types are owned and exported by `moira.heliacal`. Root exports,
facades, methods, serializers, REST models, and OpenAPI remain Phase 5 work.

## Local Verification

The focused background-composition suite is:

```text
.\.venv\Scripts\python.exe -m pytest
  tests\unit\test_visibility_spectral.py -q
```

Result at checkpoint creation: `54 passed`.

The tests cover measured-total precedence, incomplete anchor inventory,
anchor/model overlap, duplicate-safe composition, canonical ordering,
luminance summation, typed public failure, individual provenance receipts,
and explicit unquantified uncertainty.

The widened unit compatibility gate selected every test module whose filename
contains `heliacal` or `visibility`: `463 passed` at this checkpoint and
`464 passed` after the additive observer-receipt hardening.

## Remaining Phase 4 Work

- independently implement and validate the separately versioned Jones
  scattered-moonlight component;
- use ESO/PALACE outputs only in site-bound comparison fixtures;
- derive explicit environmental sensitivity envelopes.

Phase 4 is not closed by this checkpoint.
