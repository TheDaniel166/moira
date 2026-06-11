# Moira Decans Backend Standard

Version: 1.0
Date: 2026-06-11
Status: Current implementation truth; P9-12 REST admission prerequisite

## Governing Principle

Moira has two related but distinct decan subsystems:

- `moira.decanates` owns classical Chaldean faces, triplicity decans, and
  Vedic drekkana placement.
- `moira.hermetic_decans` owns the tropical Hermetic 36-decan name order,
  ruling-star table, rising-decan lookup, and nightly decan-hour division.

These surfaces must not be collapsed into one vague "decan" product. The REST
surface must preserve which doctrine produced the result, which zodiacal frame
was consumed, and whether the computation is simple longitude placement or an
astronomical night-hour product.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Decanate position

A **DecanatePosition** is:

> One longitude placed into one 10-degree decan under a named decanate doctrine.

| Field | Meaning |
|---|---|
| `system` | `chaldean_face`, `triplicity`, or `vedic_drekkana` |
| `decan_number` | Decan inside the sign, `1`, `2`, or `3` |
| `ruling_planet` | Traditional seven-planet ruler |
| `ruling_sign` | Governing sign for triplicity/drekkana, or `None` for Chaldean faces |
| `sign` | Occupied sign |
| `sign_symbol` | Occupied sign symbol |
| `degree_in_decan` | Degree elapsed inside the 10-degree span |
| `longitude_used` | Normalized longitude actually used by the doctrine |

Chaldean faces and triplicity decans consume tropical longitude directly.
Vedic drekkana consumes tropical longitude plus JD and delegates sidereal
reduction to `moira.sidereal.tropical_to_sidereal(...)`.

#### 1.2 Hermetic decan

A **Hermetic decan** is:

> One of the 36 tropical Hellenistic-Hermetic decan names in ecliptic order,
> paired with its magical/astrological ruling star assignment.

The ruling stars are not positional markers and are not expected to lie inside
their assigned tropical 10-degree spans.

#### 1.3 Hermetic decan night

A **DecanHoursNight** is:

> The 12 Hermetic decan hours spanning sunset to next sunrise for one observer
> location and date.

Its hour vessels preserve hour number, decan name, ruling star, and exact JD
boundaries.

---

### 2. Layer Structure

Current implemented layers:

```text
P1 - Decanate truth               (DecanatePosition)
P2 - Hermetic catalog truth       (DECAN_NAMES, DECAN_RULING_STARS, list_decans)
P3 - Hermetic longitude lookup    (decan_for_longitude, decan_index)
P4 - Hermetic rising decan        (decan_at)
P5 - Hermetic night-hour vessel   (DecanHour, DecanHoursNight)
P6 - Hermetic night-hour compute  (decan_hours)
P7 - Public API curation          (root/classical/facade exports)
```

Layer boundary rules:

- Decanate routes must expose the producing doctrine.
- Tropical Chaldean and triplicity routes must not imply sidereal reduction.
- Vedic drekkana routes must expose JD and ayanamsa policy input.
- Hermetic catalog routes must not imply fixed-star positional computation.
- Hermetic night-hour routes may call the existing astronomical engine but must
  validate finite JD/location inputs before doing so.

---

### 3. Public Surface

#### `moira.decanates`

| Name | Meaning |
|---|---|
| `DecanatePosition` | Frozen vessel for one decanate computation |
| `chaldean_face(longitude)` | Tropical Chaldean face placement |
| `triplicity_decan(longitude)` | Tropical triplicity decan placement |
| `vedic_drekkana(longitude, jd, ayanamsa_system="Lahiri")` | Vedic D3 placement after sidereal reduction |

#### `moira.hermetic_decans`

| Name | Meaning |
|---|---|
| `DecanHour` | Frozen vessel for one night hour |
| `DecanHoursNight` | Frozen vessel for a complete night |
| `DECAN_NAMES` | Decan constant-to-name mapping |
| `DECAN_RULING_STARS` | Decan name-to-ruling-star mapping |
| `list_decans()` | 36 decan names in ecliptic order |
| `available_decans()` | Decans whose ruling star exists in the star catalog |
| `decan_for_longitude(lon)` | Tropical longitude to Hermetic decan name |
| `decan_at(jd, lat, lon)` | Ascendant decan for a time/location |
| `decan_hours(jd, lat, lon)` | Twelve night hours for the containing night |

---

### 4. Determinism and Failure Doctrine

#### 4.1 Determinism

- Longitude placement normalizes longitudes modulo 360.
- Decan spans are equal 10-degree intervals.
- Chaldean face rulership follows the declared seven-planet cycle beginning
  with Mars at Aries 0 degrees.
- Triplicity and Vedic drekkana rulership use the same-element sign sequence:
  own sign, fifth sign, ninth sign.
- Hermetic decan names are ordered by fixed tropical 10-degree spans.
- Hermetic night hours partition the computed sunset-to-sunrise interval into
  twelve contiguous equal temporal hours.

#### 4.2 Failure doctrine

Current engine truth:

- `chaldean_face`, `triplicity_decan`, `vedic_drekkana`, and
  `decan_for_longitude` reject non-finite longitudes.
- `DecanatePosition`, `DecanHour`, and `DecanHoursNight` validate structural
  invariants at construction.
- `decan_hours` fails if finite sunset/sunrise boundaries cannot be found.

REST transport must additionally reject non-finite JD/location inputs before
calling rising-decan or night-hour computations.

---

## Part II - Validation Codex

### 5. Validation Scope

The decan backend is currently validated through:

- `tests/unit/test_decanates.py`
- `tests/unit/test_hermetic_decans.py`

### 6. Validation Claims

The following claims are currently verified:

1. `DecanatePosition` is frozen and enforces system/range invariants.
2. Chaldean faces preserve the declared Mars-starting planetary cycle.
3. Triplicity decans preserve same-element ruling-sign doctrine.
4. Vedic drekkana performs sidereal reduction and preserves traditional rulers.
5. Hermetic decan longitude lookup rejects non-finite inputs and normalizes
   longitudes.
6. Hermetic catalog/index/ruling-star functions preserve the 36-decan order.
7. Hermetic rising decan uses TT obliquity and agrees with house-engine
   Ascendant mapping for representative cases.
8. `DecanHour` and `DecanHoursNight` are frozen and validate hour/night
   partition invariants.
9. Decan night-hour computation preserves sunset-to-sunrise boundary truth in
   focused tests.

### 7. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\decanates.py moira\hermetic_decans.py tests\unit\test_decanates.py tests\unit\test_hermetic_decans.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_decanates.py tests\unit\test_hermetic_decans.py -q
```

---

## Part III - REST Admission Frontier

P9-12 may proceed to REST transport after this standard.

First admitted REST shape:

- direct-sync decanate routes for Chaldean face, triplicity decan, and Vedic
  drekkana
- Hermetic catalog and longitude routes
- Hermetic rising-decan and night-hour routes with explicit JD/location inputs

Deferred:

- chart-backed routes that derive planetary longitudes from a natal/event chart
- fixed-star positional routes for decan ruling stars
- interpretive decan meanings
