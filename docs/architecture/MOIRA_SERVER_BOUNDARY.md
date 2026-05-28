# Moira Server Boundary

Version: 1.0
Date: 2026-05-28
Status: Governing boundary for any future REST or service packaging

This document defines the operational boundary for any HTTP or service surface
built on top of Moira.

It is narrower than the constitutional engine/service distinction in
`wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`.

That foundation document answers:

- what belongs in the engine
- what belongs in the service layer

This document answers:

- how a REST or service layer may expose the engine without distorting it
- what request-flow behaviors are forbidden
- how transport schemas must preserve computational truth

---

## 1. Core Rule

The server is an access surface, not a second engine.

Equivalent phrasing:

- engine owns truth
- server owns transport

The server may expose, serialize, batch, authenticate, rate-limit, and
orchestrate engine calls.

The server must not:

- redefine doctrine
- move computational policy into HTTP handlers
- hide engine truth behind convenience-only response shapes
- mutate global kernel lifecycle state during request handling

Operational reading:

- if a behavior can change astronomical or astrological truth, it belongs in
  the engine
- if a behavior only changes how truth is validated, serialized, delivered, or
  rate-limited, it may belong in the server

---

## 2. Server Responsibilities

The server layer may own:

- HTTP routing
- request validation and response serialization
- authentication, authorization, and rate limiting
- job control, retries, and progress reporting
- persistence, caching, and result storage
- endpoint grouping and versioning
- operational deployment packaging

These are transport and workflow concerns, not computational truth concerns.

Positive examples:

- validating an HTTP body into typed request fields before calling
  `planet_at(...)`
- serializing a `TransitEvent` into JSON for transport
- storing a completed batch job result under a request or tenant ID
- rate-limiting a `batch_progressions` endpoint without changing the
  progression doctrine itself

---

## 3. Engine Responsibilities That Must Stay In The Engine

The server must not absorb:

- astronomical math
- astrology doctrine
- search and solver logic
- typed canonical result semantics
- computational policy objects that change truth
- authority mappings and validation logic

If an endpoint needs a new computed truth primitive, that primitive belongs in
the engine first and only then may be exposed by the server.

---

## 4. Request Lifecycle Rule

Request handling must be read-only with respect to kernel lifecycle state.

Admitted in request flow:

- calling stable engine surfaces through an already-initialized reader or
  `Moira` instance
- pure read computation
- response shaping and serialization

Not admitted in request flow:

- `set_kernel_path()`
- `swap_reader()`
- `reset_singleton()`
- live kernel replacement
- request-triggered mutation of shared reader topology

The server must treat kernel lifecycle configuration as startup-time
initialization, not request-time behavior.

Operationally testable prohibition:

- no route handler, background task, dependency injector, or request-scoped
  helper may call `set_kernel_path()`, `swap_reader()`, or `reset_singleton()`
  after service startup completes
- no request may choose a different global kernel by mutating shared process
  state
- kernel selection, if the deployment ever admits multiple datasets, must be
  implemented by explicit process or instance partitioning, not by live
  singleton mutation

---

## 5. Deployment Model

The server must follow the documented threading contract in `docs/threading.md`.

Required deployment posture:

1. resolve kernel paths at process startup
2. initialize a stable reader or `Moira` instance once per process
3. publish that stable read surface to request handlers
4. serve read-only computation during request handling

Preferred model:

- one stable initialized substrate per worker process

Avoid:

- hot-swapping kernel state in a live threaded process
- treating singleton lifecycle helpers as request-safe operations

If stronger isolation is required, prefer process workers over in-process
mutation.

Positive examples:

- one FastAPI process starts, resolves the kernel once, creates one stable
  `Moira` instance, and reuses it for all read requests
- a worker pool starts multiple processes, each with its own stable initialized
  reader, and serves requests without cross-process kernel mutation

---

## 6. Schema Doctrine

Transport schemas must preserve visible computational truth.

That means:

- named fields must map cleanly onto engine semantics
- doctrinal distinctions must not be flattened away
- optional truth objects must remain inspectable where the engine exposes them
- stable typed result meaning must survive serialization

Relationship to canonical engine result types:

- the engine's typed vessels remain the canonical semantic source
- a transport schema is a serialized view of those canonical result types
- transport schemas may rename, flatten, or subset fields only when that view is
  explicit, documented, and versioned
- transport schemas must never become the hidden source of truth about what an
  engine object means

Examples:

- if the engine distinguishes geometric vs apparent quantities, the server must
  not collapse them into one unlabeled field
- if the engine exposes policy-conditioned truth, the server must not silently
  omit the policy basis
- if an event includes computation truth or classification that is part of the
  public result semantics, the server should preserve or explicitly version that
  transport shape rather than erase it

The server may offer simplified response profiles, but only as explicit,
versioned views over the canonical engine result.

Positive examples:

- exposing a `TransitEvent` as JSON with `body`, `jd_ut`, `direction`, and a
  nested `relation` object that preserves the engine's relation semantics
- exposing a simplified chart-summary endpoint that returns selected chart
  fields, while the full chart endpoint preserves the richer canonical result
  structure

Operationally testable prohibition:

- a schema must not merge distinct engine fields into one ambiguous field name
  when that merge destroys doctrinal meaning
- a schema must not drop policy-conditioned fields silently if those fields are
  part of the public engine truth for that result family

---

## 7. Error Doctrine

HTTP error handling must not falsify engine failure semantics.

The server may translate exceptions into transport envelopes, but it must do so
honestly.

Required behavior:

- validation errors stay validation errors
- missing kernel readiness is surfaced clearly
- unsupported doctrine is not reworded into misleading generic success
- internal failures are logged and surfaced without pretending the engine
  produced a valid result

The server may add request IDs, status codes, and operational metadata.
It must not rewrite engine truth or uncertainty into softer but false language.

Operationally testable prohibition:

- exception-to-HTTP translation must preserve the distinction between client
  input failure, missing kernel readiness, unsupported doctrine, and internal
  failure

---

## 8. Versioning Rule

Server API versioning must not drift silently away from engine semantics.

If the server introduces:

- reduced response shapes
- renamed fields
- compatibility shims
- deprecated views

those changes must be versioned at the transport layer and documented as
transport decisions, not implied to be engine semantics.

The engine remains the canonical semantic source.

Positive examples:

- `/v1/chart` may return a reduced summary view while `/v1/chart/full` or a
  later `/v2/chart` preserves additional canonical fields
- a transport alias such as `phase_type` may coexist with a more engine-shaped
  field name so long as the mapping is explicit and stable

---

## 9. First Endpoint Rule

The first server surface should expose stable, already-audited engine products.

Good first candidates:

- chart construction
- planetary positions
- transit and ingress search
- returns
- batch operations
- lunar phases
- visibility assessment

Positive examples:

- `POST /chart`
- `POST /transits/search`
- `POST /returns/solar`
- `POST /batch/charts`
- `POST /visibility/assessment`

Poor first candidates:

- endpoints that require live mutation of kernel state
- workflow-heavy ingestion or download orchestration
- endpoints whose response doctrine has not yet stabilized in the engine

---

## 10. Anti-Patterns

The following are forbidden server-layer anti-patterns:

- embedding astronomy or doctrine directly inside route handlers
- inventing server-only meanings for engine results
- silently swapping kernels because a request asked for a different dataset
- flattening typed engine truth into opaque generic blobs
- coupling auth, billing, or tenant logic back into engine modules

If one of these appears, the boundary has failed.

Balanced positive examples:

- a route handler validates input, calls one engine surface, and serializes the
  returned canonical vessel
- a job runner coordinates several engine calls, stores progress metadata, and
  leaves all computational truth inside engine modules

---

## 11. Constitutional Summary

Moira computes truth.

The server transports that truth.

If a server feature changes what Moira means, it belongs back in the engine
design process first.
