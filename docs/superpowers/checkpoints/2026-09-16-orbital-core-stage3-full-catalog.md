# Orbital Core Stage 3 Full-Catalog Checkpoint

**Date:** 2026-09-16  
**Repository:** `C:\dev\moira`  
**Branch:** `orbital-core-stage1`  
**Committed base:** `dfad306f47901596e9edc254116ac3c6d47a3764`  
**State:** Uncommitted Stage 1, Stage 2, and Stage 3 worktree. Do not discard or
rewrite unrelated changes.

## Correction established

The sovereign asteroid release is present at:

`C:\dev\moira-asteroid-releases\moira-asteroids-2026.08.12.1`

Its manifest identifies `moira-asteroids@2026.08.12.1`, 10,025 bodies, and 401
shards. The directory contains all 401 BSP files.

Default discovery missed it because
`C:\Users\nilad\.moira\kernels\asteroids` is a stale junction to the absent
`C:\dev\moira-asteroid-releases\moira-asteroids-2026.07.27.1`. An attempted
automatic junction replacement was blocked by the command safety policy; the
junction was not changed. Use the supported `MOIRA_KERNELS_DIR` override below.

## Completed evidence

With `MOIRA_KERNELS_DIR=C:\dev\moira-asteroid-releases`, discovery resolves:

- `moira-asteroids@2026.08.12.1` — 10,025 bodies, 401 shards
- `moira-comets@2026.07.28.1` — 497 bodies, 20 shards
- packaged `moira-asteroids-wheel@2026.08.14.1` — 25 bodies, 1 shard

The Stage 3 inventory-wide geometric-node gate passed both sovereign releases:

```text
2 passed in 647.60s (0:10:47)
asteroids: 571.493s call plus 47.12s setup
comets:     26.583s call
harness: 3 manifests, 422 shards, 10,522 sovereign bodies
```

Every one of the 10,025 asteroid bodies and 497 comet bodies passed the finite
node, strict-core field mapping, modern true-date frame, canonical identity,
and catalog source-receipt assertions.

The full catalog revealed one test-only assumption in
`tests/integration/test_geometric_nodes_kernels.py`: the runtime receipt check
accepted `moira-asteroids-wheel` and `moira-comets`, but not the sovereign
`moira-asteroids` catalog. The accepted identity set now includes
`moira-asteroids`.

After that correction, the representative kernel slice is green:

```text
18 passed, 6 skipped
```

The six skips are intentional authority-admission gates. None of the installed
catalog manifests contains a reviewed Stage 3 admission bound to the exact
frozen fixture hash and tolerances. They are not missing-body skips.

## Resume command

From PowerShell in `C:\dev\moira`, run the complete 42-case Stage 3 focused
slice (allow about 12 minutes because it repeats the exhaustive catalog gate):

```powershell
$env:MOIRA_KERNELS_DIR = 'C:\dev\moira-asteroid-releases'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
$env:MOIRA_NO_DOWNLOAD = '1'
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_planetary_nodes_orbital_core.py `
  tests\server\test_server_nodes_routes.py `
  tests\integration\test_geometric_nodes_kernels.py `
  tests\integration\test_geometric_nodes_full_catalog.py `
  -q -ra --durations=10
```

Expected result with the current release manifests:

```text
42 collected; 36 passed; 6 skipped
```

For a fast preflight that does not repeat the 10,522-body sweep, omit
`tests\integration\test_geometric_nodes_full_catalog.py`; expected result is
40 collected, 34 passed, and the same 6 authority-admission skips.

## Resumed slice completed

The complete focused Stage 3 slice passed with the expected result:

```text
42 collected; 36 passed; 6 skipped
```

The six skips are only the reviewed Stage 3 catalog-authority admissions. The
full release inventory again passed for all 10,522 sovereign bodies.

The selected Stage 1/2/3 orbital regression then ran against the same release
configuration and wrote
`tmp/orbital-core-stage3-regression-full-catalog.xml`:

```text
452 collected; 440 passed; 12 skipped; 0 failed; 0 errors
2349.973 seconds
```

The twelve skips are exactly six Stage 2 apsidal-passage catalog admissions
and six Stage 3 geometric-node catalog admissions. The exhaustive element
inventory took 1524.820 seconds; the asteroid and comet node cases took
605.363 and 33.266 seconds respectively.

The Stage 3 receipt now records the sovereign asteroid identity, manifest hash,
10,522 passed bodies, two passed sovereign releases, and the measured focused
and regression counts. Its governance test enforces that evidence without
weakening either catalog-authority boundary. Canonical validation text now
distinguishes the passed full-release runtime inventory from the still-pending
catalog Horizons admissions and live-primary drift audit.

Receipt governance passed 3/3 tests. Scoped Ruff and Python compilation passed
for the Stage 3 adapter, transport, and affected catalog tests. Canonical wiki
generation, Git-wiki synchronization, website publication-manifest checking,
documentation consistency, the Stage 1 consumer-inventory audit, stale-claim
scanning, and `git diff --check` all passed.

## Boundary

No commit, version change, tag, package publication, push, or deployment has
been performed. Full runtime coverage does not itself authorize numeric
authority parity or release readiness. The mandatory live Horizons audit and
reviewed Stage 2/3 catalog-manifest admissions remain explicit release blockers.

## Resume prompt

`Resume Orbital Core Stage 3 from docs/superpowers/checkpoints/2026-09-16-orbital-core-stage3-full-catalog.md. The full-catalog and combined regression gates are complete; rerun only the lightweight closure gates unless implementation changes invalidate the measured evidence.`
