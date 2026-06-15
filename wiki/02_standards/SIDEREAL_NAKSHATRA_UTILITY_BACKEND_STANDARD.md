# Sidereal And Nakshatra Utility Backend Standard

Version: 0.2
Date: 2026-06-14
Status: implemented backend standard for P-GAP-05 REST admission
Scope: mechanical ayanamsa, tropical/sidereal longitude conversion, and
Nakshatra position lookup primitives

This standard governs the root/facade sidereal utility surfaces that are
public through Python and candidates for P-GAP-05 REST admission:

- `moira.sidereal.Ayanamsa`
- `moira.sidereal.ayanamsa`
- `moira.sidereal.tropical_to_sidereal`
- `moira.sidereal.sidereal_to_tropical`
- `moira.sidereal.list_ayanamsa_systems`
- `moira.sidereal.nakshatra_of`
- `moira.sidereal.all_nakshatras_at`

This standard does not govern Panchanga, Muhurta, Dasha, Varga, Shadbala,
Jaimini, Ashtakavarga, Vedic dignities, Manazil, or chart-backed sidereal
house derivation. Those are separate doctrine or chart-adapter surfaces.

---

## 1. Governing Objects

P-GAP-05 has four mechanical governing objects.

### Ayanamsa System Registry

Owned by:

- `moira.sidereal.Ayanamsa`
- `moira.sidereal.list_ayanamsa_systems`

Meaning:

- ordered registry of built-in named ayanamsa systems
- J2000 reference values for the built-in table
- discovery surface only; it does not compute a date-specific ayanamsa value

Admitted fields:

- `system`
- `reference_value_j2000_deg`
- `is_star_anchored`
- `default_mode`
- `supported_modes`

### Ayanamsa Value

Owned by:

- `moira.sidereal.ayanamsa`

Meaning:

- date-specific ayanamsa value in degrees for a finite `jd_ut`
- accepts named built-in systems only for REST Stage 1
- accepts explicit mode: `true` or `mean`

Admitted fields:

- `jd_ut`
- `ayanamsa_system`
- `mode`
- `ayanamsa_deg`
- `value_range`

### Longitude Conversion

Owned by:

- `moira.sidereal.tropical_to_sidereal`
- `moira.sidereal.sidereal_to_tropical`

Meaning:

- mechanical conversion between tropical and sidereal ecliptic longitude
- no chart construction
- no body identity
- no house derivation
- no Panchanga judgement

Admitted fields:

- `jd_ut`
- `ayanamsa_system`
- `mode`
- `direction`
- `input_longitude_deg`
- `output_longitude_deg`
- `ayanamsa_deg`
- `longitude_range`

### Nakshatra Position

Owned by:

- `moira.sidereal.NakshatraPosition`
- `moira.sidereal.nakshatra_of`
- `moira.sidereal.all_nakshatras_at`

Meaning:

- Nakshatra, lord, pada, degrees-in, and sidereal longitude for one tropical
  ecliptic longitude or a caller-supplied map of named tropical longitudes
- result is mechanical mansion placement only
- no Panchanga tithi/vara/yoga/karana computation
- no Muhurta interpretation
- no Dasha balance computation

Admitted fields:

- `name` for bulk entries
- `tropical_longitude_deg`
- `jd_ut`
- `ayanamsa_system`
- `nakshatra`
- `nakshatra_index`
- `nakshatra_number`
- `nakshatra_lord`
- `pada`
- `degrees_in`
- `degrees_remaining`
- `sidereal_longitude_deg`

---

## 2. Route Admission Boundary

P-GAP-05 admits bounded synchronous utility routes under two explicit
prefixes:

- `/v1/sidereal/*`
- `/v1/nakshatra/*`

Stage 1 routes are limited to:

- `GET /v1/sidereal/ayanamsa-systems`
- `POST /v1/sidereal/ayanamsa`
- `POST /v1/sidereal/convert`
- `POST /v1/nakshatra/position`
- `POST /v1/nakshatra/bulk`

The split is intentional:

- `/v1/sidereal/*` is zodiac-offset and longitude-conversion utility truth.
- `/v1/nakshatra/*` is lunar mansion placement truth.
- Neither prefix is a replacement for `/v1/panchanga/*`.

---

## 3. Ayanamsa Policy

Stage 1 REST admission must use named built-in ayanamsa systems only.

Admitted systems:

- every name returned by `Ayanamsa.ALL`

Admitted modes:

- `true`
- `mean`

Transport must reject:

- unknown ayanamsa names
- empty ayanamsa names
- invalid modes
- user-defined ayanamsa payloads

Reason:

`UserDefinedAyanamsa` is a valid Python engine surface, but REST admission
would need source/provenance fields for caller-supplied reference values and
drift terms. That is a separate packet, not a Stage 1 utility route.

---

## 4. Time And Longitude Policy

All date-specific Stage 1 requests use `jd_ut`, matching the public sidereal
functions.

Transport must validate:

- all JD values are finite
- all longitude inputs are finite
- longitude outputs are normalized to `[0, 360)`
- bulk Nakshatra maps are non-empty
- bulk Nakshatra maps are bounded by a public maximum count

Recommended Stage 1 bounds:

- maximum Nakshatra bulk entries: `64`

Longitudes may be supplied outside `[0, 360)`, because the engine conversion
functions normalize by modulo. Responses must preserve both the caller input
and normalized output truth.

---

## 5. Nakshatra Taxonomy

The REST surface must preserve the engine's current 27-Nakshatra taxonomy:

- 27 equal mansions
- span: `360 / 27` degrees
- 4 padas per Nakshatra
- pada span: `(360 / 27) / 4` degrees
- 0-based `nakshatra_index`
- 1-based `nakshatra_number`
- 1-based `pada`
- Vimshottari lord sequence as represented by `moira.sidereal.NAKSHATRA_LORDS`

The route must not add alternate Nakshatra traditions, Abhijit Nakshatra,
Manazil, mansion interpretations, or Dasha balance semantics.

---

## 6. Provenance Requirements

Every response must state:

- `source_module`: `moira.sidereal`
- `engine_entrypoint`
- `time_scale`: `UT_JD`
- `ayanamsa_system`
- `ayanamsa_mode`
- `product_kind`
- `stage_sequence`

Ayanamsa registry provenance must state:

- `registry_owner`: `moira.sidereal.Ayanamsa`
- `reference_epoch`: `J2000`
- `user_defined_ayanamsa`: `not_admitted`

Ayanamsa value and conversion provenance must state:

- `jd_policy`: `caller_supplied_UT_JD`
- `mode_policy`: `true_or_mean_only`
- `star_anchor_policy`: `engine_owned_for_true_star_anchored_systems`

Nakshatra provenance must state:

- `taxonomy`: `twenty_seven_equal_nakshatras`
- `span_deg`: `360 / 27`
- `pada_span_deg`: `(360 / 27) / 4`
- `interpretation`: `not_returned`
- `panchanga_judgement`: `not_returned`

---

## 7. Non-Goals

P-GAP-05 does not admit:

- Panchanga result/profile routes
- Muhurta classification or scoring
- Dasha balance or sequence computation
- chart-backed Moon derivation
- chart-backed sidereal house derivation
- Varga projection
- Manazil or alternate lunar mansion traditions
- Abhijit Nakshatra
- user-defined ayanamsa REST payloads
- mutable global sidereal mode
- interpretation text or recommendation language
- async sweeps or dense ephemeris tables
- kernel path mutation

---

## 8. Verification Requirements

Before REST admission, tests must cover:

- ayanamsa system registry route matches `list_ayanamsa_systems`
- ayanamsa value route parity with `ayanamsa`
- tropical-to-sidereal route parity with `tropical_to_sidereal`
- sidereal-to-tropical route parity with `sidereal_to_tropical`
- conversion round-trip invariant within floating tolerance
- Nakshatra position route parity with `nakshatra_of`
- Nakshatra bulk route parity with `all_nakshatras_at`
- Nakshatra boundary assignment around exact mansion boundaries
- invalid ayanamsa system rejection
- invalid mode rejection
- non-finite JD rejection
- non-finite longitude rejection
- empty bulk map rejection
- oversized bulk map rejection
- extra field rejection
- route registry audit confirming admitted route set

No new sidereal astronomical oracle validation is required for REST admission.
The route tests prove transport truth over existing engine functions. Existing
sidereal reference validation remains the authority for the engine substrate.

---

## 9. Admission Decision

P-GAP-05 is admitted through:

- `GET /v1/sidereal/ayanamsa-systems`
- `POST /v1/sidereal/ayanamsa`
- `POST /v1/sidereal/convert`
- `POST /v1/nakshatra/position`
- `POST /v1/nakshatra/bulk`

Reason:

- the engine surfaces already exist
- the public utility scope is mechanical and bounded
- the route family closes a real facade/root-to-REST gap
- doctrine-heavy Panchanga, Muhurta, Dasha, and mansion interpretation remain
  outside this admission
- focused server tests cover adapter truth, conversion round trip, Nakshatra
  boundary behavior, validation rejection, provenance, and route method
  boundaries
