# Small-body Type 13 apsidal rebuild checkpoint

**Date:** 2026-09-28  
**Status:** PAUSED at the user's request; implementation is in progress and is not release-ready.

## Objective and current decision

The goal is to make asteroid and comet Type 13 kernels accurate at perihelion and aphelion without reconstructing every catalog object at an unnecessarily dense global cadence.

A uniform 3-day base grid with a 9-node Hermite window was rejected by live Horizons oracle tests. It still missed the radial-distance gate for representative fast/high-eccentricity asteroids, including Moshup, Phaethon, Icarus, and Talos. The implementation now keeps the existing 10-day/7-node base grid and adds locally dense, exact Horizons samples around detected apsides. Each affected body is independently certified, halving the local cadence from 1 day down to a configured minimum when necessary.

Shared policy identifier: `moira-small-body-type13-apsidal-adaptive-v3`.

## Confirmed scientific result

A fresh, coherent full-span validation for Phaethon over 1600–2500 completed successfully:

- 1-day local sampling failed: worst radial witness error 3.1913903281092644 km.
- 12-hour local sampling passed all 1,255 detected extrema.
- Worst independent radial witness error: 0.0008365251123905182 km (about 0.837 m).
- Worst extremum-time error: 0.0001609325408935547 seconds.
- Worst extremum-distance error: 0.00047446414828300476 km (about 0.474 m).
- Final node count: 76,797 total; 32,872 base nodes and 43,925 adaptive nodes.

This validates the algorithm on the hardest known asteroid case tested so far. It does not yet validate the remaining catalog.

## Implementation present in the worktree

Added:

- `scripts/type13_adaptive_sampling.py` — shared detection, local sampling, independent witnesses, and adaptive certification.
- `scripts/horizons_response_cache.py` — atomic gzip JSON response cache bound to request identity and response SHA-256.
- `moira/data/asteroid_type13_adaptive_bodies.json` — the 59-body canonical adaptive roster, bound to the exhaustive audit receipt.
- Unit coverage for the adaptive policy, cache, asteroid audit, and comet integration.

Modified:

- `scripts/build_unified_asteroid_catalog.py` — uses an unambiguous `240h` base cadence, exact `TLIST` queries, the adaptive roster, receipts, and response caching.
- `scripts/build_comet_catalog.py` — uses the same shared adaptive certifier and unambiguous hourly cadence.
- Existing validation, manifest-governance, provenance, integration-test, and canonical wiki files remain modified from this work stream and earlier work.

No catalog kernels or release manifests have been admitted, published, committed, pushed, or released by this checkpoint.

## Validation completed

- Python: 3.14.3.
- `tests/KNOWN_ISSUES.yml`: empty.
- Ruff and `py_compile` passed for the directly changed implementation during development.
- Before the final coherent-request adjustment, the scoped builder suite passed: 25 tests.
- After the final coherent-request and chunking adjustment, the directly affected suite passed: 13 tests, with Ruff also passing.

The complete 25-test slice, integration suite, full test suite, and documentation consistency gates have not been rerun after the final adjustment.

## Oracle and catalog state

The exhaustive asteroid audit already partitions all 11,223 asteroid bodies:

- 126 direct-risk bodies with perihelion distance below 1.3 AU were checked against the existing 10-day/7-node kernel policy.
- 59 bodies failed the radial gate and span 40 asteroid shards.
- The other 11,097 bodies were analytically bounded; the worst estimated radial error was about 0.000173 km.

Still pending:

- Full adaptive validation of the remaining 58 asteroid roster bodies.
- Full adaptive validation of all 497 comets.
- Rebuild and admission of the 40 affected asteroid shards.
- Rebuild and admission of all 20 comet shards.
- Final manifest assembly that preserves the 409 unchanged asteroid shards.

## Horizons response caches

- `C:\dev\moira-candidate-cache\apsidal-v3-coherent` contains the coherent Phaethon validation responses and may be reused with the current policy.
- `C:\dev\moira-candidate-cache\apsidal-v3` contains exploratory responses produced before request coherence was fixed. Do **not** use it as scientific evidence or as input to an admitted build.

No Horizons requests or catalog-build processes were active when this checkpoint was written.

## Known implementation work before a catalog-wide run

1. Compact success certificates and failure messages. The current per-event records are scientifically useful but can make metadata and exceptions very large.
2. Add explicit roster-integrity and asteroid adaptive-invocation tests.
3. Align comet Horizons retry behavior with the asteroid builder before running all 497 comets.
4. Rerun the full scoped unit slice after the final request-coherence change.
5. Run the 59-body asteroid and 497-body comet oracle campaigns into a fresh canonical candidate directory.
6. Review the minimum 1/16-day refinement limit; builders must reject any body that cannot certify within it.
7. Rebuild candidate shards, assemble manifests without dropping unchanged asteroid shards, and run integration/full validation.
8. Update provenance and canonical wiki text only after the final policy and exhaustive receipts are stable.
9. Commit, push, and release only under a separate explicit instruction.

## Safe restart sequence

1. Re-read this checkpoint and inspect `git status --short`; preserve unrelated work.
2. Do not use `C:\dev\moira-candidate-cache\apsidal-v3`.
3. Finish certificate/log compaction and the missing focused unit tests.
4. Run Ruff and the complete scoped 25-test slice.
5. Run the remaining asteroid and comet validations into a fresh candidate directory, retaining all request and validation receipts.
6. Stop on any uncertified body rather than admitting a degraded shard.
7. Only after exhaustive validation, build candidate shards and proceed through manifest, provenance, integration, and release gates.

## Worktree publication state

- Commit: not created for this work.
- Push: not performed.
- Release: not performed.
- Scientific status: Phaethon proven; exhaustive catalog proof still incomplete.

## Continuation — 2026-09-29

The sections above preserve the state as it was known when the checkpoint was
first written. The active implementation has since advanced to policy
`moira-small-body-type13-apsidal-adaptive-v4`.

### Why v4 replaced v3

The first exhaustive v3 asteroid campaign exposed a trajectory-coherence flaw,
not an interpolation failure. Local Horizons `TLIST` integrations for chaotic
long-span objects could diverge from the full-span base integration even when
Horizons reported the same solution identifier. Hathor was the decisive case:
unanchored local integrations disagreed with the base trajectory by roughly
252 million km, while a control request containing the exact 1600 and 2500
coverage endpoints matched the base trajectory at the test epoch exactly.

Policy v4 therefore reserves two positions in every exact `TLIST` request for
the base coverage endpoints, removes those anchor rows before building the
local node series, and records the coherence rule in each certificate. The v3
candidate and exploratory caches are quarantined diagnostic evidence and must
not be admitted.

### Completed asteroid campaign

Canonical candidate:
`C:\dev\moira-candidate-small-bodies-v4\asteroids`

- 11,223 bodies built; zero failures.
- 449 of 449 shards completed.
- All 449 BSP SHA-256 receipts and all 449 metadata SHA-256 receipts verified.
- All 11,223 metadata records verified against policy v4.
- All 59 adaptive asteroid certificates passed.
- All 11,164 base-series retention certificates passed.
- Phaethon is the only asteroid that rejected the one-day level; it passed at
  the half-day level. Rejected coarser attempts remain in the certificate as
  evidence.

### Active comet campaign

Canonical candidate:
`C:\dev\moira-candidate-small-bodies-v4\comets`

The 497-comet rebuild is running as a hidden, shard-resumable process. At this
checkpoint, shards 000 and 001 are sealed (50 comets, zero failures) and shard
002 is in progress. Schwassmann-Wachmann 2 rejected its one-day level and
passed at the half-day level; all other sealed comet records accepted one day.

Operational state at the time of writing:

- Process ID: `2932` (ephemeral; verify before relying on it).
- Standard output:
  `C:\dev\moira-candidate-small-bodies-v4\comet-build-resume.stdout.log`
- Standard error:
  `C:\dev\moira-candidate-small-bodies-v4\comet-build-resume.stderr.log`
- Standard error was empty at the last health check.

If the process is no longer running, rerun the same builder command below. It
will verify and skip every sealed shard before resuming the first incomplete
one:

```powershell
.\.venv\Scripts\python.exe scripts\build_comet_catalog.py `
  C:\Users\nilad\.moira\kernels\comets\comet_master.json `
  0 497 `
  C:\dev\moira-candidate-small-bodies-v4\comets
```

### Updated validation and publication state

- Focused Ruff validation passed.
- The scoped builder and policy suite passed: 34 tests.
- Asteroid candidate validation passed as described above.
- Comet completion, final comet manifest validation, integration tests,
  documentation consistency, and final provenance/wiki updates remain pending.
- No commit, push, admission, installation, or release has been performed.
