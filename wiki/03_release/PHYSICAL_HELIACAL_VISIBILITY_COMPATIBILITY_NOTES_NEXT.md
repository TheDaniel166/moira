# Physical Heliacal Visibility - Next-Release Compatibility Notes

Status: Phase 7 compatibility boundary prepared; no release version is assigned
and no package or deployment is performed by this document.

## Existing callers

No migration is required for callers that continue using legacy visibility or
heliacal APIs. These operations retain their existing defaults and shapes:

```text
visibility_assessment(...)
visibility_tonight(...)
visibility_event(...)
POST /v1/visibility/assessment
POST /v1/visibility/tonight
POST /v1/heliacal/visibility-event
```

The new physical model is not selected by omission. Existing serialized
responses, caches, and clients are not reinterpreted as physical truth.

## Opting into the physical model

Python callers use the additive functions or matching `Moira` methods and must
supply an explicit `VisibilityDataPackConfig`:

```python
from moira import (
    PhysicalVisibilityPolicy,
    VisibilityDataPackConfig,
    physical_visibility_assessment,
)

pack = VisibilityDataPackConfig(
    r"C:\path\to\moira-physical-heliacal-visibility-1.2.0",
    expected_manifest_sha256=(
        "cf93433a9f66a5ea92832271ce3c4b023"
        "fcc8693164803539a9f1be85b17468c"
    ),
)
result = physical_visibility_assessment(
    "Mars",
    2460000.5,
    35.0,
    -105.0,
    data_pack_config=pack,
    policy=PhysicalVisibilityPolicy(),
)
```

The physical function arguments for pack and policy are keyword-only. Event
search additionally requires an explicit `PhysicalVisibilityPhase` and keeps
the search policy typed and keyword-only.

## Server configuration

REST clients cannot send a filesystem path. The deployment configures:

```text
MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY
MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_MANIFEST_SHA256
```

Only the two dedicated physical routes require this setting. If it is absent,
they return the standard HTTP 503 `server_not_configured` envelope; unrelated
and legacy routes continue normally.

## Data and licensing

Install the Python artifact and the external data artifact separately:

- `moira-astro`: MIT;
- `moira-physical-heliacal-visibility` `1.2.0`: CC BY-SA 4.0.

The external archive identity is:

```text
filename: moira-physical-heliacal-visibility-1.2.0.tar.gz
SHA-256: 0d2c98d0717c45416ad0f8f3e0b72ca28d3975f4f6c8080112ceb2bef8327d71
```

Do not copy the pack payload into the wheel or assume the Python installation
provides it. Preserve the pack's README, NOTICE, provenance, manifest, and
`SHA256SUMS` when redistributing it.

## Failure handling

Callers must branch on typed status and reason rather than treating every
negative result as "not visible":

- `evaluated`: the requested truth was computed;
- `not_evaluable`: evidence, resource, target, geometry, or model domain was
  insufficient;
- `not_found`: an evaluable event search found no owned phase transition in the
  candidate window.

Unsupported targets, phase/domain gaps, incomplete guard-day evidence, corrupt
or mismatched data, and uncertified crossings are not silently converted to a
false visibility result.

## Target compatibility

- Single-epoch assessment: Mercury, Venus, Mars, Jupiter, Saturn.
- Four-phase event search: Mars, Jupiter, Saturn, Sirius.
- Mercury/Venus physical event requests: typed
  `body_phase_not_admitted`.
- Other fixed stars and target families: typed `target_not_admitted` until a
  source-owned profile is admitted.

The physical point-source contract does not apply to the Sun, lunar crescent,
extended objects, optical aids, or live-weather/cloud conditions.

## Operational upgrade sequence

1. Install the exact candidate wheel in staging.
2. Acquire the exact external pack archive and verify its SHA-256.
3. Extract it without renaming or changing any pack file.
4. Configure the server-owned directory and optional manifest pin.
5. Verify installed Moira version and native backend identity.
6. Load the pack with downloads disabled and confirm manifest
   `cf93433a...17468c`.
7. Exercise one evaluated assessment, one evaluated event, one typed unsupported
   target/phase, and one unconfigured-server HTTP 503.
8. Promote only the exact staged engine and data artifacts.

Website adoption remains a downstream operation after these engine and data
release gates pass.
