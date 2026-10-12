"""Publication provenance, fail-closed generation and portable receipts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from scripts import build_website_docs_bundle as bundle
from scripts.build_website_docs_bundle import (
    _canonical_text_bytes,
    _sha256_path,
)


def test_publication_receipts_normalize_checkout_line_endings(tmp_path) -> None:
    lf_path = tmp_path / "lf.md"
    crlf_path = tmp_path / "crlf.md"
    lf_path.write_bytes(b"# Receipt\n\nPortable text.\n")
    crlf_path.write_bytes(b"# Receipt\r\n\r\nPortable text.\r\n")

    expected = b"# Receipt\n\nPortable text.\n"
    assert _canonical_text_bytes(lf_path) == expected
    assert _canonical_text_bytes(crlf_path) == expected
    assert len(_canonical_text_bytes(lf_path)) == len(_canonical_text_bytes(crlf_path))
    assert _sha256_path(lf_path) == _sha256_path(crlf_path)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def publication_repo(tmp_path, monkeypatch):
    """A real, local Git history; no kernels, network, or scientific fixtures."""

    root = tmp_path / "engine"
    root.mkdir()
    files = {
        "pyproject.toml": (
            '[project]\nname = "moira-astro"\nversion = "1.2.3"\n'
            'requires-python = ">=3.10"\nlicense = "MIT"\n'
            'classifiers = ["Programming Language :: Python :: 3.14"]\n'
        ),
        "CHANGELOG.md": "## [Unreleased]\n\n## [1.2.3] - 2026-10-12\n\nRelease.\n",
        "wiki/02_standards/DOC.md": "# Public documentation\n",
        "wiki/03_release/NOTES.md": "# Release notes\n",
        "wiki/03_release/COMPATIBILITY.md": "# Compatibility notes\n",
        "website_docs/publication.json": '{"prior": "snapshot"}\n',
    }
    config = {
        "schema_version": 1,
        "last_verified": "2026-10-12",
        "release_history_floor": "1.2.2",
        "documents": [{
            "id": "public-doc", "kind": "doc", "route": "/docs/public",
            "output": "content/public.md", "source": "wiki/02_standards/DOC.md",
        }],
        "release_summaries": [{
            "version": "1.2.3", "date": "2026-10-12",
            "added": [], "changed": [], "fixed": [], "validation": [],
            "release_notes": "wiki/03_release/NOTES.md",
            "compatibility_notes": "wiki/03_release/COMPATIBILITY.md",
        }],
    }
    files["website_docs/publication_sources.json"] = json.dumps(config)
    modules = {}
    for name in ("root", "essentials", "classical", "predictive", "facade", "vedic"):
        module = ModuleType("moira" if name == "root" else f"moira.{name}")
        module.__all__ = ["ExistingFeature"]
        modules[name] = module
        source = "moira/__init__.py" if name == "root" else f"moira/{name}.py"
        files[source] = '__all__ = ["ExistingFeature"]\n'
    for name, module in modules.items():
        if name != "root":
            setattr(modules["root"], name, module)
    monkeypatch.setitem(sys.modules, "moira", modules["root"])
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(root, "init", "--initial-branch=main")
    _git(root, "config", "user.name", "Publication test")
    _git(root, "config", "user.email", "publication@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "Synthetic release")
    _git(root, "tag", "v1.2.3")
    monkeypatch.setattr(bundle, "REPO_ROOT", root)
    monkeypatch.setattr(bundle, "CONFIG_PATH", root / "website_docs/publication_sources.json")
    monkeypatch.setattr(bundle, "OUTPUT_PATH", root / "website_docs/publication.json")
    monkeypatch.setattr(bundle, "CHANGELOG_PATH", root / "CHANGELOG.md")
    monkeypatch.setattr(bundle, "_contract_sources", lambda: [])
    monkeypatch.setattr(bundle, "_catalog_metrics", lambda: {})
    monkeypatch.setattr(bundle, "_capability_metrics", lambda: {})
    return root, modules


def _advance_source(root: Path) -> None:
    (root / "wiki/02_standards/DOC.md").write_text("# New documentation\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "Add a feature after release")


def test_candidate_tracks_new_source_without_refreshing_prior_snapshot(publication_repo, tmp_path):
    root, modules = publication_repo
    release_commit = _git(root, "rev-parse", "HEAD")
    modules["root"].__all__.append("NewFeature")
    (root / "moira/__init__.py").write_text(
        '__all__ = ["ExistingFeature", "NewFeature"]\n', encoding="utf-8"
    )
    _advance_source(root)
    prior_snapshot = bundle.OUTPUT_PATH.read_bytes()
    output = tmp_path / "ci" / "publication.json"
    args = ["--candidate", "--output", str(output)]
    assert bundle.main(args) == 0
    generated = output.read_bytes()
    manifest = json.loads(generated)
    assert manifest["engine_release"]["commit"] == release_commit
    assert manifest["publication"] == {
        "kind": "candidate", "source_commit": _git(root, "rev-parse", "HEAD"),
        "source_tree": _git(root, "rev-parse", "HEAD^{tree}"), "worktree_dirty": False,
    }
    assert "NewFeature" in manifest["python_exports"]["root"]["symbols"]
    assert manifest["documents"][0]["source_sha256"] == _sha256_path(
        root / "wiki/02_standards/DOC.md"
    )
    recorded_hash = manifest.pop("manifest_sha256")
    assert recorded_hash == bundle._sha256_bytes(bundle._json_bytes(manifest, pretty=False))
    assert bundle.main([*args, "--check"]) == 0
    assert output.read_bytes() == generated
    assert bundle.OUTPUT_PATH.read_bytes() == prior_snapshot


def test_untagged_candidate_is_valid_but_not_a_release(publication_repo):
    root, _ = publication_repo
    _git(root, "tag", "-d", "v1.2.3")
    # An identically named branch must not impersonate a missing tag.
    _git(root, "branch", "v1.2.3")
    manifest = bundle.build_manifest(candidate=True)
    assert manifest["engine_release"]["commit"] is None
    assert manifest["publication"]["kind"] == "candidate"
    with pytest.raises(bundle.PublicationError, match="tag.*missing"):
        bundle.build_manifest(release_tag="v1.2.3")


def test_release_artifact_binds_the_exact_clean_tag(publication_repo, tmp_path):
    root, _ = publication_repo
    output = tmp_path / "release" / "publication.json"
    args = ["--release-tag", "v1.2.3", "--output", str(output)]
    assert bundle.main(args) == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["publication"]["kind"] == "release"
    assert manifest["publication"]["source_commit"] == manifest["engine_release"]["commit"]
    assert manifest["publication"]["source_commit"] == _git(root, "rev-parse", "HEAD")
    assert manifest["publication"]["worktree_dirty"] is False
    assert bundle.main([*args, "--check"]) == 0


def test_release_rejects_newer_head_at_an_old_version(publication_repo):
    root, _ = publication_repo
    _advance_source(root)
    with pytest.raises(bundle.PublicationError, match="exact release tag commit"):
        bundle.build_manifest(release_tag="v1.2.3")


def test_release_rejects_wrong_version_tag(publication_repo):
    with pytest.raises(bundle.PublicationError, match="does not match"):
        bundle.build_manifest(release_tag="v9.9.9")


def test_dirty_source_is_visible_in_candidate_and_forbidden_in_release(publication_repo):
    root, _ = publication_repo
    (root / "wiki/02_standards/DOC.md").write_text("# Local edit\n", encoding="utf-8")
    assert bundle.build_manifest(candidate=True)["publication"]["worktree_dirty"] is True
    with pytest.raises(bundle.PublicationError, match="clean tracked worktree"):
        bundle.build_manifest(release_tag="v1.2.3")


@pytest.mark.parametrize("mode", [["--candidate"], ["--release-tag", "v1.2.3"]])
def test_artifact_modes_require_separate_output(publication_repo, mode):
    with pytest.raises(SystemExit) as error:
        bundle.main(mode)
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        bundle.main([*mode, "--output", str(bundle.OUTPUT_PATH)])
    assert error.value.code == 2


def test_artifact_modes_are_mutually_exclusive(publication_repo, tmp_path):
    with pytest.raises(SystemExit) as error:
        bundle.main(["--candidate", "--release-tag", "v1.2.3", "--output", str(tmp_path / "out.json")])
    assert error.value.code == 2


def test_default_snapshot_check_still_fails_read_only_on_staleness(publication_repo, capsys):
    snapshot = bundle.OUTPUT_PATH.read_bytes()
    assert bundle.main(["--check"]) == 1
    assert "manifest is stale" in capsys.readouterr().err
    assert bundle.OUTPUT_PATH.read_bytes() == snapshot
    assert bundle.main([]) == 0
    generated = bundle.OUTPUT_PATH.read_bytes()
    assert "publication" not in json.loads(generated)
    assert bundle.main(["--check"]) == 0
    assert bundle.OUTPUT_PATH.read_bytes() == generated


def test_candidate_check_rejects_tampering_without_repairing_it(publication_repo, tmp_path):
    output = tmp_path / "candidate.json"
    args = ["--candidate", "--output", str(output)]
    assert bundle.main(args) == 0
    tampered = output.read_text(encoding="utf-8").replace('"ExistingFeature"', '"InventedFeature"')
    output.write_text(tampered, encoding="utf-8")
    assert bundle.main([*args, "--check"]) == 1
    assert output.read_text(encoding="utf-8") == tampered


@pytest.mark.parametrize("prefix", bundle.FORBIDDEN_PUBLIC_SOURCE_PREFIXES)
def test_candidate_still_rejects_private_documents(publication_repo, tmp_path, prefix, capsys):
    config = json.loads(bundle.CONFIG_PATH.read_text(encoding="utf-8"))
    config["documents"][0]["source"] = f"{prefix}private.md"
    bundle.CONFIG_PATH.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "candidate.json"
    assert bundle.main(["--candidate", "--output", str(output)]) == 1
    assert "private/internal source is not publishable" in capsys.readouterr().err
    assert not output.exists()


def test_candidate_still_rejects_release_summary_gaps(publication_repo, tmp_path, capsys):
    config = json.loads(bundle.CONFIG_PATH.read_text(encoding="utf-8"))
    config["release_summaries"] = []
    bundle.CONFIG_PATH.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "candidate.json"
    assert bundle.main(["--candidate", "--output", str(output)]) == 1
    assert "release summary gap" in capsys.readouterr().err
    assert not output.exists()


def test_candidate_still_rejects_duplicate_public_exports(publication_repo, tmp_path, capsys):
    _, modules = publication_repo
    modules["vedic"].__all__.append("ExistingFeature")
    output = tmp_path / "candidate.json"
    assert bundle.main(["--candidate", "--output", str(output)]) == 1
    assert "duplicate public exports" in capsys.readouterr().err
    assert not output.exists()


def test_candidate_still_rejects_missing_documents(publication_repo, tmp_path, capsys):
    root, _ = publication_repo
    (root / "wiki/02_standards/DOC.md").unlink()
    output = tmp_path / "candidate.json"
    assert bundle.main(["--candidate", "--output", str(output)]) == 1
    assert "missing publication source" in capsys.readouterr().err
    assert not output.exists()


def test_candidate_still_rejects_catalog_receipt_hash_mismatch(publication_repo, tmp_path, monkeypatch, capsys):
    root, _ = publication_repo
    (root / "catalog.json").write_text("{}\n", encoding="utf-8")
    (root / "identity.json").write_text(
        json.dumps({"source": {"release_manifest_sha256": "0" * 64}}), encoding="utf-8"
    )
    monkeypatch.setattr(bundle, "_catalog_metrics", lambda: bundle._position_catalog_metrics(
        manifest_source="catalog.json", identity_source="identity.json"
    ))
    output = tmp_path / "candidate.json"
    assert bundle.main(["--candidate", "--output", str(output)]) == 1
    assert "SHA-256 does not match" in capsys.readouterr().err
    assert not output.exists()


def test_ci_generates_candidates_and_requires_exact_tag_evidence_before_pypi():
    root = Path(__file__).resolve().parents[2]
    hardening = yaml.safe_load((root / ".github/workflows/release-hardening.yml").read_text(encoding="utf-8"))
    steps = hardening["jobs"]["release-hardening"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "build_website_docs_bundle.py --candidate --output" in commands
    assert "build_website_docs_bundle.py --check\n" not in commands
    assert "if git rev-parse" not in commands
    assert any(step.get("uses") == "actions/upload-artifact@v4" and
               step["with"]["if-no-files-found"] == "error" for step in steps)
    release = yaml.safe_load((root / ".github/workflows/pypi-publish.yml").read_text(encoding="utf-8"))
    assert "website-publication" in release["jobs"]["publish"]["needs"]
    publication = release["jobs"]["website-publication"]
    assert publication["needs"] == "validate-release"
    commands = "\n".join(step.get("run", "") for step in publication["steps"])
    assert 'build_website_docs_bundle.py --release-tag "$GITHUB_REF_NAME" --output' in commands
