# Post-Phase-10 Astrocartography Rendering Adapter Workflow

Version: 0.3
Date: 2026-06-12
Status: Implemented as internal server adapter; no public route added
Scope: Rendering-convenience materialization for admitted Astrocartography line
truth

This document defines the Astrocartography rendering-adapter operation. It is
an adapter workflow for making admitted Astrocartography line responses easier
for map clients to render. It is not a new computation family, not a new public
REST route family, and not a rendered map product.

This workflow is downstream of the selected minor-body and fixed-star
Astrocartography admission workflow. The adapter renders admitted line truth,
but it does not decide minor-body, comet, or fixed-star coordinate policy.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `docs/architecture/P10-01_ASTROCARTOGRAPHY_TRANSPORT_DESIGN.md`
- `docs/architecture/POST_PHASE10_ASTROCARTOGRAPHY_MINOR_BODY_STAR_ADMISSION_WORKFLOW.md`
- `wiki/02_standards/ASTROCARTOGRAPHY_BACKEND_STANDARD.md`

Authoritative computational source:

- `moira/astrocartography.py`

Authoritative REST source:

- the admitted `/v1/astrocartography/lines`
- the admitted `/v1/astrocartography/chart/lines`

---

## 1. Purpose

The adapter exists to help browser or website map layers draw the already
computed Astrocartography line truth without inventing a second computation.

Before implementation starts, the selected minor-body and fixed-star
Astrocartography admission workflow must establish what body classes are
admitted as line subjects and which remain direct-coordinate-only or deferred.

Permitted adapter responsibilities:

- consume existing `ACGLine` vessels or admitted Astrocartography line response
  shapes
- split sampled ASC/DSC curves at antimeridian crossings
- normalize point order and longitude representation for stable drawing
- materialize MC/IC meridians as explicit draw segments
- attach non-computational style hints by body and line type
- preserve the original Astrocartography provenance block

The adapter may reorganize geometry for drawing. It must not change the
astronomical meaning of a line.

---

## 2. Non-Goals

This workflow does not admit:

- new public computation routes
- GeoJSON route variants
- Web Mercator or any projection authority
- rendered images
- map tiles
- dense grids
- contour extraction
- atlas generation
- catalog-wide fixed-star, asteroid, comet, or small-body sweeps
- selected minor-body or fixed-star coordinate derivation policy
- async heavy-output workflows
- line recomputation outside `moira.astrocartography`

If any of those products become necessary, they require a separate route
admission design.

The relevant prerequisite for selected minor-body and fixed-star subjects is:

- `docs/architecture/POST_PHASE10_ASTROCARTOGRAPHY_MINOR_BODY_STAR_ADMISSION_WORKFLOW.md`

---

## 3. Governing Inputs

Allowed inputs:

- `ACGLine` objects produced by `moira.astrocartography`
- serialized line entries from the admitted Astrocartography REST responses
- the original Astrocartography provenance block
- optional caller-owned visual style preferences that do not affect geometry

Required line truth fields:

- `planet`
- `line_type`
- `points`
- `longitude`
- `jd_ut`
- `metadata`

The adapter must preserve the distinction between:

- MC/IC meridians, which are single longitude products
- ASC/DSC sampled curves, which are approximation samples
- computation provenance, which belongs to the Astrocartography response
- render metadata, which belongs only to the adapter output

---

## 4. Render Primitive Shape

The first implementation produces internal render primitives, not a new REST
response model.

Implemented primitive fields:

- `body`
- `line_type`
- `primitive_type`
- `segments`
- `source_index`
- `wrap_policy`
- `style_key`
- `source_provenance`

Implemented primitive types:

- `sampled_curve`
- `meridian`

Implemented wrap-policy values:

- `none`
- `antimeridian_split`

`segments` should be a list of point sequences. Splitting a curve at the
antimeridian creates multiple segments; it must not delete or recompute source
points.

---

## 5. Antimeridian Splitting Doctrine

The adapter should split sampled ASC/DSC curves when adjacent longitudes imply
an antimeridian crossing.

Required behavior:

- preserve original point order inside each segment
- keep latitude values unchanged
- normalize longitude representation consistently for the target renderer
- avoid interpolating new astronomical points unless a later design admits
  interpolation policy explicitly
- record `wrap_policy="antimeridian_split"` when a split occurs

Do not treat dateline splitting as a new Astrocartography calculation. It is a
drawing preparation step over existing samples.

---

## 6. Meridian Materialization Doctrine

MC and IC line products are longitude meridians. The adapter may materialize
them as draw segments spanning the renderable latitude range.

Required behavior:

- preserve the original meridian longitude
- mark `primitive_type="meridian"`
- avoid implying sampled curve precision where the source product is a meridian
- avoid clipping or projection logic unless owned by the consuming renderer

If a client needs projection-specific clipping, that is a renderer concern or a
later projection-adapter design.

---

## 7. Style Hint Doctrine

Style hints are allowed only as rendering metadata.

Allowed style hints:

- body key
- line-type key
- stroke category
- label category
- optional z-order bucket

Forbidden style behavior:

- changing computation by style
- hiding lines by default in a way that changes the returned truth
- encoding doctrine decisions in CSS-like names
- replacing provenance with display labels

---

## 8. Provenance Preservation

The adapter output must preserve the source Astrocartography provenance block
unchanged, or embed it as a clearly named `source_provenance` object.

Adapter-specific metadata may be added beside it:

- adapter name
- adapter version
- generated primitive count
- segment count
- wrap policy summary

Adapter metadata must never replace computational provenance.

---

## 9. Implementation Sequence

Implemented sequence:

1. Completed the selected minor-body and fixed-star Astrocartography admission
   workflow.
2. Added an internal server adapter; no public route was added.
3. Defined render primitive dataclasses.
4. Implemented meridian materialization for MC/IC.
5. Implemented antimeridian splitting for ASC/DSC sampled curves.
6. Added deterministic ordering by body, line type, and source order.
7. Preserved source provenance exactly.
8. Added structural tests.
9. Kept public routing unchanged.

---

## 10. Verification Requirements

Before implementation is considered complete, tests must prove:

- MC/IC meridians materialize without changing source longitude
- ASC/DSC sampled curves split at antimeridian crossings
- non-crossing sampled curves remain one segment
- point order is stable
- no source points are dropped
- source provenance is preserved
- style hints do not alter geometry
- primitive ordering is deterministic

Recommended test shape:

- pure structural unit tests over small synthetic line fixtures
- one integration-style test that adapts an actual admitted
  Astrocartography route response shape

No numerical Astrocartography validation should be added here unless the
underlying computation changes, which this workflow forbids.

---

## 11. Admission Rule

This workflow is implemented without creating a new REST route. The adapter
lives at:

- `moira_server/services/astrocartography_rendering.py`

The structural tests live at:

- `tests/server/test_server_astrocartography_rendering_adapter.py`

A public `/v1/astrocartography/*` rendering route may be considered only after
a separate admission design answers:

- whether the product is a render primitive, GeoJSON, projected geometry, or
  rendered map
- how output size is bounded
- whether async handling is required
- how provenance is preserved
- whether the route changes the REST contract or only repackages admitted line
  truth

Until then, the admitted Astrocartography REST truth remains the four P10-01
routes only.

---

## 12. Implementation Receipt

Implemented current adapter boundary:

- internal render packet and primitive dataclasses
- MC/IC meridian materialization
- ASC/DSC sampled-curve antimeridian splitting
- longitude normalization for rendering
- deterministic primitive ordering
- caller-owned style hints as render metadata only
- source provenance preservation by reference
- no projection ownership
- no GeoJSON route
- no public REST route

Verification run:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira_server\services\astrocartography_rendering.py tests\server\test_server_astrocartography_rendering_adapter.py
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_astrocartography_rendering_adapter.py tests/unit/test_astrocartography.py tests/server/test_server_astrocartography_routes.py -q
```

Observed verification result:

- 54 focused tests passed
- existing Astrocartography computational and route tests remained green
- no public route was added
