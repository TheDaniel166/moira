# Partial Closure Roadmap

**Date:** 2026-04-04  
**Scope:** All 46 `partial` rows in `SWISS_EPHEMERIS_TO_MOIRA_DRAFT.md`  
**Goal:** Map each to a specific resolution action that closes it to `mapped`, `stdlib`, or `unsupported`.

This document does not propose refactoring. Each resolution is the smallest correct change.

---

## Resolution Types

| Code | Meaning |
| --- | --- |
| `CLOSE:mapped` | Code already exists. Row update + verification only. No new code. |
| `CLOSE:stdlib` | Python standard library handles this. No Moira surface needed. |
| `CLOSE:unsupported` | Intentionally outside Moira's architecture. Reclassify the row. |
| `THIN` | One function or wrapper of < 10 lines. |
| `VESSEL` | New typed result vessel + one public function. |
| `AUDIT` | Existing surface probably covers it. Read-only investigation to confirm and update the row. |
| `ECLIPSE` | Eclipse surface audit. Code likely exists; shape needs confirmation against Swiss output spec. |
| `DEFERRED` | Requires validation work, catalog audit, or multi-file scope. Not a quick win. |

---

## Group A — Close as `unsupported.design` (no code, doctrine clarification only)

These are intentional architecture decisions, not gaps. The rows should be reclassified.

| Swiss symbol | Resolution | Action |
| --- | --- | --- |
| `set_topo` | `CLOSE:unsupported` | Moira is stateless by design. Global observer state is explicitly rejected. Update row note: "per-call observer arguments are the Moira idiom; global state is `unsupported.design`." |
| `set_sid_mode` | `CLOSE:unsupported` | Same doctrine. No global sidereal mode. Per-call `ayanamsa(jd_ut, Ayanamsa.X)` is the correct idiom. The note should say `unsupported.design`. |

---

## Group B — Close as `stdlib` (no Moira surface needed)

| Swiss symbol | Resolution | Action |
| --- | --- | --- |
| `day_of_week` | `CLOSE:stdlib` | `datetime.weekday()` or `calendar.day_name[...]`. Update row. |
| `get_planet_name` | `CLOSE:stdlib` | Body name strings are self-describing; `Body.SUN == "Sun"`. No dedicated helper is needed. Update row. |
| `difdeg2n` | `CLOSE:stdlib` | `normalize_degrees(a - b)` using the existing `moira.coordinates.normalize_degrees`. Add this as the mapped idiom in the row rather than `stdlib`. Change to `mapped`. |
| `deg_midp` | `CLOSE:stdlib` | `normalize_degrees((a + b) / 2)` for same-hemisphere; `normalize_degrees((a + b + 360) / 2)` for cross-zero case. Idiomatic one-liner. Change to `mapped` with note. |

---

## Group C — Close as `mapped` (code exists, row is stale)

A verification call or read of the function signature is all that is needed before updating the row.

| Swiss symbol | Current partial reason | Moira surface | Verification needed |
| --- | --- | --- | --- |
| `utc_to_jd` | "exact helper name from draft not audited" | `moira.julian.jd_from_datetime(dt: datetime) -> float` — exact match | Confirm function exists in `__all__`. Change row to `mapped`. |
| `deltat_ex` | "no exact flag variant audited" | `DeltaTPolicy` covers model selection and flag-equivalent behavior; `delta_t_nasa_canon(year)` provides the variant algorithm | Confirm `DeltaTPolicy` admits the extended model. Change row to `mapped`. |
| `get_ayanamsa_ex_ut` | "no exact flag variant audited" | `moira.sidereal.ayanamsa(jd_ut, Ayanamsa.X)` is the per-call equivalent; no flags needed | Run `help(ayanamsa)`. Change row to `mapped`. |
| `get_ayanamsa_name` | "no audited exact label helper" | `Ayanamsa.LAHIRI.name` on the `StrEnum` returns `"LAHIRI"`; `str(Ayanamsa.LAHIRI)` returns the value | Confirm `Ayanamsa` is a `StrEnum`. Change row to `mapped`. |
| `azalt` | "no audited one-call Swiss-style wrapper" | `moira.coordinates.equatorial_to_horizontal(ra_deg, dec_deg, lat_deg, jd_ut) -> tuple[float, float]` — azimuth + altitude | Confirm signature + return. Change row to `mapped`. |
| `sol_eclipse_when_glob` | "class method, not flat function" | `EclipseCalculator().next_solar_eclipse(jd_start)` — searches globally by construction | Confirm it does not require a location argument. Change row to `mapped`. |
| `lun_eclipse_when` | "class method" | `EclipseCalculator().next_lunar_eclipse(jd_start)` | Same as above. Change row to `mapped`. |
| `sol_eclipse_how` | "closest current local-attribute surface" | `EclipseCalculator().solar_local_circumstances(jd, lat, lon)` returns `SolarEclipseLocalCircumstances` including magnitude, obscuration, contact geometry | Confirm `SolarEclipseLocalCircumstances` fields match Swiss `sol_eclipse_how` output attributes. |
| `lun_eclipse_how` | "shape differs" | `LunarEclipseAnalysis` and `lunar_local_circumstances()` exist with umbral depth, penumbral fraction, contacts | Read `LunarEclipseAnalysis` fields vs Swiss `lun_eclipse_how` output spec. |
| `mooncross_ut` | "exact target-longitude helper naming differs" | `next_transit(Body.MOON, target_lon, jd_start)` in `moira.transits` — exact semantic match | Confirm `next_transit` accepts `Body.MOON` and a target longitude. Change row to `mapped`. |
| `solcross_ut` | "exact target-longitude helper naming differs" | `next_transit(Body.SUN, target_lon, jd_start)` in `moira.transits` | Same. Change row to `mapped`. |
| `heliacal_ut` | "star-oriented verified; planets not stated" | Planets: `visibility_event(body, kind, jd_start, lat, lon)` in `moira.heliacal`. Stars: `heliacal_rising(star, jd_start, lat, lon)` / `heliacal_setting(...)`. Both are public. | Update row note to name both surfaces. Change row to `mapped`. |
| `jdet_to_utc` | "shape differs" | `calendar_datetime_from_jd(jd) -> CalendarDateTime` or `datetime_from_jd(jd) -> datetime` in `moira.julian` | Confirm the return vessels + confirm TT input is accepted. Change row to `mapped` with note about the typed vessel. |
| `jdut1_to_utc` | "no exact UT1-specific helper audited" | `datetime_from_jd(jd) -> datetime` in `moira.julian` — UT1/UTC distinction is sub-millisecond for most use; Moira uses UT throughout | Note that Moira does not expose a UT1-specific variant; `datetime_from_jd` is the correct idiom. Change to `mapped` with a clarifying note. |
| `calc_ut` | "split across low-level and facade" | `planet_at(body, jd_ut)` returns `PlanetData` with longitude, latitude, distance, speed — exact semantic match for the primary Swiss `calc_ut` use case | The split is just Moira's cleaner architecture. Change row to `mapped` with a migration note. |

---

## Group D — Thin implementations — COMPLETED 2026-04-05

### `deltat` — `delta_t_from_jd(jd_ut: float) -> float` ✓

**Resolved:** `delta_t_from_jd` added to `moira/julian.py`. One-liner delegating to `delta_t(decimal_year_from_jd(jd_ut))`. Exported from `moira/__init__.py` and `moira/facade.py`. DRAFT row updated to `mapped`.
Promote to `__init__.py` and `facade.py`. Update DRAFT row.

---

### `sidtime0` — `apparent_sidereal_time_at(jd_ut: float, longitude: float = 0.0) -> float` ✓

**Resolved:** `apparent_sidereal_time_at` added to `moira/julian.py`. Derives nutation and true obliquity internally via deferred import of `moira.obliquity` (avoids circular dependency). `longitude=0` returns GAST; non-zero returns LAST. Exported from `moira/__init__.py` and `moira/facade.py`. DRAFT row updated to `mapped`.

Note: the roadmap draft pseudocode referenced a non-existent `nutation_components` function. Actual implementation uses `obliquity.nutation(jd_tt)` and `obliquity.true_obliquity(jd_tt)`.

---

### `calc` — TT entry point ✓

**Resolved:** `planet_at` already exposes `jd_tt: float | None = None` at `planets.py:608`. When supplied, the UT→TT conversion is bypassed entirely. No new code was needed. DRAFT row updated to `mapped`.

---

## Group E — Needs a vessel + public function (medium scope)

### `pheno_ut` — `planet_phenomena_at(body, jd_ut) -> PlanetPhenomena`

**Current gap:** No single Moira function returns what Swiss `pheno_ut` returns: phase angle, illumination fraction, elongation, apparent diameter, apparent magnitude.

**What exists:**
| Attribute | Source |
| --- | --- |
| `apparent_magnitude` | `_target_apparent_magnitude(body, jd_ut)` in `heliacal.py` (internal) |
| `elongation_deg` | `_signed_elongation(body, jd_ut)` in `heliacal.py` (internal) |
| `phase_angle_deg` | `phase_angle(body, jd_ut)` in `moira.phase` (public) |
| `illumination_fraction` | `phase_fraction(body, jd_ut)` or derivable from phase angle |
| `angular_diameter_arcsec` | derivable from distance and known body radius |

**Resolution:** Define `PlanetPhenomena` dataclass and `planet_phenomena_at(body, jd_ut) -> PlanetPhenomena` in `moira/phenomena.py`. Promote to `__init__.py` and `facade.py`. Close `pheno_ut` row.

---

### `nod_aps_ut` — `nodes_and_apsides_at(body, jd_ut) -> NodesAndApsides`

**Current gap:** Swiss `nod_aps_ut` returns nodes + apsides for a body in one call. Moira has:
- Lunar nodes: `mean_node`, `true_node` in `moira.nodes`
- Planetary apsides: `perihelion`, `aphelion` in `moira.phenomena`
- Planetary nodes: `all_planetary_nodes` in `moira.planetary_nodes`

These surfaces exist but no combined vessel exists.

**Resolution:** Define `NodesAndApsides` dataclass and `nodes_and_apsides_at(body, jd_ut) -> NodesAndApsides` in `moira/nodes.py` or `moira/planetary_nodes.py`. For the Moon: populate from `true_node`/`mean_node`. For planets: populate from `planetary_nodes` + `perihelion`/`aphelion`. Close `nod_aps_ut` row.

---

## Group F — Eclipse surface audit (`ECLIPSE`) — COMPLETED 2026-04-04

All rows audited against `moira/eclipse.py` and `moira/occultations.py`. 9 of 10 closed to `mapped`. One genuine partial remains.

| Swiss symbol | Result | Finding |
| --- | --- | --- |
| `sol_eclipse_when_glob` | `mapped` | `next_solar_eclipse(jd_start)` — global, no location arg |
| `sol_eclipse_when_loc` | **partial** (improved note) | `solar_local_circumstances` anchors to global event; does not search for next eclipse specifically visible at the observer's location |
| `sol_eclipse_where` | `mapped` | `solar_eclipse_path(jd_start) → SolarEclipsePath`; validated against Swiss `where` fixture |
| `sol_eclipse_how` | `mapped` | `SolarEclipseLocalCircumstances.event.data.eclipse_magnitude` + `sun_apparent_radius`, `moon_apparent_radius`, `topocentric_separation_deg`, `topocentric_overlap` |
| `lun_eclipse_when` | `mapped` | `next_lunar_eclipse(jd_start)` — global search |
| `lun_eclipse_when_loc` | `mapped` | `lunar_local_circumstances(jd, lat, lon) → LunarEclipseLocalCircumstances`; per-contact azimuth/altitude/visible for all 7 contacts |
| `lun_eclipse_how` | `mapped` | `LunarEclipseAnalysis.gamma_earth_radii` + `event.data.eclipse_magnitude/eclipse_type` + shadow radii |
| `lun_occult_when_glob` | `mapped` | `lunar_occultation(target, jd_start, jd_end)` / `lunar_star_occultation(...)` — omit observer coords for geocentric |
| `lun_occult_when_loc` | `mapped` | same functions with `observer_lat=`, `observer_lon=` → topocentric search |
| `lun_occult_where` | `mapped` | `lunar_occultation_path_at(...)` / `lunar_star_occultation_path_at(...)` → `OccultationPathGeometry`; IOTA-validated |

---

## Group G — Rise/set parity audit — COMPLETED 2026-04-04

Both rows audited against `moira/rise_set.py`.

| Swiss symbol | Result | Finding |
| --- | --- | --- |
| `rise_trans` | `mapped` | `find_phenomena` returns `'Rise'`, `'Set'`, `'Transit'`, `'AntiTransit'`; covers all Swiss `CALC_RISE`/`CALC_SET`/`CALC_MTRANSIT`/`CALC_ITRANSIT` use cases |
| `rise_trans_true_hor` | `mapped` | `altitude=<val>` kwarg or `RiseSetPolicy(horizon_altitude=<val>)` drives the bisection threshold directly; `RiseSetPolicy(refraction=False)` gives geometric horizon |

---

## Group H — Small catalog audit (`ISIS`, fictional bodies) — COMPLETED 2026-04-04

| Swiss symbol | Result | Finding |
| --- | --- | --- |
| `SE_ISIS` | `mapped` | Asteroid 42 Isis — real minor planet, NAIF ID 2000042. `asteroid_at("Isis", jd_ut)` via `moira/asteroids.py` catalog. |
| `SE_NIBIRU` | `unsupported.doctrine` | No accepted scientific ephemeris, no NAIF ID, no SPK kernel. Fictional body. Moira is astronomical-truth-first; fictional bodies with no real orbital solution are outside its design scope. |
| `SE_HARRINGTON` | `unsupported.doctrine` | Robert Harrington's unconfirmed Planet X hypothesis. Never assigned a NAIF ID; no SPK kernel exists. Same doctrine. |
| Uranian bodies (Cupido…Poseidon, Transpluto) | `mapped` (prior session) | Already in `moira.uranian` with mean orbital elements. Separate verified row. |

---

## Summary Table

| Symbol | Group | Resolution code | Effort |
| --- | --- | --- | --- |
| `set_topo` | A | `CLOSE:unsupported` | None |
| `set_sid_mode` | A | `CLOSE:unsupported` | None |
| `day_of_week` | B | `CLOSE:stdlib` | None |
| `get_planet_name` | B | `CLOSE:stdlib` | None |
| `difdeg2n` | B | `CLOSE:mapped` (idiom note) | None |
| `deg_midp` | B | `CLOSE:mapped` (idiom note) | None |
| `utc_to_jd` | C | `CLOSE:mapped` | Verify |
| `deltat_ex` | C | `CLOSE:mapped` | Verify |
| `get_ayanamsa_ex_ut` | C | `CLOSE:mapped` | Verify |
| `get_ayanamsa_name` | C | `CLOSE:mapped` | Verify |
| `azalt` | C | `CLOSE:mapped` | Verify |
| `sol_eclipse_when_glob` | C | `CLOSE:mapped` | Verify |
| `lun_eclipse_when` | C | `CLOSE:mapped` | Verify |
| `sol_eclipse_how` | C | `AUDIT` → mapped | Read fields |
| `lun_eclipse_how` | C | `AUDIT` → mapped | Read fields |
| `mooncross_ut` | C | `CLOSE:mapped` | Verify |
| `solcross_ut` | C | `CLOSE:mapped` | Verify |
| `heliacal_ut` | C | `CLOSE:mapped` | Note update |
| `jdet_to_utc` | C | `CLOSE:mapped` | Verify |
| `jdut1_to_utc` | C | `CLOSE:mapped` | Verify + note |
| `calc_ut` | C | `CLOSE:mapped` | Note update |
| `deltat` | D | `mapped` ✓ | `delta_t_from_jd` added |
| `sidtime0` | D | `mapped` ✓ | `apparent_sidereal_time_at` added |
| `calc` | D | `mapped` ✓ | `jd_tt` kwarg already existed at `planets.py:608` |
| `pheno_ut` | E | `VESSEL` | ~80 lines |
| `nod_aps_ut` | E | `VESSEL` | ~100 lines |
| `sol_eclipse_when_loc` | F | **partial** (improved note) | Genuine gap: location-anchored search |
| `sol_eclipse_when_glob` | C→F | `mapped` | None |
| `sol_eclipse_where` | F | `mapped` | None |
| `sol_eclipse_how` | F | `mapped` | None |
| `lun_eclipse_when` | C→F | `mapped` | None |
| `lun_eclipse_when_loc` | F | `mapped` | None |
| `lun_eclipse_how` | F | `mapped` | None |
| `lun_occult_when_glob` | F | `mapped` | None |
| `lun_occult_when_loc` | F | `mapped` | None |
| `lun_occult_where` | F | `mapped` | None |
| `rise_trans` | G | `mapped` | None |
| `rise_trans_true_hor` | G | `mapped` | None |
| `ISIS`, `NIBIRU`, etc. | H | `AUDIT` → mixed | Catalog read |
| `sidtime0` | D | `THIN` | ~10 lines |
| `deltat` | D | `THIN` | ~5 lines |
| `utc_to_jd` | C | `CLOSE:mapped` | Verify |
| `jdut1_to_utc` | C | `CLOSE:mapped` | Verify |

---

## Recommended Execution Order

### Phase 1 — Zero-code closes (Groups A + B + C, verification only)
Close approximately **20 rows** with no implementation. Only row updates and one verification command per symbol.

Sequence:
1. Verify `utc_to_jd`, `azalt`, `mooncross_ut`, `solcross_ut`, `calc_ut` in one pass — all likely already `mapped`
2. Reclassify `set_topo`, `set_sid_mode` → `unsupported`
3. Reclassify `day_of_week`, `get_planet_name` → `stdlib`; add `difdeg2n`, `deg_midp` as `mapped` idiom notes
4. Confirm `jdet_to_utc`, `jdut1_to_utc` via `julian.py` public surface
5. Confirm eclipse group-C rows (`sol_eclipse_when_glob`, `lun_eclipse_when`, `sol_eclipse_how`, `lun_eclipse_how`) via `eclipse.py` vessel fields
6. Update `heliacal_ut` row to name both planet and star surfaces

Estimated DRAFT.md result after Phase 1 + completed Groups F & G: **partial: ~24**, **mapped: ~81**

### Phase 2 — Thin implementations (Group D) — COMPLETED 2026-04-05

1. ✓ `delta_t_from_jd(jd_ut)` → closes `deltat`
2. ✓ `apparent_sidereal_time_at(jd_ut, longitude)` → closes `sidtime0`
3. ✓ `jd_tt` kwarg on `planet_at` already existed — closes `calc` (no code needed)

### Phase 3 — Vessel implementations (Group E)
Two new vessels. Each requires a new dataclass + public function + tests.

1. `planet_phenomena_at(body, jd_ut) -> PlanetPhenomena` → closes `pheno_ut`
2. `nodes_and_apsides_at(body, jd_ut) -> NodesAndApsides` → closes `nod_aps_ut`

### Phase 4 — Eclipse and occultation audits (Group F)
Read-only investigation against the Swiss spec for each of the six rows. No new code unless a field is genuinely missing.

### Phase 5 — Rise/set audit (Group G)
One focused read of `find_phenomena` + `RiseSetPolicy`. Likely closes both rows with no new code.

### Phase 6 — Catalog audit (Group H)
Read `moira/data/` and `moira/asteroids.py` for named small-body entries.
