# Physical Heliacal Visibility Phase 3 Restart Checkpoint

Date: 2026-07-30

Updated: 2026-07-31

Status: Phase 3 scoped acceptance and pre-commit cleanup complete; uncommitted
resting point

Baseline and current `HEAD`:
`2141a33bebe9898e1164824c06aba28a8408adeb`

`origin/main` at checkpoint:
`2141a33bebe9898e1164824c06aba28a8408adeb`

Governing roadmap:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Closure receipt:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md)

## Resting State

Phase 3 engine work has reached its scoped exit gate. The additive Python
direct-module boundary now has:

- certified visibility-margin event solving;
- typed first-day and last-day ownership;
- exact data-pack version 1.2 admission;
- Mars, Jupiter, Saturn, and Sirius event admission;
- explicit Mercury and Venus event non-admission;
- sovereign Sirius identity and BSC5/CALSPEC/CIE profile binding;
- independent pack, certificate, and event-golden validators; and
- live exact-pack Jupiter and Sirius engine replays.

No Phase 4 work has started. No facade, serializer, REST, OpenAPI, native,
website, version, tag, release, or deployment work is included.

The working tree is intentionally uncommitted. Nothing was staged, committed,
or pushed at this checkpoint.

## Exact Accepted Evidence

### Runtime tests

Repository `.venv`, Python 3.14.3, offline mode:

```text
Phase 3 focused unit and governance gate:
51 passed

Exact-pack external-golden engine replay:
2 passed
Jupiter: 32.505 seconds
Sirius:  18.611 seconds

Broad physical-visibility compatibility gate:
672 collected
671 passed
1 skipped: pre-existing empty optional validation enumeration
0 failed
0 deselected
```

The current validation harness collected both integration cases successfully.
The new replay originally carried a free-form `serial` reason. The current
harness correctly rejected it, and the marker was removed because the tests
do not mutate a shared resource. They remain `slow` and
`requires_ephemeris`.

### Independent offline validators

All three returned `status: accepted` without a network:

```text
pack manifest:
cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c

crossing certificate:
eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e

event golden:
8111d662df77b1a8b3f53258fef02a1fcf5f3c21a980e3a48df9a7c5d5838518
```

The certificate validator independently derived a
`8799.984190715346` magnitude/day ceiling below the admitted
`16384.0` ceiling.

The independent event validator reproduced:

| Target | Engine/oracle difference | Guard maximum margin |
|---|---:|---:|
| Jupiter | 1.2063503265 seconds | -0.0954001603 magnitude |
| Sirius | 2.5644600391 seconds | -0.3868969047 magnitude |

Both are within the declared 60-second oracle tolerance, and both guard days
remain non-qualifying.

### Static checkpoint gates

```text
Python compilation: passed
Ruff F and E9 rules on the scoped Python paths: passed
git diff --check: passed
LF attributes for all byte-bound Phase 3 tools and receipts: verified
```

The scoped lint gate removed one unused local assignment from the new event
solver. It had no behavioral role.

The broader compatibility gate exposed one stale pre-Phase-3 expectation in
`tests/unit/test_visibility_spectral.py`: Sirius was still listed with Moon
and Uranus as a target rejected before pack loading. Sirius is now an admitted
version 1.2 single-epoch target, so only that obsolete parameter row was
removed. Moon and Uranus still prove rejection without pack loading, and the
complete compatibility gate then passed.

The source-laboratory README now documents:

- the exact version 1.0, 1.1, and 1.2 pack lineage;
- the Phase 2 and Phase 3 offline build/validation commands;
- the Sirius BSC5/CALSPEC/CIE source boundary;
- the crossing-certificate and independent event-golden validators; and
- the remaining scientific and public-contract limits.

## External Read-Only Evidence

Exact pack:

```text
\\wsl.localhost\Ubuntu\home\nilad\.cache\moira\
visibility-reference-lab\data-packs\
moira-physical-heliacal-visibility-1.2.0-v3
```

Source inputs:

```text
\\wsl.localhost\Ubuntu\home\nilad\.cache\moira\
visibility-reference-lab\source
```

Ephemeris:

```text
C:\Users\nilad\.moira\kernels\de441.bsp
```

These are external read-only validation resources. They are not repository
payloads and must not be staged.

## Phase 3-Owned Working Paths

Review and stage only these Phase 3 or earlier physical-visibility paths:

```text
.gitattributes
moira/_visibility_event_solver.py
moira/_visibility_lut.py
moira/_visibility_spectral.py
moira/_visibility_stellar_targets.py
moira/heliacal.py
moira/data/physical_heliacal_visibility_data_pack_compatibility_v1_2.json
scripts/build_visibility_phase3_data_pack.py
scripts/validate_visibility_phase3_data_pack.py
scripts/validate_visibility_phase3_event_certificate.py
scripts/validate_visibility_phase3_event_goldens.py
scripts/visibility_reference_lab/README.md
scripts/visibility_reference_lab/phase3_event_crossing_certificate.json
scripts/visibility_reference_lab/phase3_stellar_target_profile_pack_spec.json
scripts/visibility_reference_lab/physical_heliacal_visibility_data_pack_compatibility_v1_2.json
tests/golden/physical_visibility_phase3_events.json
tests/integration/test_physical_visibility_phase3_goldens.py
tests/unit/test_physical_visibility_event.py
tests/unit/test_visibility_event_solver.py
tests/unit/test_visibility_phase3_governance.py
tests/unit/test_visibility_spectral.py
tests/unit/test_visibility_stellar_targets.py
wiki/01_doctrines/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_ADMISSION_DOCTRINE.md
wiki/05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CHECKPOINT_2026-07-30.md
wiki/05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md
wiki/05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_RESTART_CHECKPOINT_2026-07-30.md
wiki/06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md
```

Some listed tracked files also carry Phase 1 or Phase 2 physical-visibility
work from this same roadmap. Inspect their complete diff before staging.

## Protected Unrelated Work

The checkout contains concurrent validation-assurance work. Do not edit or
stage any of the following as part of Phase 3:

```text
conftest.py
pyproject.toml
docs/superpowers/plans/2026-07-29-moira-validation-assurance-implementation-plan.md
scripts/replay_test_receipt.py
tests/conftest.py
tests/_pytest_plugins/**
tests/harness_meta/**
tests/scratch/**
tests/stress/**
tests/tools/**
tests/support/small_body_resource_policy.py
wiki/03_validation/RESOURCE_BINDING_LEDGER_2026-05-04.md
moira.wiki
```

Other modified tests outside the Phase 3-owned list above also belong to the
concurrent validation-assurance work and must remain unstaged.

## Continuation Completed on 2026-07-31

1. `HEAD`, `origin/main`, the empty index, and dirty-tree ownership boundary
   were reconfirmed.
2. The stale source-laboratory README was updated.
3. Compilation, scoped Ruff, document consistency, diff, focused unit,
   independent validator, exact-pack engine replay, and broad compatibility
   gates passed.
4. The single stale Sirius non-admission test row was removed and the broad
   gate was rerun from the beginning.
5. The owned diff was reviewed without staging any path.

No engine correctness or documentation blocker remains in Phase 3. The only
remaining action is a deliberately scoped commit and push after explicit user
authorization. Phase 4 remains inactive.

## Exact Runtime Replay

From repository root in PowerShell:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_KERNEL_PATH = 'C:\Users\nilad\.moira\kernels\de441.bsp'
$env:MOIRA_PHASE3_VISIBILITY_PACK = '\\wsl.localhost\Ubuntu\home\nilad\.cache\moira\visibility-reference-lab\data-packs\moira-physical-heliacal-visibility-1.2.0-v3'

.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_visibility_phase3_governance.py `
  tests/unit/test_visibility_stellar_targets.py `
  tests/unit/test_visibility_event_solver.py `
  tests/unit/test_physical_visibility_event.py `
  -q

.\.venv\Scripts\python.exe -m pytest `
  tests/integration/test_physical_visibility_phase3_goldens.py `
  -q
```

Expected result at this checkpoint:

```text
51 passed
2 passed
```
