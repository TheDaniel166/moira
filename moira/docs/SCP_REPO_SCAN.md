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

### Near-constitutional / partially constitutionalized

- [`chart_shape.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/chart_shape.py)
  Already contains architecture-freeze and validation-codex language in the
  module itself, has a curated `__all__`, and has a public-API test. It would
  benefit from being externalized into a formal backend standard, but it is not
  the highest-value next target because much of the constitutional work is
  already present.

---

## 3. Highest-Value Next SCP Targets

These are the strongest next candidates because they have real subsystem shape
but are not yet constitutionally governed at the same level as houses, aspects,
parans, dignities, and lots.

### Tier 1 - Best next candidates

#### 3.1 Patterns

- [`patterns.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/patterns.py)

Why it is strong:

- coherent engine with one clear result vessel
- already depends on an SCP-mature substrate: aspects
- explicit detector set and curated public surface already exist
- likely benefits from formal truth preservation, classification, and hardening
  around pattern doctrine, deduplication, ordering, and detector boundaries

Why it is now the best next move:

- smaller conceptual scope than `transits` or `eclipse`
- simpler dependency tree
- already depends on a now-constitutionalized aspect substrate
- likely ready for Phase 1 truth preservation immediately

#### 3.2 Transits

- [`transits.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/transits.py)

Why it is strong:

- clear computational core around search and returns
- multiple meaningful result vessels
- already exposes a practical public surface
- likely contains doctrine that should be separated from raw search behavior

Why it belongs in Tier 1:

- the transit engine is reused across multiple higher-level techniques
- it likely benefits from explicit invariants and failure/determinism doctrine

### Tier 2 - High-value but heavier targets

#### 3.3 Eclipse

- [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py)

Why it would benefit enormously:

- major engine with many result vessels
- deep delegated architecture
- real classification and local-circumstance layers
- already important enough to deserve constitutional clarity

Why it is not the first recommendation:

- larger and riskier
- depends on several adjacent eclipse helper modules
- constitutionalization should likely cover the eclipse cluster, not just one
  file in isolation

This is the biggest payoff target, but not the easiest next target.

#### 3.4 Fixed Stars / Unified Star Surface

- [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py)
- [`stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
- possibly [`gaia.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/gaia.py)

Why this cluster matters:

- there is already a real star domain in the repo
- public surface is split across multiple files
- doctrine and boundary ownership are likely not yet fully explicit

Why it should wait:

- subsystem boundary should be defined first
- the constitutional target is probably a star subsystem cluster, not a single
  file

---

## 4. Medium-Value SCP Targets

These are legitimate candidates, but either narrower, less central, or less
ready than the top group.

### 4.1 Progressions

- [`progressions.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/progressions.py)

Likely benefits:

- explicit progression doctrine
- result-vessel hardening
- deterministic ordering and failure semantics

Why not yet:

- smaller test surface than top candidates
- less obviously layered today

### 4.2 Synastry

- [`synastry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/synastry.py)

Likely benefits:

- could become a real integration subsystem over multiple constitutionalized
  engines

Why not yet:

- should probably wait until more source subsystems are constitutionalized

### 4.3 Sothic

- [`sothic.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/sothic.py)

Interesting because:

- coherent domain
- multiple result vessels

Why later:

- more specialized
- lower centrality than patterns/transits/eclipse

### 4.4 Variable Stars

- [`variable_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/variable_stars.py)

Likely benefits:

- doctrine clarification
- explicit profiles and failure behavior

Why later:

- more niche than the major astrology engines

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

Why:

- they are foundational primitives
- they may warrant standards of their own eventually
- but they do not fit the same layered astrology-subsystem SCP shape as cleanly

### Helper modules that likely belong to a parent subsystem constitution

- [`eclipse_geometry.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_geometry.py)
- [`eclipse_search.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_search.py)
- [`eclipse_contacts.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_contacts.py)
- [`eclipse_canon.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse_canon.py)
- [`phase.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/phase.py)
- [`spk_reader.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/spk_reader.py)

Why:

- they are important, but architecturally subordinate to larger engines

### Catalog / data surfaces

- [`asteroids.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/asteroids.py)
- [`classical_asteroids.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/classical_asteroids.py)
- [`main_belt.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/main_belt.py)
- [`centaurs.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/centaurs.py)
- [`tno.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/tno.py)
- [`behenian_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/behenian_stars.py)
- [`royal_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/royal_stars.py)

Why:

- many are thin data/catalog layers
- SCP likely applies better to the parent subsystem they feed

---

## 6. Repo-Wide Recommendation Order

If the goal is to continue constitutionalizing Moira in dependency-respecting
order, the best next sequence is:

1. [`patterns.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/patterns.py)
2. [`transits.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/transits.py)
3. eclipse subsystem cluster centered on [`eclipse.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/eclipse.py)
4. fixed-stars / unified-star subsystem cluster centered on [`fixed_stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/fixed_stars.py) and [`stars.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/stars.py)
5. [`progressions.py`](c:/Users/nilad/OneDrive/Desktop/Moira/moira/progressions.py)

Rationale:

- `lots` has now completed the full 12-phase SCP cycle and should be treated as a constitutionalized subsystem, not a pending candidate
- `patterns` is the cleanest next constitutionalization because it sits atop an
  already-mature aspect substrate and has manageable scope
- `transits` is central and reusable, but somewhat more search-heavy and technique-branching
- `eclipse` is extremely valuable but should be approached as a cluster
- `stars` likely requires subsystem-boundary clarification before the phase work
- `progressions` is a credible next-wave candidate once the higher-centrality targets above it are resolved

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
