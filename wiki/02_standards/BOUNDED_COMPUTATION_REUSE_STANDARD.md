# Bounded computation reuse

**Status:** private engine infrastructure, first admitted by the VED-011 marriage
performance work. This standard governs exact reuse within one owned computation
scope. It does not establish a public cache API or cross-request service.

## Governing object

A memo retains the immutable result of one deterministic computation for the
same exact inputs and the same bound dependencies. Reuse removes duplicate
execution; it neither interpolates a result nor substitutes a nearby epoch,
smaller interval, different source or different numerical regime.

`moira/_bounded_memo.py` provides `bounded_memo(function, key=..., maxsize=...)`
and `binary64_key`. The module depends only on the standard library and has no
marriage, reader, calendar, frame or policy dependency. Every wrapper owns its
own bounded LRU, creating-thread identity and statistics. No global result
store retains finished requests or borrowed resources.

## Admission contract

1. Bind the callable to one stable dependency scope. A reader snapshot, source
   tables, correction policy, numerical regime and other unkeyed dependencies
   must remain fixed for that scope. A changed dependency requires a new scope
   or explicit `cache_clear`; the helper cannot infer scientific equivalence.
2. Define an exact **bytes** key containing every remaining input. Binary64
   fields must preserve signed zero and adjacent representable values. A
   differential key includes value endpoints, derivative endpoints, center
   endpoints, radius and centered flag. Coarse/precise mode is a separate input.
3. Reuse only immutable primitives, tuples and recursively immutable frozen
   dataclasses. Mutable containers, lazy iterators and mutable fields inside
   frozen vessels are rejected before insertion. Do not mutate frozen vessels
   through low-level Python escape hatches.
4. Keep resource admission, lifetime leases, source checks, cancellation and
   required accounting outside the memo. A hit does not replay side effects.
   The pure-computation wrapper must not become a route around a budget check.
5. Bound entry count and each result's size. `maxsize=0` retains no results;
   positive capacities evict the least recently used entry. This is an entry
   bound, not a claim of a universal process-memory limit.
6. Use the wrapper on its creating thread. Calls, statistics and invalidation
   from another thread are rejected, including cache hits. Independent requests
   on different threads create independent wrappers.
7. Exceptions propagate and are never cached. A failed evaluation must be tried
   again when requested; it cannot become a successful or permanently missing
   result through reuse. `None` may be a legitimate immutable result when the
   owning computation explicitly gives it that meaning.

`cache_info()` returns detached hit/miss/capacity/size observations;
`cache_clear()` releases entries and resets those observations. `__wrapped__`
retains the original callable for scoped differential validation. No runtime
configuration, optional dependency or public selector is introduced.

## First production use: marriage numerical evidence

The marriage request owns five pure-computation memos:

| Owner | Reused object | Capacity |
|---|---|---:|
| `AstronomyEnclosures` | TT differential to TDB differential | 4,096 |
| `AstronomyEnclosures` | TDB differential and record layout to all admitted record arguments | 8,192 |
| `FrameEnclosures` | TT differential to frame precession polynomials | 4,096 |
| `FrameEnclosures` | TT differential plus coarse/precise mode to full frame angles | 4,096 |
| `FrameEnclosures` | Angle differential to its ordered cosine/sine pair | 4,096 |

All rounded arithmetic schedules, branch families and source-domain checks are
retained. Coarse and precise modes share the same precession polynomials only;
their nutation enclosures remain distinct. Frame rotations still perform the
same ordered operations with the exact original trigonometric results.

The serving `pair()` owner still selects the reader/descriptor, checks source
identity and seams, and charges its work meter before asking for record
arguments. Public evaluation/reader/root counters keep their existing meaning.
These new memos remove unmetered duplicate arithmetic, not accounted work.

## Reuse by another feature

Another engine owner may use the same helper after declaring its own stable
dependencies, exact key, immutable result and finite capacity. A tested example
outside marriage wraps the existing `julian.tt_to_tdb` calculation with an
exact binary64 epoch key. That demonstrates independence from marriage; it does
not enable persistent caching of arbitrary ephemeris results.

Before another production admission, verify key distinctions, dependency
isolation, eviction/recomputation, failure retry, ownership/lifetime, budget
placement and exact output equivalence against the uncached computation. Keep
that product's independent authority and invariant tests. Regression identity
demonstrates preservation; it is not a new external astronomical oracle.

See the [marriage reuse validation receipt](../03_validation/MARRIAGE_ELECTION_REUSE_2026-10-10.md)
for measurements, source fingerprints and the executed acceptance corpus.
