# P11-06 Asteroid Families And Subsets Transport Design

Version: 0.1
Date: 2026-06-13
Status: admitted
Scope: bounded asteroid subset convenience and Nesvorny family membership REST routes

## 1. Admission Boundary

P11-06 admits the narrow asteroid subset and family REST surface:

- `GET /v1/asteroids/subsets`
- `GET /v1/asteroids/subsets/{subset}/list`
- `POST /v1/asteroids/subsets/{subset}/positions`
- `GET /v1/asteroids/families/by-number/{number}`
- `GET /v1/asteroids/families/{family_name}/members`
- `POST /v1/asteroids/families/chart`

This is not full asteroid-family interpretation transport. It admits bounded
identity, membership, and selected subset-position convenience routes.

Deferred:

- family-wide position sweeps
- resonance/aspect-network transport
- rendered family maps
- asteroid-family astrocartography
- arbitrary family catalog search
- photometry
- topocentric or equatorial subset products
- kernel build, shard, and manifest-management routes
- edits to the bundled family catalog

## 2. Governing Objects

P11-06 has two distinct governing objects.

Named subset routes govern curated Moira asteroid identity sets:

- `classical`
- `main_belt`
- `centaurs`
- `tnos`

These routes use asteroid names and NAIF IDs, and subset positions delegate to
the admitted P11-04 asteroid position transport.

Family routes govern Nesvorny/PDS dynamical-family membership:

- one MPC asteroid number to one family name, or no family
- one family name to bounded MPC-number members
- one supplied list of MPC numbers to grouped family membership

These routes use MPC catalog numbers, not NAIF IDs.

## 3. Request Shapes

`GET /v1/asteroids/subsets`

- no request body

`GET /v1/asteroids/subsets/{subset}/list`

- `subset`: one of `classical`, `main_belt`, `centaurs`, `tnos`
- `q`: optional name or NAIF contains filter
- `limit`: integer bounded to `1 <= limit <= 500`

`POST /v1/asteroids/subsets/{subset}/positions`

- `subset`: one of `classical`, `main_belt`, `centaurs`, `tnos`
- `dt`: timezone-aware datetime
- `bodies`: optional 1 to 500 subset body names or NAIF IDs; omitted means all
  members of the subset
- `skip_missing`: boolean, default `true`

`GET /v1/asteroids/families/by-number/{number}`

- `number`: positive MPC catalog number

`GET /v1/asteroids/families/{family_name}/members`

- `family_name`: exact Nesvorny family name
- `offset`: integer bounded to `>= 0`
- `limit`: integer bounded to `1 <= limit <= 500`

`POST /v1/asteroids/families/chart`

- `numbers`: 1 to 500 positive MPC catalog numbers

## 4. Response Shape

Subset registry responses return:

- subset slug
- display label
- source catalog
- member count
- stage sequence

Subset list responses return:

- subset slug and label
- body names
- NAIF IDs
- loaded-kernel availability by NAIF ID
- provenance with subset source module, catalog source, query, limit, and stage
  sequence

Subset position responses return:

- subset slug and label
- datetime
- per-body admitted asteroid position responses
- missing entries
- sovereignty aggregate
- subset provenance recording requested bodies, resolved subset bodies, returned
  bodies, missing bodies, loaded-kernel truth, and stage sequence

Family lookup responses return:

- MPC number
- family name or `null`
- Nesvorny/PDS provenance

Family members responses return:

- family name
- bounded member list
- total available count
- returned count
- Nesvorny/PDS provenance

Family chart grouping responses return:

- grouped family mapping
- ungrouped MPC numbers
- Nesvorny/PDS provenance

## 5. Validation Rules

The admitted surface rejects:

- unknown subset slugs
- list/member limits outside `1..500`
- negative family offsets
- non-positive family lookup numbers
- naive subset position datetimes
- empty subset position body entries
- empty family chart lists
- non-positive family chart numbers
- family chart lists above 500 numbers

Out-of-subset bodies in subset position requests are reported in `missing` when
`skip_missing=true`; otherwise the lookup failure is allowed to surface.

## 6. Provenance Rules

Subset routes must record:

- subset source module
- subset catalog source
- loaded-reader availability truth where relevant
- stage sequence

Family routes must record:

- `NASA_PDS_ast_nesvorny_families_v2_2015`
- `MPC_catalog_number`
- `moira.asteroid_families`
- stage sequence

Family names are catalog labels. Similar names, such as `Koronis`,
`Koronis(2)`, and `Karin`, must remain distinct.

## 7. Verification

Admission verification:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\models\asteroids.py moira_server\services\asteroids.py moira_server\routers\asteroids.py tests\server\test_server_small_body_list_routes.py
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_small_body_list_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_asteroid_api.py -q
```

The focused server tests verify:

- subset registry serialization
- subset list kernel availability truth
- unknown subset and invalid limit rejection
- subset position delegation and provenance
- out-of-subset missing behavior
- timezone and empty-body rejection
- family lookup provenance
- bounded family member responses
- invalid family bounds rejection
- family chart grouping with live catalog distinctions
- invalid family chart list rejection

Route registry audit after admission:

- exactly 9 admitted asteroid routes:
  - `/v1/asteroids/position`
  - `/v1/asteroids/bulk`
  - `/v1/asteroids/list`
  - `/v1/asteroids/subsets`
  - `/v1/asteroids/subsets/{subset}/list`
  - `/v1/asteroids/subsets/{subset}/positions`
  - `/v1/asteroids/families/by-number/{number}`
  - `/v1/asteroids/families/{family_name}/members`
  - `/v1/asteroids/families/chart`

## 8. Completion Boundary

P11-06 is complete for bounded subset convenience and family membership
transport.

It is not complete for family-wide position sweeps, resonance/aspect networks,
rendered family maps, family astrocartography, photometry, topocentric or
equatorial subset products, or kernel-management routes.
