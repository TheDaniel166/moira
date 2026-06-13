# P11-07 Manazil / Lunar Mansions Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: direct Arabic lunar mansion catalog, position, bulk, and tradition lookup routes

## 1. Admission Boundary

P11-07 admits the narrow Manazil REST surface:

- `GET /v1/manazil/catalog`
- `POST /v1/manazil/position`
- `POST /v1/manazil/bulk`
- `GET /v1/manazil/traditions/{tradition}/mansions/{mansion_index}`

This is not chart-backed lunar mansion admission. It admits direct longitude
transport over the existing `moira.manazil` engine surface.

Deferred:

- chart-backed Moon mansion routes
- natal chart mansion profiles
- electional scoring
- mansion condition networks
- heliacal or fixed-star mansion variants
- Vedic nakshatra routes
- alternate non-equal mansion boundary systems

## 2. Governing Object

The admitted REST result is a `MansionPosition` from `moira.manazil`, serialized
for HTTP transport with explicit mansion system, computation mode, tradition,
and sidereal policy provenance.

The route family admits two computation modes:

- `tropical`: direct longitude assignment
- `sidereal`: explicit `jd_ut`, ayanamsa system, and ayanamsa mode

Both modes use the same 28 equal mansion boundaries. Variant traditions change
textual attribution only; they do not change the mansion boundary calculation.

## 3. Request Shapes

`GET /v1/manazil/catalog`

- no request body

`POST /v1/manazil/position`

- `longitude`: finite ecliptic longitude
- `mode`: `tropical` or `sidereal`, default `tropical`
- `jd_ut`: required when `mode=sidereal`
- `ayanamsa_system`: non-empty string, default `Lahiri`
- `ayanamsa_mode`: non-empty string, default `true`
- `tradition`: one of `al_biruni`, `abenragel`, `ibn_alarabi`, `agrippa`,
  `picatrix`

`POST /v1/manazil/bulk`

- `positions`: 1 to 500 named finite longitudes
- same `mode`, `jd_ut`, `ayanamsa_system`, `ayanamsa_mode`, and `tradition`
  fields as position requests

`GET /v1/manazil/traditions/{tradition}/mansions/{mansion_index}`

- `tradition`: admitted tradition name
- `mansion_index`: integer in `1..28`

## 4. Response Shape

Catalog responses return:

- all 28 mansion records
- mansion span in degrees
- admitted traditions
- provenance

Position responses return:

- mansion record
- degrees inside mansion
- original longitude
- computation longitude used for assignment
- provenance

Bulk responses return:

- keyed position responses
- total count
- provenance

Tradition lookup responses return:

- mansion index
- tradition
- nature
- signification
- provenance

## 5. Validation Rules

The admitted surface rejects:

- non-finite longitudes
- non-finite JDs
- sidereal requests without `jd_ut`
- empty bulk maps
- bulk maps above 500 entries
- empty bulk keys
- invalid tradition names
- mansion indices outside `1..28`

## 6. Provenance Rules

All admitted responses must preserve:

- mansion system: `Arabic_Manazil_28_equal_mansions`
- computational basis: `equal_division_360_by_28`
- default authority: `al_biruni_book_of_instruction`
- computation mode
- tradition
- requested longitude when applicable
- normalized longitude when applicable
- `jd_ut`, ayanamsa system, and ayanamsa mode when sidereal mode is used
- stage sequence

## 7. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\manazil.py moira_server\services\manazil.py moira_server\routers\manazil.py tests\server\test_server_manazil_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_manazil_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_manazil.py -q
```

The focused server tests verify:

- catalog route returns all 28 mansions and admitted traditions
- boundary behavior around `MANSION_SPAN`
- 360-degree wrap behavior
- tradition attribution selection
- sidereal mode rejects missing `jd_ut`
- non-finite longitude rejection
- bounded bulk position responses
- empty bulk keys and oversized bulk payload rejection
- tradition lookup response and invalid input rejection

Route registry audit after admission:

- exactly 4 admitted Manazil routes:
  - `/v1/manazil/catalog`
  - `/v1/manazil/position`
  - `/v1/manazil/bulk`
  - `/v1/manazil/traditions/{tradition}/mansions/{mansion_index}`

## 8. Completion Boundary

P11-07 is complete for direct Arabic lunar mansion catalog, position, bulk, and
tradition lookup transport.

It is not complete for chart-backed Moon mansion routes, natal mansion profiles,
electional scoring, mansion condition networks, heliacal/fixed-star mansion
variants, Vedic nakshatra transport, or alternate non-equal mansion systems.
