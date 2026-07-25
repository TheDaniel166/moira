# Moira Decans Backend Standard

Version: 1.1
Date: 2026-07-25
Status: Classical decanates admitted; Hermetic catalog in research quarantine

> **Containment correction.** Direct comparison with the currently inspected
> Liber Hermetis witness contradicts the name order attributed to it by
> `moira.hermetic_decans`. The Hermetic catalog and every result derived from
> that catalog are therefore excluded from the package root, facade, and REST
> application pending a source-led reconstruction.

## Governing Principle

Moira has one admitted decan subsystem and one quarantined research module:

- `moira.decanates` owns classical Chaldean faces, triplicity decans, and
  Vedic drekkana placement.
- `moira.hermetic_decans` preserves a disputed 36-name/ruling-star catalog and
  its lookup geometry for research only.

These surfaces must not be collapsed into one vague "decan" product. Only
`moira.decanates` may be presented as admitted doctrine. The quarantined module
must not appear in the REST route registry or curated Python import surfaces.

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

#### 1.2 Quarantined Hermetic decan candidate

A candidate record in the current research catalog is:

> One of 36 tropical ten-degree slots paired with a disputed name and
> ruling-star assignment that has not passed source admission.

This is a description of stored data, not a claim that the name, order,
star assignment, or tropical framing is historically correct.

#### 1.3 Quarantined catalog night partition

A **DecanHoursNight** is:

> A structural 12-part sunset-to-sunrise partition labeled from the
> quarantined catalog.

Its hour vessels preserve hour number, decan name, ruling star, and exact JD
boundaries.

---

### 2. Layer Structure

Current implemented layers and admission states:

```text
P1 - Decanate truth               (DecanatePosition)
P2 - Quarantined catalog data     (DECAN_NAMES, DECAN_RULING_STARS, list_decans)
P3 - Research lookup geometry     (decan_for_longitude, decan_index)
P4 - Research rising lookup       (decan_at)
P5 - Research night vessels       (DecanHour, DecanHoursNight)
P6 - Research night partition     (decan_hours)
P7 - Public containment           (excluded from root/facade/REST)
```

Layer boundary rules:

- Decanate routes must expose the producing doctrine.
- Tropical Chaldean and triplicity routes must not imply sidereal reduction.
- Vedic drekkana routes must expose JD and ayanamsa policy input.
- No Hermetic catalog, rising, or night-hour routes may be registered while
  the catalog remains quarantined.

---

### 3. Public Surface

#### `moira.decanates`

| Name | Meaning |
|---|---|
| `DecanatePosition` | Frozen vessel for one decanate computation |
| `chaldean_face(longitude)` | Tropical Chaldean face placement |
| `triplicity_decan(longitude)` | Tropical triplicity decan placement |
| `vedic_drekkana(longitude, jd, ayanamsa_system="Lahiri")` | Vedic D3 placement after sidereal reduction |

#### `moira.hermetic_decans` (direct research import only)

The symbols below are retained to support reconstruction and structural
testing. They are not part of `moira`, `moira.facade`, or the REST contract.

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
- The quarantined catalog code orders its stored labels by fixed tropical
  10-degree spans; this does not validate the historical catalog.
- Its night algorithm partitions the computed sunset-to-sunrise interval into
  twelve contiguous equal temporal hours; this validates geometry only.

#### 4.2 Failure doctrine

Current admitted and quarantined structural behavior:

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

The admitted decanate backend and quarantined research module are tested
separately through:

- `tests/unit/test_decanates.py`
- `tests/unit/test_hermetic_decans.py`

### 6. Validation Claims

The following admitted claims are currently verified:

1. `DecanatePosition` is frozen and enforces system/range invariants.
2. Chaldean faces preserve the declared Mars-starting planetary cycle.
3. Triplicity decans preserve same-element ruling-sign doctrine.
4. Vedic drekkana performs sidereal reduction and preserves traditional rulers.
5. Quarantined-module tests verify internal lookup, vessel, and astronomical
   partition consistency only. They do not validate the catalog against a
   primary historical source.

### 7. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\decanates.py moira\hermetic_decans.py tests\unit\test_decanates.py tests\unit\test_hermetic_decans.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_decanates.py tests\unit\test_hermetic_decans.py tests\server\test_server_decans_routes.py -q
```

---

## Part III - REST Admission Frontier

The admitted REST shape is:

- direct-sync decanate routes for Chaldean face, triplicity decan, and Vedic
  drekkana

Deferred:

- chart-backed routes that derive planetary longitudes from a natal/event chart
- fixed-star positional routes for decan ruling stars
- interpretive decan meanings
- every Hermetic catalog/longitude/rising/night-hour route until the catalog
  is reconstructed and separately admitted
