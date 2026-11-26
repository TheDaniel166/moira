# P-GAP-03 Orbital Elements Transport Design

Version: 0.5<br>
Date: 2026-11-26<br>
Status: Strict elements and bounded apsidal variants admitted
Scope: Bounded REST adaptation of strict osculating elements and apsidal passages

This design follows
`wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md`. Center, frame and
passage-direction selection are `admit_now` as synchronous read-only transport
over the existing `osculating_elements` and `apsidal_passages` engines.
The serving reader owns the geometric state. Frozen Horizons element and
passage fixtures and two-sided DE441 lunar radial checks govern verification.

---

## 1. Route Family

- `POST /v1/orbits/elements`
- `POST /v1/orbits/distance-extremes`

The elements route is a Stage 1 adapter over:

```python
osculating_elements(
    body,
    jd_ut,
    center=request.center,
    frame=request.frame,
    reader=engine._reader,
)
```

The distance-extremes route makes one strict `apsidal_passages` call with
the request's center, direction, optional TDB-day bound, and serving reader.

---

## 2. Requests And Admission

Both requests retain:

- `body: str`
- `jd_ut: float`
- extra fields forbidden

`jd_ut` is a UT1 Julian Day on both routes. The engine resolves body identity
and center eligibility against its admitted sources. `SUN` remains the
default for planets and admitted small bodies. The Moon requires `EARTH`.

The elements request accepts `J2000_ECLIPTIC` (default),
`MEAN_ECLIPTIC_OF_DATE`, or `TRUE_ECLIPTIC_OF_DATE`. The frame router applies
its TT model intervals.

Distance extrema accept `NEXT` (default) or `PREVIOUS` from the inclusive
start epoch. `max_days` accepts a positive finite JSON number. Omitted or
null bounds use 1.5 osculating periods for elliptic conics and the verified
route interval otherwise. The engine bounds all searches by coverage and its
evaluation budget.

---

## 3. Elements Response

Sun-centered results retain the existing `elements` field names:

- `name`
- `epoch_jd` (now explicitly TT)
- semi-major axis, eccentricity, and inclination
- ascending node, argument of perihelion, and mean anomaly
- mean motion and orbital period
- derived perihelion and aphelion distances

Earth-centered lunar results call the argument and derived distances
`arg_perigee_deg`, `perigee_distance_au`, and `apogee_distance_au`.
Undefined fields are nullable and the receipt preserves their engine names
and geometric reasons.

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
- evaluated center, frame, orientation, conic shape, and undefined fields;
- the complete gravity rule and primary PCK receipt;
- exact frame construction and router branch;
- every routed SPK leg, traversal sign, segment type, coverage interval,
  content identity, and catalog identity where applicable;
- intersection coverage and fixed pool generation; and
- all singularity thresholds and their policy ID.

No local kernel or manifest path may be serialized.

---

## 4. Distance-Extremes Stage 2 Migration

Both passage outcomes share one immutable reader snapshot, clock identity,
gravity model, and route plan.

- Sun-centered events use `perihelion_jd` and `aphelion_jd` at TT, with
  corresponding AU distances. Earth-centered lunar events use `perigee_jd`
  and `apogee_jd` with the same units.
- `DistanceExtremesTimeResponse` uses the common UT1 input, TT output, TDB
  state-evaluation contract and complete conversion receipt.
- Provenance serializes the evaluated center and direction, algorithm version,
  both scale-explicit outcomes,
  frozen route schedule and path-free source legs, segment use counts, seam
  witnesses, search constants/window, and total evaluation count.

The default Sun/next search with an automatic window retains HTTP 422 when
either outcome is unavailable. Completed Earth-centered, previous, or
explicitly bounded searches return both engine statuses independently.
Missing convenience epochs and distances are null.

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
- invoke the strict element or passage function with the requested policy;
- map the result into the center-specific field names;
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
- preserved Sun/J2000 defaults and exact legacy numeric fields;
- selected lunar center, admitted frame branches and stable out-of-range
  errors;
- exact distance-extremes UT1/TT/TDB values and conversion receipt;
- complete outcome, route, source-usage, seam, search-policy, and gravity
  provenance with no local paths;
- one strict passage invocation, including a partial outcome under an
  explicit bound;
- earlier and later lunar apsides with two-sided DE441 radial witnesses; and
- stable translations for passage-unavailable and search-computation errors.

The REST tests use deterministic fixtures and the installed DE441 reader.
The offline JPL Horizons, NAIF and SOFA fixtures govern engine parity.

---

## 8. Deferred Transport

Separate approval and versioned schemas are required for:

- additional centers, frames, and body identities beyond the strict reducer;
- mean element tables, visual-binary elements, and apparent orbital elements;
- bulk/range/table routes; and
- datetime convenience input.
