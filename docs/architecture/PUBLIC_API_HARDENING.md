# Additive public API hardening

Public APIs may grow without editing a second, exact copy of all export names.
The current admission declaration is the module's curated `__all__`; facade
methods are explicitly declared public methods on `Moira` and its mixins.
This does not automatically export every imported name or private helper.

## What the release gate enforces

- Previously enumerated root exports and facade methods remain compatibility
  floors: their removal still fails. The historical inventories are preserved
  verbatim and are never generated from the running package to obtain a pass.
- Every current export has a valid name, is bound, is duplicate-free, and does
  not expose private helpers or imported module namespaces. The existing
  `__author__` and `__version__` metadata exports remain explicitly admitted.
- Every root export is also admitted by the canonical facade and resolves to
  the same object. Root exports remain a curated subset, not a mirror of every
  facade export.
- Star import matches the current curated root declaration exactly, including
  object identity; no undeclared names may leak.
- Every current public facade method is checked for instance callability,
  including newly added, inherited, static, and class methods.
- Layering and product-specific identity, signature, default, doctrine,
  scientific accuracy, and provenance tests retain their existing policy.

The shared guards have adversarial self-tests for both accepted additions and
rejected removals, missing bindings, duplicate names, private helpers, module
leaks, layer inconsistencies, and shadowed methods. Release Hardening runs
these tests as well as the actual package surface checks.

## Adding a feature

1. Declare its intended exports in the owning module and curated public layers.
   An intentional public facade method must use a public name; internal helper
   methods must use an underscore prefix.
2. Add feature-specific behavior and public-contract tests. Structural guards
   do not establish scientific correctness, doctrine, documentation, or
   semantic compatibility.
3. Run `python -m pytest tests/unit/test_public_api_contract.py
   tests/unit/test_public_api_drift.py
   tests/unit/test_api_surface_adversarial_audit.py -q` in the project `.venv`,
   followed by the relevant feature and release slices.

Do not append every additive feature to the historical compatibility floor.
Advancing that floor is a deliberate release-contract review, not an automatic
snapshot update. Until a new API enters the release floor, its own product
tests must protect it from removal. Existing signature/default tests remain
necessary: these name-based floors do not freeze call signatures or behavior.

Scientific snapshots, raw authority responses, source hashes, native substrate
requirements, oracle tolerances, and kernel prerequisite policies are outside
this change. Dynamic surface validation must not normalize or refresh that
evidence merely to turn CI green.
