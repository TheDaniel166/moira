# Physical Heliacal Visibility Phase 2 Checkpoint

Date: 2026-07-30
Status: historical implementation checkpoint; Phase 2 is now closed

Final receipt:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CLOSURE_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CLOSURE_2026-07-30.md)

## Boundary

This checkpoint covers Python spectral single-epoch truth only. It does not
activate the Phase 3 event solver, Phase 4 environmental expansion, Phase 5
root/facade/REST parity, native parity, automatic data acquisition, or runtime
radiative-transfer execution.

The physical data pack remains an explicit caller-supplied local path. The
engine does not search for, download, generate, or silently substitute a pack.
All legacy visibility policies and call paths remain separate.

## Implemented

- exact validation of the installed compatibility contract, root manifest,
  semantic pack version, engine contract, payload inventory, file sizes,
  per-file SHA-256 values, notices, provenance, and declared source artifact;
- no-extrapolation interpolation of photopic/scotopic directional twilight
  luminance and 400-bin direct spectral extinction;
- maximum-contributing-corner solver uncertainty plus maximum, p95, and
  storage error receipts;
- CIE MES2 fixed-point adaptation with a bounded same-equation bisection
  fallback;
- Crumey equations 28 and 34 with fixed `F=2` and explicit published
  background domain;
- measured total directional background precedence, fully qualified SQM
  transformation, modeled twilight plus source-owned dark-sky anchor, and
  visibly coarse explicit Bortle fallback;
- rejection of background double counting;
- response-weighted photopic and scotopic target transmission;
- typed evaluated-clear, not-applicable, missing-dependency, and out-of-domain
  results with component, atmosphere, validity-domain, observer, background,
  target, threshold, and data-pack receipts; and
- an additive owning-module `physical_visibility_assessment()` path that does
  not alter `visibility_assessment()`.

At this checkpoint, Moira owned the first-candidate planetary magnitude
identity:
`mallama_hilton_2018_moira_planetary_v1`. A caller cannot relabel that
calculation. Caller input is limited to source-identified spectral response
weights for the requested target. The closure subsequently removed that
temporary caller-profile surface and made all first-candidate planetary
profiles pack-owned.

## Observer Protocol Correction

The admitted identifier is:

```text
known_location_directed_averted_observation_v1
```

The target location is known and attention is directed, but the visual task is
averted/peripheral after adaptation to the immediate directional field. This
correction was made before public contract parity because CIE TN 007:2017
clause 6 does not admit MES2 for a foveal task.

## Exact Source Receipts

| Source | SHA-256 | Admitted use |
|---|---|---|
| Crumey 2014 arXiv PDF | `fa6ef183f9402be4d321bff5fa2c112510f89ca683b534e33c63fdb6538e50a4` | Equations 28 and 34 |
| CIE TN 004:2016 PDF | `a549fcf5f98ae5fdd959b331dbb91eae99f5fd397bd288ad6b59c43723a4494f` | MES2 equations and quantities |
| CIE TN 007:2017 PDF | `efdd11f4bdf7d77ab3b1fb8e6b94ac89599521eba7425e474bbc82cf34c7877a` | Official worked examples and task restriction |
| Tousey-Koomen 1953 public page | `4e50f748c6c0de310ceeadcbbcd0a6626a3fccd74fe1063f9cc91640ad3212ef` | Independent eight-row threshold check |

The source-owned equation fixture is
`tests/fixtures/physical_visibility_phase2_equations_v1.json`.

## Data-Pack Runtime Receipt

The exact Phase 1 pack was loaded through the new public orchestration path on
Windows from its explicit local directory:

```text
pack_id: moira-physical-heliacal-visibility
version: 1.0.0
manifest_sha256: 49ac2b68ea105a8e055b27e8d4d70f6cbfe9533f971ef5e6000f0bdd95d6771b
```

The deterministic smoke geometry was target true altitude `5 degrees`, solar
center altitude `-6 degrees`, and relative solar azimuth `60 degrees`. It
returned `evaluated_clear_sky`, seven component receipts, an in-domain
validity receipt, and a visibility margin of
`-1.944806269496668 magnitude`. The uniform target spectrum used in this smoke
was test-only evidence and is not an admitted planetary profile.

## Verification

- `62` Phase 2 loader, equation, composition, public-orchestration, failure,
  boundary, provenance, error-envelope, and pickle round-trip tests pass.
- Ruff passes on the Phase 2 implementation and test files.
- The focused legacy selection passes `181` tests after deselecting the same
  two pre-existing resource-mocking failures.
- The two remaining legacy failures are:
  - lunar Yallop event fixture does not provide an active planetary kernel for
    the later assessment call; and
  - fixed-star not-found fixture mocks `planet_at` but not the newer Sun
    `sky_position_at` resource path.
- Neither failure enters a Phase 2 file or indicates a changed legacy default.

## Gates Open At This Checkpoint

All checkpoint gates are now closed:

- pack version 1.1 owns source-locked profiles for Mercury, Venus, Mars,
  Jupiter, and Saturn;
- an independent validator rederives the target payload from exact local
  source receipts without importing the builder or engine;
- JSON-safe and immutable pickle round trips pass without activating Phase 5;
- both incomplete legacy resource fixtures were repaired at their test
  boundaries; and
- the final closure receipt records the exact pack, test, and documentation
  evidence.
