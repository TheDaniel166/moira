# P11-U1 Catalog Umbrella Doctrine Decision

Version: 0.1
Date: 2026-06-13
Status: deferred for doctrine; discovery-only future candidate
Scope: Phase 11 generic `/v1/catalogs/*` route-family evaluation

## 1. Decision

P11-U1 does not admit `/v1/catalogs/*` routes in Phase 11.

The only future umbrella shape that remains eligible is a discovery-only
registry. It may tell clients which admitted catalog-bearing families exist,
where their family-native routes live, and what provenance rules govern them.

It must not perform cross-family search, object lookup, computation, position
calculation, catalog joins, or catalog-wide sweeps.

## 2. Reason For Deferral

Phase 11 admitted several catalog-bearing families, but they are not one
doctrinal class:

- fixed stars are star-catalog position identities
- variable stars are photometric catalog and state identities
- multiple stars are system-catalog and resolvability identities
- asteroids and comets distinguish known identity from loaded-kernel
  availability
- asteroid families use MPC catalog numbers and Nesvorny/PDS membership
- Manazil are doctrinal lunar mansion records, not physical objects
- planetary nodes expose method catalogs and orbital geometry products

A generic catalog route that returns "catalog items" would erase these
differences unless it is carefully restricted.

## 3. Doctrine Gate

Before any `/v1/catalogs/*` route is admitted, the design must answer:

1. Is the route discovery-only?
2. Does it avoid returning object records from family catalogs?
3. Does it preserve family-native route ownership?
4. Does it preserve each family's provenance vocabulary?
5. Does it distinguish catalog identity from computational availability?
6. Does it avoid cross-family search?
7. Does it avoid computation, positions, and derived states?
8. Does it avoid catalog-wide sweeps?

If any answer is no, the umbrella remains deferred.

## 4. Admissible Future Shape

A future discovery-only umbrella may expose:

- `GET /v1/catalogs`
- `GET /v1/catalogs/{family}`

The response may include:

- family slug
- display label
- phase admission unit
- phase status
- website verdict
- route family prefix
- admitted route names
- source doctrine document
- transport design document
- backend standard document where present
- provenance summary
- deferred expansion summary

The response must not include:

- catalog member records
- star names, asteroid names, comet names, mansion records, or node entries
- computed positions
- state or condition results
- kernel coverage lists
- cross-family search results
- arbitrary query text

## 5. Family-Native Ownership

Each family keeps its own route ownership:

- fixed, variable, and multiple stars stay under `/v1/stars/*`
- asteroids, subsets, and families stay under `/v1/asteroids/*`
- comets stay under `/v1/comets/*`
- Manazil stay under `/v1/manazil/*`
- orbital nodes stay under `/v1/nodes/*`

The umbrella may point to those surfaces. It may not replace them.

## 6. Rejected Route Shapes

The following shapes are rejected for Phase 11:

- `GET /v1/catalogs/search?q=...`
- `GET /v1/catalogs/{family}/items`
- `GET /v1/catalogs/{family}/items/{id}`
- `POST /v1/catalogs/positions`
- `POST /v1/catalogs/bulk`
- `POST /v1/catalogs/cross-reference`
- `POST /v1/catalogs/sweep`

These shapes would either duplicate family-native routes or flatten
family-specific provenance and availability semantics.

## 7. Verification Requirements For Future Admission

If a discovery-only umbrella is later admitted, verification must prove:

- route registry adds only discovery routes
- no object member records are returned
- no computation path is called
- no loaded-kernel coverage is inferred
- every advertised family links to an existing admitted family route prefix
- every advertised family links to its doctrine or transport document
- response shape is stable and bounded without pagination
- `/v1/catalogs/*` does not expose search query parameters

## 8. Current Completion Boundary

P11-U1 is complete as a doctrine decision.

It is not a route admission. The correct current status remains
`defer_for_doctrine`, with the narrowed future stance:

- discovery-only registry may be reconsidered later
- search, member lookup, computation, and catalog sweeps remain excluded
