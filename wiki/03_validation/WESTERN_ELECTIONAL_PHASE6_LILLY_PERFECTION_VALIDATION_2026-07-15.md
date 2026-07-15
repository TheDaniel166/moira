# Western Electional Phase 6 — Lilly Perfection Validation

Date: 2026-07-15  
Profile: `lilly_1647_perfection_v1`  
Status: admitted as a bounded engine, facade, and REST product

## Computational product

The admitted object is a time-ordered trace of exact traditional-planet
aspects, stations, and sign ingresses over a caller-selected UT1 interval,
followed by six William Lilly doctrine witnesses:

1. direct perfection;
2. translation of light;
3. collection of light;
4. prohibition;
5. refranation;
6. frustration.

It is not a complete electional judgement, a score, a recommendation, or a
generic traditional-perfection system.

## Primary source audit

The governing source is William Lilly, *Christian Astrology* (London, 1647),
Books I-II, Wellcome Collection scan identifier `b30338724`. The user-supplied
research copy is external to the repository and was not copied into package
data or documentation.

The facsimile has no usable text layer, so target pages were rendered and
visually checked. PDF page 134 corresponds to printed page 99. The governing
mapping is therefore:

| PDF page | Printed page | Verified object |
|---:|---:|---|
| 145 | 110 | beginning of prohibition |
| 146 | 111 | bodily/aspectual prohibition, refranation, translation |
| 147 | 112 | reception and beginning of frustration |
| 148 | 113 | frustration completed; planetary orb context |
| 160 | 125 | direct modes and translation introduction |
| 161 | 126 | received translation and collection |

No facsimile image or long quotation is committed. Runtime source references
identify the printed pages and scan identifier.

## Fixed computational policy

- seven traditional planets only;
- UT1 input with Moira's internal TT ephemeris conversion;
- apparent geocentric true-ecliptic-of-date longitude with the canonical
  astrometric geocentric longitude rate exposed by `planet_at`;
- tropical zodiacal Ptolemaic aspects;
- exact directional aspect branches;
- admission within summed canonical Lilly 1647 planetary moieties;
- a 31-day maximum trace interval;
- event ties within one second are indeterminate;
- prior significator sign ingress makes direct perfection indeterminate;
- translation requires a swifter translator, separation from the first
  significator, application to the second, reception by house, active
  Dorothean triplicity, or Egyptian term, and no earlier intervening planetary
  contact;
- collection requires significators that do not behold one another by sign,
  application to one slower collector, and reception of that collector by
  each significator in any admitted essential dignity;
- prohibition requires the same swifter third planet to reach both
  significators before their intended perfection;
- frustration is a prior conjunction of the heavier significator with a third
  planet and does not duplicate a complete prohibition sequence;
- refranation requires the swifter applying significator to station
  retrograde before exactitude.

The Egyptian-bound and sect-active-triplicity choices are Moira-owned profile
bindings because the perfection passages name term and triplicity without
selecting a competing table. They are exposed in `LillyPerfectionPolicy` and
the REST response rather than hidden.

## Public surface

- `moira.classical_perfection.lilly_perfection_at(...)`
- package-root `lilly_perfection_at(...)`
- `Moira.lilly_perfection_at(...)`
- `POST /v1/electional/western/classical-perfection`

The REST request fixes the profile id, types both significators as traditional
planets, requires a strict sect boolean, rejects identical significators, and
enforces the same interval bound as the engine. The response exposes policy,
initial states, all events, six witnesses, reception bases, source references,
reader provenance, and explicit non-judgement/non-scoring truth.

## Verification evidence

All commands used the repository `.venv`, Python 3.14.3,
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`.

Focused doctrine, REST, and kernel slice:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_classical_perfection.py tests\server\test_server_classical_perfection_routes.py tests\integration\test_classical_perfection_de441.py -q
```

Result at admission: 19 passed. The synthetic cases isolate all six forms and
their boundaries, including canonical Jupiter/Saturn moieties, incomplete
prohibition, intervened translation, sign-level beholding for collection,
wrong exact-aspect branch selection, sign ingress, and deterministic event
ordering. The integration case exercises the discovered local `de441.bsp`
through the real planetary reduction and station paths and verifies ordered,
unique exact-aspect/ingress chronology. This is regression and invariant
evidence, not empirical validation of astrological claims.

Curated public-surface governance:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_western_electional.py tests\unit\test_api_surface_adversarial_audit.py -q -k "not built_wheel_matches_source_public_surface"
```

Result: 86 passed. The local wheel-build test was explicitly excluded and no
wheel was built or placed in the repository.

The broader Western-electional slice then ran 355 tests across the Ramesey,
Sahl, Dorotheus, bounds, signed-motion, lunar-flow, profile-scan, classical-
perfection, facade, REST, OpenAPI, integration, and public-governance files.
All 355 passed with the same explicit wheel-test exclusion. A separate
unmocked `TestClient` request to
`POST /v1/electional/western/classical-perfection` used the application-created
engine and local DE441 reader and returned HTTP 200, four ordered trace events,
the canonical Lilly moiety policy id, and
`Moira.lilly_perfection_at` transport provenance.

`scripts/check_doc_consistency.py` passed, and the changed engine/facade/server
modules passed `py_compile` under the same `.venv` interpreter.

## Sovereignty audit

| Axis | Result | Evidence |
|---|---|---|
| Ontology ownership | Pass | Named event trace and six source witnesses; no generic success flag. |
| Derivation ownership | Pass | Predicate boundaries map to visually verified primary pages and named Moira substrate objects. |
| Structural ownership | Pass | Immutable named vessels and chronological events; no external-engine slot or repair structure. |
| Policy ownership | Pass | Aspect, moiety, reception, ingress, tie, sect, bounds, interval, and language policies are explicit. |
| Validation ownership | Pass for Lilly v1 admission | Source-isolation tests, invariants, DE441 chronology, root/facade governance, REST round trip, and OpenAPI checks carry the proof. |

## Exclusions and remaining source gates

This admission does not define Sahl or Bonatti perfection profiles, abscission,
or reflection of light. Sahl's *Introduction* and the full Bonatti *Book of
Astronomy* remain necessary before those named products can be designed. No
unadmitted form is inferred from Lilly or exposed under a generic lineage.
