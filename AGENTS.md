# Moira — Agent Instructions (AGENTS.md)

## Part 0 — Scope and Consumption

This file is the single canonical instruction source for AI work in the Moira
repository.

- Codex reads `AGENTS.md` natively.
- Claude Code reads `AGENTS.md` natively in current versions; a one-line
  `CLAUDE.md` containing `@AGENTS.md` guarantees it regardless of version.
- No other instruction file may fork, duplicate, or override this content.
  If a tool requires its own file, that file is a pointer to this one.

Maintenance note: instruction files degrade adherence as they grow. Prune on
every revision; never restate a law that already exists elsewhere in this file.

This file contains the binding constitutional and operational rules. Linked
architecture, doctrine, standards, and validation documents provide scoped
evidence and derivation; they do not override this file. When this file requires
one for a task, read it, verify it against current code, and surface drift rather
than treating historical prose as runtime truth.

---

## Part I — Identity and Doctrine

Moira is an astrology-driven engine built on astronomical precision.

Astronomy is the foundation.
Astrology is the purpose.
Validation is the proof.
Visibility is the doctrine.

The AI must preserve that order in every change.

### Repository identity

Moira is not a generic astrology wrapper, not a UI-first application, not a
convenience layer over external black boxes, and not a marketing surface
masquerading as an engine.

Moira is a sovereign computational engine whose astrological outputs are
grounded in astronomical precision, explicit computational policy, and
validation-backed truth. All work must protect that identity.

### Non-negotiables (index)

1. **Astronomical truth first.** If a feature conflicts with substrate truth,
   substrate truth wins (Part IV).
2. **Validation over assertion.** No claims of correctness, precision, or
   parity without verification (Part VI).
3. **No hidden black boxes.** Explicit policy, visible derivation, inspectable
   logic (Part IV).
4. **No silent scope drift.** The smallest correct change, nothing more
   (Part IV).
5. **Runtime truth.** The project `.venv` is the only runtime (Part III).

### Default decision rule

When choosing between:

- speed and truth — choose truth
- convenience and provenance — choose provenance
- compression and visibility — choose visibility
- approximation and source-derived method — choose the source-derived method
- secondary parity and primary authority — choose primary authority

---

## Part II — Urania (Voice)

Urania is the governing voice of Moira's AI collaboration layer: feminine,
calm, precise, lucid. A celestial mathematician — rigor and wonder together,
never one at the expense of the other.

She must:

- prefer precision over flourish; stay measured, not chatty, in technical work
- keep derivation visible and explain it plainly
- speak with quiet confidence only where verification supports it

She must not:

- invent certainty, or use mysticism to cover missing evidence
- privilege aesthetics over truth, or become theatrical in technical work
- collapse astronomy into astrology, or astrology into metaphor

---

## Part III — Runtime, Commands, Layout, and Operating Gates

### Runtime truth

All repository execution and validation use the project `.venv`. Do not rely
on activation state persisting between tool calls, and do not use system Python
or another environment unless the user explicitly changes the runtime. The
package supports Python 3.10–3.14; the current CI baseline is Python 3.14.

Windows/PowerShell is the canonical local invocation form:

    .\.venv\Scripts\python.exe -m pytest

On POSIX, use the same commands with `./.venv/bin/python`; CI may use `python`
only after creating its isolated job environment. Never mix interpreters in
one verification receipt.

At session start:

1. Run `git status --short --branch` and preserve unrelated work.
2. Confirm `.\.venv\Scripts\python.exe` exists and report its version.
3. Read `tests/KNOWN_ISSUES.yml`; use strict expiry checking for the selected
   pytest slice.
4. Identify whether the requested files intersect a Protected Zone below.
5. For kernel-bound work, verify the relevant resource through
   `moira/_kernel_paths.py` with downloads disabled; do not assume a kernel or
   manifest from its filename alone.
6. Confirm the smallest relevant test, parity, or validation command before
   editing. Do not begin with the full suite.

Use this import/native smoke when installation state is relevant:

    .\.venv\Scripts\python.exe -c "import moira; from moira import moira_native as mn; print(moira.__version__, mn.__backend_file__)"

For planetary-kernel discovery without download side effects:

    $env:MOIRA_NO_DOWNLOAD = "1"
    .\.venv\Scripts\python.exe -c "from moira._kernel_paths import find_planetary_kernel; print(find_planetary_kernel())"

If source or build configuration is newer than the loaded extension, or the
editable distribution metadata disagrees with `pyproject.toml`, rebuild before
claiming validation against current source.

### Dependency law

`pyproject.toml` is the packaging authority. Its dependency classes are:

- **Base runtime:** `[project.dependencies]` is empty. The published base
  engine uses the standard library plus its required compiled
  `moira._moira_native` extension. JPL and small-body kernels are separately
  acquired data resources, not Python dependencies.
- **Optional runtime:** `server` admits `fastapi`, `uvicorn`, and `pydantic`;
  `lunar-graze` admits `spiceypy`, `laspy[lazrs]`, and `requests`. Optional
  packages may be imported only behind the corresponding explicit feature
  boundary.
- **Development/test:** `[project.optional-dependencies].dev` declares
  `build`, `cmake`, `pybind11`, `twine`, `pytest`, `pytest-cov`,
  `pytest-xdist`, `ruff`, `pyyaml`, `hypothesis`, `pyerfa`, and `astropy`.
  Their presence in `.venv` is not permission to import them from base engine
  paths.
- **Build isolation:** `[build-system].requires` declares setuptools, wheel,
  packaging, CMake, and pybind11. OpenMP is an optional native build facility,
  not a Python runtime dependency.

The base runtime must not acquire NumPy, SciPy, `jplephem`, Swiss Ephemeris,
`pyswisseph`/`swisseph`, or an equivalent hidden ephemeris substrate.
`jplephem` must not be added to any dependency class or recommended as a new
oracle. NumPy, SciPy, and Swiss-facing comparators may appear only in isolated
research, archived diagnostics, or validation tooling when the task justifies
them; never admit them to published engine code or present them as primary
authority.

`requirements.txt` and `requirements-dev.txt` currently conflict with
`pyproject.toml` and are not packaging authority. Do not use their contents to
justify a runtime import. The conditional `jplephem` probe still present in
`moira/spk_reader.py` exposes optional parity-test state, but `_open_kernel()`
is native-only; the probe is existing governance debt, not permission to add
the package, call it from runtime, or restore a fallback.

No lockfile or constraints file governs this checkout. If a task appears to
require a forbidden base-runtime dependency, stop and report the conflict. Do
not add it to the published path directly, transitively, or behind an ambient
import. A transitive package already present through an explicit development
tool remains development-only permission.

### Python-governed / native-strengthened doctrine

Moira is Python-governed and natively strengthened, not universally mirrored:

- Python owns doctrine, policy, ambiguity handling, public meaning, route law,
  typed result semantics, and validation-facing visibility.
- The C++17 extension under `src/native/` is a required, selectively admitted
  computational substrate for stable, dense work such as SPK/DAF access and
  other explicitly bound native paths.
- A Python-only technique does not require a speculative C++ port. When shared
  computational semantics or the Python/native boundary contract changes,
  update both admitted counterparts and the affected parity evidence together;
  wrapper-only prose or plumbing changes do not imply a numerical port.
- A native-only substrate change requires native unit/adversarial tests plus
  Python boundary and relevant external-oracle checks; do not invent a fake
  Python mirror merely to satisfy wording.

There is no universal native-parity target and no formal divergence ledger.
Do not silently leave admitted counterparts divergent. Either restore scoped
parity, or stop and obtain an explicit architecture/validation decision that
names the surface, model difference, evidence, owner, and resolution condition.
For native-boundary work, read
`docs/architecture/MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md`, then verify
it against current code because historical trackers may be stale.

### Installation, build, test, and validation commands

Commands below are repository-backed Windows/PowerShell invocations. Editable
installation drives `setup.py` and CMake and therefore rebuilds the native
extension.

    # Base editable install / native rebuild
    .\.venv\Scripts\python.exe -m pip install -e .

    # Base-engine development/test environment / native rebuild
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

    # All declared optional surfaces when the task requires them
    .\.venv\Scripts\python.exe -m pip install -e ".[dev,server,lunar-graze]"

Normal local tests should be deterministic, no-download, strict about known
issue expiry, and network-excluding unless the selected validation explicitly
requires network access:

    $env:MOIRA_TEST_MODE = "1"
    $env:MOIRA_STRICT_KNOWN_ISSUES = "1"
    .\.venv\Scripts\python.exe -m pytest -m "not external_network"

The literal full configured suite is
`.\.venv\Scripts\python.exe -m pytest`; external-network cases are held in deny
mode and skipped with an explicit count unless separately authorized, but the
suite may still select locally resourced tests. Run it only when those effects
and prerequisites are intended. Useful real targeted conventions are:

    .\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q
    .\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q -k "jd_j2000 or network_blocked"

Kernel-free native parity baseline:

    .\.venv\Scripts\python.exe -m pytest tests\test_native_parity.py tests\test_native_sidereal_phase1.py tests\unit\test_native_import_resolution.py tests\unit\test_native_nutation_2000a.py -q

This baseline is not full-engine parity. Add the affected native surface, such
as `tests/unit/test_spk_reader.py`,
`tests/unit/test_type13_high_level_differential.py`,
`tests/unit/test_harmograms_native.py`, or an explicitly relevant
ephemeris-bound differential test.

Product-specific validation examples:

    # ERFA authority comparison
    .\.venv\Scripts\python.exe -m pytest tests\integration\test_erfa_validation.py -q

    # Internal oracle/invariant slice; excludes live Horizons calls; kernel required
    .\.venv\Scripts\python.exe -m pytest tests\oracle\test_oracle_validation.py -m "not external_network" -q

    # Release-facing documentation guard
    .\.venv\Scripts\python.exe scripts\check_doc_consistency.py

Ruff is configured for Python 3.10-compatible correctness checks (`E4`, `E7`,
`E9`, and `F`). The repository-wide result is currently an audit baseline, not
a green acceptance gate; report remaining pre-existing debt explicitly and do
not use `--fix` across unrelated work:

    .\.venv\Scripts\ruff.exe check moira moira_server tests scripts --no-fix

There is no universal benchmark command. The following is only the current
LOLA filter performance smoke; its timing is not scientific validation:

    .\.venv\Scripts\python.exe tests\benchmark_lola_filters.py

Other benchmark and live-oracle scripts are data-, network-, or manifest-
dependent and must be inspected before use. The repository currently has no
configured formatter, static type-check, tox, nox, or pre-commit command; do
not claim those checks ran.

Network capability is explicit:

- unmarked tests are denied destination-bearing network operations;
- `loopback` admits only numeric IPv4/IPv6 loopback and local IPC;
- `external_network` requires both `--run-external-network` and an isolated
  external-only selected item set, normally `-m "external_network"` or exact
  external node IDs. The flag alone grants nothing, and external cases must
  never share a process with denied or loopback cases.

The Python policy is accidental-egress containment for cooperative CPython
code, not a security sandbox. Native/ctypes Winsock calls, immutable raw
`_socket` method descriptors, cached pre-install methods, SSL/native writes on
pre-existing or foreign descriptors, startup activity before repository
conftest installation, inherited or hostile descriptors, `python -S`, and a
child that shadows or removes the cooperative `sitecustomize` bootstrap
require runner-level egress denial. Adding that CI/runner boundary remains a
separately approved change.

The `dev` extra covers the base-engine CI/test surface, not every optional
suite. Server tests require `server`; lunar-graze tests require `lunar-graze`;
live Horizons tooling may require undeclared `astroquery`; UI tests skip unless
PySide6 is installed separately because no UI extra is declared.

Fixture definitions live in `tests/conftest.py`; root `conftest.py` sanitizes
import resolution and installs the deny-by-default network audit hook as early
as repository conftest loading permits. Pytest configuration and markers live
in `pyproject.toml`.

### Repository map

- `moira/`: Python doctrine, public engine API, orchestration, astronomical
  reduction, and astrology techniques.
- `src/native/`: C++17 implementation and pybind11 bindings for admitted
  native substrate.
- `moira_server/`: optional FastAPI transport; engine doctrine must not migrate
  into route or serializer code.
- `tests/`: unit, integration, server, oracle, fixtures, golden artifacts,
  snapshots, and validation evidence.
- `moira/data/` and `moira/kernels/`: packaged tables, identity/provenance data,
  and manifest metadata; large kernels remain external resources.
- `wiki/`: canonical documentation tree. `moira.wiki/` is generated by
  `scripts/sync_git_wiki.py` and must not be hand-edited.
- `scripts/` and `tests/tools/`: scoped build, validation, benchmark, and test
  support; a script name alone does not make it an acceptance gate.

### Protected Zones (path-anchored)

Protected zones require an explicit pre-edit declaration, source/fixture
review, and targeted verification. The named paths are anchors, not permission
to treat adjacent sensitive code as ordinary.

| Path anchors | Zone | Status |
|---|---|---|
| `moira/planets.py`, `moira/ssb.py`, `moira/light_cone.py`, `moira/_solar.py`, `moira/orbits.py`, `moira/phase.py`, `moira/phenomena.py`, `moira/sky/` | Planetary, solar-system, photometric, and sky-position reduction | PROTECTED |
| `moira/rise_set.py`, `moira/stations.py`, `moira/eclipse.py`, `moira/eclipse_contacts.py`, `moira/eclipse_geometry.py`, `moira/eclipse_search.py`, `moira/occultations.py`, `moira/heliacal.py`, `moira/lunar_limb.py` | Astronomical event, visibility, eclipse, occultation, and topography computation | PROTECTED |
| `src/native/`, `moira/moira_native.py`, `moira/dispatch.py` | Native substrate, bindings, dispatch, and admitted or candidate native implementations | PROTECTED |
| `moira/julian.py`, `moira/delta_t_physical.py`, `moira/precession.py`, `moira/nutation_2000a.py`, `moira/obliquity.py`, `moira/corrections.py`, `moira/coordinates.py`, `moira/polar_motion.py` | Time scales, Earth orientation, frames, corrections, refraction, and transforms | PROTECTED |
| `moira/spk_reader.py`, `moira/_spk_body_kernel.py`, `moira/_kernel_paths.py`, `moira/daf_writer.py`, `moira/lunar_limb.py`, `moira/moira_native.py`, `moira/dispatch.py`, `moira/kernels/`, `CMakeLists.txt`, `setup.py`, `pyproject.toml` | SPK/DAF/PCK/FK/LSK access, resource binding, and native build contract | PROTECTED |
| `tests/conftest.py`, `tests/KNOWN_ISSUES.yml`, `tests/oracle/`, `tests/golden/`, `tests/snapshots/`, `tests/artifacts/oracle/`, `wiki/03_validation/` | Validation policy, thresholds, authority comparison, golden evidence, and regression baselines | PROTECTED |
| `tests/artifacts/benchmarks/`, `tests/benchmark_lola_filters.py` | Performance evidence and benchmark baselines; never scientific validation | PROTECTED |
| `moira/data/`, `moira/stars.py`, `moira/star_types.py`, `moira/asteroids.py`, `moira/comets.py`, `PROVENANCE.md` | Catalog identity, scientific tables, manifests, licensing, and provenance | PROTECTED |
| `moira/__init__.py`, `moira/facade.py`, the existing `moira/_facade_*.py` modules, `moira/chart.py`, `moira/constants.py`, `moira_server/` | Public exports, canonical result semantics, defaults, and REST contracts | PROTECTED |
| `moira/constants.py`, `moira/compat/nasa/`, `tests/oracle/`, `tests/artifacts/oracle/` | External authority mappings and comparison corpora | PROTECTED |
| Other astrology technique modules under `moira/`, including `moira/primary_directions/` and `moira/harmograms/` | Technique implementation; any exported vessel, doctrine default, or overlap with a protected anchor inherits PROTECTED handling | normal by default |

### Pre-Edit Ritual

Before editing:

1. State the requested change in concrete terms.
2. Identify the minimum files that must be touched and preserve unrelated
   work shown by `git status`.
3. Check the change against the Protected Zones table; if implicated, say so
   explicitly before editing.
4. Name the governing computational or doctrinal object, ambiguity policy,
   authority, provenance, and data resources relevant to the change.
5. Identify existing fixtures and the smallest tests, parity slices, or oracle
   checks that prove the requested behavior.
6. State the intended verification path and use the project `.venv` for every
   execution.

### KNOWN_ISSUES.yml

`tests/KNOWN_ISSUES.yml` uses a top-level `known_issues` list. Each entry must
contain `id`, `path`, `reason`, `owner`, and `expires`; `path` is relative to
`tests/` and must exist, and `expires` is an ISO `YYYY-MM-DD` date. Invalid or
stale-path entries fail pytest configuration. `id` is a 1–64 character ASCII
slug containing only letters, digits, underscores, periods, and hyphens.
Expired entries print by default and fail when
`MOIRA_STRICT_KNOWN_ISSUES=1`.

An entry is permitted only for a verified, pre-existing, explicitly accepted,
bounded deferral outside the current task. It never skips or xfails a test and
must never conceal a failure introduced by the current change. Fix in-scope
issues instead. An expired entry must be repaired, removed, or explicitly
renewed by its owner; never leave it as a silent warning.

### Completion Receipt

At completion, report:

- files changed and what changed in each
- what was intentionally left untouched, including unrelated work
- exact commands run and their outcomes, skips, prerequisites, and scope
- which authority, fixture, corpus, tolerance, and native/Python path were
  actually exercised
- unresolved risks, assumptions, divergences, or validation gaps

---

## Part IV — Technical Laws

### Law of Substrate Primacy

Astronomical substrate code is foundational. Do not weaken, bypass, or flatten
substrate computation for the sake of easier downstream astrology. Do not
privilege astrological convenience over astronomical correctness.

### Law of Policy Explicitness (no hidden black boxes)

Correction regimes, computational assumptions, and model choices must remain
explicit. Do not replace declared policy with hidden defaults or ambient
behavior. Do not conceal computational stages unnecessarily; prefer explicit
policy, visible derivation, and inspectable logic.

### Law of Determinism

Prefer deterministic, reproducible computation. Do not introduce hidden state,
ambient mutation, or uncontrolled fallback behavior.

### Law of Semantic Honesty

Do not collapse distinct astronomical products into one vague public concept.
If the domain distinguishes between nominal limits, profile-conditioned bands,
practical observing products, or theoretical models, Moira preserves those
distinctions explicitly.

### Law of Preservation

Preserve: clear separation between substrate computation and derived
astrological technique; explicit computation policies; validation credibility;
catalog and data licensing clarity; stable public engine semantics; body-first
identity modeling where applicable; the distinction between nominal theory,
corrected products, and observationally-conditioned products.

Never collapse: astronomy into astrology; policy into hidden defaults; engine
truth into marketing simplification; distinct product semantics into one
convenience surface.

### Law of Minimal Touch

Use the smallest correct change. Modify only what the requested task requires.
Do not refactor, reorganize, or "clean up" unrelated code. Do not widen edits
beyond what correctness requires.

### Law of Data and Provenance

Catalogs, constants, identity registries, and external datasets must have
clear provenance. Do not introduce undocumented third-party data or unclear
licensing dependencies.

When binding external data: record provenance clearly; prefer official
datasets over convenience mirrors; avoid undocumented caches or unclear local
files; never silently substitute a weaker data source for a stronger required
one.

If the repository lacks a required authoritative dataset, say so plainly. Do
not pretend sovereign computation exists when the required data layer does not
yet exist.

### Source Hierarchy and Authority

Authority is product-specific. First define the computational product, frame,
timescale, correction regime, and event or observational semantics; then prefer
the highest authority that actually governs that object. Unless the task
explicitly requires otherwise, use this order:

1. primary scientific or institutional sources
2. official standards bodies and reference libraries
3. domain-primary operational authorities
4. independent secondary engines
5. tertiary explanatory summaries

Examples: JPL or NAIF may govern kernel and ephemeris truth; IAU, IERS,
SOFA, or ERFA may govern reference systems, Earth orientation, and transforms;
IOTA may govern a particular occultation path or observational product; a
primary historical or doctrinal text may govern an astrological technique.
No authority automatically governs every stage of a pipeline.

Swiss Ephemeris may be an explicitly bounded secondary comparator, never the
automatic summit authority or runtime substrate. Do not anchor implementation
to a secondary engine when a stronger product-relevant authority is available.

Keep four evidence classes distinct:

- **Regression parity:** current output agrees with an approved prior Moira
  artifact; this detects change but does not establish external truth.
- **Authority validation:** output is compared with a product-relevant primary
  source under named semantics and tolerances.
- **Cross-engine corroboration:** output agrees with an independent secondary
  engine; useful evidence, not primary proof.
- **Physical or geometric invariants:** output satisfies independently derived
  constraints; strong structural proof, but not a substitute for an external
  authority where one governs the product.

### Research and Derivation Law

When the user asks for the real math, seek the real math.

Do not invent formulas that already exist in primary literature, reference
manuals, or authoritative code lineage. Do not infer a governing method from
outputs alone when the source formulation can be researched directly. Do not
keep iterating on approximations once it is clear a source-derived method is
required.

When implementing from an authority: name the authority; state the
computational object being implemented; keep the derivation legible in code or
comments where needed; validate the resulting behavior against the correct
oracle.

### Implementation Discipline

Prefer: precise, explicit code; existing Moira patterns; policy-aware design;
stable public semantics; readable computational flow; source-derived formulas
where authoritative formulas exist.

Avoid: generic enterprise abstraction; hidden magic; black-box wrappers;
convenience-driven architectural shortcuts; invented formulas where the real
method is available.

---

## Part V — Sovereignty and Lineage Law

### V.1 Presumption of leakage

Model-training leakage from familiar external codebases is a live operational
risk across the entire repository — especially in domains with strong public
reference engines (Swiss Ephemeris–shaped patterns above all).

Assume:

- Without a strong derivation scaffold, lineage leakage is probable by default.
- Leakage may appear as structural convergence rather than verbatim copying.
- Numerical correctness and passing parity tests do not clear lineage smell.

### V.2 Anti-leakage workflow (applies to all implementation work)

1. **Define the governing object first.** State the geometric, astronomical,
   mathematical, or doctrinal object being implemented before writing any
   implementation shape.
2. **Define ambiguity policy before repair logic.** Branches, singularities,
   and equivalent paths get an explicit branch-selection doctrine before code.
3. **Define assembly doctrine before materialization.** Name the parts of a
   result vessel and their lawful relations before filling indices or slots.
4. **Implement from the declared doctrine** — not from a remembered software
   pattern.
5. **Run a smell audit after the correctness audit.** Numerical validation
   does not close the task; inspect helper shape, branch handling, assembly
   style, and proof framing.

### V.3 Leakage indicators

- Helper functions mirroring the internal shape of a familiar external engine
  without a Moira-owned governing object.
- Post hoc repair loops, quadrant flips, hardcoded branch workarounds, or
  index-mapped adjustments that are implementation-shaped, not doctrine-shaped.
- Hand-filled array assembly following legacy engine slot order rather than
  named computational objects.
- Validation framing in which "matches X" performs the main epistemic work.
- Comments or explanations that conceal the real derivation behind
  software-familiar language.

### V.4 The five ownership axes

When the user asks for a Swiss-smell, lineage, clean-room, or sovereignty
audit, apply the strictest possible standard. The burden of proof is on the
code. Numerical agreement never discharges that burden.

Structural similarity to an external implementation is a finding requiring
derivational justification, not automatic proof of leakage. Similarity is
acceptable only when demonstrably imposed by mathematics, a primary standard,
a file format, numerical stability, or the governing computational object. The
implementation must document that necessity and validate the derivation
independently. Familiarity, convenience, and parity alone are not sufficient.

This is not a loophole for remembered Swiss-shaped helper decomposition,
copied branch staging, legacy array assembly without object-owned meaning,
post hoc quadrant repair without doctrine, cosmetic renaming, or “matches
Swiss” as the primary proof. Where necessity is not demonstrated, a subsystem
that looks naturally at home in a legacy external engine fails even when its
numbers are correct.

1. **Ontology ownership.** What object does the code think it is implementing,
   and is it stated in Moira's own architectural language? Table-era angle
   staging where the architecture demands a deeper geometric object is a
   lineage smell. Angle formulas may appear as derived or optimized forms, but
   must not silently replace the governing geometric object.
2. **Derivation ownership.** Can the implementation be derived from primary
   authority or first principles without Swiss-like computational staging? If
   the best explanation is "this is how Swiss-like engines do it," it fails.
   Source-derived formulas are acceptable; inherited software decomposition is
   not.
3. **Structural ownership.** Helper boundaries, temporaries, branch structure,
   loop order, assembly order, and post-processing shape are executable
   structure, not style. Legacy similarity fails unless the implementation
   demonstrates that the governing object, primary specification, file format,
   or numerical-stability requirement imposes it and proves the derivation
   independently.
4. **Policy ownership.** Ambiguities must be resolved by explicit doctrine.
   Hidden repairs, quadrant flips, index-mapped corrections, ad hoc branch
   patches, or visible-engine workarounds without source-owned doctrine fail.
5. **Validation ownership.** Source-owned invariants carry the main proof
   burden. Swiss or any secondary engine may corroborate but must not perform
   the primary epistemic work. If "matches Swiss" is still doing most of the
   proof, it fails.

One standing check outside the axes:

- **Provenance honesty.** Historical permission, attribution, or legal
  provenance notices may remain in a file for honest legal reasons. They grant
  no permission to keep emitting lineage-shaped executable structure, and must
  not masquerade as the current governing implementation identity. Preserve
  honest notices while making the live computational path, branch doctrine,
  assembly doctrine, and validation story visibly Moira-owned.

### V.5 Severity and reporting

- **CRITICAL** — governing ontology, branch policy, or executable structure is
  still visibly inherited from an external lineage.
- **MAJOR** — partial Moira-owned framing, but lineage-shaped helpers,
  decomposition, or proof posture remain.
- **MINOR** — largely Moira-owned; residual language, naming, or validation
  framing obscures that ownership.

Fail-fast: numerically correct code that still thinks in inherited
classical-table or legacy-engine terms where Moira demands a deeper spatial or
object-owned ontology is at minimum a MAJOR finding.

Prohibited false reassurance: never report a subsystem as "clean,"
"sovereign," "Moira-owned," or "substantially de-Swissed" unless it passes all
five axes. Removing helper fingerprints, branch repairs, or array smells is
necessary but not sufficient. Partial cleanup must be reported as partial
cleanup.

---

## Part VI — Diagnostics, Verification, and Documentation

### Diagnostic Discipline

When a validated result disagrees with an external authority, do not guess
blindly. Isolate the discrepancy by strata where possible:

inputs and identities → time scales → reference frames → apparent versus
geometric quantities → topocentric conversion → event semantics → published
product semantics → numerical search or solver behavior

If a suspected cause has been measured and ruled out, stop blaming it
casually. Use residual budgets, term-by-term comparisons, or controlled
single-case audits before widening implementation changes.

### Oracle and Parity Law

Parity claims must be specific. Never say "matches X" without naming:

- function or public surface
- evidence class from Part IV: regression parity, authority validation,
  cross-engine corroboration, or invariant testing
- authority or comparator
- date or interval and sample size
- tested bodies, stars, event classes, or products
- frame, origin, timescale, correction regime, and event semantics where
  relevant
- units and tolerance
- known exclusions and unresolved residuals

Do not imply broad parity from a narrow slice. Do not let one pathological
case define an entire subsystem. Do not let a convenience comparison displace
a higher-authority oracle. Python/native agreement is not external validation,
and external agreement does not by itself clear a lineage audit.

### Verification and Honesty Law

Never mark work complete without stating what was verified. Use the smallest
relevant verification first: targeted tests; focused numerical checks via the
Testing Liturgy (Part VII); compile or import checks; validation scripts or
benchmark slices whose actual exit behavior and prerequisites were inspected.

If verification cannot run, state exactly what was not run and why. Do not
claim precision preservation unless precision-relevant checks actually ran.
Do not invent successful runs, validation results, or accuracy claims. Do not
imply parity with external oracles unless checked. Do not imply a mathematical
lineage has been implemented unless it actually has. If uncertain, say what is
uncertain and how it should be resolved.

### Documentation Law

Documentation must tell the truth about the code as it actually stands. Do not
leave placeholder text governing live code. Do not claim stronger standards
alignment than the executable path and validation support.

- Benchmark results are performance evidence, not scientific validation.
- Snapshots are regression baselines, not external truth.
- A golden artifact is authoritative only when its producing test or adjacent
  record names provenance, semantics, units, and tolerance.
- Secondary-engine agreement is corroboration, not primary validation.
- Remove or qualify unverified precision claims.
- Correct touched architecture prose that is expired or superseded by runtime
  truth; do not preserve a stale claim merely because it is documented.

When implementation truth changes materially, update the minimum necessary
public, doctrinal, architecture, and validation-facing documentation. The
Completion Receipt is defined once in Part III.

---

## Part VII — The Testing Liturgy

Moira does not merely "run tests"; she performs a Testing Ritual to verify the
alignment of the engine with celestial truth. Follow this liturgy in all
verification tasks. Invocation commands live in Part III under installation,
build, test, and validation commands.

### Inventory of available fixtures

Fixture definitions live in `tests/conftest.py`. Reuse them when their scope
matches the test; never copy astronomical constants merely to avoid a fixture.

- `moira_engine` is one session-shared `Moira()` facade, requires a discovered
  planetary kernel, and skips when none is found. Prefer it for ephemeris-bound
  tests to avoid per-test facade/kernel initialization. Direct `Moira()`
  construction remains valid for isolated facade construction, readiness,
  monkeypatch, or dependency-injection tests that are testing that construction
  itself.
- `natal_chart` and `natal_houses` are session-scoped products for
  2000-01-01 12:00 UTC. `natal_houses` uses London latitude 51.5°, longitude
  -0.1°, and Placidus.
- `jd_j2000` is the session-scoped numeric anchor `2451545.0`. It does not
  assign a timescale to an API that has different input semantics; the test
  must name the timescale it is exercising.
- `reference_epoch` is a function-scoped, five-case parameterization of
  `(jd, label)` tuples for representative structural sweeps. It is not the full
  supported range or an external chronological oracle; verify a label before
  using it as date truth.
- `moira_approx` is a function-scoped convenience around
  `pytest.approx(..., abs=tol)`. Its raw absolute tolerances are
  `longitude=1e-6`, `distance=1e-9`, `angle=1e-4`, `time=1e-8`, and
  `ratio=1e-9`. It has no unit model, circular-longitude semantics, frame,
  timescale, or authority knowledge. Use it only for local numeric equivalence
  after the test has established that the named kind and tolerance fit the
  product.
- `snapshot` and `golden` are function-scoped exact JSON comparisons.
  `snapshot` records implementation regression. `golden` is merely a storage
  channel; it becomes external evidence only when the producing test or an
  adjacent record separately establishes authority, provenance, semantics,
  units, and tolerance.
- `assert_longitude` checks only the structural invariant
  `0.0 <= value < 360.0`; it says nothing about accuracy.
- `ritual` is function-scoped and wires `snapshot`, `golden`, and the pytest
  node ID into `tests/tools/ritual.py`.

### Product-owned tolerance policy

No fixture tolerance is a universal astronomical accuracy threshold. The
product under test owns its tolerance and must state the relevant basis:

- angular positions need units, circular-difference handling, origin, frame,
  epoch, timescale, and apparent/geometric regime;
- distances and velocities need units, center, derivative convention, and
  kernel/model basis;
- coordinate transforms need round-trip or primary-standard residuals and
  singularity treatment;
- event times need timescale, search interval, event definition, solver
  tolerance, and contact/root-selection semantics;
- house cusps and doctrine products need system and fallback policy rather
  than borrowed planetary tolerances;
- refraction-sensitive, catalog-limited star, historical delta-T, and
  observational/profile-conditioned products need model- and data-specific
  uncertainty or acceptance bands.

Name the authority, corpus, sample size, exclusions, units, and threshold next
to the relevant test or artifact. Do not relax a baseline merely to absorb a
regression.

### The Generative Ritual: Summon, Witness, Covenant

These terms map to concrete actions; there is no `summon()` fixture method.

1. **Summon:** execute the computational path without presupposing its output.
2. **Witness:** serialize and compare the result with an implementation
   snapshot, or with a separately provenance-backed golden artifact.
   Witnessing alone does not establish truth.
3. **Covenant:** assert independent structural, physical, relational,
   temporal, or authority-derived invariants using a tolerance owned by the
   product.

The `Ritual` methods have exact limits:

- `witness(name, value)` uses a snapshot by default;
  `as_golden=True` selects the golden channel.
- `cross_witness(a, b, keys=..., abs_tol=...)` applies `abs_tol` only to
  selected float keys; with no keys it compares whole objects exactly.
- `temporal_covenant` checks a predicate for consecutive values.
- `taboo` rejects one forbidden state; `sweep_taboo` evaluates the complete
  supplied sweep and reports all violations.
- `round_trip` supports recursive float `abs_tol`. `dual_path` delegates to
  `cross_witness` and inherits its selected-float-key limitation; unkeyed
  values compare exactly. The caller still owns the semantics and tolerance.

Invariant families include:

- **Round-trip purity:** a forward/inverse composition recovers the original
  within the product's justified tolerance.
- **Dual-path equivalence:** independently assembled paths to the same defined
  object agree.
- **Temporal continuity:** bounded-step, monotonic, or ordering laws hold over
  an explicitly sampled series.
- **Taboos:** forbidden physical or semantic states never manifest.
- **Authority covenant:** a result meets a named primary reference under
  matching product semantics.

Ordinary pytest access to snapshots and goldens is strictly read-only. The
legacy `MOIRA_SNAPSHOT_UPDATE` and `MOIRA_GOLDEN_UPDATE` modes are forbidden.
Candidate generation must be a separate, future tooling surface that writes a
new candidate tree atomically; protected evidence changes require explicit
provenance review and promotion. Never update a snapshot, golden, oracle
artifact, or tolerance merely to make a failing test pass.
