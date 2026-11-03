# Website publication generation and release evidence

The website publication manifest is generated metadata, not an independently
approved astronomical baseline. Its source allowlist, catalog identity receipts,
export declarations, release summaries and document hashes still fail closed.
Generating it must never refresh scientific fixtures or relax their thresholds.

## Independent documentation export

Website documentation export is separate from engine hardening, distribution
builds and PyPI publication. The engine release workflow does not generate or
test these exports, check website documentation configuration, or run the
consumer-usage audit. A missing website release summary cannot block the
engine package. No website-publication workflow is installed in this repo.

When documentation publication is requested separately, the commands below
generate and check an artifact against its selected source.

The additive `publication` field identifies `kind: candidate`, the source
commit/tree, and whether tracked source is dirty. `engine_release.commit`
continues to mean the declared version's tag commit, not the candidate's source
commit. It is null when that version has not been tagged. A candidate is not
evidence that its new features have been published to PyPI or deployed.

    .\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --candidate --output build\website-publication\publication.json
    .\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --candidate --output build\website-publication\publication.json --check

## Optional exact-tag documentation evidence

Use `--release-tag` to generate an exact-tag artifact instead of a candidate.
Documentation generation requires the tag to match the package version, HEAD to
equal the tag's commit, and tracked source to be clean. No tag is created,
moved or substituted by the generator. This documentation check is independent
of PyPI publication.

The release artifact's `publication.kind` is `release`; its source commit is
the same as `engine_release.commit`. Artifact retention follows the repository's
Actions policy; this is retained build evidence, not a new public download or
website deployment. For durable publication, retain the manifest alongside its
immutable source revision through the separately authorized publication train.

    .\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --release-tag vX.Y.Z --output build\website-publication\publication.json

## Committed website-ingest snapshot

The existing `website_docs/publication.json` and its schema remain compatible
with the website ingest tool. This is an explicit publication checkpoint, not
an every-commit CI snapshot. Before a website documentation ingest, regenerate
and commit it together with the intended source changes:

    .\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py
    .\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --check

The default `--check` remains a read-only exact-current-source snapshot check;
it still rejects stale or tampered snapshots. CI/release artifact modes require
an explicit output and cannot overwrite this committed snapshot. Website code,
deployment facts, engine versions, kernel files and Vedic calculation code are
not modified by candidate or release generation.
