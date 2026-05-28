# Moira Threading And GIL Contract

## Purpose

This document defines the public threading contract for Moira's computational
surface.

It exists to answer four questions plainly:

1. what concurrent read behavior is supported
2. what lifecycle mutation behavior is not supported
3. what the native extension does with the Python GIL
4. how Moira should be deployed in threaded services

This is a usage contract, not a promise that every global mutation pattern is
safe under live server traffic.

---

## Core Rule

Moira admits concurrent read-heavy computation on a stable, already-initialized
kernel substrate.

Moira does not admit live mutation of global kernel lifecycle state during
concurrent computation.

That distinction governs the rest of this document.

---

## `SpkReader`

### Admitted

- Concurrent read calls on an already-open `SpkReader`
- Reuse of the same open `SpkReader` across multiple worker threads when all
  calls are pure reads
- Concurrent calls to `position()`, `position_and_velocity()`,
  `has_segment()`, `has_segment_at()`, `coverage()`, and `covered_bodies()`
  while the reader remains open

### Not Admitted

- Calling `close()` while other threads are actively reading from the same
  reader
- Treating `swap_reader()` or `reset_singleton()` as request-safe operations
  during live threaded traffic
- Publishing a reader to workers and then mutating its lifecycle underneath
  them

### Notes

- `SpkReader` is read-oriented and supports concurrent reads through an open
  reader
- The global singleton lifecycle is serialized with a module `RLock`, but that
  only protects replacement mechanics; it does not make live hot-swapping safe
  for in-flight computations

---

## `KernelPool`

### Admitted

- Concurrent read routing across already-constructed contained readers
- Use as a stable published read surface for worker threads

### Not Admitted

- Mutating the pool after it has been published to active worker threads
- Treating reader addition or replacement as a live concurrent service
  operation

---

## `Moira` Facade

### Admitted

- Pure read-only computational calls on a stable initialized `Moira` instance
- Cross-thread calls that only read through the established reader context

### Not Admitted

- Changing kernel/session configuration during concurrent request handling
- Treating kernel path reconfiguration as a request-safe operation
- Assuming facade reader routing makes global lifecycle mutation safe

### Notes

- The facade routes public calls through a stable reader override context
- That routing gives downstream code a consistent reader during the call
- It does not turn startup/test lifecycle APIs into safe live-traffic mutation
  APIs

---

## Singleton Helper Policy

These helpers exist, but they are not all equal in concurrency safety.

### Safe For Established Read Access

- `get_reader()`

### Startup/Test Lifecycle Only

- `set_kernel_path()`
- `swap_reader()`
- `reset_singleton()`
- `add_to_global_pool()`

These lifecycle helpers should be treated as initialization, test, or controlled
shutdown tools. They should not be used to hot-swap kernel state under active
threaded request load.

---

## Native GIL Policy

Moira's native extension uses `py::gil_scoped_release` on long-running pure
native work where it is safe to do so.

This generally includes:

- evaluator batch computation
- SPK segment evaluation
- native kernel-handle batch operations
- bulk geometry transforms
- event and search kernels
- payload and kernel I/O paths that perform native work without Python object
  access during the released section

The GIL is intentionally retained where the binding:

- consumes Python callbacks
- depends on Python-owned iteration during the active work section
- is short enough that release is not operationally meaningful
- constructs Python objects as the main body of work

So the rule is not "release the GIL everywhere". The rule is "release it on
material pure-native work, and retain it intentionally elsewhere".

---

## Recommended Service Deployment Pattern

### Preferred

1. Resolve kernel paths at startup
2. Initialize the reader or `Moira` instance once
3. Publish that stable read surface to worker threads
4. Serve only pure read computations during request handling

### Avoid

- calling `swap_reader()` in response to requests
- calling `reset_singleton()` while requests are in flight
- hot-replacing kernel state in a live threaded process

### Stronger Isolation

If deployment requires stronger operational isolation than shared-thread reads,
prefer worker processes over live singleton mutation.

---

## Operational Summary

### Safe

- concurrent reads on a stable initialized substrate
- cross-thread computational use of an open reader
- cross-thread computational use of a stable `Moira` instance

### Unsafe Or Unsupported

- concurrent lifecycle mutation of the global reader
- `close()` during in-flight reads
- live kernel hot-swapping in a threaded server

---

## Audit Basis

This contract is backed by:

- `SpkReader` and facade machine contracts
- native mutex audits for evaluator and kernel-handle internals
- native GIL-release audit tests
- singleton first-access concurrency witness tests

It should be updated if those audited truths change.
