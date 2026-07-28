# Compatibility Notes - Moira 6.1.0

## Upgrade Boundary

This document covers the public upgrade from `6.0.1` to `6.1.0`. Consumers
upgrading directly from `6.0.0` also inherit the complete 9,974-name asteroid
identity registry documented in the 6.0.1 notes.

Version 6.1.0 is additive for valid profection and unified-profile consumers.
It preserves the valid explicit-null form of the former Decennial deep-method
field while continuing to reject every named deep method.

## Birth Data and Cached Charts

Birth records remain input data: datetime, location, and the application's
existing chart preferences. No database schema migration is required solely
for Moira 6.1.0.

Applications that persist or cache computed chart responses should invalidate
or refresh those derived responses after upgrading. Users do not need to
re-enter birth data; they only need to refresh or regenerate their charts so
the new chronology and provenance receipts are present.

## Profection API Additions

The dated schedule accepts:

- `civil_timezone`;
- `interval_policy`, fixed to
  `equal_twelfths_of_civil_anniversary_year`;
- `ambiguous_time_policy`, either `earlier_occurrence` or
  `later_occurrence`; and
- the existing explicit February 29 anniversary policy.

The response adds exact UTC and Julian boundaries, twelve ordered intervals,
the active month, and typed timezone/method provenance. Generated REST clients
should be regenerated from the 6.1.0 OpenAPI document.

The annual-only calculation remains available without constructing dated
intervals.

### Timezone requirements

An explicit IANA `civil_timezone` resolves through standard-library `zoneinfo`.
The host must provide the requested IANA entry. Moira does not download
timezone data, silently substitute a fixed offset, or claim an unavailable
database version.

Repeated local anniversary times require an explicit ambiguity policy.
Nonexistent local anniversary times fail closed.

## Decennial Request Compatibility

The admitted request contract supports levels 1 and 2 only.

The deprecated `deep_subdivision_method` request field has a null-only schema:

- omission is accepted;
- explicit JSON `null` is accepted;
- `"valens"`, `"hephaistio"`, and every other string are rejected; and
- no `DecennialDeepSubdivisionMethod` OpenAPI enum is exposed.

This preserves valid 6.0/6.0.1 generated-client payloads that serialize the
default as `null` without reopening the unadmitted L3/L4 policy.

Response models retain `deep_subdivision_method` as a compatibility receipt
whose only valid value is `null`.

## Unified Hellenistic Profile

The profile carries dated profection chronology when the required query context
is supplied, and its method identifier advances to the v2 contract.

Consumers that compare method identifiers or deserialize exhaustive
provenance models must admit the new identifier and chronology policy fields.

The profile continues to exclude Firdaria, medieval almutens, later electional
rules, unscoped primary-direction branches, Hermetic product geometry and star
attribution, Decennial L3/L4, Triacontaeteris, and interpretive scoring.

## Aspect and Pattern Additions

`motion_state` is an additive aspect response field. Callers using exhaustive
generated response models should regenerate them.

Whole-sign and zodiacal longitudes are normalized consistently at the
`0`/`360` seam. Results exactly on a sign boundary may therefore differ from a
consumer's former floating-point edge classification while remaining within
the same declared half-open sign policy.

`AspectGraphNode.aspect_counts` is the preferred immutable name.
`family_counts` remains available for compatibility.

## Small-Body Identity Changes

Unified body-resolution surfaces now fail closed when an unqualified name
matches both an asteroid and a comet. The current collisions are `Halley` and
`Encke`.

Use one of:

- a family qualifier, such as `asteroid:Halley` or `comet:Halley`;
- the canonical comet designation, such as `1P/Halley` or `2P/Encke`; or
- an explicit family argument where the Python surface provides one.

Dedicated asteroid and comet routes remain family-scoped. Their short inputs
do not become globally unique aliases.

The engine wheel contains identity and release metadata, not the external BSP
shards. Retain or install the exact matching catalog release before expecting
position capability. The packaged metadata manifests now carry the exact
release versions and hashes named by the asteroid and comet identity receipts;
their presence alone still does not satisfy installed-shard readiness.

## Python 3.10 Optional Server

The optional server remains supported on Python 3.10. Server enums now use
Moira's compatibility `StrEnum` boundary rather than importing the Python
3.11-only standard-library class directly.

Deployment acceptance should import `moira_server`, construct the application,
and generate OpenAPI in the actual minimum-version environment.

## Recommended Migration Sequence

1. Install `moira-astro==6.1.0` in a disposable or staging environment.
2. Regenerate REST/OpenAPI client models.
3. Retain omitted or explicit-null Decennial deep-method fields; remove every
   named deep-method value.
4. Qualify ambiguous small-body names on unified routes.
5. Ensure the host resolves every IANA zone used by dated profections.
6. Run chart/profile, aspect, small-body, and cache-refresh tests.
7. Refresh derived chart responses from unchanged birth records.
8. Promote the exact staged artifact.
9. Verify installed version, health, OpenAPI, one dated profection boundary,
   one ambiguity failure, and one qualified small-body request.

## Upgrade Pin

Base engine:

```text
moira-astro==6.1.0
```

Optional server:

```text
moira-astro[server]==6.1.0
```
