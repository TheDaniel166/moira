# P11-08 Planetary And Small-Body Nodes Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: planetary mean-element nodes and reader-backed geometric osculating node routes

## 1. Admission Boundary

P11-08 admits the narrow orbital node REST surface:

- `GET /v1/nodes/catalog`
- `POST /v1/nodes/planetary/mean`
- `POST /v1/nodes/planetary/mean/bulk`
- `POST /v1/nodes/geometric`

This is not lunar-node admission. It exposes orbital nodes and apsides over the
existing `moira.planetary_nodes` engine surface.

Deferred:

- lunar true-node and mean-node REST routes
- chart-backed node profiles
- nodal aspect networks
- catalog-wide small-body node sweeps
- rendered node maps
- asteroid/comet route widening
- small-body kernel manifest management

## 2. Governing Object

The admitted REST result is an `OrbitalNode` from `moira.planetary_nodes`,
serialized with explicit method, frame, kernel, and validity provenance.

The route family admits two computation methods:

- `mean_elements`: kernel-free Meeus / Simon mean orbital elements
- `geometric_osculating`: reader-backed osculating geometry derived from
  heliocentric state vectors

The two methods are intentionally separate. Mean planetary nodes are not a
fallback for geometric nodes, and geometric nodes are not treated as an
identity-catalog lookup.

## 3. Request Shapes

`GET /v1/nodes/catalog`

- no request body

`POST /v1/nodes/planetary/mean`

- `planet`: non-empty string accepted by `planetary_node`
- `jd`: finite Julian Day

`POST /v1/nodes/planetary/mean/bulk`

- `jd`: finite Julian Day
- `planets`: optional list of 1 to 8 non-empty planet names; omitted means all
  admitted mean-element planets

`POST /v1/nodes/geometric`

- `body`: non-empty body name for the active reader path
- `jd_ut`: finite UT Julian Day

## 4. Response Shape

Node responses return:

- body
- ascending node
- descending node
- perihelion
- aphelion
- inclination
- eccentricity
- semi-major axis
- provenance

Catalog responses return:

- admitted mean-element planet entries
- a reader-backed `loaded_spk_body` entry
- method availability and kernel requirement truth
- provenance

Bulk responses return:

- keyed mean-element node records
- total count
- provenance

## 5. Validation Rules

The admitted surface rejects:

- non-finite `jd`
- non-finite `jd_ut`
- empty planet names
- unknown mean-element planet names
- empty geometric body names
- Sun and Moon for geometric heliocentric nodes
- empty mean bulk lists
- mean bulk lists above 8 entries
- empty mean bulk entries

## 6. Provenance Rules

All admitted responses must preserve:

- method
- requested body or planet list
- returned body or planet list
- JD and JD scale
- frame: `heliocentric_tropical_ecliptic`
- coordinate basis
- kernel requirement
- kernel source
- validity note
- source module: `moira.planetary_nodes`
- stage sequence

Mean-element provenance must identify:

- `Meeus_Simon_mean_orbital_elements`
- `kernel_free_mean_element_table`
- the documented 2000 BCE to 3000 CE approximate validity envelope

Geometric provenance must identify:

- `osculating_state_vector_angular_momentum_and_eccentricity_vector`
- reader selection
- active-reader dependence
- loaded-body availability as a reader concern, not a REST catalog claim

## 7. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\nodes.py moira_server\services\nodes.py moira_server\routers\nodes.py moira_server\app.py moira_server\routers\__init__.py tests\server\test_server_nodes_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_nodes_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_chart_metadata_truth.py::test_moira_planetary_node_delegates_to_singular_wrapper tests\unit\test_api_surface_adversarial_audit.py -q
```

The focused server tests verify:

- catalog route declares distinct methods
- mean single route returns a node and explicit provenance
- mean routes reject empty, non-finite, and unknown inputs
- mean bulk defaults to the admitted eight-body mean-element set
- mean bulk rejects empty entries and oversized lists
- geometric route passes the server engine reader to `geometric_node`
- geometric route preserves osculating provenance
- geometric route rejects empty body, non-finite JD, and Sun

Route registry audit after admission:

- exactly 4 admitted node routes:
  - `/v1/nodes/catalog`
  - `/v1/nodes/planetary/mean`
  - `/v1/nodes/planetary/mean/bulk`
  - `/v1/nodes/geometric`

## 8. Completion Boundary

P11-08 is complete for bounded mean planetary node transport and single-body
reader-backed geometric osculating node transport.

It is not complete for lunar-node REST routes, chart-backed node profiles,
nodal interpretation, nodal aspect networks, catalog-wide small-body node
sweeps, rendered node maps, or small-body kernel manifest management.
