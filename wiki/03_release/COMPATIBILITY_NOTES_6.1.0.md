# Compatibility Notes - Moira 6.1.0

## Upgrade Boundary

This document covers the public upgrade from `6.0.0` to `6.1.0`.

The release is additive for valid profection and unified-profile consumers.
It deliberately rejects the former unadmitted Decennial deep-method request
field. It does not change stored birth-data requirements.

## Birth Data And Cached Charts

Birth records remain input data: datetime, location, and the application’s
existing chart preferences. No database schema migration is required solely
for Moira 6.1.0.

Applications that persist or cache computed chart responses should invalidate
or refresh those derived responses after upgrading. Users do not need to
re-enter birth data; they only need to refresh or regenerate their charts so
the new chronology and provenance receipts are present.

## Profection API Additions

The dated schedule accepts:

- `civil_timezone`;
- `interval_policy`, currently fixed to
  `equal_twelfths_of_civil_anniversary_year`;
- `ambiguous_time_policy`, either `earlier_occurrence` or
  `later_occurrence`; and
- the existing explicit February 29 anniversary policy.

When a dated schedule is requested, the response includes a typed chronology
with exact UTC and Julian boundaries, twelve ordered intervals, and an active
month index. Callers with generated models should regenerate them from the
6.1.0 OpenAPI document.

The annual-only calculation remains available without constructing dated
intervals.

## Timezone Requirements

An explicit IANA `civil_timezone` is resolved through standard-library
`zoneinfo`. The host must provide the requested IANA entry. Moira does not
download timezone data, silently substitute a fixed offset, or claim an
unavailable database version.

If the host lacks the entry, the call fails with a clear validation error.
Direct callers may omit `civil_timezone` and use the timezone-aware natal
datetime supplied by the application.

Repeated local anniversary times now require an explicit ambiguity policy.
Nonexistent local anniversary times fail closed.

## Decennial Requests

The admitted request contract supports levels 1 and 2 only.

Remove `deep_subdivision_method` from request payloads. The 6.1 request schema
does not expose that property or a `DecennialDeepSubdivisionMethod` enum.
Because request models are strict, sending the former field returns
`422 validation_error`.

Response models retain `deep_subdivision_method` as a compatibility receipt
whose only valid value is `null`. This prevents an unnecessary response-shape
break while making it impossible to represent an admitted deep method.

## Unified Hellenistic Profile

The profile now carries the dated profection chronology when the required
query context is supplied. Its method identifier advances to the v2 contract.

Consumers that compare method identifiers or deserialize exhaustive provenance
models must admit the new identifier and chronology policy fields.

The profile still excludes:

- Firdaria;
- medieval almutens;
- later electional rules;
- unscoped primary-direction branches;
- Hermetic star attribution and product geometry;
- Decennial L3/L4;
- Triacontaeteris; and
- interpretive or synthetic scoring.

## Removed Or Rejected Inputs

No curated 6.0 Hermetic symbol is restored.

The following remain invalid:

- `decan_hours`;
- dormant Hermetic route payloads;
- Decennial levels above 2;
- named Valens or Hephaistio deep-subdivision selectors; and
- `include_timelord_distributions`.

Do not treat their absence as a missing 6.1 feature.

## Database And Persistence Guidance

Moira does not own the application database and this release does not require
altering stored natal records.

For applications that cache derived output:

1. deploy the 6.1.0 engine and regenerate typed client contracts;
2. invalidate cached 6.0 computed chart/profile payloads;
3. retain the underlying birth data unchanged;
4. ask users to refresh charts, or regenerate them automatically; and
5. persist the new 6.1 chronology/provenance response if the application
   normally caches computed output.

## Recommended Migration Sequence

1. Install `moira-astro==6.1.0` in a disposable or staging environment.
2. Regenerate REST/OpenAPI client models.
3. Remove the Decennial deep-method request property from callers.
4. Ensure the host can resolve every IANA zone used by dated profections.
5. Run chart/profile contract and cache-refresh tests.
6. Refresh derived chart responses from unchanged birth records.
7. Promote the exact staged artifact.
8. Verify version, health, dated profection boundaries, and one ambiguous-time
   failure case in the deployed environment.

## Upgrade Pin

Base engine:

```text
moira-astro==6.1.0
```

Optional server:

```text
moira-astro[server]==6.1.0
```
