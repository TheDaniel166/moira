# Moira 6.1.0 - Contract and Release Integrity

**Release date:** 2026-07-28

**Public upgrade path:** 6.0.1 to 6.1.0

Moira 6.1.0 adds authoritative dated monthly profections and strengthens the
engine's public-contract, aspect-pattern, Python-compatibility, and small-body
release boundaries. It is a minor release because it adds typed capability
while preserving admitted computations and valid 6.0.1 requests.

The 9,974-name asteroid identity expansion shipped in 6.0.1. Version 6.1.0
inherits that registry and adds the release-integrity and collision policies
needed to consume it safely.

## Highlights

- Twelve exact dated monthly-profection intervals between consecutive civil
  anniversaries.
- A chronology-aware Hellenistic chart profile with stricter cross-component
  truth and provenance invariants.
- Explicit aspect motion state, stable whole-sign seam behavior, deterministic
  pattern edges, and repaired Grand Sextile detection.
- Immutable asteroid and comet release receipts with complete checksum,
  provenance, and loader-admission policy.
- Fail-closed cross-family small-body identity resolution.
- A Python 3.10-compatible optional server surface and preserved acceptance of
  the deprecated Decennial `deep_subdivision_method: null` request field.

## Dated Monthly Profections

`profection_chronology(...)` constructs twelve contiguous, half-open intervals
between exact consecutive civil anniversaries. The admitted interval policy is:

`equal_twelfths_of_civil_anniversary_year`

Each result records:

- civil timezone and available timezone-data provenance;
- interval, leap-day, and repeated-time policies;
- exact query, annual-start, and annual-end UTC instants;
- matching Julian Day values;
- twelve ordered interval boundaries;
- the active month index; and
- each month's profected longitude, sign, and domicile lord.

The chronology is identified as a `computational_projection`. It is not
presented as Valens IV.28's separate day-Sun/night-Moon distance method, twelve
fixed 30-day periods, a 365.25-day quotient, or twelve civil-calendar months.

### Civil-time failure semantics

Civil anniversaries preserve the natal local wall clock:

- a February 29 nativity requires the explicit `february_28` or `march_1`
  policy;
- a wall time inside a daylight-saving gap fails closed;
- a repeated wall time requires `earlier_occurrence` or `later_occurrence`;
- Moira never silently moves a nonexistent local time or guesses a fold; and
- the exact natal instant remains the age-zero anchor.

Named IANA lookup uses Python's standard-library `zoneinfo` interface. Moira
does not download timezone data or claim a database version the host does not
expose.

## Unified Hellenistic Profile

`HellenisticChartProfile` advances to the chronology-aware v2 method and
rejects cross-component contradictions involving:

- datetime and Julian Day identity;
- Whole Sign house composition;
- angles, sect, and the ordered classical seven;
- aspect identity and overcoming policy;
- foundational-lot evaluated and unresolved partitions;
- profection chronology and activation;
- Decennial sect and L1/L2 assembly;
- Zodiacal Releasing policy and Fortune angularity; and
- method, source, inclusion, exclusion, and provenance receipts.

The profile remains non-interpretive and score-free.

### Closed Hellenistic exclusions

The following are settled exclusions, not unfinished 6.1 work:

- Hermetic fixed-star attribution and product geometry;
- the removed `decan_hours()` experiment;
- Decennial L3/L4 and named Valens/Hephaistio deep methods;
- Triacontaeteris;
- Valens distribution interpretation; and
- synthetic Hellenistic condition scores.

The source-reconstructed Gundel/Harley names and planetary faces remain
research data. They are absent from curated root, classical, facade, REST, and
OpenAPI product surfaces.

## Aspect and Pattern Contracts

Aspect and pattern calculation now preserves stable observable semantics at
the public boundary:

- longitudes normalize consistently at the `0`/`360` seam, including
  IEEE-754-scale whole-sign boundary cases;
- `AspectData.motion_state` explicitly distinguishes applying, exact,
  separating, stationary, and indeterminate results;
- stationary truth is body-relative rather than inferred from one absolute
  speed threshold;
- duplicate aspect edges resolve deterministically;
- `AspectGraphNode.aspect_counts` exposes an immutable compatibility-safe view
  while legacy `family_counts` remains available; and
- Grand Sextile detection requires and reports the complete closed geometry.

These changes repair edge behavior without removing existing aspect names or
legacy facade entry points.

## Small-Body Release and Identity Integrity

### Immutable catalog releases

Asteroid and comet distributions now have the same release-grade identity
model:

- immutable catalog ID and version;
- exact manifest SHA-256;
- per-file byte length and SHA-256;
- `SHA256SUMS`;
- archive checksum;
- provenance notice and source revision; and
- a loader gate that rejects incomplete, mismatched, or zero-byte shards.

Generated identity files are byte-stable across Windows and POSIX checkouts,
and website publication consumes only tracked Git sources. The metadata-only
manifests retained in the wheel are now byte-identical to the immutable
manifests named by those identity receipts. They remain metadata until at
least one referenced BSP shard is installed; automatic discovery does not
mistake a manifest-only wheel for a position-capable catalog.

The authoritative asteroid release remains:

| Field | Receipt |
|---|---|
| Catalog | `moira-asteroids` |
| Version | `2026.07.27.1` |
| Bodies | 9,974 |
| Shards | 399 |
| Sampling | 10-day step, 7-node window |
| Manifest SHA-256 | `0560302f877a46cebc550376ae70665fefab84801078181cf3c4199ce86d49d0` |

The authoritative comet release is:

| Field | Receipt |
|---|---|
| Catalog | `moira-comets` |
| Version | `2026.07.28.1` |
| Bodies | 497 |
| Shards | 20 |
| Sampling | 30-day step, 5-node window |
| Manifest SHA-256 | `31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1` |

### Cross-family name collisions

Asteroid and comet catalogs currently share the normalized names `Halley` and
`Encke`. Unified position, chart, progression, void-of-course, and
astrocartography paths no longer guess which family the caller intended.

- `asteroid:Halley` selects asteroid Halley.
- `comet:Halley` and `1P/Halley` select the comet.
- `asteroid:Encke` selects asteroid Encke.
- `comet:Encke` and `2P/Encke` select the comet.
- An unqualified colliding name fails with typed ambiguity evidence.

Dedicated asteroid or comet routes remain family-scoped and retain their
existing convenient aliases.

## Python and REST Compatibility

Moira continues to support Python 3.10 through 3.14. Every optional-server enum
uses Moira's `StrEnum` compatibility boundary, and the release workflow imports
and constructs the server on the minimum supported Python.

The Decennial request boundary remains L1/L2 only:

- `levels` accepts 1 or 2;
- omission of `deep_subdivision_method` is valid;
- explicit `deep_subdivision_method: null` remains valid for 6.0/6.0.1 client
  compatibility;
- every named deep method remains invalid; and
- response compatibility receipts remain present and fixed to `null`.

## Validation Boundary

The release gate covers:

- Hellenistic source goldens, generated inventories, profile invariants, REST,
  serializer, and OpenAPI parity;
- civil-anniversary continuity, UTC/JD agreement, leap-day, gap, repeat, and
  active-boundary behavior;
- aspect seam, motion-state, deterministic pattern, and Grand Sextile cases;
- asteroid/comet identity, release receipt, loader, and collision policies;
- Python 3.10 optional-server import and OpenAPI construction;
- public API, documentation, and generated-publication drift; and
- source, wheel, and installed-artifact release identity.

No new broad numerical ephemeris-parity claim is made for the separately
distributed small-body kernels.

## Installation

```text
moira-astro==6.1.0
```

For the optional server:

```text
moira-astro[server]==6.1.0
```

Read `COMPATIBILITY_NOTES_6.1.0.md` before regenerating typed clients or
upgrading an application that caches computed chart responses.
