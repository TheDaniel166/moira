# Follow-up: release gates run twice on the same commit

**Status:** follow-up task, not scheduled. Raised during the 6.14.1 release.
**Date:** 2026-11-15
**Scope:** `.github/workflows/release-candidate.yml`,
`.github/workflows/pypi-publish.yml`
**Do not start this while a release is in flight.**

## The observation

A release runs the hardening and acceptance gates twice, against byte-identical
source. Both parent workflows call the same reusable files:

```yaml
# release-candidate.yml          and   pypi-publish.yml
release-hardening:
  uses: ./.github/workflows/release-hardening.yml
release-acceptance:
  uses: ./.github/workflows/release-acceptance.yml
```

Measured on 6.14.1, both runs on the same commit:

| run | workflow | trigger ref | head sha |
|---|---|---|---|
| 43729943486 | `release-candidate.yml` | `release-candidate` | `78d3ab152d13` |
| 43731383085 | `pypi-publish.yml` | `v6.14.1` | `78d3ab152d13` |

Cost of the duplicated pair on the candidate side:

```
Release Hardening Gate          563 s
Release Acceptance Matrix Gate  138 s
                                701 s  = 11 min 41 s
```

That is paid again during publication, delaying the upload by roughly the same
amount after the commit has already been proven green.

Only `validate-release` legitimately differs between the two, and it must:
the candidate runs `check_release_identity.py --candidate`, the tag run uses
`--tag "$GITHUB_REF_NAME"`. Those are different assertions. Leave them alone.

## Why the duplication exists

This is deliberate, and any change must preserve the reason.

`pypi-publish.yml` triggers on `push: tags: 'v*'` — **any** `v*` tag, including
one pushed by hand that never passed through `scripts/release.py` and therefore
never had a candidate run. Its gates are the only thing standing between such a
tag and a PyPI upload, which is irreversible. `AGENTS.md` states the rule:
tag-triggered PyPI publication requires both gates before building
distributions.

`release-candidate.yml` exists for the complementary reason, recorded in its own
header: "so a tag can never be the first place a gate fails." That is not
theoretical. 6.14.0 was tagged and its publication failed during wheel building,
leaving a dead tag that is still on origin. The candidate flow is what keeps
that from being the normal outcome.

So the two runs serve different purposes even though they execute the same
checks. The waste is real, but it is the price of a tag-triggered publisher that
has to be safe when invoked on its own.

## Proposed change

Make `pypi-publish.yml` skip the two gates **only** when it can prove this exact
commit already passed them, and run them otherwise.

Sketch: a small job before `release-hardening` that queries the Actions API for a
`release-candidate.yml` run with `head_sha == github.sha` and
`conclusion == success`, and emits a boolean. The two gate jobs gain an `if:`
on that boolean being false. `build-wheels` and `build-sdist` keep their existing
`needs:` on both gate jobs, since a skipped job satisfies `needs` while a failed
one does not.

The default must be to run. Any uncertainty — API error, rate limit, no matching
run, ambiguous result — resolves to running the gates, never to skipping them.

## Acceptance criteria

- A tag pushed by `scripts/release.py` after a green candidate run on the same
  commit skips both gates and publishes, with the skip visible in the run graph
  rather than silent.
- A tag pushed by hand at a commit with no candidate run runs both gates in
  full.
- A tag at a commit whose candidate run failed, was cancelled, or is still in
  progress runs both gates in full.
- An API failure in the proving job runs both gates in full.
- The saving is demonstrated on a real release: publication reaches
  `build-wheels` roughly twelve minutes sooner.

## What must not regress

- A hand-pushed tag must never reach `Publish to PyPI` without both gates
  having passed somewhere on that exact commit.
- The candidate flow stays. Removing it to avoid the duplication would return
  us to tags being the first place a gate can fail, which is how 6.14.0 died.
- `validate-release` keeps running in both workflows with its own arguments.

## Risks

The main one is that gate-skipping logic becomes security-relevant code. A bug
that returns "already proven" too readily silently removes the last check before
an irreversible upload. It deserves the same scrutiny as the gates themselves,
and it should fail closed in every branch.

A smaller one: the proving job reads the Actions API, so publication acquires a
dependency on that API being reachable. Failing closed turns an outage into a
slow release rather than an unsafe one, which is the correct trade.

## Alternatives considered

- **Remove the gates from `pypi-publish.yml`.** Rejected: hand-pushed tags would
  publish ungated.
- **Remove `release-candidate.yml`.** Rejected: reintroduces dead tags.
- **Make the hardening gate faster instead.** Worth doing on its own merits and
  independent of this, but it does not address paying twice.
- **Accept the duplication.** Entirely defensible. Twelve minutes per release is
  a modest price for a publisher that is safe standalone, and this task should
  only be taken up if release latency becomes a real irritation.
