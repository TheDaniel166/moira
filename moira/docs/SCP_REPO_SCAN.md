# SCP Repository Scan

## Purpose

This document applies the
[`00_SUBSYSTEM_CONSTITUTIONALIZATION_PROCESS.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/00_SUBSYSTEM_CONSTITUTIONALIZATION_PROCESS.md)
doctrine across the current Moira repository and identifies which subsystems
would benefit most from constitutionalization next.

This is not a popularity ranking and not a file-size ranking.

It is a scan for:

- real computational cores
- existing doctrine hidden in code
- meaningful result vessels and service surfaces
- enough subsystem coherence that SCP can apply cleanly
- enough maturity that the next phase can be justified without phase-skipping

**Last updated**: 2026-03-22

---

## 1. Scan Doctrine

SCP applies most strongly to subsystems that already exhibit most of these:

- a real authoritative engine
- non-trivial doctrine or scoring logic
- result vessels or service objects
- helper growth around a coherent domain
- existing test surface
- some public usage or package exposure

SCP applies less strongly to files that are primarily:

- pure math primitives
- thin wrappers over another engine
- catalog/data access modules
- auxiliary search helpers that belong to a larger engine

Those files may still be hardened, but usually as part of a larger subsystem
rather than as independent constitutional targets.

---

## 2. Already Constitutionalized or Close

These subsystems already have explicit backend constitutions or are operating
close to that standard.

### Fully constitutionalized

- [`aspects.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/aspects.py)
  Documented by [`ASPECT_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/ASPECT_BACKEND_STANDARD.md)
- [`houses.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/houses.py)
  Documented by [`HOUSES_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/HOUSES_BACKEND_STANDARD.md)
- [`parans.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/parans.py)
  Documented by [`PARANS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/PARANS_BACKEND_STANDARD.md)
- [`dignities.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/dignities.py)
  Documented by [`DIGNITIES_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/DIGNITIES_BACKEND_STANDARD.md)
- [`lots.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/lots.py)
  Documented by [`LOTS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/LOTS_BACKEND_STANDARD.md)
- [`patterns.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/patterns.py)
  Documented by [`PATTERNS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/PATTERNS_BACKEND_STANDARD.md)
- [`transits.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/transits.py)
  Documented by [`TRANSITS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/TRANSITS_BACKEND_STANDARD.md)
- [`progressions.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/progressions.py)
  Documented by [`PROGRESSIONS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/PROGRESSIONS_BACKEND_STANDARD.md)
- [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py)
  Documented by [`ECLIPSE_MODEL_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/ECLIPSE_MODEL_STANDARD.md)

### Self-constitutionalized (architecture freeze + validation codex in module)

- [`chart_shape.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/chart_shape.py)
  Contains a full architecture-freeze declaration, frozen threshold constants,
  detection-order rationale, handle-in-gap doctrine, and a validation codex in
  the module docstring. Has curated `__all__` and a public API test.

---

## 3. Highest-Value Next SCP Targets

### Tier 1 - Best next candidates

#### 3.1 Fixed Stars / Unified Star Surface

- [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py)
- [`stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
- possibly [`gaia.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/gaia.py)

Why it is now the best next candidate:

- the star surface already spans multiple files and needs explicit ownership
  boundaries
- `fixed_stars.py` contains doctrine beyond catalog lookup, especially heliacal
  phenomena
- constitutionalizing this cluster would close the heliacal wiring gap and
  stabilize the unified star API

### Tier 2 - High-value but heavier targets

#### 3.2 Synastry

- [`synastry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/synastry.py)

Why it matters:

- synastry is now an integration point over several constitutionalized engines
  such as aspects, houses, lots, transits, and progressions
- a constitution here would be a meta-constitution over already-governed
  sources

Why it still waits:

- the test surface is still very thin
- it needs broader coverage before a meta-constitutional pass is safe

---

## 4. Medium-Value SCP Targets

### 4.1 Timelords (Firdaria + Zodiacal Releasing)

- [`timelords.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/timelords.py)

Has non-trivial time-lord doctrine but still lacks a dedicated test file strong
enough to anchor a constitutional pass.

### 4.2 Dasha

- [`dasha.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/dasha.py)

Vimshottari period doctrine is real and significant, but the subsystem still
needs a dedicated test anchor.

### 4.3 Sothic

- [`sothic.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sothic.py)

Coherent and doctrinally meaningful, but less central than the remaining
star/timing candidates.

### 4.4 Variable Stars

- [`variable_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/variable_stars.py)

Good test surface and real doctrine, but lower priority than the unified star
cluster that should likely define the parent boundary first.

---

## 5. Files Better Treated as Supporting Modules, Not Primary SCP Targets

These files matter, but usually as dependencies inside a larger subsystem
constitution rather than as standalone constitutional programs.

### Mathematical / astronomical primitives

- [`coordinates.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/coordinates.py)
- [`julian.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/julian.py)
- [`obliquity.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/obliquity.py)
- [`precession.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/precession.py)
- [`nutation_2000a.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/nutation_2000a.py)
- [`corrections.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/corrections.py)

### Helper modules that belong to a parent subsystem constitution

- [`eclipse_geometry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_geometry.py)
- [`eclipse_search.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_search.py)
- [`eclipse_contacts.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_contacts.py)
- [`eclipse_canon.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_canon.py)
- [`phase.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/phase.py)
- [`spk_reader.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/spk_reader.py)
- [`fixed_star_groups.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_star_groups.py)

### Catalog / data surfaces

- [`asteroids.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/asteroids.py)
- [`classical_asteroids.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/classical_asteroids.py)
- [`main_belt.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/main_belt.py)
- [`centaurs.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/centaurs.py)
- [`tno.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/tno.py)
- [`behenian_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/behenian_stars.py)
- [`royal_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/royal_stars.py)
- [`varga.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/varga.py) *(until wired + tested)*

---

## 6. Repo-Wide Recommendation Order

If the goal is to continue constitutionalizing Moira in dependency-respecting
order, the best next sequence is:

1. fixed-stars / unified-star subsystem cluster centered on [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py) and [`stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
2. [`synastry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/synastry.py)
3. [`timelords.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/timelords.py) / [`dasha.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/dasha.py)
4. [`sothic.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sothic.py)
5. [`variable_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/variable_stars.py)

Rationale for changes from the previous scan:

- `progressions.py` is now fully constitutionalized and documented by
  [`PROGRESSIONS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/PROGRESSIONS_BACKEND_STANDARD.md)
- `eclipse.py` is now constitutionalized and removed from the pending list
- the star cluster is now the highest-value unresolved subsystem boundary
- synastry rises in importance as more source engines become constitutionalized

---

## 7. Practical Rule for Future Scans

When evaluating a file or subsystem for SCP candidacy, ask:

1. Is there a real authoritative computational core?
2. Is there hidden truth that later users would otherwise need to reconstruct?
3. Is there already enough subsystem coherence that preserved truth, typed
   classification, and inspectability would be meaningful?
4. Is the next phase justified by existing lower-phase reality?
5. Is this a subsystem, or only a helper inside a larger subsystem?

If the answer to 1-4 is yes, and 5 indicates a real subsystem, it is a good SCP
candidate.

If 5 indicates a helper or primitive, it should usually be constitutionalized
through its parent subsystem instead.
