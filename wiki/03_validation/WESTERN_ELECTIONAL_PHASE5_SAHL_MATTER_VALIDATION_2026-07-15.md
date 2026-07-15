# Western Electional Phase 5 — Sahl Matter-Profile Validation

Date: 2026-07-15  
Scope: Sahl bin Bishr, *On Elections*, §§43-55  
Evidence class: primary-source derivation, regression/invariant testing, DE441
substrate integration, and REST/OpenAPI contract validation

## Admitted products

Phase 5 admits six separate single-moment products:

- `sahl_building_v1` (§§43-46)
- `sahl_demolition_v1` (§47)
- `sahl_land_v1` (§§48-49)
- `sahl_wells_and_rivers_v1` (§50)
- `sahl_planting_v1` (§§51-53)
- `sahl_sowing_v1` (§§54-55)

They are public through `evaluate_sahl_matter_profile(...)`,
`sahl_matter_profile_at(...)`, `Moira.sahl_matter_profile_at(...)`, and
`POST /v1/electional/western/sahl-matter-profile`. The REST request enum names
exactly those six products. Every response embeds the general
`sahl_moon_condition_v1` evaluation and the complete source-ordered matter
clause set.

## Authority and policy boundary

The governing witness is Sahl bin Bishr, *On Elections*, in Benjamin N.
Dykes, *Choices & Inceptions: Traditional Electional Astrology*, Part III,
printed pp. 106-110. Dykes's apparatus is part of the held witness and records
the relevant Crofts, al-Rijāl, al-Khayyat, and al-ʿImrānī parallels.

The following source objects are computationally closed in v1 where used:

- classical sign quadruplicities and elements;
- explicit whole-sign configurations and Sahl moiety bodily joins;
- caller-declared effective quadrant houses and named whole-sign places;
- the sect-aware Lot of Fortune;
- Dorothean triplicity and explicitly selected Egyptian bounds;
- lunar increase in light;
- explicitly named benefic, malefic, node, and angular conditions.

The held source does not close "increased/defective in number,"
eastern/ascending, ascending or descending in a circle, cleansing, generic
adaptation/fortification, or several separation/cadency phrases to exclusive
predicates. Each remains a typed `not_evaluable` clause with observable
alternatives, policy id, explanation, and citation. A later convention is not
substituted silently. In a compound gate, a proved-false explicit conjunct may
clear the gate; an unresolved required conjunct cannot trigger it.

## Invariants exercised

- Six profile identities produce six distinct clause sequences.
- Clause order is contiguous and source-owned.
- Triggered and unresolved summaries derive only from visible clauses.
- A triggered gate dominates profile status; otherwise any unresolved clause
  makes the profile indeterminate.
- `source_complete` and `complete_matter_profile` are true while
  `complete_electional_judgement` is false.
- No score, rank, advice, or recommendation is returned.
- Building's explicit Saturn/Tail/angular danger, wells' malefic-Midheaven
  gate, and sowing's under-rays compound boundary have adversarial tests.
- All six profiles execute against the discovered DE441 reader at J2000 and
  preserve that reader provenance.
- FastAPI round trips every profile and OpenAPI exposes the exact six-value
  request enum plus typed nested evidence.

## Sovereignty audit

The implementation is organized around six named source products and their
ordered clauses, not around an external engine's helper or array layout.
Ambiguous branches are governed by explicit profile policy and typed
`not_evaluable` states. Whole-sign, quadrant, bodily-join, dignity, bound, and
triplicity computations are exposed as named measurements. Primary-source
derivation and Moira-owned invariants carry the proof; no Swiss or other
secondary engine supplies implementation structure or validation authority.

## Verification receipt

All commands used `.\.venv\Scripts\python.exe` on Python 3.14.3 with
`MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`. `tests/KNOWN_ISSUES.yml` was empty.

- `pytest tests/unit/test_sahl_matter_profiles.py -q` — 12 passed.
- `pytest tests/server/test_server_sahl_electional_routes.py -q` — 17 passed.
- `pytest tests/integration/test_sahl_electional_de441.py -q` — 3 passed;
  discovered `de441.bsp` exercised.
- Public-surface governance was run with
  `test_built_wheel_matches_source_public_surface` explicitly excluded; the
  source snapshot and `Moira` method snapshot passed.
- The combined electional unit, DE441 integration, public-surface, OpenAPI,
  serializer, service, and router slice passed: 159 passed, with the local
  wheel-build test explicitly excluded.
- An unmocked FastAPI `TestClient` posted all six profile ids through
  `POST /v1/electional/western/sahl-matter-profile`; every request returned
  HTTP 200, the requested identity, nested general Sahl evaluation, visible
  reader provenance, and the `Moira.sahl_matter_profile_at` facade entrypoint.
- `python -m py_compile` passed for every changed engine, facade, model,
  service, serializer, and router module.
- `python scripts/check_doc_consistency.py` passed.
- `git diff --check` passed, and no `.whl` file exists in the repository
  outside the project `.venv`.

This validation establishes source representation, invariant behavior,
transport fidelity, and DE441-backed substrate integration. It does not
empirically validate Sahl's astrological claims or turn these profiles into a
complete electional judgement.
