# Muhurta Lagna composition standard

**Date:** 9 October 2026. **Owner:** `moira/muhurta_lagna.py` and
`moira/muhurta_lagna_dated.py`. [Source decisions and fixtures](../06_roadmap/VEDIC_LAGNA_SOURCE_AND_PLAN_2026-10-09.md)
control this finite VED-010 admission; [validation](../03_validation/MUHURTA_LAGNA_VALIDATION_2026-10-09.md)
records executed checks.

## 1. Public contract

`evaluate_muhurta_lagna_strength(sidereal_longitudes, *, jd_ut1,
lagna_sidereal_longitude=None, natal_moon_sidereal_longitude=None,
natal_lagna_sidereal_longitude=None, shadbala_result=None, policy=None)`
returns independently inspectable Lagna/Navamsa/placement/strength components.
The mapping admits any subset of the nine named Vedic bodies; numeric inputs
are finite and uncoerced, angles in[0,360). Opposite nodes must agree both
geometrically (1e-9-degree representation tolerance) and by sign. Missing
Lagna, bodies, natal reference or strength remain explicitly unavailable where
needed; an incomplete chart never earns a normalized total.

`MuhurtaLagnaPolicy` selects the purpose, Navamsa reading, optional Parihara
and named ayanamsa. Applied house/aspect/relationship/nature/strength policies
are returned. No unspecified house or aspect school is selected invisibly.
The catalogue enumerates these choices, endpoint conventions and exclusions.
The source record contains their full rule definitions and attribution limits.

## 2. Snapshot and strength context

`muhurta_lagna_for_datetime(dt, latitude, longitude, *, policy=None,
include_shadbala=False, hora_lord=None, natal_moon_sidereal_longitude=None,
natal_lagna_sidereal_longitude=None, reader=None)` admits an aware, real civil
instant; no naive datetime, Unix timestamp or nonexistent local time. Latitude
is[-90,90], longitude[-180,180]. Exact poles return unavailable Lagna geometry.
A missing kernel/clock/anchor raises MuhurtaResourceError; an uncovered epoch
raises MuhurtaCoverageError. Borrowed readers are never closed or replaced.

The snapshot carries the resolved epoch, reader binding, node mode, longitude
frame and actual inputs. Lagna geometry uses the canonical house owner.
Shadbala is opt-in, with declared Porphyry geometry, JD weekday, actual sunrise/sunset
day/night and optional caller hora lord. It exposes every existing component;
it does not act as a surrogate for dignity or cancel restrictions by threshold.
For direct Shadbala input, matching epoch/frame and consistent arithmetic are
required; observational authenticity remains the caller's responsibility.

## 3. Interpretation of results

The general and marriage profiles are separate. The marriage result contains
MC 87/92's0-20 Lagna placement score, which is neither Shadbala nor Varga
Vimshopaka. At commentary endpoints10 and 15 both applicable bands are returned.
Its favorable label does not override an independent restriction.

Rules have nullable truth and named prerequisites. Restrictions retain raw
detection after an opt-in MC 88 exception. A missing prerequisite can produce
`unavailable` or `exception_unavailable`; a known sufficient alternative can
still establish an exception. The existing six VED-009 temporal detectors are
not automatically modified. `activity_suitability="not_evaluated"` is always
returned. Continuous windows and complete purpose elections are outside this
snapshot product.

## 4. REST and compatibility

- `GET /v1/muhurta/lagna/catalogue`: kernel-free profile discovery.
- `POST /v1/muhurta/lagna/direct`: caller-supplied sidereal facts and optional complete Shadbala receipt.
- `POST /v1/muhurta/lagna/datetime`: the serving engine's reader-derived snapshot.

Requests forbid extra fields, unsupported policies, boolean/string numeric
coercion, nonfinite values, invalid node geometry and stale/malformed strength
receipts. All responses use declared models. Resource errors are 503;
coverage and invalid input errors are 422. Serializers project the canonical
engine result and do not own doctrinal rules.

The shared D9 boundary fix changes incorrectly assigned exact/subdivision
edge values. The source-backed Venus-to-Moon enemy correction changes Cancer
dignity and consumers of natural/compound relations. These changes preserve
the existing algorithms' declared authorities rather than introducing a
second incompatible table. Other Varga methods, legacy Muhurta score/search,
Tara/Chandra policy and VED-009 detection contracts are preserved.

## Strength repair follow-through — 9 October 2026

`shadbala_result` now retains the complete supplied/derived strength receipt
alongside the per-planet summary, including context, selected Saptavargaja
scale and canonical war ledger. Direct REST input accepts the engine dataclass
shape, including paired-array evidence. Signed canonical Kala war adjustments
are admitted only with their checked ledger; corrupted sums/thresholds/evidence
still reject. Missing polar solar events preserve Lagna evidence with
`shadbala_basis=unavailable_shadbala_solar_geometry` and no fabricated strength.

The second adversarial repair canonicalizes admitted classical-planet
positions from the Shadbala context before computing Lagna signs, Navamsas,
houses, predicates and placement scores. A tolerated difference across a
discrete boundary therefore cannot contradict the attached strength evidence.
Missing input bodies remain missing, and supplied nodes remain unchanged.
Context-backed positional components are recomputed during direct admission;
balanced edits that preserve totals still reject. Dated strength uses the
same explicitly declared civil-UTC weekday as the Shadbala REST products.
