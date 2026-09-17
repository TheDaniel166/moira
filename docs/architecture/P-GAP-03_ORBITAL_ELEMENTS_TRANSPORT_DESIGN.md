# P-GAP-03 Orbital Elements Transport Design

Version: 0.4<br>
Date: 2026-09-15<br>
Status: Stage 2 distance-extremes adapter upgraded; broader orbital transport deferred
Scope: bounded REST adaptation of strict Sun/J2000 planet elements and passages

This design follows
`wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md`. The Python engine now
has a broader strict API, but P-GAP-03 deliberately retains a narrow transport
surface.

---

## 1. Route Family

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

The elements route is a Stage 1 adapter over:

```python
osculating_elements(
    body,
    jd_ut,
    center=OrbitalCenter.SUN,
    frame=OrbitalFrame.J2000_ECLIPTIC,
    reader=engine._reader,
)
```

The distance-extremes route remains an adapter over
`distance_extremes_at(body, jd_ut, reader)`, which is now the planet-only
compatibility layer over one strict `apsidal_passages` call with `center=SUN`
and `direction=NEXT`.

---

## 2. Requests And Admission

Both requests retain:

- `body: str`
- `jd_ut: float`
- extra fields forbidden

`jd_ut` means UT1 Julian Day on the elements route. It is not UTC, TT, or TDB.

Transport admission remains the nine historical planet names: Mercury through
Pluto. Sun, Moon, EMB, asteroids, comets, calculated points, fixed stars, and
unknown names are rejected by request validation or translated engine errors.
The broader Python admission is intentionally not inferred into REST.

Reasons for the narrower boundary:

- the existing response requires elliptic fields to be non-null;
- the request has no center or frame field;
- small-body release ownership needs a separate deployment design; and
- open-conic and undefined-field transport needs an explicit schema version.

---

## 3. Elements Response

The existing `elements` field names remain compatible:

- `name`
- `epoch_jd` (now explicitly TT)
- semi-major axis, eccentricity, and inclination
- ascending node, argument of perihelion, and mean anomaly
- mean motion and orbital period
- derived perihelion and aphelion distances

The surrounding `time` block is upgraded to carry:

- `input_time_scale = UT1_JD`
- `state_evaluation_scale = TDB_JD`
- `output_time_scale = TT_JD`
- `jd_ut`, `epoch_tt`, and `epoch_tdb`
- Delta T and TDB-minus-TT in seconds
- the source-owned Delta-T policy/source/retarget receipt
- NAIF `naif0012` policy, version, URL, SHA-256, byte count, and iteration count

The elements provenance is allowlisted and path-free. It carries:

- source module and strict engine entrypoint;
- required Sun center and fixed J2000-ecliptic frame;
- the complete gravity rule and primary PCK receipt;
- exact frame construction and router branch;
- every routed SPK leg, traversal sign, segment type, coverage interval,
  content identity, and catalog identity where applicable;
- intersection coverage and fixed pool generation; and
- all singularity thresholds and their policy ID.

No local kernel or manifest path may be serialized.

---

## 4. Distance-Extremes Stage 2 Migration

The distance-extremes request, top-level result field names, and planet-only
admission remain compatible. Its semantics and receipt are corrected:

- `DistanceExtremesResponse` remains the result vessel.
- `perihelion_jd` and `aphelion_jd` are explicitly TT.
- `DistanceExtremesTimeResponse` uses the common UT1 input, TT output, TDB
  state-evaluation contract and complete conversion receipt.
- the engine is invoked once so the two outcomes share one immutable reader
  snapshot, clock identity, gravity model, and route plan.
- provenance serializes the algorithm/version, both scale-explicit outcomes,
  frozen route schedule and path-free source legs, segment use counts, seam
  witnesses, search constants/window, and total evaluation count.

The transport does not add strict-core request fields. Center, direction, and
automatic window policy remain fixed adapter choices; the Moon, EMB, comets,
asteroids, previous passages, and explicit windows remain Python-only pending a
separately versioned transport design.

---

## 5. Error Mapping

Specific orbital exceptions are matched before generic Python exceptions.

| Error family | HTTP | Stable category |
|---|---:|---|
| invalid input/body/center | 422 | validation |
| frame unavailable or outside model interval | 422 | frame |
| body/catalog not loaded or kernel missing | 503 | resource |
| coverage unavailable | 422 | coverage |
| passage unavailable | 422 | orbital event availability |
| gravity/time/source receipt unavailable | 503 | authority |
| degenerate state | 422 | geometry |
| passage convergence or evaluation-budget exhaustion | 500 | computation |
| unexpected internal computation failure | 500 | computation |

Only allowlisted finite details enter the response. Kernel paths are reduced to
safe content labels. Unexpected exception text is logged with a request ID and
is absent from the client response.

---

## 6. Service Ownership

`moira_server/services/orbits.py` owns adaptation only:

- retrieve the already configured engine reader;
- invoke the strict element or passage function with the route's fixed policy;
- map the result into the existing element names;
- serialize the new time and provenance blocks; and
- leave kernel selection, body resolution, time conversion, state routing,
  gravity selection, frame construction, and conic extraction in the engine.

The service must not mutate global kernel paths, infer catalog availability,
recalculate elements from chart positions, or remove undefined values.

---

## 7. Verification

The transport gate requires:

- inner- and outer-planet success;
- parity with the strict engine result;
- exact UT1/TT/TDB labels and values;
- complete path-free source, gravity, frame, time, and singularity receipts;
- request validation and all Stage 1 orbital error translations;
- redaction of paths and non-finite internal measurements;
- proof that `/v1/orbits/distance-extremes` retained its bounded Stage 2
  admission;
- exact distance-extremes UT1/TT/TDB values and conversion receipt;
- complete outcome, route, source-usage, seam, search-policy, and gravity
  provenance with no local paths;
- one strict passage invocation and TT parity with the engine adapter; and
- stable translations for passage-unavailable and search-computation errors.

The REST tests use deterministic engine fixtures. Primary astronomical parity
is owned by the engine's offline JPL Horizons/NAIF/SOFA fixtures and isolated
live Horizons drift audit, not reimplemented in the adapter test.

---

## 8. Deferred Transport

Separate approval and versioned schemas are required for:

- Moon and Earth-centered requests;
- EMB, asteroids, and comets;
- selectable centers or frames;
- circular/equatorial undefined fields;
- parabolic and hyperbolic results;
- bulk/range/table routes;
- datetime convenience input; and
- selectable passage direction/window or non-planet passage transport.
