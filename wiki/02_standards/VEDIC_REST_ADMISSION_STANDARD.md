# Vedic REST admission and policy receipts — VED-005

**Scope:** the 30 existing Vimshottari, alternate-dasha, Shadbala, Vedic
dignity, Sade Sati and Vedic profile routes. This is an engine/server contract;
website adoption, publication, release and deployment are separate actions.

## Governing object and ownership

REST admits typed inputs and selects existing computation policies. Engine
registries own ayanamsas, house identities, dasha lords, year bases and
calculations. The server must not reconstruct astronomy, invent eligibility,
or rely on an ambient reader to complete an engine-owned calculation.

The [validation receipt](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md)
records the reproduced defects and checks. Numerical/historical authority is
distinct from admission, reader ownership and transport fidelity. This package
changes no classical rules, source tables, numerical formulae or native code.

## Route and input coverage

| Family | Routes | Admitted inputs and policies |
| --- | ---: | --- |
| Vimshottari | 5 | Civil natal/current datetimes; strict integer levels 1–5; registered ayanamsa or default; `savana_360`/`julian_365.25` or default |
| Ashtottari/Yogini | 9 | Strict finite Moon longitude/JD; levels 1–4; four existing year bases; registered ayanamsa; strict Ashtottari bypass Boolean and optional sign index 0–11; valid period tree |
| Shadbala | 6 | Civil datetime, strict finite observer, supported house code/name, registered ayanamsa, optional classical Hora lord and nested policy |
| Vedic dignity | 7 | Classical planet identity; strict finite supplied longitude/map values, or admitted chart context; direct provenance label versus chart conversion policy kept distinct |
| Sade Sati | 2 | Strict finite natal Moon/Saturn longitudes; civil start/end timestamps with start before end; registered window ayanamsa |
| Vedic profile | 1 | Strict finite observer, civil timestamps, strict inclusion/node Booleans and dasha depth; preflight of selected components; explicit policy receipt |

Extra fields are forbidden. JSON numbers are admitted for finite floating
inputs, including integer-valued JSON numbers. Booleans, numeric strings, NaN
and infinities are rejected. Integer/sign fields reject Booleans, floats and
strings. Boolean switches accept JSON Booleans only.

Civil dates accept timezone-aware ISO timestamp text or aware Python datetime
objects. Unix epoch numbers and numeric timestamp strings are rejected before
coercion, including through the Vedic bundle and the existing Panchanga chart
entry point. Equivalent timezone offsets preserve the same instant. A
Vimshottari current instant cannot precede birth. Engine-owned cycle/date
coverage checks remain authoritative.

Longitudes retain existing wrapping semantics. Dignity maps may contain a
subset of the seven classical planets; missing entries are not filled with
zero. REST rejects unknown or nodal keys. The underlying engine's direct-map
behavior is unchanged. This intentionally replaces the old relationship
route's silent skip of unknown keys.

## Alternate dasha period trees and frame selection

An incoming period identifies an admitted system and a lord in that system's
existing registry. Its level is 1–4 and its finite duration is positive.
Children retain the system, advance one level, are ordered/nonoverlapping and
are contained by the parent. Partial children are allowed; neither complete
coverage nor missing children are fabricated. Each node admits at most eight
children, the number of lords in each admitted system; one incoming level-1
tree therefore has at most 585 nodes.

Interval comparisons use `1e-6` Julian day, the existing alternate-dasha
interval-validation tolerance. Generated child endpoints accumulate binary64
rounding. Admission never snaps or rewrites supplied endpoints. Tests admit
generated Ashtottari/Yogini trees and reject excursions beyond this margin,
out-of-order/overlapping children, foreign systems and non-finite duration.

For chart-backed sequences/profiles, an omitted nested policy uses the
requested chart ayanamsa, preserving default year basis and Ashtottari bypass.
A supplied policy must agree with the chart ayanamsa. Returned sequence
policy and chart provenance identify the same selected frame. Direct routes
retain their default policy and caller-owned supplied input contract.

This adds no Ashtottari applicability calculation. Existing bypass and the
engine's rejection of insufficient eligibility context are preserved.

## Shadbala reader and applied policy

Chart/house derivation and Shadbala computation use the same owning engine.
The service calls the existing reader-bound `engine.shadbala(...)`; a
discovered kernel works without an independently configured global reader.
An outer test/request reader must not replace that engine's reader.

All six HTTP responses carry `policy_receipt`. Full-response children share
the same receipt from one support-truth derivation. Fields are:

- `requested_ayanamsa_system`, optional `policy_ayanamsa_system`,
  `applied_ayanamsa_system` and `ayanamsa_precedence` (`policy` or `request`);
- `requested_house_system`, canonical `resolved_house_system`, engine-owned
  `effective_house_system` and `polar_fallback_applied`;
- optional caller-supplied `hora_lord` (`None` preserves engine behavior).

Nested Shadbala policy retains precedence over the top-level ayanamsa.
Supported house codes and names/aliases resolve to the engine registry code.
Unknown systems are rejected before chart work. Existing polar fallback
remains available and its effective house system is disclosed. Numerical
result/profile service functions and serializers remain usable independently;
a serializer without request context leaves its optional receipt `None`.

## Vedic profile composition

The profile preflights selected child requests and chart identities before
astronomy dispatch and constructs only selected components. All supplied
fields still obey their declared admission schema. An invalid Hora lord is
rejected at the request boundary even when Shadbala is omitted.

Independent Panchanga/Shadbala ayanamsa overrides remain admitted. The bundle
does not silently force a common frame. Its `policy_receipt` records:

- the requested top-level ayanamsa;
- `component_ayanamsa_systems` for evaluated Panchanga, Shadbala and/or dasha;
- `mixed_ayanamsa_frames`, computed from evaluated component frames;
- the applied dasha year basis when dasha is evaluated;
- explicitly supplied `inactive_inputs` belonging to omitted components.

The ordinary chart section retains its existing chart semantics and is not
relabeled as a sidereal calculation. Omitted components remain `None` and are
absent from `included_sections`. A declared policy for an omitted component
is never reported as applied.

## Compatibility, errors and remaining boundaries

For admitted valid inputs, existing calculation and component-route parity
are retained. Request compatibility intentionally tightens for previously
coerced values, unknown dignity keys/lords, malformed trees and unknown house
systems. Clients must send actual typed JSON values. Receipts are additive
response fields; they do not replace numerical result fields.

Malformed requests and invalid selected policy identities produce the existing
422 `validation_error` / `input_validation` envelope, with the matching
`X-Request-ID`, before astronomy dispatch. Resource/coverage errors retain
their separate engine/server meaning.

This finite admission package does not claim every Vedic route was audited or
every historical numerical component was independently recertified. Range,
response-size and execution-budget work remains a separately scoped operational
frontier: Sade Sati has no additional HTTP span cap, and current Vimshottari
still generates its existing bounded depth-5 sequence. This repair does not
silently reduce admitted date ranges or depth. Future changes must name their
budget policy, coverage/compatibility effect and validation evidence.
