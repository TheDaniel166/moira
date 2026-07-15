# Signed Aspect Motion Validation — 2026-07-15

## Product

This ledger validates the instantaneous, caller-supplied longitude product
exposed by:

- `moira.aspects.aspect_motion_witness(...)`
- `Moira.aspect_motion_witness(...)`
- `POST /v1/aspects/motion-witness`

It does not validate a future aspect-perfection search, a station search, or
any historical electional interpretation.

## Governing geometry

For normalized longitudes `lambda1` and `lambda2`, Moira selects the shortest
directed separation in `[-180, 180)`. For a nonzero aspect angle, the target
uses the sign of that directed separation. The directed error is:

```text
directed_error = directed_separation - signed_exact_target
relative_speed = speed2 - speed1
orb_rate = sign(directed_error) * relative_speed
```

Away from exactness and stationary singularities, a negative orb rate is
applying and a positive orb rate is separating. At zero separation, a selected
non-conjunction has equally near positive and negative branches; Moira reports
the branch and state as indeterminate rather than choosing one silently.

The aspect angle and default orb come from `moira.constants.Aspect`. The
request's positive `orb_factor` scales that default. Exactness and relative
standstill use separately serialized caller-visible numerical tolerances.
Known bodies retain Moira's existing body-specific stationary thresholds;
unknown point names use the existing 0.005 degree/day fallback. Every triggered
station condition is returned as a named reason.

## Evidence classes

- **Geometric invariants:** directed wrap, branch selection, error magnitude,
  relative-rate sign, orb-rate sign, exactness, and immutable result state.
- **Regression protection:** the pre-existing `AspectData` applying/separating
  behavior and `/v1/aspects/from-longitudes` contract remain unchanged.
- **Transport parity:** engine, root export, `Moira`, REST serialization, and
  OpenAPI expose the same witness semantics.

This work uses no external ephemeris or secondary astrology engine. The
mathematical proof is first-principles angular kinematics; it is not an
authority-validation claim about an astronomical chart reduction.

## Adversarial cases

- 359/1 degree wrap on both applying and separating relative rates;
- positive and negative signed aspect branches;
- exact sextile and opposition with no supplied speeds;
- explicit nonzero exactness tolerance;
- one missing speed and both missing speeds;
- one body below its stationary threshold;
- equal speeds producing relative standstill;
- motion truth outside the selected orb;
- equal positive/negative branches at zero separation;
- non-finite, untrimmed, duplicate, unknown-aspect, and invalid-policy inputs;
- frozen result mutation rejection;
- root/facade identity and typed REST/OpenAPI contracts.

## Commands

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"

.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_aspect_motion_witness.py -q

.\.venv\Scripts\python.exe -m pytest `
  tests\server\test_server_aspect_motion_witness.py -q
```

## Remaining boundary

Phase 2B must add a time-ordered previous-separation/next-connection event
flow. This instantaneous witness supplies its local signed geometry but does
not determine Dorotheus V.9's source-owned search interval or stake mapping.
