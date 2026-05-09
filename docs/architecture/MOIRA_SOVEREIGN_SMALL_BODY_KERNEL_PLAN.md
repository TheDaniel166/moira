# Moira Sovereign Small-Body Kernel Plan

Status date: 2026-05-09

Purpose:
Freeze the random-asteroid failure diagnosis, define the replacement
doctrine for `sb441-n373s.bsp` and the legacy `asteroids.bsp` surface, and
record the first verified sovereign type-13 subset result.

This is now an active migration path with a proven subset, not merely a
forward plan.

## Current Diagnosis

The `2026-05-09` absolute oracle audit established three important truths:

- the planetary public path is externally healthy
- the custom Moira-owned type-13 `Toutatis` path is externally healthy
- the broad random-asteroid public surface is not healthy

The asteroid failure is not one vague discrepancy class. It currently splits
into two concrete faults:

1. `sb441-n373s.bsp` bodies are being corrupted by the `SmallBodyKernel`
   type-2/type-3 execution path
2. `asteroids.bsp` uses a legacy frame code (`1900017`) that is not being
   handled correctly by the current public asteroid path

The first fault is more foundational:

- `sb441` itself is healthy as a source kernel
- `SpkReader.position(10, target, jd_tt)` on `sb441` is healthy
- `SmallBodyKernel.position(target, jd_tt)` on the same `sb441` body is not

That means the random-asteroid broad-surface failure is a small-body
infrastructure problem, not a planetary problem and not a mere apparent-term
residual.

## Governing Decision

Moira will prefer the long-term sovereign small-body path rather than
investing in deeper compatibility maintenance for legacy mixed segment
formats.

The intended separation is:

- planets stay on `DE441` and the major-planet substrate
- small bodies move onto Moira-owned type-13 sampled-state kernels

That separation is doctrinally clean:

- planetary truth remains JPL planetary-kernel governed
- erratic or non-planetary bodies move to an explicit Moira-owned sampled
  state product

## Target Doctrine

The sovereign small-body layer should have these properties:

- source authority remains explicit
- source states are sampled from the higher-authority kernel or external
  authority, not invented
- output format is Moira-owned type 13
- frame policy is explicit and uniform
- validation is performed against the source kernel before public admission
- public asteroid routing should eventually no longer depend on the broken
  `SmallBodyKernel` type-2/type-3 path

## Important Constraint

The current `write_spk_type13()` implementation cannot emit all 373 `sb441`
bodies into one BSP file, because it currently supports only a single summary
record and a single name record.

So the sovereign replacement should be designed as:

- a sharded type-13 kernel set
- plus a manifest that records shard membership, provenance, sampling policy,
  and verification results

not as one giant monolithic replacement file.

## Build Program

1. Read source states from `sb441-n373s.bsp` through the healthy `SpkReader`
   path, not through `SmallBodyKernel`
2. Sample body states on a declared cadence across declared coverage
3. Convert source velocities to the unit law required by Moira's type-13
   writer (`km/s`)
4. Emit sharded type-13 BSP files
5. Emit a manifest describing:
   - source kernel
   - date range
   - cadence
   - shard membership
   - body identity mapping
   - node verification results
6. Validate the new type-13 shards against the source kernel and then against
   external oracle samples where appropriate

## Admission Standard

The sovereign replacement should not be admitted merely because it is cleaner.

It must prove:

- node fidelity against the source kernel
- stable public-path behavior through `asteroid_at(...)`
- acceptable external-oracle agreement on a representative minor-body sample

Until then, this is an active migration path, not a completed replacement.

## Proven Subset

As of `2026-05-09`, the sovereign path has already cleared one important
admission-style proof on a real failure slice.

A Moira-owned type-13 shard was built from healthy `sb441` source states for
the same 20-body asteroid sample that previously failed catastrophically on
the public legacy path:

- `Adeona`
- `Aeria`
- `Aethra`
- `Apollonia`
- `Ara`
- `Boliviana`
- `Cantabia`
- `Echo`
- `Eos`
- `Hypatia`
- `Kalypso`
- `Luscinia`
- `Makemake`
- `Mashona`
- `Nemesis`
- `Oceana`
- `Phaeo`
- `Semiramis`
- `Tisiphone`
- `Ursula`

Artifacts:

- `tests/artifacts/kernels/sb441_type13_random20/manifest.json`
- `tests/artifacts/kernels/sb441_type13_random20/sb441_type13_shard_001.bsp`
- `tests/artifacts/oracle/absolute_oracle_check_2026-05-09_sovereign_random20.json`

What this proved:

- node fidelity against the sampled `sb441` source states stayed extremely
  tight, with max node errors on the order of `1e-08 km`
- the same 20-body public-surface oracle slice that failed on the legacy
  path collapsed into a healthy sub-arcsecond regime on the sovereign path

Measured result for the sovereign 20-body slice on `2026-05-09`:

- asteroid median absolute longitude delta: `0.0611"`
- asteroid median absolute latitude delta: `0.0115"`
- asteroid max absolute longitude delta: `0.1286"`
- asteroid max absolute latitude delta: `0.0578"`

This does not yet prove that the full sovereign small-body migration is
complete. It does prove that the replacement doctrine is executable and that
it resolves the diagnosed failure class on a representative real subset.

## Broader Build Milestone

The sovereign path has also now cleared a broader practical milestone:

- full `sb441` named-body transcode over `2020-01-01` to `2030-01-01`
- `355` named bodies admitted
- `15` type-13 shard files emitted
- all named `sb441` bodies covered by `ASTEROID_NAIF` were included

Artifacts:

- `tests/artifacts/kernels/sb441_type13_full_2020_2030/manifest.json`
- `tests/artifacts/oracle/absolute_oracle_check_2026-05-09_sovereign_full_random20.json`

The live `2026-05-09` external-oracle audit on a random 20-body slice drawn
from that full sovereign build stayed healthy:

- asteroid median absolute longitude delta: `0.0554"`
- asteroid median absolute latitude delta: `0.0105"`
- asteroid max absolute longitude delta: `0.1081"`
- asteroid max absolute latitude delta: `0.0257"`

This does not yet mean the public routing layer has been migrated. It does
mean the sovereign shard build is already viable at meaningful scale.
