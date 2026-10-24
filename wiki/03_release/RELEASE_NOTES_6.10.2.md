# Release Notes - Moira 6.10.2

**Release date:** 23 October 2026.

This bounded patch follows published 6.10.1. It does not include unrelated
unreleased geodetic, eclipse or house changes on the development main branch.

## Primary-direction chronology

- Natal Solar Rate now passes the validated natal Sun speed to distributor
  entry/exit boundaries as well as participating events.
- `POST /v1/primary-directions/time-keys` converts already solved arcs through
  the existing six engine keys without repeating the geometry search.
- Each result preserves one matching key, age, perfection JD UT1 and calendar
  timestamp. Dynamic RA and Longitude use real ephemeris bisection and refuse
  unavailable resources; no static key or analytical estimate replaces them.
- The batch shares the primary-directions UT1 clock and returns its natal
  solar rate. It accepts at most 1,024 named arcs and 2,048 key projections,
  refuses duplicate ids/keys and invalid or non-finite arcs, and reuses repeated
  identical arc/key calculations within a request.

## Validation boundary

Focused kernel-backed tests exercise all six keys, zero-arc origin, dynamic
forward-motion residuals, age/JD/calendar invariants, natal-rate boundaries,
input budgets and failure propagation. This is bounded invariant and transport
evidence; it is not external validation of predicted biographical events.

See [compatibility notes](COMPATIBILITY_NOTES_6.10.2.md).
