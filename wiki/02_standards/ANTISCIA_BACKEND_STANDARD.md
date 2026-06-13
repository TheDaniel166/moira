# Antiscia Backend Standard

**Subsystem:** `moira/antiscia.py`
**Computational Domain:** Solstitial and equinoctial longitude reflections
**Status:** Backend standard for Phase 12 REST admission

---

## 1. Scope

This standard governs Moira's ordinary antiscia backend surface:

- `AntisciaAspect`
- `antiscion(longitude)`
- `contra_antiscion(longitude)`
- `find_antiscia(positions, orb=1.0)`
- `antiscia_to_point(point_longitude, positions, point_name="Point", orb=1.0)`

The subsystem computes zodiacal mirror points and contact searches over
ordinary ecliptic longitudes. It is a pure arithmetic astrology engine. It does
not compute planetary positions, house cusps, primary directions, or chart
motion.

## 2. Authority And Provenance

The implemented canon named by the module is:

- Vettius Valens, *Anthology* II.37
- William Lilly, *Christian Astrology* (1647), p. 90

The computational authority in Moira is the explicit reflection formula:

```text
antiscion(longitude)        = (180 - longitude) mod 360
contra_antiscion(longitude) = (360 - longitude) mod 360
```

These formulae are the backend doctrine. Transport layers may expose them but
must not replace them with sign-name lookup tables or interpretive shortcuts.

## 3. Governing Objects

### 3.1 Antiscion point

An antiscion point is the reflection of a zodiacal longitude across the
0 Cancer / 0 Capricorn solstice axis.

### 3.2 Contra-antiscion point

A contra-antiscion point is the reflection of a zodiacal longitude across the
0 Aries / 0 Libra equinox axis.

### 3.3 Antiscia contact

An `AntisciaAspect` records one admitted contact:

- `body1`
- `body2`
- `aspect` as `"Antiscion"` or `"Contra-Antiscion"`
- `lon1`
- `lon2`
- reflected `shadow`
- angular `orb`

The `shadow` field is the reflected longitude of `body1`. The `orb` is the
minimum circular angular distance between `shadow` and `lon2`.

## 4. Admitted Computations

### 4.1 Direct reflection

The direct primitive returns a reflected longitude in `[0, 360)`.

Admitted forms:

- antiscion of one longitude
- contra-antiscion of one longitude
- both reflections of one longitude

### 4.2 Pair contact search

`find_antiscia(positions, orb)` tests unordered body pairs for both antiscion
and contra-antiscion contact. For each pair and aspect kind, it checks both
directions and keeps the tighter direction when either direction qualifies.
Results are sorted by increasing orb.

### 4.3 Point contact search

`antiscia_to_point(point_longitude, positions, point_name, orb)` tests whether
each supplied body casts an antiscion or contra-antiscion onto one fixed target
point. Results are sorted by increasing orb.

## 5. Required Transport Invariants

Any REST admission for `/v1/antiscia/*` must preserve these invariants:

- reject non-finite longitudes before calling the engine
- normalize or document longitude wrap policy explicitly
- reject negative, non-finite, or unreasonably large orb values
- require unique non-empty body names in position maps
- preserve the engine labels `"Antiscion"` and `"Contra-Antiscion"`
- preserve `body1` as the body whose reflected point forms the contact
- preserve `shadow` and `orb` explicitly in responses
- sort contact responses by increasing orb
- bound chart/contact request size before public exposure

Transport should admit direct reflection routes before chart-wide contact
routes.

## 6. Primary-Direction Boundary

Ordinary antiscia and primary-direction antiscia are distinct surfaces.

This standard governs `moira.antiscia` only. It does not govern:

- `moira.primary_directions.antiscia.PrimaryDirectionAntisciaKind`
- `PrimaryDirectionAntisciaTarget`
- `project_primary_direction_antiscia_longitude`
- primary-direction arc search using antiscion targets

The primary-direction subsystem may use the same reflection formula for target
projection, as verified by `tests/unit/test_primary_direction_antiscia.py`, but
its governing object is a primary-direction target and arc, not an ordinary
chart antiscia contact.

REST documentation must not merge `/v1/antiscia/*` with primary-direction
routes or imply that ordinary antiscia contact search computes directed arcs.

## 7. Validation Requirements

Minimum validation for transport admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\antiscia.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_astrology_adversarial_gauntlet.py tests\unit\test_primary_direction_antiscia.py -q
```

The transport test suite must additionally cover:

- antiscion is an involution
- contra-antiscion is an involution
- boundary values at `0`, `90`, `180`, `270`, and wrap-adjacent longitudes
- pair-search deduplication
- point-search output ordering
- non-finite longitude rejection
- invalid orb rejection

## 8. Non-Goals

This subsystem does not provide:

- ephemeris computation
- house calculation
- aspect search beyond antiscion and contra-antiscion contacts
- primary-direction arc search
- directed symbolic interpretation
- antiscia networks or scoring profiles
- transit, progression, or solar-return orchestration

Those products require separate route design or separate subsystem standards.

## 9. Change Policy

The following are doctrine-sensitive and require explicit review before change:

- the two reflection formulae
- the meaning of `Antiscion` and `Contra-Antiscion`
- deduplication semantics in pair searches
- result ordering by orb
- the boundary between ordinary antiscia and primary-direction antiscia

The REST layer may validate, serialize, and bound the current backend. It must
not introduce hidden interpretive scoring.
