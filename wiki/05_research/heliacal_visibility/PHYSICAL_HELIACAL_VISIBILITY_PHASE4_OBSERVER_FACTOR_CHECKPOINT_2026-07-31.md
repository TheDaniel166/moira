# Physical Heliacal Visibility Phase 4 Observer-Factor Checkpoint

Date: 2026-07-31
Status: doctrine resolved and receipt hardened; Phase 4 remains open

## Question Resolved

The roadmap asked for an admitted observer-factor input and valid range. The
source review shows that exposing a generic experience or skill slider would
misstate Crumey's model.

In Crumey (2014), the overall field factor `F` may combine target, medium,
laboratory-scaling, detection-practice, and personal effects. It is not an
isolated observer parameter. The paper uses `F = 2` as a notional
illustrative value for naked-eye point-source examples; contextual values
discussed elsewhere in the paper do not establish a universal validity range
for individual observers.

Blackwell's underlying threshold normalization is also a repeated-trial
detection condition, not a confidence score for one observation.

## Admission Decision

The named physical observer protocol keeps a fixed singleton contract:

```text
model:
  crumey_2014_equation_53_fixed_notional_f2_v1
value:
  F = 2.0
mutable:
  false
probabilistic detection claim:
  false
```

There is no caller-supplied physical observer-factor field. A future
calibrated observer protocol would require a new protocol/model identifier,
the calibration experiment and receipt, and an independently justified
domain. It would not silently mutate this protocol.

The legacy `VisibilityPolicy.crumey_field_factor` remains a separate existing
contract and is not changed by this decision.

## Receipt Hardening

`PhysicalObserverProtocolReceipt` now carries:

- the fixed field-factor model identifier;
- `F = 2.0`;
- `detection_field_factor_mutable = false`;
- exact Crumey source identifiers; and
- `probabilistic_detection_claimed = false`.

The same facts appear in the generic `observer_protocol` component receipt.
The independently existing threshold receipt continues to report the actual
factor used, so the observer and threshold receipts must agree.

## Compatibility

The new receipt fields are additive defaults appended to the existing
dataclass. No calculation, model identifier, policy input, legacy function,
or default changes.

## Local Verification

The focused spectral suite asserts:

- the physical policy exposes no detection-field-factor input;
- the observer receipt reports the immutable `F = 2` contract;
- the threshold receipt used the same factor;
- no probabilistic claim is made; and
- the generic component receipt preserves the same facts.

Focused result after observer-receipt hardening:
`tests/unit/test_visibility_spectral.py` — `55 passed`.

The widened heliacal/visibility unit gate passed `464` tests, and the
visibility/phase server-route gate passed `24` tests.

## Remaining Phase 4 Work

- independently implement and validate the separately versioned Jones
  scattered-moonlight component;
- use ESO/PALACE outputs only in site-bound comparison fixtures; and
- derive explicit environmental sensitivity envelopes without calling them
  observer probability or scientific confidence.

Phase 4 is not closed by this checkpoint.
