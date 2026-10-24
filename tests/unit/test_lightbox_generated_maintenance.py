"""Release metadata remains enforced without imposing a routine PR workflow."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("maintenance_under_test", ROOT / "scripts/maintain_generated.py")
assert SPEC is not None and SPEC.loader is not None
MAINTENANCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MAINTENANCE
SPEC.loader.exec_module(MAINTENANCE)


def test_dependency_order_includes_every_existing_generated_gate():
    scripts = [stage.script for stage in MAINTENANCE.STAGES]
    assert scripts == [
        "sync_rest_api_reference.py", "generate_hellenistic_inventory.py",
        "generate_lightbox_calculation_inventory.py", "generate_lightbox_conformance_manifest.py",
        "generate_lightbox_family_register.py", "generate_lightbox_family_assessment.py",
        "generate_lightbox_assurance_matrix.py", "generate_lightbox_public_status.py",
        "check_lightbox_release_gate.py", "sync_git_wiki.py",
    ]


def test_check_plan_is_read_only_and_refresh_preserves_review_boundaries():
    for stage in MAINTENANCE.STAGES:
        if stage.script == "check_lightbox_release_gate.py":
            assert stage.check_arguments == stage.refresh_arguments == ()
        else:
            assert stage.check_arguments == ("--check",)
        assert "reclassify" not in " ".join(stage.refresh_arguments)
        assert "replay_lightbox_receipts.py" != stage.script
        assert "audit_lightbox_product_usage.py" != stage.script
    assert MAINTENANCE.STAGES[-1].refresh_arguments == ("--no-prune",)


def test_check_uses_current_interpreter_checkout_and_no_download_environment(monkeypatch):
    calls = []
    monkeypatch.setenv("MAINTENANCE_UNRELATED_SETTING", "preserve")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "0")
    monkeypatch.setenv("PYTHONPATH", "existing-import-root")

    def run(command, *, cwd, env, check):
        calls.append(command)
        assert command[0] == sys.executable
        assert cwd == MAINTENANCE.REPO_ROOT
        assert Path(command[1]).parent == cwd / "scripts"
        assert check is False
        assert env["MAINTENANCE_UNRELATED_SETTING"] == "preserve"
        for key in ("MOIRA_NO_DOWNLOAD", "MOIRA_TEST_MODE", "MOIRA_STRICT_KNOWN_ISSUES", "PYTHONUTF8"):
            assert env[key] == "1"
        assert env["PYTHONPATH"] == str(cwd) + os.pathsep + "existing-import-root"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--check"]) == 0
    assert len(calls) == len(MAINTENANCE.STAGES)
    assert os.environ["MOIRA_NO_DOWNLOAD"] == "0"


@pytest.mark.parametrize("failed_index", range(len(MAINTENANCE.STAGES)))
def test_stale_or_failed_stage_stops_before_downstream_steps(monkeypatch, capsys, failed_index):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=17 if len(calls) == failed_index + 1 else 0)

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--check"]) == 17
    assert len(calls) == failed_index + 1
    error = capsys.readouterr().err
    assert MAINTENANCE.STAGES[failed_index].name in error
    assert MAINTENANCE.STAGES[failed_index].repair_hint in error
    assert "--refresh" in error


def test_refresh_verifies_the_complete_dependency_chain_after_writing(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--refresh"]) == 0
    stages = MAINTENANCE.STAGES
    assert len(calls) == 2 * len(stages)
    for stage, command in zip(stages, calls[:len(stages)]):
        assert tuple(command[2:]) == stage.refresh_arguments
    for stage, command in zip(stages, calls[len(stages):]):
        assert tuple(command[2:]) == stage.check_arguments


def test_refresh_failure_preserves_diagnostics_and_does_not_claim_current(monkeypatch, capsys):
    monkeypatch.setattr(MAINTENANCE.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    assert MAINTENANCE.main(["--refresh"]) == 1
    assert "Generated artifacts are current" not in capsys.readouterr().out


def test_post_refresh_verification_can_fail(monkeypatch):
    count = 0

    def run(*args, **kwargs):
        nonlocal count
        count += 1
        return SimpleNamespace(returncode=23 if count > len(MAINTENANCE.STAGES) else 0)

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--refresh"]) == 23


@pytest.mark.parametrize("failed_index", [4, 6, 8])
def test_review_blocker_stops_refresh_before_wiki_or_verification(monkeypatch, failed_index):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if len(calls) == failed_index + 1 else 0)

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--refresh"]) == 1
    assert len(calls) == failed_index + 1
    assert not any(Path(command[1]).name == "sync_git_wiki.py" for command in calls)


def test_launch_error_is_reported_without_running_later_stages(monkeypatch, capsys):
    def run(*args, **kwargs):
        raise OSError("test launch failure")

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--check"]) == 1
    assert "test launch failure" in capsys.readouterr().err


def test_interrupt_has_explicit_non_success_exit(monkeypatch):
    def run(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(MAINTENANCE.subprocess, "run", run)
    assert MAINTENANCE.main(["--check"]) == 130


@pytest.mark.parametrize("arguments", [[], ["--refresh", "--check"]])
def test_mode_must_be_explicit_and_unambiguous(arguments):
    with pytest.raises(SystemExit) as error:
        MAINTENANCE.main(arguments)
    assert error.value.code == 2


def test_new_public_type_requires_refresh_and_check_does_not_write(tmp_path, monkeypatch):
    """Release checks still reject stale membership and preserve reviewed inputs."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "inventory_fixture.py").write_text(
        "from pathlib import Path\nimport sys\n"
        "source = Path('public_types.txt').read_text()\n"
        "output = Path('inventory.txt')\n"
        "if '--check' in sys.argv:\n"
        "    raise SystemExit(0 if output.read_text() == source else 1)\n"
        "output.write_text(source)\n",
        encoding="utf-8",
    )
    (tmp_path / "public_types.txt").write_text("ExistingVessel\nNewPassiveVessel\n")
    (tmp_path / "inventory.txt").write_text("ExistingVessel\n")
    protected = [tmp_path / name for name in ("baseline.json", "product-use.json", "receipts.json", "unrelated.txt")]
    for path in protected:
        path.write_bytes(b"preserve reviewed input\n")
    monkeypatch.setattr(MAINTENANCE, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(MAINTENANCE, "STAGES", (MAINTENANCE.Stage("Fixture inventory", "inventory_fixture.py", "Review new exports."),))
    assert MAINTENANCE.main(["--check"]) == 1
    assert (tmp_path / "inventory.txt").read_text() == "ExistingVessel\n"
    assert MAINTENANCE.main(["--refresh"]) == 0
    assert MAINTENANCE.main(["--check"]) == 0
    assert all(path.read_bytes() == b"preserve reviewed input\n" for path in protected)


def _workflow(name="release-hardening.yml"):
    # BaseLoader retains GitHub's YAML `on` key instead of treating it as bool.
    return yaml.load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


@pytest.mark.parametrize("name", ["release-hardening.yml", "release-acceptance.yml"])
def test_broad_suites_are_manual_and_reusable_not_routine_push_requirements(name):
    events = _workflow(name)["on"]
    assert set(events) == {"workflow_dispatch", "workflow_call"}


def test_tag_builds_and_publication_require_both_same_commit_release_suites():
    workflow = _workflow("pypi-publish.yml")
    assert workflow["on"] == {"push": {"tags": ["v*"]}}
    jobs = workflow["jobs"]
    gates = {"release-hardening", "release-acceptance"}
    for gate in gates:
        job = jobs[gate]
        assert job["uses"] == f"./.github/workflows/{gate}.yml"
        assert job["needs"] == "validate-release"
        assert "if" not in job and "continue-on-error" not in job
        # No ref override: the reusable suites and checkout use the tagged source.
        assert "with" not in job
    for name in ("build-wheels", "build-sdist", "publish"):
        job = jobs[name]
        assert gates <= set(job["needs"])
        assert "if" not in job and "continue-on-error" not in job
    assert {"build-wheels", "build-sdist", "website-publication"} <= set(jobs["publish"]["needs"])
    assert workflow["permissions"] == {"contents": "read"}


def test_release_generated_gate_checks_without_refresh_and_runs_its_regressions():
    job = _workflow()["jobs"]["generated-artifacts"]
    assert job["name"] == "Generated Artifact Gate"
    assert "if" not in job
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["submodules"] == "recursive"
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "python scripts/maintain_generated.py --check" in commands
    assert "--refresh" not in commands
    assert "test_lightbox_generated_maintenance.py" in commands
    assert 'tests/unit/test_docstring_governance.py -k "test_checker or test_preflight"' in commands
    assert not any(step.get("continue-on-error") == "true" for step in steps)


def test_full_release_hardening_waits_for_generated_gate():
    needs = _workflow()["jobs"]["release-hardening"]["needs"]
    assert "generated-artifacts" in ([needs] if isinstance(needs, str) else needs)


def test_generated_release_context_is_unique_across_workflows():
    names = []
    for path in sorted(path for path in (ROOT / ".github/workflows").iterdir() if path.suffix.lower() in {".yml", ".yaml"}):
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        names.extend(job.get("name", key) for key, job in workflow.get("jobs", {}).items())
    assert names.count("Generated Artifact Gate") == 1


def test_release_context_names_keep_failures_identifiable():
    jobs = _workflow()["jobs"]
    assert {key: jobs[key]["name"] for key in ("docstring-preflight", "generated-artifacts", "python-310-server-compatibility", "release-hardening")} == {
        "docstring-preflight": "Engine Docstring Preflight",
        "generated-artifacts": "Generated Artifact Gate",
        "python-310-server-compatibility": "Python 3.10 Server Compatibility Gate",
        "release-hardening": "Release Hardening Gate",
    }
