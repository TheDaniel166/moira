# Gochara REST standard

Date: 6 October 2026. Status: implemented source contract; local validation receipts belong to the [Vedic surface ledger](../06_roadmap/VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md). Registered source routes do not imply a released package or deployed service.

The [Gochara backend standard](GOCHARA_BACKEND_STANDARD.md) owns judgment doctrine. Transport is a bounded, synchronous, read-only view over the same public engine. Supplied-position routes evaluate caller inputs; the [date-derived compositor](GOCHARA_DATE_DERIVED_STANDARD.md) derives reader-bound astronomical inputs from explicit epochs or aware civil instants. Neither product searches dated windows, blends source schools or turns unadmitted catalogue evidence into executable presets.

| Method | Path | Product |
| --- | --- | --- |
| POST | `/v1/gochara/evaluate` | Source-bound snapshot assessments, policies, observations, active/exempt witnesses and independent raw BAV. |
| POST | `/v1/gochara/profile` | The same snapshot plus local profiles, reconciled aggregate partitions and observed blocker-to-subject network. |
| POST | `/v1/gochara/from-epochs` | Complete reader-bound natal/transit composition from two explicit UT1 Julian dates. |
| POST | `/v1/gochara/from-datetimes` | The same composition from two timezone-aware civil instants. |
| GET | `/v1/gochara/doctrine-options` | Thirty cited admission records across sixteen topics; optional `topic` filter. |

## Request contract

`natal_moon_sidereal_longitude` and `transit_sidereal_longitudes` are caller-supplied sidereal degrees. A snapshot contains one through seven classical bodies. Finite JSON numbers are accepted, including integral numbers; booleans, numeric strings, NaN/Infinity, unknown bodies and extra fields are rejected with the shared HTTP 422 `validation_error` envelope. Finite longitudes normalize modulo 360 in the engine; exact sign endpoints and tiny negative values retain its existing ownership rule.

Optional `raw_bav` maps observed subject names to exactly twelve integer counts in 0–8, in absolute zodiac-sign order. The transport constructs the existing BAV vessel with the sum of those supplied counts. It does not certify that the table is unreduced or belongs to the same birth. Those remain explicit caller assertions, as do the shared sidereal frame and astronomical epoch of supplied positions. BAV does not override baseline indications or Vedha.

Optional `policy` exposes precisely the four admitted axes:

| Field | Default | Admitted alternatives |
| --- | --- | --- |
| `source_profile` | `phaladeepika_26_sastri_1950_seven_classical` | No alternative executable corpus. |
| `vedha_mode` | `ordinary` | `baseline_only` |
| `completeness` | `retain_partial` | `require_complete` |
| `bav_mode` | `raw_if_supplied` | `omit`, `require_all_raw` |

Complete mode requires all seven positions. Required BAV mode requires a table for every observed subject. Omit mode rejects supplied BAV. Reference and participant universes are fixed by the source profile rather than supplied independently.

Example request to `POST /v1/gochara/profile`:

```json
{
  "natal_moon_sidereal_longitude": 0,
  "transit_sidereal_longitudes": {"Mercury": 210, "Venus": 0}
}
```

Both planets are known blocked in this example, while other eligible blocker observations remain incomplete. The two active graph edges are Venus → Mercury and Mercury → Venus. These illustrative supplied positions are not an astronomical authority sample.

## Response truth

Typed response fields preserve named source, selected cited choices, supplied position origin, fixed subjects/blockers, missing subjects, baseline membership, individual indication citations, directed pairs, exemptions, observed completeness and raw BAV availability. A known blocker establishes `blocked` independently of observation completeness. Missing bodies do not become zero-degree graph nodes. Baseline-only omits Vedha rather than declaring clearance.

The canonical snapshot appears once at the profile root. Redundant engine back-references from summary and network nodes are represented by that shared snapshot. Each local profile retains its assessment; each graph edge retains the full source-bound witness. Named model fields read the frozen vessels through Pydantic's attribute mapping; no `__dict__`, recursive internal-layout dump or narrative parsing is used.

Catalogue `topic` values are the sixteen admitted catalogue topics; unsupported filters receive 422. Responses preserve `admitted`, `source_attested_not_admitted`, `disputed_not_admitted`, `research_required` and `outside_snapshot_scope`, together with authority kind, citations and limitations. All five routes are discoverable under the `gochara` tag and `classical-vedic` family through OpenAPI and `/v1/meta/routes`. The catalogue now includes two additional admitted engine-scope records for reader-derived epochs and raw natal BAV composition.

Validation covers all twelve scope combinations; all 36 source-fixture Vedha pairs through HTTP; raw BAV, malformed/unknown inputs, partial/exempt relations and graph reconciliation. No website delivery, release publication, deployed readiness or predictive accuracy claim follows from these tests.

## Date-derived requests and responses

`from-epochs` requires finite JSON numbers `natal_jd_ut1` and
`transit_jd_ut1` in `[-10000000, 10000000]`. They denote UT1, not UTC or TT.
`from-datetimes` instead requires `natal_dt` and `transit_dt` as ISO datetime
strings with explicit timezone offsets. Bare dates, naive times and numeric
timestamps are rejected. Each civil instant is converted to UTC and then UT1
through the existing Moira clock policy. Both routes reject extra fields,
caller BAV tables, unknown ayanamsas and unsupported correction switches.

The optional `policy` has `ayanamsa_system` (default `Lahiri`),
`natal_bav_mode` (`omit` or `compute_raw`) and nested `gochara_policy` containing
the existing snapshot choices. Its default completeness is `require_complete`.
`compute_raw` requires `birth_location` with finite numeric `latitude` strictly
between -90 and 90 and `longitude` between -180 and 180, north/east positive.
Location is rejected without computation. `compute_raw` with inner BAV `omit`,
or omission with inner `require_all_raw`, receives 422 before astronomy.

Example request to `POST /v1/gochara/from-datetimes`:

```json
{
  "natal_dt": "1990-01-01T05:30:00+05:30",
  "transit_dt": "2026-10-06T00:00:00Z",
  "birth_location": {"latitude": 28.6139, "longitude": 77.209},
  "policy": {"natal_bav_mode": "compute_raw", "ayanamsa_system": "Lahiri"}
}
```

The typed `GocharaDateResponse` returns `natal` and `transit` clock/frame
receipts, astronomical policy, optional birth location and natal Lagna, eight
natal sign references when BAV is computed, explicit BAV source, and the
canonical `profile`. Each epoch includes UT1/TT/TDB, Delta-T source and tidal
correction, serving DE/LE identity, actual ayanamsa/method/anchor and all seven
tropical and sidereal inputs. The nested snapshot's supplied-position origin
describes its evaluator input stage; the outer epochs identify the engine
astronomy that supplied it. No astronomy or doctrine is rebuilt by serializers.

| Outcome | HTTP | Error code |
| --- | --- | --- |
| Invalid/ambiguous input, policy contradiction or nonunique Lagna | 422 | `validation_error` |
| Natal or transit epoch outside serving kernel coverage | 422 | `gochara_date_outside_coverage` |
| Missing planetary segment, time identity or live anchor resource | 503 | `gochara_resource_unavailable` |

All failures use the shared request-id envelope. Resource errors expose a
bounded stage message; internal paths and low-level exception details remain
in the exception cause. Resource failure never produces a successful partial
dated snapshot. Tests exercise the real compositor with analytic astronomy
through loopback and compare HTTP responses to the same facade result.
