# Physical Heliacal Visibility Phase 5 Closure

Date: 2026-08-04
Status: Complete
Starting engine revision: `690b8cb85de934f7bd308b62d0315c584bad5c64`

## Closed gate

Phase 5 closes public-contract parity for the already admitted physical
single-epoch assessment and four-phase event solver. It does not change the
scientific calculation, legacy visibility doctrine, Phase 4 Jones component,
or data-pack admission policy.

## Python contract

The physical enums, policy inputs, results, receipts, pack identities, and
public functions retain one object identity across:

- `moira.heliacal`, the owning module;
- the curated `moira` root;
- `moira.facade`; and
- `moira.sky.visibility`.

`Moira.physical_visibility_assessment()` and
`Moira.physical_visibility_event()` expose the same required pack configuration
and forward the complete physical policy and event search policy. No facade
field is reconstructed, dropped, or replaced with a different default.

The Phase 4 Jones/Paranal component remains outside this public-contract
commit. Phase 5 neither promotes its Phase 4-only symbols nor combines that
component with the sea-level physical visibility pack.

## REST contract

Two additive operations are admitted:

- `POST /v1/visibility/physical-assessment`
- `POST /v1/visibility/physical-event`

The requests expose the complete engine-owned atmosphere, directional/SQM/
Bortle background variants, modeled background components, directional
horizon, physical policy, and search policy. Pydantic models reject unknown
fields and non-finite values.

No request accepts a directory, path, or pack configuration. Deployment owns
those values through:

- `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY`
- `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_MANIFEST_SHA256`

The manifest pin is optional. The directory is required only when either
physical route is called. A missing or invalid server-side resource setting
returns HTTP 503 with `server_not_configured` in the standard Moira error
envelope.

The response contract mirrors all fields in the engine's 16 public result and
receipt dataclasses, including table format, model and engine-contract
identity, compatibility and manifest receipts, validity domain, dependency
state, atmosphere, observer protocol, background, target, threshold, error
budget, horizon, ephemeris, solver, sensitivity, and component inventory.

## Compatibility boundary

The following legacy operations remain exact:

- `POST /v1/visibility/assessment`
- `POST /v1/visibility/tonight`
- `POST /v1/heliacal/visibility-event`

Phase 5 adds no physical field to their request or response models. Tests bind
the ordered OpenAPI property inventories for the legacy assessment and general
visibility-event request/response schemas. The Phase 5 transport inventory was
re-audited; no edit to the phenomena models, services, serializers, or router
was required because the new operations live under the dedicated visibility
route family and the phenomena route remains the legacy contract.

## Verification receipt

The final clean staged-snapshot run collected 69 focused public-contract,
server, and legacy-compatibility tests:

```text
69 passed
```

It covered:

- public export identity and `Moira` delegation;
- full nested request-to-policy reconstruction;
- server-only pack configuration and rejection of client paths;
- typed missing-pack assessment and event responses;
- field-for-field parity for all 16 engine result/receipt dataclasses;
- nested pack identity, horizon, solver, and sensitivity serialization;
- exact legacy schema preservation; and
- OpenAPI discovery for both new routes.

The generated REST inventory was synchronized from `create_app().openapi()` and
records:

```text
440 paths
440 operations: GET 35, POST 405
436 versioned /v1 paths
```

Targeted Ruff checks pass for the Phase 5 modules and tests, with only the
repository's established root/facade re-export categories (`E402` and `F811`)
excluded. The generated REST reference check also passes. The test snapshot
was created from the repository index over the starting engine revision, so
none of the uncommitted Phase 4 Jones work or unrelated validation-assurance
work was present or available to satisfy imports.

## Durable boundary

Phase 5 is complete. Phase 6 starts with benchmarking only; native work remains
optional and requires evidence that the admitted Python implementation misses
the recorded performance budget. Phase 7 remains responsible for a matching
Paranal scenario pack, full scientific validation/admission, release material,
and downstream website adoption.
