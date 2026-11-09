"""The release command decides its next step from repository state alone."""

from __future__ import annotations

import pytest

from scripts import release
from scripts.check_lightbox_release_gate import EVIDENCE_PATHS


def test_release_kind_accepts_only_the_next_version():
    assert release.release_kind("6.13.1", "6.13.2") == "patch"
    assert release.release_kind("6.13.1", "6.14.0") == "minor"
    assert release.release_kind("6.13.1", "7.0.0") == "major"
    for target in ("6.13.1", "6.13.3", "6.14.1", "6.12.0", "8.0.0"):
        with pytest.raises(release.ReleaseError):
            release.release_kind("6.13.1", target)
    with pytest.raises(release.ReleaseError):
        release.parse_version("6.14.0rc1")


def test_every_registered_version_statement_exists_exactly_once_in_the_repository():
    current = release.check_release_identity._project_version()
    for path, _, _ in release.VERSION_EDITS:
        text, _ = release.read_text(path)
        bumped = release.bump_text(path, text, current, "99.0.0", "major")
        assert bumped != text and "99.0.0" in bumped
        with pytest.raises(release.ReleaseError):
            release.bump_text(path, bumped, current, "99.0.1", "patch")


def test_bump_rewrites_the_release_kind_word_and_rejects_unknown_files():
    text = "This README documents the `6.13.1` patch-release baseline.\n"
    assert release.bump_text("README.md", text, "6.13.1", "6.14.0", "minor") == (
        "This README documents the `6.14.0` minor-release baseline.\n"
    )
    with pytest.raises(release.ReleaseError):
        release.bump_text("README.md", text + text, "6.13.1", "6.14.0", "minor")
    with pytest.raises(release.ReleaseError):
        release.bump_text("setup.cfg", text, "6.13.1", "6.14.0", "minor")


def test_phase_follows_the_two_release_commits_and_the_tag():
    phase = release.release_phase
    attested = "Attest exact-source 6.14.0 release verification"
    assert phase("6.14.0", "6.13.1", "Fix a typo", tagged=False) == "prepare"
    assert phase("6.14.0", "6.14.0", "Prepare minor release 6.14.0", tagged=False) == "attest"
    assert phase("6.14.0", "6.14.0", attested, tagged=False) == "candidate"
    assert phase("6.14.0", "6.14.0", attested, tagged=True) == "publish"
    with pytest.raises(release.ReleaseError, match="--reattest"):
        phase("6.14.0", "6.14.0", "Fix the candidate failure", tagged=False)
    assert phase("6.14.0", "6.14.0", "Fix the candidate failure", tagged=False, reattest=True) == "attest"
    assert phase("6.14.0", "6.14.0", attested, tagged=False, reattest=True) == "attest"


def _row(surface, contract="a", scope=True):
    return {"surface_id": surface, "api_contract_sha256": contract, "in_lightbox_calculation_scope": scope}


def test_surface_diff_reports_added_removed_changed_and_reclassified_surfaces():
    old = {"python_exports": [_row("keep"), _row("gone"), _row("edit"), _row("move")], "rest_operations": []}
    new = {
        "python_exports": [
            _row("keep"), _row("edit", "b"), _row("move", scope=False), _row("calc"), _row("plain", scope=False),
        ],
        "rest_operations": [_row("GET /v1/new")],
    }
    diff = release.surface_diff(old, new)
    assert diff["python_exports"] == {
        "added": ["calc", "plain"], "removed": ["gone"], "changed": ["edit"],
        "rescoped": ["move"], "calculation_added": ["calc"],
    }
    assert diff["rest_operations"]["added"] == ["GET /v1/new"]
    text = release.describe_surface_diff(diff, limit=1)
    assert "Python exports: 2 added (1 in calculation scope), 1 removed, 1 contracts changed, 1 reclassified" in text
    assert "... and 1 more" in text


def test_binding_changes_identity_only_and_leaves_reviewed_content_alone():
    baseline = {
        "baseline_date": "2026-11-09", "source_parent_revision": "old", "engine_version": "6.13.1",
        "inventory_fingerprint_sha256": "f1", "canonical_entries": 1341, "review": {"surface_change": "prose"},
    }
    bound = release.bind_baseline(baseline, version="6.14.0", fingerprint="f2", parent="new", today="2026-12-01")
    assert bound == {
        **baseline, "baseline_date": "2026-12-01", "source_parent_revision": "new",
        "engine_version": "6.14.0", "inventory_fingerprint_sha256": "f2",
    }
    assert baseline["engine_version"] == "6.13.1" and list(bound) == list(baseline)
    snapshot = {
        "audit_date": "2026-10-31", "engine_version": "6.13.1", "inventory_fingerprint_sha256": "f1",
        "limitations": ["note"], "entries": [{"surface_id": "x"}],
    }
    rebound = release.bind_snapshot(snapshot, version="6.14.0", fingerprint="f2")
    assert rebound == {**snapshot, "engine_version": "6.14.0", "inventory_fingerprint_sha256": "f2"}


def test_baseline_review_must_be_rewritten_by_a_person_before_the_prepare_commit():
    head_baseline = {
        "baseline_date": "2026-11-09",
        "review": {"from_baseline_date": "2026-10-31", "surface_change": "old"},
    }
    head_snapshot = {"limitations": ["old note"]}
    stale = release.review_problems(head_baseline, dict(head_baseline), head_snapshot, dict(head_snapshot), "6.14.0")
    assert len(stale) == 2 and "review block" in stale[0] and "limitations note" in stale[1]
    wrong_date = {"review": {"from_baseline_date": "2026-10-31", "surface_change": "new"}}
    noted = {"limitations": ["old note", "December 1, 2026 minor release 6.14.0: reviewed rebind."]}
    assert "2026-11-09" in release.review_problems(head_baseline, wrong_date, head_snapshot, noted, "6.14.0")[0]
    reviewed = {"review": {"from_baseline_date": "2026-11-09", "surface_change": "new"}}
    assert release.review_problems(head_baseline, reviewed, head_snapshot, noted, "6.14.0") == []


def test_prepare_commit_refuses_paths_outside_the_release_set():
    allowed = [
        "pyproject.toml", "CHANGELOG.md", "moira/facade.py", "moira.wiki",
        "wiki/03_release/RELEASE_NOTES_6.14.0.md", "website_docs/publication_sources.json",
    ]
    assert release.unexpected_prepare_paths(allowed) == []
    receipts = [path for path in EVIDENCE_PATHS if not path.startswith("wiki/")]
    assert receipts
    assert release.unexpected_prepare_paths([*allowed, "moira/houses.py", "tests/unit/test_x.py", *EVIDENCE_PATHS]) == sorted(
        ["moira/houses.py", "tests/unit/test_x.py", *receipts]
    )


def test_repository_slug_reads_https_and_ssh_remotes():
    assert release.repository_slug("https://github.com/TheDaniel166/moira") == "TheDaniel166/moira"
    assert release.repository_slug("https://github.com/TheDaniel166/moira.git\n") == "TheDaniel166/moira"
    assert release.repository_slug("git@github.com:TheDaniel166/moira.git") == "TheDaniel166/moira"
    with pytest.raises(release.ReleaseError):
        release.repository_slug("https://example.org/moira.git")


def test_workflow_verdict_uses_the_latest_run_of_the_named_workflow_for_the_commit():
    workflow = release.CANDIDATE_WORKFLOW

    def run(number, status, conclusion=None, path=workflow, sha="abc"):
        return {
            "run_number": number, "run_attempt": 1, "status": status, "conclusion": conclusion,
            "path": path, "head_sha": sha,
        }

    verdict = release.workflow_verdict
    assert verdict({"workflow_runs": []}, workflow, "abc") == ("pending", None)
    unrelated = {"workflow_runs": [
        run(9, "completed", "success", path=release.PUBLISH_WORKFLOW), run(8, "completed", "success", sha="zzz"),
    ]}
    assert verdict(unrelated, workflow, "abc")[0] == "pending"
    assert verdict({"workflow_runs": [run(1, "completed", "failure"), run(2, "in_progress")]}, workflow, "abc")[0] == "pending"
    assert verdict({"workflow_runs": [run(1, "completed", "failure"), run(2, "completed", "success")]}, workflow, "abc")[0] == "success"
    assert verdict({"workflow_runs": [run(3, "completed", "cancelled")]}, workflow, "abc")[0] == "failure"


def test_release_workflow_paths_name_real_workflows():
    for path in (release.CANDIDATE_WORKFLOW, release.PUBLISH_WORKFLOW):
        assert (release.ROOT / path).is_file()
