# P12-U1 Specialist Umbrella Doctrine Decision

Version: 0.1
Date: 2026-06-13
Status: deferred for doctrine; discovery-only future candidate
Scope: Phase 12 generic `/v1/special/*` route-family evaluation

## 1. Decision

P12-U1 does not admit `/v1/special/*` routes in Phase 12.

The only future umbrella shape that remains eligible is a discovery-only
registry. It may tell clients which specialist analytical families exist, where
their family-native routes live, and what doctrine documents govern them.

It must not perform computation, chart analysis, range searches, scoring,
interpretive synthesis, cross-family aggregation, or generic "special"
payload normalization.

## 2. Reason For Deferral

Phase 12 specialist families are not one doctrinal class:

- Uranian exposes Hamburg School hypothetical-body positions and must preserve
  hypothetical-body provenance.
- Harmonics transforms chart longitudes by harmonic number and may branch into
  sweeps, aspects, composites, and vibrational fingerprints.
- Phase and photometry expose astronomical phase, elongation, illumination,
  angular diameter, and magnitude products with body-specific limits.
- Antiscia exposes solstitial reflection and contact doctrine, distinct from
  primary-direction antiscia.
- Nine Parts preserves Abu Ma'shar formula variants, dependencies, reversal
  policy, and condition profiles.
- Planetary Hours depend on date, location, sunrise/sunset, high-latitude
  behavior, and hour-ruler sequence.
- Huber depends on house-frame truth, Huber house zones, age point, contacts,
  and dynamic intensity.
- Sothic exposes Egyptian civil-date conversion, Sirius heliacal ranges,
  epoch search, drift prediction, and profile/network products.
- Longevity / Hyleg-Alcocoden is interpretively high-stakes and remains
  deferred pending doctrine.
- Lord of the Orb and Lord of the Turn expose separate medieval lordship
  systems with distinct source, method, blocker, and condition-profile truth.

A generic `/v1/special/*` route would erase those differences unless it is
strictly restricted to discovery metadata.

## 3. Doctrine Gate

Before any `/v1/special/*` route is admitted, the design must answer:

1. Is the route discovery-only?
2. Does it avoid accepting chart, body, date, location, or analysis inputs?
3. Does it avoid returning computed analytical results?
4. Does it preserve family-native route ownership?
5. Does it preserve each family's doctrine vocabulary?
6. Does it distinguish direct primitives from chart-backed profiles?
7. Does it distinguish one-instant computation from range/search workflows?
8. Does it avoid cross-family aggregation or comparison?
9. Does it avoid interpretive synthesis and scoring?
10. Does it avoid acting as a compatibility wrapper over named family routes?

If any answer is no, the umbrella remains deferred.

## 4. Admissible Future Shape

A future discovery-only umbrella may expose:

- `GET /v1/special`
- `GET /v1/special/{family}`

The response may include:

- family slug
- display label
- phase admission unit
- phase status
- website verdict
- route family prefix
- admitted route names
- source engine module
- backend standard document where present
- transport design document where present
- doctrine decision document where present
- provenance summary
- deferred expansion summary
- required input classes, stated only as metadata
- admitted product categories, stated only as metadata

The response must not include:

- chart payloads
- point, body, date, location, or house inputs
- computed positions, phases, reflections, hours, lordships, or profiles
- harmonic or Sothic sweep results
- longevity results
- Huber contacts or intensity scores
- cross-family summaries
- arbitrary query text
- dynamic compatibility transforms into family-native request models

## 5. Family-Native Ownership

Each family keeps its own route ownership:

- Uranian stays under `/v1/uranian/*`
- Harmonics stays under `/v1/harmonics/*`
- Phase and photometry stay under `/v1/phase/*`
- Antiscia stays under `/v1/antiscia/*`
- Nine Parts stays under `/v1/nine-parts/*`
- Planetary Hours stays under `/v1/planetary-hours/*`
- Huber stays under `/v1/huber/*`
- Sothic stays under `/v1/sothic/*`
- Longevity, if ever admitted, stays under `/v1/longevity/*`
- Lord of the Orb stays under `/v1/lord-of-the-orb/*`
- Lord of the Turn stays under `/v1/lord-of-the-turn/*`

The umbrella may point to those surfaces. It may not replace them, proxy them,
or make their doctrine look interchangeable.

## 6. Rejected Route Shapes

The following shapes are rejected for Phase 12:

- `GET /v1/special/search?q=...`
- `POST /v1/special/calculate`
- `POST /v1/special/profile`
- `POST /v1/special/chart`
- `POST /v1/special/bulk`
- `POST /v1/special/compare`
- `POST /v1/special/sweep`
- `POST /v1/special/report`
- `POST /v1/special/{family}`
- `POST /v1/special/{family}/calculate`

These shapes would either duplicate family-native routes or flatten distinct
specialist doctrine into a generic analytical envelope.

## 7. Verification Requirements For Future Admission

If a discovery-only umbrella is later admitted, verification must prove:

- route registry adds only discovery routes
- no request body is accepted
- no computation path is called
- no family-native service function is invoked
- no chart, body, location, house, or date input is accepted
- every advertised family links to an existing family route prefix or an
  explicitly deferred family entry
- every advertised family links to its ledger entry and doctrine documents
- response shape is stable and bounded without pagination
- `/v1/special/*` does not expose search query parameters
- OpenAPI output shows discovery metadata only

## 8. Current Completion Boundary

P12-U1 is complete as a doctrine decision.

It is not a route admission. The correct current status remains
`defer_for_doctrine`, with the narrowed future stance:

- discovery-only registry may be reconsidered later
- computation, chart analysis, range searches, scoring, synthesis,
  compatibility wrappers, and cross-family aggregation remain excluded
