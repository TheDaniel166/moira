# Primary Directions Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the primary-directions subsystem along three fronts — make its admitted key-fallback *visible*, remove a dead misleading property, and open two research-gated tracks (Morinus positional sovereignty, one frontier admission) — without violating the subsystem's P12 constitutional freeze.

**Architecture:** Phase A is fully-specified, low-risk hardening on the already-frozen surface (visibility + honesty), each change paired with a doc/contract update so the freeze stays truthful. Phases B and C are **research-first**: each begins with a primary-source investigation that produces a doctrine card, and only then admits code. No formula or rate is invented; source-pending values are named seams the research task must pin.

**Tech Stack:** Python 3.11+ (StrEnum, frozen slotted dataclasses), pytest, the project `.venv` as the authoritative runtime (CLAUDE.md §2 Runtime Truth).

## Global Constraints

- Runtime: use the project `.venv` for all execution and validation. Do not use system Python. (CLAUDE.md §2)
- Protected zones touched: primary-directions is constitutionally closed through `P12`. Any behavioral change requires updating the governing freeze packet — the invariant register and validation codex — in the same change. (CLAUDE.md §6, §6A, §12)
- Machine contracts: `PrimaryArc` carries `[MACHINE_CONTRACT v1]` with `"agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}`. Removing a public property is an `api_change` and requires explicit human confirmation before proceeding. `tests/unit/test_docstring_governance.py` enforces contract validity. (CLAUDE.md §6A)
- No invented math: Phases B and C must not introduce a formula or rate that is not source-derived and named in a doctrine card. If the source is unavailable, the task stops at "source not yet recovered" and does not guess. (CLAUDE.md §4, §16)
- Semantic honesty: do NOT collapse the byte-identical arc laws (`_equatorial_arcs`, `_zodiacal_projected_arcs`, `_regiomontanus_under_pole_arcs`/`_campanus_under_pole_arcs`). Their coincidence is intentional; distinct doctrinal objects stay named. (CLAUDE.md §5, §10A)
- Testing Liturgy: use existing fixtures (`moira_engine`, `natal_chart`, `moira_approx`); never construct `Moira()` in a test or declare local astronomical constants. (CLAUDE.md §19)
- Minimal touch: modify only what each task requires. (CLAUDE.md §2, §5 Law of Minimal Touch)

---

## Phase A — Visibility & Honesty (fully specified, low risk)

### Task A1: Make the admitted key-token fallback visible

**Context / why this is not a "raise instead":** `_normalize_key` silently coerces an unrecognized key token to Naibod. `tests/unit/test_primary_direction_keys.py::test_primary_direction_key_truth_normalizes_unknown_and_bad_solar_rate` asserts this leniency as correct behavior. So the fallback is *admitted doctrine*, not a bug. The tension with the Law of Determinism (CLAUDE.md §5, "no uncontrolled fallback") is resolved not by removing leniency but by making the coercion **inspectable** — "Visibility is the doctrine" (§Final Doctrine). Scope is deliberately the key-*token* fallback only; the separate Solar-bad-rate rate-substitution is left untouched here and noted as a deferred sibling.

**Files:**
- Modify: `moira/primary_directions/keys.py` (the `PrimaryDirectionKeyTruth` dataclass ~L62-L78, `_normalize_key` ~L81-L85, `primary_direction_key_truth` ~L88-L109)
- Test: `tests/unit/test_primary_direction_keys.py`
- Doc: `wiki/02_standards/primary_directions/primary_directions_invariant_register.md` (record the new inspectable-fallback invariant)

**Interfaces:**
- Consumes: nothing new.
- Produces: `PrimaryDirectionKeyTruth` gains two read-only fields — `requested_key: str` (the original token as given) and `fallback_applied: bool` (True iff an unrecognized token was coerced to Naibod). `primary_direction_key_truth(...)` populates both. Existing `key`, `family`, `rate_degrees_per_year` semantics are unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_primary_direction_keys.py`:

```python
def test_primary_direction_key_truth_exposes_fallback_visibility() -> None:
    honored = primary_direction_key_truth(PrimaryDirectionKey.PTOLEMY)
    assert honored.fallback_applied is False
    assert honored.requested_key == "ptolemy"

    coerced = primary_direction_key_truth("unknown")
    assert coerced.key is PrimaryDirectionKey.NAIBOD  # leniency preserved
    assert coerced.fallback_applied is True            # but now visible
    assert coerced.requested_key == "unknown"

    genuine_naibod = primary_direction_key_truth("naibod")
    assert genuine_naibod.fallback_applied is False     # real Naibod is not a fallback
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/unit/test_primary_direction_keys.py::test_primary_direction_key_truth_exposes_fallback_visibility -v`
Expected: FAIL with `AttributeError: 'PrimaryDirectionKeyTruth' object has no attribute 'fallback_applied'`

- [ ] **Step 3: Write minimal implementation**

In `moira/primary_directions/keys.py`, replace `_normalize_key` with a fallback-signalling resolver and extend the truth vessel:

```python
def _resolve_key(key: str | PrimaryDirectionKey) -> tuple[PrimaryDirectionKey, bool]:
    if isinstance(key, PrimaryDirectionKey):
        return key, False
    try:
        return PrimaryDirectionKey(str(key).lower()), False
    except ValueError:
        return PrimaryDirectionKey.NAIBOD, True
```

Extend the dataclass (add two defaulted fields so existing external construction stays valid):

```python
@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyTruth:
    """Vessel: Record of the exact mathematical rate and family for a specific time-key."""
    key: PrimaryDirectionKey
    family: PrimaryDirectionKeyFamily
    rate_degrees_per_year: float
    requested_key: str = ""
    fallback_applied: bool = False

    def __post_init__(self) -> None:
        expected_family = PrimaryDirectionKeyPolicy(self.key).family
        if self.family is not expected_family:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: family does not match key"
            )
        if self.rate_degrees_per_year <= 0.0:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: rate_degrees_per_year must be positive"
            )
        if self.fallback_applied and self.key is not PrimaryDirectionKey.NAIBOD:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: fallback must resolve to Naibod"
            )
```

Update the builder to record both fields:

```python
def primary_direction_key_truth(
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> PrimaryDirectionKeyTruth:
    resolved_key, fallback_applied = _resolve_key(key)
    if resolved_key is PrimaryDirectionKey.SOLAR:
        resolved_rate = abs(solar_rate) if solar_rate is not None else _NAIBOD_RATE
        if resolved_rate <= 0.0:
            resolved_rate = _NAIBOD_RATE
    elif resolved_key is PrimaryDirectionKey.PTOLEMY:
        resolved_rate = _PTOLEMY_RATE
    elif resolved_key is PrimaryDirectionKey.CARDAN:
        resolved_rate = _CARDAN_RATE
    else:
        resolved_rate = _NAIBOD_RATE
    policy = PrimaryDirectionKeyPolicy(resolved_key)
    requested = key.value if isinstance(key, PrimaryDirectionKey) else str(key).lower()
    return PrimaryDirectionKeyTruth(
        key=resolved_key,
        family=policy.family,
        rate_degrees_per_year=resolved_rate,
        requested_key=requested,
        fallback_applied=fallback_applied,
    )
```

Then update the two call sites of the removed `_normalize_key`: `convert_arc_to_time` already delegates to `primary_direction_key_truth`, so it needs no change. Confirm `_normalize_key` has no other references before deleting it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/unit/test_primary_direction_keys.py -v`
Expected: PASS — the new test plus all five pre-existing tests (including `test_primary_direction_key_truth_normalizes_unknown_and_bad_solar_rate`, whose `unknown.key is NAIBOD` assertion still holds).

- [ ] **Step 5: Update the invariant register**

In `wiki/02_standards/primary_directions/primary_directions_invariant_register.md`, add one line under the key-doctrine invariants: "An unrecognized key token is coerced to Naibod (admitted leniency) and the coercion is inspectable via `PrimaryDirectionKeyTruth.fallback_applied` / `.requested_key`."

- [ ] **Step 6: Commit**

```bash
git add moira/primary_directions/keys.py tests/unit/test_primary_direction_keys.py wiki/02_standards/primary_directions/primary_directions_invariant_register.md
git commit -m "feat(primary_directions): make admitted key-token fallback inspectable"
```

---

### Task A2: Remove the dead, misleading `PrimaryArc.key_family` property

**Context / why removal:** `PrimaryArc.key_family` (`moira/primary_directions/__init__.py:949-951`) always returns the *default* policy's family (`STATIC`), regardless of any key, because a `PrimaryArc` stores no key — keys are applied at `.years(key=...)`. A repo-wide grep confirms **zero consumers**: no serializer, service, test, or doc reads it. It reports a fiction (§5 Law of Semantic Honesty). Removal is the minimal honest fix. **This is an `api_change`** under the `PrimaryArc` machine contract and requires explicit human confirmation (the user's "do all this" is taken as that confirmation; re-confirm at execution if in doubt). Note `key_family` is not listed in the contract's `api.frozen`/`api.internal`, so removal does not falsify the contract text.

**Files:**
- Modify: `moira/primary_directions/__init__.py:949-951` (delete the property)
- Test: `tests/unit/test_primary_directions_public_api.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `PrimaryArc` no longer exposes `key_family`. Callers wanting a key family use `PrimaryDirectionKeyPolicy(key).family` or `primary_direction_key_truth(key).family` explicitly.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_primary_directions_public_api.py`:

```python
def test_primary_arc_does_not_expose_fictional_key_family() -> None:
    from moira.primary_directions import PrimaryArc, PrimaryDirectionMotion

    arc = PrimaryArc(
        significator="Sun",
        promissor="MC",
        arc=12.5,
        direction="D",
        motion=PrimaryDirectionMotion.DIRECT,
    )
    # An arc holds no key, so it must not claim a key family.
    assert not hasattr(arc, "key_family")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/unit/test_primary_directions_public_api.py::test_primary_arc_does_not_expose_fictional_key_family -v`
Expected: FAIL — `key_family` still present.

- [ ] **Step 3: Remove the property**

Delete these lines from `moira/primary_directions/__init__.py` (currently 949-951):

```python
    @property
    def key_family(self) -> PrimaryDirectionKeyFamily:
        return PrimaryDirectionKeyPolicy().family
```

If `PrimaryDirectionKeyFamily` / `PrimaryDirectionKeyPolicy` become unused imports after removal, leave them — they remain re-exported on the package surface via other paths; run the import check in Step 5 to confirm nothing breaks.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/unit/test_primary_directions_public_api.py -v`
Expected: PASS.

- [ ] **Step 5: Run the governance and import checks**

Run: `.venv/Scripts/python -m pytest tests/unit/test_docstring_governance.py -v`
Run: `.venv/Scripts/python -c "import moira.primary_directions"`
Expected: PASS / clean import (confirms the `PrimaryArc` contract still validates and no dangling reference remains).

- [ ] **Step 6: Commit**

```bash
git add moira/primary_directions/__init__.py tests/unit/test_primary_directions_public_api.py
git commit -m "refactor(primary_directions): remove dead misleading PrimaryArc.key_family"
```

---

### Task A3: Full Phase-A regression gate

**Files:** none (verification only).

- [ ] **Step 1: Run the whole primary-directions test surface**

Run: `.venv/Scripts/python -m pytest tests/unit/test_primary_direction_keys.py tests/unit/test_primary_directions_public_api.py tests/unit/test_primary_direction_geometry.py tests/unit/test_primary_directions.py -v`
Expected: all PASS. If any pre-existing test referenced `key_family` (none found in survey), fix by switching it to the explicit `PrimaryDirectionKeyPolicy(key).family` form and note it in the commit.

- [ ] **Step 2: Commit any incidental test adjustments**

```bash
git add -A
git commit -m "test(primary_directions): phase-A regression gate green"
```

---

## Phase B — Morinus positional sovereignty (research-gated)

**Precise scope:** The Morinus *aspectual* branch is already sovereign — `moira/primary_directions/morinus.py::project_morinus_aspect_point` is a formula-grade circle-of-aspects projection. What is *not* sovereign is the Morinus **positional/conjunction** arc, which shares `_equatorial_arcs` with Meridian (`moira/primary_directions/geometry.py:404-408`), and is honestly marked `SHARED_NARROW` in the geometry truth table (`geometry.py:112-117`). Phase B resolves that one branch — and it may resolve *toward confirmation* (Morinus positional directions genuinely equal equatorial RA-difference) rather than toward a new formula. Both outcomes are legitimate; guessing is not.

### Task B1: Recover the Morinian positional directional law (research → doctrine card)

**Files:**
- Create: `wiki/01_doctrines/primary_directions/primary_directions_truth_card_morinus_positional.md`
- Modify (only if the card concludes a distinct law exists): none yet — code lands in B2.

**This task produces a document and a decision, no code.**

- [ ] **Step 1: Assemble the primary sources**

Consult, in authority order (CLAUDE.md §3): Morin de Villefranche *Astrologia Gallica* Book 22 (directions) as the primary; then reproducible secondary worked examples (Gansten, *Primary Directions*; Kolev/Halloran Morinus material listed in `primary_directions_roadmap.md` §Research Sources). Record exactly which edition/section states the positional-direction construction.

- [ ] **Step 2: State the governing object in Moira's terms**

In the truth card, answer the §10A admission questions for the Morinus positional branch: What geometric object is being directed (equatorial hour-circle? prime-vertical? Morinian mundane frame)? Is the arc an RA difference, or an oblique ascension under a Morinian pole, or something else? Cite the source formulation, not the current code.

- [ ] **Step 3: Render the sovereignty verdict**

The card must conclude with exactly one of:
- **(a) Distinct law recovered** — give the source-derived formula symbolically, name it (e.g. `MORINUS_POSITIONAL_<frame>`), and specify a validation oracle (a published worked example with expected arc). Proceed to B2.
- **(b) Confirmed equatorial** — argue from source that Morinus positional = equatorial RA-difference, so the shared law is *correct*, not a placeholder. Then B2 becomes a truth-table relabel, not new math.

- [ ] **Step 4: Commit the card**

```bash
git add wiki/01_doctrines/primary_directions/primary_directions_truth_card_morinus_positional.md
git commit -m "docs(primary_directions): Morinus positional-law truth card and sovereignty verdict"
```

### Task B2: Admit the recovered law OR relabel the truth (conditional on B1)

> The exact TDD steps here are finalized after B1, because the formula (or the confirmation) is the deliverable of B1 — writing them now would violate CLAUDE.md §4/§16. The task's *shape* is fixed below; the source-derived arc expression is the single seam B1 fills.

**If B1 outcome (a) — distinct law:**

**Files:**
- Modify: `moira/primary_directions/geometry.py` (add a `MORINUS_POSITIONAL_*` law function; route `PrimaryDirectionMethod.MORINUS` positional/conjunction cases to it in `compute_primary_direction_arcs`; update `primary_direction_geometry_truth` to `SOVEREIGN` with `shared_with=()`)
- Test: `tests/unit/test_primary_direction_geometry.py`, `tests/unit/test_primary_direction_morinus.py`
- Doc: `wiki/02_standards/primary_directions/primary_directions_invariant_register.md`, `wiki/06_roadmap/primary_directions/primary_directions_roadmap.md` (move Morinus from "shared narrow" to "sovereign")

- [ ] **Step 1:** Write a failing test asserting the published worked-example arc from B1's card (exact expected value from the source), directed under Morinus positional, matches within `moira_approx(kind="angle")`.
- [ ] **Step 2:** Run it; expect FAIL (still routing to `_equatorial_arcs`).
- [ ] **Step 3:** Implement the `MORINUS_POSITIONAL_*` law exactly as the card specifies; re-route in the dispatcher; flip the sovereignty record.
- [ ] **Step 4:** Run geometry + morinus tests; expect PASS. Add a divergence test proving Morinus positional now differs from Meridian on a case where the source says they must differ.
- [ ] **Step 5:** Update invariant register + roadmap sovereignty status.
- [ ] **Step 6:** Commit `feat(primary_directions): sovereign Morinus positional directional law`.

**If B1 outcome (b) — confirmed equatorial:**

- [ ] **Step 1:** Write a test asserting Morinus positional == Meridian RA-difference is the *doctrinally correct* identity (not a placeholder), referencing the card.
- [ ] **Step 2-3:** Update `primary_direction_geometry_truth` for Morinus: keep the shared law but change its documentation/comment to cite the source confirming equivalence; if the truth model supports an "intentionally shared, source-confirmed" state distinct from "shared placeholder," add it. Update roadmap §Mathematical sovereignty status accordingly.
- [ ] **Step 4:** Run governance + geometry tests; expect PASS.
- [ ] **Step 5:** Commit `docs(primary_directions): confirm Morinus positional equals equatorial by source`.

---

## Phase C — One frontier admission (research-gated)

**Doctrine:** The roadmap deliberately keeps frontiers closed until a formula-grade source exists (§Recommended Immediate Path Forward). Phase C admits exactly **one** first frontier, chosen for having the crispest source, and follows the same research-first shape. Do not batch multiple frontiers.

### Task C1: Select and source the first frontier (research → truth card)

**Files:**
- Create: `wiki/01_doctrines/primary_directions/primary_directions_truth_card_<frontier>.md`

- [ ] **Step 1: Choose the candidate.** Recommended first candidate: **Neo-converse motion doctrine**, because the roadmap already has a dedicated research packet for it (`wiki/05_research/primary_directions/primary_directions_neo_converse_research.md`) — the source work is partly done, lowering the "invented math" risk. Alternative if a documented rate is preferred: a new **time key** with a published degrees-per-year rate. Record the chosen candidate and why in the card.
- [ ] **Step 2: Extract the governing definition** from the source packet: for neo-converse, the exact motion/perfection rule that distinguishes it from `TRADITIONAL_CONVERSE`; for a key, the exact rate constant and its family (static/dynamic).
- [ ] **Step 3: Specify the admission surface** — which policy axis it extends (`PrimaryDirectionConverseDoctrine` for neo-converse, or `PrimaryDirectionKey` + rate for a key), the invariant additions to `PrimaryDirectionsPolicy.__post_init__`, and the validation oracle.
- [ ] **Step 4: Commit the card.**

```bash
git add wiki/01_doctrines/primary_directions/primary_directions_truth_card_<frontier>.md
git commit -m "docs(primary_directions): <frontier> admission truth card"
```

### Task C2: Admit the frontier branch (conditional on C1)

> Finalized after C1; the definition/rate is C1's deliverable. Shape below.

**If a new time key:**
- **Files:** Modify `moira/primary_directions/keys.py` (add enum member, rate constant, family branch in `primary_direction_key_truth`); Test `tests/unit/test_primary_direction_keys.py`; Doc invariant register + roadmap §Time keys count.
- [ ] **Step 1:** Failing test: `primary_direction_key_truth(<NEW_KEY>).rate_degrees_per_year == <source rate>` and correct family.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Add the enum member + `_<NEW>_RATE = <source value>` + branch. Keep `fallback_applied` semantics from A1 intact.
- [ ] **Step 4:** Run keys tests; expect PASS.
- [ ] **Step 5:** Update roadmap "N of ~25 keys" and invariant register.
- [ ] **Step 6:** Commit `feat(primary_directions): admit <NEW_KEY> time key`.

**If neo-converse:**
- **Files:** Modify `moira/primary_directions/converse.py` (add doctrine member), `moira/primary_directions/__init__.py` (`PrimaryDirectionsPolicy` invariants + `admitted_motions`), `moira/primary_directions/geometry.py` only if the arc sign/route differs; Test `tests/unit/test_primary_direction_converse.py`; Doc invariant register + roadmap Stage 7.
- [ ] **Step 1:** Failing test: a neo-converse arc for a case where the source packet gives an expected value distinct from traditional converse, within `moira_approx(kind="angle")`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Add `NEO_CONVERSE` doctrine; extend policy invariants so it is only admitted in its lawful configuration; implement the distinguishing rule exactly as the card states.
- [ ] **Step 4:** Run converse + geometry tests; expect PASS, plus a test proving neo-converse ≠ traditional converse where the source requires.
- [ ] **Step 5:** Update roadmap Stage 7 (neo-converse: implemented) and invariant register.
- [ ] **Step 6:** Commit `feat(primary_directions): admit neo-converse motion doctrine`.

---

## Self-Review

**Spec coverage:**
- Bucket A (safe fixes) → Tasks A1 (fallback visibility), A2 (dead property), A3 (regression gate). ✅
- Bucket B (Morinus sovereignty) → Tasks B1 (research/card), B2 (conditional admit/relabel). ✅ — narrowed honestly to the positional branch after discovering the aspectual branch is already sovereign.
- Bucket C (frontier) → Tasks C1 (select/source), C2 (conditional admit). ✅ — scoped to one frontier per doctrine.

**Placeholder scan:** Phase A steps contain complete code and exact commands. Phases B2/C2 intentionally defer *final* TDD detail to their research task — this is required sequencing under CLAUDE.md §4/§16 (no invented math), not a lazy placeholder; each names the single source-derived seam and fixes the surrounding structure. The one literal seam per conditional task (`<source rate>`, `MORINUS_POSITIONAL_*` formula) is explicitly the deliverable of the preceding research task.

**Type consistency:** `PrimaryDirectionKeyTruth` fields (`requested_key: str`, `fallback_applied: bool`) are used consistently in A1's test and builder. `_resolve_key` returns `tuple[PrimaryDirectionKey, bool]` and is consumed only in `primary_direction_key_truth`. A2 removes `key_family` and no later task references it. B2/C2 reference `compute_primary_direction_arcs`, `primary_direction_geometry_truth`, `PrimaryDirectionsPolicy` exactly as they exist today.

**Doctrine gate:** Every behavioral change (A1, A2, B2, C2) pairs with an invariant-register and/or roadmap update in the same task, honoring the P12 freeze packet requirement (§6, §12).

---

## Execution Handoff

Phases are independent and can be executed or approved separately. Recommended order: **A → B → C**, but A can ship alone.
