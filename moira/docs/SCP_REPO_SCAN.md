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
- [`synastry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/synastry.py)
  Documented by [`SYNASTRY_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SYNASTRY_BACKEND_STANDARD.md)
- unified-star subsystem centered on [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py) and [`stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
  Documented by [`STARS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/STARS_BACKEND_STANDARD.md)
- [`sothic.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sothic.py)
  Documented by [`SOTHIC_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SOTHIC_BACKEND_STANDARD.md)
- [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py)
  Documented by [`ECLIPSE_MODEL_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/ECLIPSE_MODEL_STANDARD.md)
- timing doctrine cluster: [`timelords.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/timelords.py) and [`dasha.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/dasha.py)
  Documented by [`TIMELORDS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/TIMELORDS_BACKEND_STANDARD.md)
  and [`DASHA_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/DASHA_BACKEND_STANDARD.md)

### Self-constitutionalized (architecture freeze + validation codex in module)

- [`chart_shape.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/chart_shape.py)
  Contains a full architecture-freeze declaration, frozen threshold constants,
  detection-order rationale, handle-in-gap doctrine, and a validation codex in
  the module docstring. Has curated `__all__` and a public API test.

- [`void_of_course.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/void_of_course.py)
  Contains a full architecture-freeze declaration covering frozen scan/bisection
  constants, traditional and modern body set doctrine, eight-target aspect
  doctrine, crossing-detection formula with guard rationale, and VOC start
  determination doctrine. Includes a twelve-rule validation codex and curated
  `__all__`.

- [`multiple_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/multiple_stars.py)
  Contains a full architecture-freeze declaration covering system-type dispatch
  doctrine (VISUAL/WIDE/SPECTROSCOPIC/OPTICAL), Kepler solver constants,
  Thiele-Innes projection doctrine, Dawes resolvability formula, and combined
  magnitude formula. Includes an eleven-rule validation codex and curated
  `__all__`.

---

## 3. Highest-Value Next SCP Targets

### Tier 1 - Best next candidates

The timing doctrine cluster (`timelords.py` and `dasha.py`) has been fully
constitutionalized through all twelve SCP phases. See §2 (Fully constitutionalized)
and the recommendation order update in §6.

---

## 4. Medium-Value SCP Targets

### 4.1 Variable Stars

- [`variable_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/variable_stars.py)

Good test surface and real doctrine, but lower priority than the major timing
cluster now that the parent unified-star boundary is constitutionalized.

### 4.2 Gaia

- [`gaia.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/gaia.py)

Now better treated as a possible follow-on constitutional target only where the
parent unified-star subsystem boundary justifies pulling Gaia deeper into the
frozen surface.

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

1. [`variable_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/variable_stars.py)
2. supporting expansion around the star cluster, including [`gaia.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/gaia.py) where justified by the parent subsystem boundary

Rationale for changes from the previous scan:

- `progressions.py` is now fully constitutionalized and documented by
  [`PROGRESSIONS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/PROGRESSIONS_BACKEND_STANDARD.md)
- `synastry.py` is now fully constitutionalized and documented by
  [`SYNASTRY_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SYNASTRY_BACKEND_STANDARD.md)
- the unified-star subsystem centered on `fixed_stars.py` and `stars.py` is now
  fully constitutionalized and documented by
  [`STARS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/STARS_BACKEND_STANDARD.md)
- `sothic.py` is now fully constitutionalized and documented by
  [`SOTHIC_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/SOTHIC_BACKEND_STANDARD.md)
- `eclipse.py` is now constitutionalized and removed from the pending list
- the timing doctrine cluster (`timelords.py` and `dasha.py`) is now fully
  constitutionalized through all twelve SCP phases, documented by
  [`TIMELORDS_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/TIMELORDS_BACKEND_STANDARD.md)
  and [`DASHA_BACKEND_STANDARD.md`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/docs/DASHA_BACKEND_STANDARD.md)
- the highest-value unresolved candidates are now variable-star work and
  possible Gaia follow-on hardening

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
