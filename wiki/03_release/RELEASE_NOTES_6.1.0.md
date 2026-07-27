# Moira 6.1.0 - Hellenistic Contract Stabilization

**Release date:** 2026-07-27

**Public upgrade path:** 6.0.0 to 6.1.0

Moira 6.1.0 adds the dated monthly-profection contract needed by timeline
consumers and hardens the completed Hellenistic boundary established in 6.0.0.
It does not reopen Hermetic star attribution or geometry, Decennial L3/L4,
Triacontaeteris, or Valens distribution interpretation.

## Why This Is A Minor Release

The release adds typed chronology and transport fields while preserving the
admitted 6.0 Hellenistic computations. It also removes an unadmitted Decennial
request selector and tightens invariant enforcement. The result is a new
backward-compatible capability for callers using valid 6.0 contracts, with
fail-closed rejection for callers that were sending the former speculative
deep-method option.

## Dated Monthly Profections

`profection_chronology(...)` now constructs twelve contiguous, half-open
monthly intervals between exact consecutive civil anniversaries. The sole
admitted interval policy is:

`equal_twelfths_of_civil_anniversary_year`

Each receipt preserves:

- the civil timezone;
- the timezone-data source and any available version;
- the interval and ambiguity policies;
- the exact query, annual-start, and annual-end UTC instants;
- matching Julian Day values;
- twelve ordered interval boundaries;
- the active month index;
- each month’s profected longitude, sign, and domicile lord; and
- whether an explicit repeated-time resolution was actually applied.

The method is identified as `computational_projection`. It is not represented
as Valens IV.28’s separate day-Sun/night-Moon distance method, twelve fixed
30-day periods, a 365.25-day quotient, or twelve civil-calendar months.

## Civil-Time Failure Semantics

REST callers may supply an explicit IANA `civil_timezone` after normalizing
their datetime values to UTC. Direct Python callers may instead retain the
timezone attached to the natal datetime.

Civil anniversaries preserve the natal local wall clock:

- a February 29 nativity requires `february_28` or `march_1`;
- a wall time that falls in a daylight-saving gap fails closed;
- a repeated wall time requires `earlier_occurrence` or `later_occurrence`;
- Moira never silently moves a nonexistent time or guesses a fold; and
- the exact natal instant remains the age-zero anchor.

Named IANA lookup uses Python’s standard-library `zoneinfo` interface. Moira
does not download timezone data or claim a database version the host does not
expose. A host without the requested IANA entry receives an explicit error.

## Unified Profile Hardening

`HellenisticChartProfile` now composes the chronology receipt and rejects
cross-component contradictions, including:

- datetime and Julian Day disagreement;
- non-Whole-Sign composition;
- invalid angles or sect contradictions;
- reordered or incomplete Classic Seven bodies;
- aspect identity errors;
- overlapping foundational-lot evaluated/unresolved partitions;
- missing or policy-inconsistent chronology;
- Decennial sect mismatch;
- Zodiacal Releasing policy mismatch; and
- inclusion, exclusion, method, source, or provenance disagreement.

The profile method identifier advances to the chronology-aware v2 contract.

## Decennial L1/L2 Boundary

The admitted Decennial engine remains complete at L1/L2:

- request models accept levels 1 and 2 only;
- no deep-subdivision request selector or OpenAPI enum is exposed;
- direct engine construction rejects non-`None` deep methods;
- aggregate and profile vessels cannot contain L3/L4 periods; and
- response `deep_subdivision_method` receipts remain present only as
  compatibility fields fixed to `null`.

Sending the former request field is a validation error, not an inert option.

## Closed Exclusions

The following are settled exclusions from this release and are not unfinished
6.1 work:

- Hermetic fixed-star attribution;
- Hermetic tropical/rising projection as a product capability;
- the removed `decan_hours()` night-hour experiment;
- Decennial L3/L4 and named Valens/Hephaistio deep methods;
- Triacontaeteris;
- Valens distribution scoring or interpretation; and
- synthetic Hellenistic condition scores.

The source-reconstructed Gundel/Harley names and planetary faces remain
available only through the direct research module. They are absent from
curated root, classical, facade, REST, and OpenAPI product surfaces.

## Validation

Release hardening covers:

- source-owned Hellenistic goldens;
- generated capability and API inventories;
- engine, root, classical, facade, serializer, REST, and OpenAPI parity;
- Decennial request-depth and response-sentinel enforcement;
- Hermetic public-route absence;
- chronology continuity, UTC/JD agreement, DST gaps and repeats, leap policy,
  active-boundary ownership, and timezone transport;
- unified-profile adversarial invariants;
- public API and doctrine drift; and
- active-document terminology regression.

The base runtime remains standard-library plus the required native extension;
`[project.dependencies]` remains empty.

## Installation

```text
moira-astro==6.1.0
```

For the optional FastAPI server:

```text
moira-astro[server]==6.1.0
```

Read `COMPATIBILITY_NOTES_6.1.0.md` before upgrading a typed REST client or a
consumer that persists rendered chart responses.
