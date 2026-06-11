# Moira Varga Backend Standard

Version: 1.0
Date: 2026-06-11
Status: Current implementation truth; P9-11 REST admission prerequisite

## Governing Principle

The Moira Varga backend is a Vedic divisional-chart placement subsystem. It
maps caller-supplied sidereal ecliptic longitudes into the currently implemented
Shodashvarga divisions and preserves the resulting varga sign, symbol, degree,
division number, and mapped varga longitude in an immutable `VargaPoint`.

This document reflects current implementation truth. It does not claim that the
module performs tropical-to-sidereal conversion, derives chart positions, or
implements every specialized school-specific varga variant.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Varga point

A **VargaPoint** in Moira is:

> One body's placement inside one Vedic divisional chart, computed from one
> caller-supplied sidereal longitude.

| Field | Meaning |
|---|---|
| `varga_name` | Display name of the division |
| `varga_number` | Division number, such as `9` for Navamsha |
| `longitude` | Normalized source longitude |
| `varga_longitude` | Mapped longitude in the varga sign |
| `sign` | Varga sign name |
| `sign_symbol` | Varga sign symbol |
| `sign_degree` | Degree within the varga sign |

`VargaPoint` is frozen and slotted. This matches its machine contract: the
result vessel is read-only once constructed.

#### 1.2 Generic varga formula

The generic formula divides each 30-degree sign into `n` equal segments and
maps the segment index through the zodiac:

```text
segment_idx = floor(longitude / (30 / n))
sign_idx = segment_idx % 12
sign_degree = (longitude % (30 / n)) * n
```

This is the active computation for:

- `calculate_varga(...)`
- `navamsa`
- `saptamsa`
- `dashamansa`
- `dwadashamsa`
- `trimshamsa`
- `shashthamsha`
- `ashtamsha`
- `shodashamsha`
- `vimshamsha`
- `chaturvimshamsha`
- `shashtiamsha`

#### 1.3 Parashari sign-offset wrappers

The backend also implements specific sign-offset rules for five divisions:

- `hora` / D2
- `chaturthamsha` / D4
- `saptavimshamsha` / D27
- `khavedamsha` / D40
- `akshavedamsha` / D45

These wrappers compute the varga sign by their declared Parashari offset rule
and then materialize a `VargaPoint`.

---

### 2. Layer Structure

The Varga backend is intentionally small:

```text
P1  - Truth preservation             (VargaPoint)
P3  - Inspectability                 (__repr__)
P10 - Hardening                      (range tests, frozen vessel contract)
P12 - Public API curation            (__all__, root/vedic/classical/facade exports)
```

Layer boundary rules:

- All public computation functions consume sidereal longitudes.
- The module does not compute ayanamsa.
- The module does not compute chart positions.
- Wrapper functions delegate result materialization to `calculate_varga(...)` or
  `_build_varga_point(...)`.
- A REST adapter must not hide tropical-to-sidereal reduction inside this
  module's transport family.

---

### 3. Public Surface

All public names are declared in `moira/varga.py`.

#### Vessel

| Name | Meaning |
|---|---|
| `VargaPoint` | Frozen result vessel for one divisional placement |

#### Computation functions

| Function | Division | Rule |
|---|---:|---|
| `calculate_varga` | arbitrary `n` | generic |
| `navamsa` | D9 | generic |
| `saptamsa` | D7 | generic |
| `dashamansa` | D10 | generic |
| `dwadashamsa` | D12 | generic |
| `trimshamsa` | D30 | generic computational alternative |
| `hora` | D2 | Parashari odd/even Cancer/Leo rule |
| `chaturthamsha` | D4 | Parashari sign-offset rule |
| `shashthamsha` | D6 | generic |
| `ashtamsha` | D8 | generic |
| `shodashamsha` | D16 | generic |
| `vimshamsha` | D20 | generic |
| `chaturvimshamsha` | D24 | generic |
| `saptavimshamsha` | D27 | Parashari triplicity-start rule |
| `khavedamsha` | D40 | Parashari odd/even Aries/Libra rule |
| `akshavedamsha` | D45 | Parashari odd/even Aries/Capricorn rule |
| `shashtiamsha` | D60 | generic |

---

### 4. Determinism and Failure Doctrine

#### 4.1 Determinism

- Longitudes are normalized with modulo 360.
- Sign order is Aries through Pisces, index `0` through `11`.
- `sign_degree` is always intended to remain in `[0, 30)`.
- `varga_longitude` is always intended to remain in `[0, 360)`.
- The same longitude and division always produce the same `VargaPoint`.

#### 4.2 Failure doctrine

Current implementation truth:

- Public functions do not currently reject non-finite longitudes explicitly.
- REST transport must reject non-finite longitude inputs before calling the
  engine.
- `VargaPoint` is immutable after construction.

No dedicated `validate_varga_output(...)` helper is currently exposed. The
current backend hardening is provided by vessel immutability, output range
tests, boundary tests, and wrapper-specific rule tests.

---

## Part II - Validation Codex

### 5. Validation Scope

The Varga backend is currently validated through:

- `tests/unit/test_varga.py`
- `tests/unit/test_shodashvarga.py`
- public API surface checks in `tests/unit/test_api_surface_adversarial_audit.py`

### 6. Validation Claims

The following claims are currently verified:

1. D1 identity behavior is preserved.
2. Generic segment boundaries advance signs and reset degrees correctly.
3. 360-degree wrapping and periodicity are preserved.
4. `sign_degree` is scaled from segment remainder.
5. Convenience wrappers preserve declared varga names and numbers.
6. Output `varga_longitude` and `sign_degree` ranges hold across samples.
7. `VargaPoint.__repr__` exposes name, division, sign, and minutes.
8. `VargaPoint` is immutable.
9. D2, D4, D27, D40, and D45 sign-offset rules are covered by focused tests.
10. Generic Shodashvarga wrappers preserve names, division numbers, ranges, and
    longitude wrapping.
11. Sign names and symbols remain consistent.

### 7. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\varga.py tests\unit\test_varga.py tests\unit\test_shodashvarga.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_varga.py tests\unit\test_shodashvarga.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_doctrine_surfaces.py tests\unit\test_api_surface_adversarial_audit.py -q
```

---

## Part III - REST Admission Frontier

P9-11 may proceed to REST transport design after this standard.

First admitted REST shape should be direct-sync:

- caller-supplied sidereal longitude
- explicit varga selector
- direct single-varga route
- named Shodashvarga route
- optional batch route for multiple bodies or multiple vargas

Chart-backed convenience routes should be deferred until the server adapter
explicitly owns tropical-to-sidereal reduction and records ayanamsa policy
truth.
