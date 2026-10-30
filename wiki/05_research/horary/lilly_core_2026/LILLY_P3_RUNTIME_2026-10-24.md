# Lilly P3 Moon and considerations runtime

Date: 2026-10-24. Governing specification:
[P3 decisions](LILLY_P3_MOON_CONSIDERATIONS_DECISIONS_2026-10-23.md) and
[photograph collation](LILLY_P3_SOURCE_COLLATION_2026-10-23.md).

Status: **additive finite engine runtime implemented**, with direct submodule
APIs in [horary_moon.py](../../../../moira/horary_moon.py) and
[horary_considerations.py](../../../../moira/horary_considerations.py).
The fixed profile is `lilly_1647_moon_considerations_v1`. This is evidence for
the named rules, not complete judgement or predictive admission. The historical
packet and fixture admission flags remain unchanged.

The existing horary/perfection v1 and generic VOC contracts, P2 implementation,
shared numerical services, native code, facade and REST are unchanged. No
website, Workspace, UI, release, deployment or repository-setting work is part
of this implementation.

## Lunar trace and source binding

`LillyMoonTrace` is frozen. It retains all supplied exact contacts, application
episodes and classical sign crossings, including excluded contact evidence.
Its P2 `LillySnapshotContext` needs an explicit epoch label and UT1 JD.
Provenance names the physical model or an explicitly synthetic source. Supplied
trace records are caller assertions under that provenance; construction does
not independently establish their astronomy.

The three coverage receipts distinguish past contacts, exact contacts and
application episodes. They retain interval, completion state, reasons and
assurance. Complete future coverage must contain the query through the latest
possible sign exit before absence of connection can be asserted. Partial work
does not become a negative result. A known separation premise requires evidence
IDs; an empty bounded past scan leaves that premise unknown.

`lilly_moon_sequence` retains every eligible contact in chronological groups.
Exact point ties remain simultaneous. Overlapping uncertainty envelopes form
order-unresolved components; this does not assert that all members are pairwise
simultaneous. Repeated contacts survive. A partial past or unresolved last group
does not certify a unique last separation. Last/next planets receive no
automatic additional significator roles.

## Numerical trace builder

`trace_lilly_moon` accepts a normalized-longitude callable `(body,jd_ut1)`, an
explicit provenance record, context and `LillyMoonSearchPolicy`. Request-local
position caching is bounded. The retained policy exposes interval lengths,
step, root/angular/rate/curvature controls, numerical velocity step and work
limits. Defaults are four days before and four after the query; these are
resource choices, not astrological durations. The allowed study is at most
sixteen days.

The existing private adaptive contact scanner supplies exact/orb crossings and
stationary touches. The new builder partitions orb windows at exact contacts,
relative-rate roots and both bodies' verified sign crossings. Each qualified
open episode requires decreasing absolute aspect residual, strict P2 selected
summed-moiety membership and the corresponding whole-sign aspect relation.
Only relative finite differences of the same longitude product are used;
the separate astrometric speed field is not substituted for that derivative.

A touch of a sign boundary is not an ingress. The next lunar exit is asserted
only after its ingress scan completes. If ingress, orb/exact or relative-motion
partitioning is unresolved, derived candidate episodes remain explicitly
unverified and cannot establish an application connection. Their boundaries
and IDs stay available. Valid earlier evidence remains available when later
work reaches a budget limit. Per-scan receipts expose evaluations,
subdivisions, completed subintervals and reasons; the trace also retains the
actual position-evaluation count and the full numerical policy.

Event envelopes use four root tolerances or the floating-point time-resolution
floor, whichever is larger. These are declared numerical-resolution envelopes,
not statistical uncertainties or interval-enclosure certificates. Caller-supplied
uncertainty remains distinct from this solver policy. Finite adaptive completion
is not proof that an arbitrary function has no extra unsampled roots. Callback,
kernel and resource errors propagate; they are not classified as no connection.
Work-budget exhaustion instead produces partial coverage with explicit reasons.

`lilly_moon_at` is the canonical astronomical adapter. It requires an explicitly
opened `SpkReader` and performs no kernel acquisition. It uses the existing
apparent geocentric tropical true-ecliptic/equinox-of-date longitude product,
canonical UT1-to-TT conversion and SPK TT-to-TDB boundary. Light time,
aberration, deflection, precession and nutation stay owned by planetary
reduction. Provenance records the actual planetary/lunar product IDs, kernel
SHA-256, query UT1/TT epochs and canonical Delta-T identity. Historical source
clock/calendar conversion is still a separate admission.

## Explicit VOC definitions

`lilly_void_of_course(trace, definition=...)` requires a `LillyVOCDefinition`:

- `EXACT_BEFORE_INGRESS`: a contact envelope wholly after the query and before
  the earliest sign exit disproves void status. Query/ingress overlap is retained
  as boundary evidence. No-connection requires complete relevant coverage and
  a known separation premise.
- `APPLICATION_IN_REMAINING_SIGN`: a verified open episode with a definite
  intersection with the remaining sign disproves void status. Possible-only
  overlap or an unverified candidate remains unresolved. Empty exact-contact
  output does not establish absence of application.

There is no default definition and no generic `traditional` alias. An explicitly
unmet separation premise makes the p.112 proposition not applicable. Missing
history remains unknown unless an independently established connection already
disproves no-connection. A query coincident with a possible lunar ingress leaves
the sign ordering unresolved. Results preserve all connection, boundary,
excluded-evidence IDs and reasons. The unique historical reading of
application/forthwith remains open.

## Contextual considerations

The consideration functions take the same explicit P2 snapshot context. Missing
positions and qualitative inputs remain unknown at the affected proposition.
Known negatives survive unrelated missing inputs. Outputs keep raw trigger,
qualification, qualified state, scope, observations, source attribution and
evidence separately.

`LillyQualitativeEvidence` binds proposition kind, actual subjects/roles, epoch,
source, explanation and supporting evidence IDs. Reusing an assessment as a
different proposition is rejected, even at the same epoch. No bare boolean or
dignity sum establishes youth, corresponding age, very strong principals,
unfortunate/impeded testimony, late Moon or balanced testimony. Actual principal
role identities remain distinct even when both happen to have the same planet.

| Surface | Behavior |
|---|---|
| `lilly_early_ascendant` | `[0,3)` degree trigger; very-young AND descriptive correspondence exception |
| `lilly_late_ascendant` | `[27,30)` trigger; age correspondence OR certain timed-event figure exception; a precisely timed question is not that event-figure exception |
| `lilly_late_moon` | Qualitative late assessment, with separate Gemini/Scorpio/Capricorn emphasis; no invented numerical cutoff |
| `lilly_via_combusta` | Explicit `[195,225)` membership and `as_some_say` attribution; independent of late-Moon testimony |
| `lilly_saturn_considerations` | Separate first/seventh clauses, with source-qualified retrograde emphasis and different scopes |
| `lilly_artist_warning` | P.122 cusp/lord alternatives with the explicit non-seventh-topic eligibility condition |
| `lilly_seventh_lord_warning` | P.123 unfortunate/fallen/malefic-term alternatives, consuming P2 condition evidence without inheriting another clause's topic exception |
| `lilly_solar_proximity` / `lilly_first_ruler_combust` | Same-sign combustion, distinct 17-minute/8:30/17-degree thresholds, separate boundary classes, correct ruler/epoch binding and Sun-self non-applicability |
| `lilly_hour_agreement` | Separate identity/triplicity/nature routes under a bound question/context/observer receipt or a labelled documentary assertion |
| `lilly_testimony_balance` | Source-qualified balance/deferral evidence; arbitrary testimony counts are not an admitted ontology |
| `lilly_lunar_orientation` | Lunar solar-cycle oriental/occidental halves with conjunction/opposition boundaries; no visibility inference |

Solar distance computation exposes its derived floating-point roundoff envelope
in arcminutes. A threshold falling in that tiny numerical envelope remains a
boundary; it is not moved into a positive interior band. This is numerical
representation handling, not a new source orb or endpoint default. A known
different-sign condition still establishes absence of combustion independently
of an unresolved cazimi threshold. The printed ten-degree contradiction remains
quarantined in the unchanged source packet.

`adapt_horary_planetary_hour` accepts the existing validated hour vessel,
rechecks its unequal-hour geometry, and requires matching question, epoch and
observer. Derived hour sect must agree with any known snapshot sect. A known
receipt sect remains usable when snapshot sect was missing. Documentary Mars-hour
examples retain source-asserted origin and unspecified historical epochs.

VOC qualifications retain raw VOC, named-sign and principal-strength facts as
separate states. They never erase raw void status or produce an outcome.
Unknown raw VOC keeps qualification applicability unknown. No global chart
invalidity, confidence, strength or yes/no aggregator is exposed.

## Example and validation scope

```python
from moira.horary_reception import LillySnapshotContext
from moira.horary_considerations import (
    LillyQualitativeEvidence, LillyQualitativeKind, lilly_early_ascendant,
)
from moira.horary_moon import LillyP3State

epoch = LillySnapshotContext("synthetic-didactic-example", is_day_chart=None)
youth = LillyQualitativeEvidence(
    epoch, LillyQualitativeKind.VERY_YOUNG, LillyP3State.PRESENT, ("querent",),
    "synthetic-source-assessment", "Didactic premise, not a numerical age cutoff",
    ("example-youth-premise",),
)
result = lilly_early_ascendant(2, context=epoch, very_young=youth)
# Description evidence is missing, so the qualified caution remains unknown.
```

The regression suites compare production functions with the previously prepared
193-fixture bundle, preserving its historical non-admission fields. Additional
tests cover analytic linear trajectories and tangencies, all directed classical
contacts, repeated/tied events, partial ingress scans, unresolved episode
premises, bounded work, source exceptions, unknowns, immutable receipts and
binding failures. Local DE441 tests at J2000 and a 2024 epoch independently
project the canonical equatorial Cartesian product and perform a separate
uniform-bracket/bisection contact search. These are geometric/search invariants,
not a claim of independent ephemeris accuracy or predictive validation.

P4 still owns complete perfection-route chronology, mechanism precedence,
continuation and multi-window dependencies. Historical chart reconstruction,
symbolic timing, a complete testimony ontology, and latitude/speed/visibility
judgement remain separately admitted work. Root/facade/REST expansion also
requires its own scoped contract; no published v1 meaning changes here.
