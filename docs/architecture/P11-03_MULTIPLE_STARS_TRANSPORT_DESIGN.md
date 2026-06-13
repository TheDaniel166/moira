# P11-03 Multiple Stars Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded multiple-star catalog, list, and selected-system state REST
routes

## 1. Admission Boundary

P11-03 admits the narrow multiple-star REST surface:

- `GET /v1/stars/multiple/list`
- `GET /v1/stars/multiple/{name}`
- `POST /v1/stars/multiple/state`

This is not broad multiple-star catalog expansion. It admits HTTP transport
over Moira's curated Multiple Star Systems Oracle.

Deferred:

- catalog-wide state sweeps
- rendered binary-orbit diagrams
- multi-aperture observing plans
- arbitrary custom telescope/seeing policies beyond Dawes aperture
- new catalog ingestion or exhaustive WDS/INT4 exposure

## 2. Governing Object

The admitted REST result is derived from `moira.multiple_stars`.

The transport layer does not recompute orbital doctrine. It performs:

1. request validation
2. datetime to Julian Day conversion for state routes
3. catalog resolution through `multiple_star`
4. selected state computation through `components_at` and `is_resolvable`
5. response serialization with explicit provenance

## 3. Request Shapes

`GET /v1/stars/multiple/list`

- `q`: optional search term
- `system_type`: optional system-type filter
- `limit`: bounded by the router, `1 <= limit <= 500`

`GET /v1/stars/multiple/{name}`

- `name`: multiple-star system name or designation

`POST /v1/stars/multiple/state`

- `dt`: timezone-aware datetime
- `system`: non-empty multiple-star system name or designation
- `aperture_mm`: finite telescope clear aperture, `0.0 < value <= 10000.0`

## 4. Response Shape

Catalog responses preserve:

- canonical system name and designation
- aliases
- system type
- component records
- orbital elements or reference separations
- catalog combined magnitude
- computed combined magnitude
- classical quality
- note
- provenance

State responses preserve:

- catalog system response
- separation in arcseconds
- position angle in degrees
- requested-aperture resolvability
- 100 mm and 200 mm resolvability snapshots
- dominant component
- component snapshot
- provenance

The provenance object records:

- catalog sources: WDS, INT4, 6OC, and named literature sources
- system type
- orbit model
- orbital doctrine
- Dawes-limit resolvability doctrine
- combined-magnitude doctrine
- primary orbit label and uncertainty
- requested datetime, normalized UTC datetime, and JD for state routes
- requested aperture and computed Dawes limit
- transport stage sequence

## 5. Validation Rules

The admitted surface rejects:

- naive datetimes on state routes
- empty system names on state routes
- non-positive apertures
- non-finite apertures
- apertures above 10000 mm
- list limits outside `[1, 500]`

Unknown multiple-star names remain semantic lookup failures from the underlying
Multiple Star Systems Oracle.

## 6. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\stars.py moira_server\services\stars.py moira_server\serializers\stars.py moira_server\routers\stars.py tests\server\test_server_stars_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_stars_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_multiple_stars.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_multiple_stars_external_reference.py -q
```

Route registry audit after admission:

- 269 non-documentation routes
- 265 versioned `/v1` routes
- 12 `/v1/stars/*` routes
- exactly 3 admitted multiple-star routes:
  - `/v1/stars/multiple/list`
  - `/v1/stars/multiple/{name}`
  - `/v1/stars/multiple/state`

The route tests verify:

- route registration
- catalog record fidelity
- component and orbital element preservation
- computed combined magnitude preservation
- state parity against `components_at`, `angular_separation_at`,
  `position_angle_at`, and `is_resolvable`
- provenance preservation
- adversarial request rejection for datetime, system name, aperture, and list
  limit bounds

## 7. Admission Verdict

P11-03 is admitted as a bounded synchronous multiple-star catalog/state REST
family.

Later multiple-star work is explicit expansion, not implicit widening of this
admitted surface.
