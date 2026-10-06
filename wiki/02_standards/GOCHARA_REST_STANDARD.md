# Gochara REST standard

Date: 6 October 2026. Status: implemented source contract; local validation receipts belong to the [Vedic surface ledger](../06_roadmap/VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md). Registered source routes do not imply a released package or deployed service.

The [Gochara backend standard](GOCHARA_BACKEND_STANDARD.md) owns doctrine. Transport is a bounded, synchronous, read-only view over the same public engine. It does not compute astronomy, infer an epoch or ayanamsa, search dated windows, blend source schools, or turn catalogue evidence into executable presets.

| Method | Path | Product |
| --- | --- | --- |
| POST | `/v1/gochara/evaluate` | Source-bound snapshot assessments, policies, observations, active/exempt witnesses and independent raw BAV. |
| POST | `/v1/gochara/profile` | The same snapshot plus local profiles, reconciled aggregate partitions and observed blocker-to-subject network. |
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

Catalogue `topic` values are the sixteen admitted catalogue topics; unsupported filters receive 422. Responses preserve `admitted`, `source_attested_not_admitted`, `disputed_not_admitted`, `research_required` and `outside_snapshot_scope`, together with authority kind, citations and limitations. All three routes are discoverable under the `gochara` tag and `classical-vedic` family through OpenAPI and `/v1/meta/routes`.

Validation covers all twelve scope combinations; all 36 source-fixture Vedha pairs through HTTP; raw BAV, malformed/unknown inputs, partial/exempt relations and graph reconciliation. No website delivery, release publication, deployed readiness or predictive accuracy claim follows from these tests.
