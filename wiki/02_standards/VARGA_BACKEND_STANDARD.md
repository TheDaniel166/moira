# Moira Varga Backend Standard

Version: 1.2
Date: 2026-10-07
Status: Current engine/REST truth; bounded D60 source profiles

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
| `deity` | Nullable named D60 enrichment; generic D60 remains null |
| `d60_method` | Actual full-position D60 convention (`harmonic`, `pvr_textbook_linear` or `classical_derived_linear`); null for non-D60 or unknown legacy/manual metadata |
| `d60_source_references` (property) | Applied source/derivation chain, copied to REST; empty for non-D60 or unknown manual metadata |
| `d60_degree_attribution` (property) | `generic_harmonic`, `modern_composed`, `classical_derived`, or null for non-D60/unknown metadata; a derived policy is not a direct classical D60 degree prescription |

`VargaPoint` is frozen and slotted. This matches its machine contract: the
result vessel is read-only once constructed.
Its D60 receipt rejects a sign-only method or an inapplicable division.

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
| `D60Method` | Harmonic, Santhanam sign-only, composed PVR textbook/linear or classical-derived proportional selection |
| `D60SignResult` | Frozen sign-only placement; no mapped longitude/degree |

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
| `shashtiamsha` | D60 | harmonic default, `pvr_textbook_linear` or `classical_derived_linear` |
| `d60_sign` | D60 sign only | harmonic default, `bphs_santhanam_sign`, `pvr_textbook_linear` or `classical_derived_linear` |

The [D60 source standard](D60_SOURCE_ADMISSION_STANDARD.md) owns the selected
edition, sign formula, four corrected deity names, strict method applicability,
strength effects and limits of continuous-degree evidence. The Santhanam source
method is accepted by `d60_sign`, `varga_sign_index` at divisor 60 and Vimshopaka
groups containing D60. It is rejected by full-position wrappers and facade
methods before chart work. Harmonic numeric defaults are retained.
The separately named PVR profile admits full positions through scalar, chart
and Shodashvarga consumers with two source locators. It combines dated modern
primary prescriptions; direct classical continuous-D60-degree prescription is unestablished.
Its direct inputs are strict finite numbers and it cannot select another named
division. Deity naming still uses the identified Santhanam table.

The classical-derived profile is also complete through the same consumers.
It shares the proportional coordinates with a different reviewed source
chain and an explicit Moira derivation receipt. [Its adjudication](../06_roadmap/D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md)
separates D60 sign authority, general subdivision arithmetic, D12 fractional
correspondence, Raman's D9 degree notes and the D60 extension. Source-profile
groups normalize the shared input before evaluating other divisions, including
tiny negative wrap limits. This retains each division's own sign doctrine.

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

- Existing full-position helpers retain their numeric input behavior; this
  package is not a general Varga input audit. The new `d60_sign` helper rejects
  bool/string/nonfinite inputs explicitly and requires an actual `D60Method`.
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
- `tests/unit/test_d60_deities.py`
- `tests/unit/test_vedic_chara_d60_admission.py`
- `tests/server/test_vedic_chara_d60_admission.py`
- `tests/unit/test_d60_full_position.py`
- `tests/server/test_d60_full_position.py`
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

## Part III - Admitted REST Surface

Eight placement routes cover generic, named, Shodashvarga, direct batches and
three chart-derived shapes. The chart adapter owns tropical-to-sidereal
reduction and returns its ayanamsa/context provenance. Every point preserves
canonical nullable `deity`, applied `d60_method` and positional source locators
through the shared serializer.

`POST /v1/varga/d60/sign` exposes the typed sign-only result. Seven named/full
Shodashvarga request schemas admit `harmonic` and `pvr_textbook_linear`; source-only or unknown
selections receive HTTP 422 before chart derivation. Vimshopaka exposes the
selected D60 method for groups containing D60 and copies its actual receipt.
See [REST reference](../02_services/REST_API_REFERENCE.md) and the
[implementation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
and [full-profile receipt](../03_validation/D60_FULL_POSITION_VALIDATION_2026-10-07.md).
