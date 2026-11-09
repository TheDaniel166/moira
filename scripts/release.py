"""Carry one Moira release from its written notes to a verified candidate.

    .venv\\Scripts\\python.exe scripts\\release.py 6.14.0
    .venv\\Scripts\\python.exe scripts\\release.py 6.14.0 --publish

The command is resumable: it reads the repository state, runs the next phase,
and can be run again after any stop.

prepare    Requires the hand-written CHANGELOG entry, release notes,
           compatibility notes and publication summary. Bumps every version
           string, regenerates release metadata and binds the Light Box
           baseline and product-usage snapshot to the new inventory identity.
           It stops once for the human review of that baseline, then commits
           "Prepare <kind> release X.Y.Z".
attest     Replays the Light Box contracts on that exact clean commit,
           regenerates the evidence, publishes the wiki mirror and commits
           "Attest exact-source X.Y.Z release verification".
candidate  Runs the local CI plan, pushes main, and runs the tag's gates on
           GitHub against the untagged commit (release-candidate.yml).
publish    Only with --publish and a green candidate: tags, pushes the tag and
           follows the PyPI publication.

It never writes release prose, coverage thresholds, admissions or a review
verdict. Those stay with the reviewer; the command only refuses to continue
until they exist.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_release_identity  # noqa: E402
from scripts.check_lightbox_release_gate import ATTESTATION_PATHS, EVIDENCE_PATHS, WIKI_GITLINK_PATH  # noqa: E402


VALIDATION = "wiki/03_validation"
INVENTORY = f"{VALIDATION}/LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
BASELINE = f"{VALIDATION}/LIGHT_BOX_RELEASE_BASELINE.json"
SNAPSHOT = f"{VALIDATION}/LIGHT_BOX_PRODUCT_USAGE_SNAPSHOT.json"
PUBLICATION = "website_docs/publication_sources.json"
CANDIDATE_BRANCH = "release-candidate"
CANDIDATE_WORKFLOW = ".github/workflows/release-candidate.yml"
PUBLISH_WORKFLOW = ".github/workflows/pypi-publish.yml"
# (path, pattern, replacement); {old}, {new} and {kind} are filled per release.
VERSION_EDITS = (
    ("pyproject.toml", r'^version = "{old}"$', 'version = "{new}"'),
    ("moira/facade.py", r'^__version__ = "{old}"$', '__version__ = "{new}"'),
    ("README.md", r"documents the `{old}` (?:major|minor|patch)-release baseline", "documents the `{new}` {kind}-release baseline"),
    ("llms.txt", r"\(current: {old}\)", "(current: {new})"),
    ("wiki/02_standards/API_REFERENCE.md", r"\*\*Engine baseline:\*\* {old}", "**Engine baseline:** {new}"),
)
PREPARE_FILES = frozenset({path for path, _, _ in VERSION_EDITS} | {"CHANGELOG.md", PUBLICATION})
PREPARE_PREFIX = "wiki/"
ENVIRONMENT = {"MOIRA_NO_DOWNLOAD": "1", "MOIRA_TEST_MODE": "1", "MOIRA_STRICT_KNOWN_ISSUES": "1", "PYTHONUTF8": "1"}


class ReleaseError(RuntimeError):
    """A release step cannot continue; the message says what to do next."""


# --------------------------------------------------------------------------
# Pure decisions
# --------------------------------------------------------------------------

def parse_version(value: str) -> tuple[int, int, int]:
    """Read a stable X.Y.Z version."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ReleaseError(f"not a stable X.Y.Z version: {value!r}")
    major, minor, patch = (int(part) for part in value.split("."))
    return major, minor, patch


def release_kind(previous: str, target: str) -> str:
    """Name the step from the previous version; refuse anything but the next one."""
    old, new = parse_version(previous), parse_version(target)
    steps = {
        (old[0] + 1, 0, 0): "major",
        (old[0], old[1] + 1, 0): "minor",
        (old[0], old[1], old[2] + 1): "patch",
    }
    if new not in steps:
        raise ReleaseError(f"{target} is not the next major, minor or patch release after {previous}")
    return steps[new]


def bump_text(path: str, text: str, previous: str, target: str, kind: str) -> str:
    """Rewrite the one version statement a file carries; fail if it is not exactly one."""
    for edit_path, pattern, replacement in VERSION_EDITS:
        if edit_path == path:
            expression = pattern.format(old=re.escape(previous))
            updated, count = re.subn(expression, replacement.format(new=target, kind=kind), text, flags=re.MULTILINE)
            if count != 1:
                raise ReleaseError(f"{path}: expected one version statement for {previous}, found {count}")
            return updated
    raise ReleaseError(f"{path} carries no registered version statement")


def release_phase(target: str, head_version: str, head_subject: str, *, tagged: bool, reattest: bool = False) -> str:
    """Choose the next phase from committed state alone."""
    if tagged:
        return "publish"
    if head_subject == f"Attest exact-source {target} release verification" and not reattest:
        return "candidate"
    if re.fullmatch(rf"Prepare (major|minor|patch) release {re.escape(target)}", head_subject) or (
        reattest and head_version == target
    ):
        return "attest"
    if head_version == target:
        raise ReleaseError(
            f"HEAD already carries {target} but is neither its prepare nor its attest commit. "
            "If a fix was committed after attestation, rerun with --reattest to replay the "
            "contracts on the current commit."
        )
    return "prepare"


def surface_diff(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, dict[str, list[str]]]:
    """Compare two inventories by surface identity and API contract."""
    result = {}
    for group in ("python_exports", "rest_operations"):
        before = {row["surface_id"]: row for row in old[group]}
        after = {row["surface_id"]: row for row in new[group]}
        result[group] = {
            "added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "changed": sorted(
                key for key in set(before) & set(after)
                if before[key]["api_contract_sha256"] != after[key]["api_contract_sha256"]
            ),
            "rescoped": sorted(
                key for key in set(before) & set(after)
                if before[key]["in_lightbox_calculation_scope"] != after[key]["in_lightbox_calculation_scope"]
            ),
            "calculation_added": sorted(
                key for key in set(after) - set(before) if after[key]["in_lightbox_calculation_scope"]
            ),
        }
    return result


def describe_surface_diff(diff: Mapping[str, Mapping[str, Sequence[str]]], *, limit: int = 40) -> str:
    """Render the surface comparison the reviewer needs for the baseline."""
    lines = []
    for group, label in (("python_exports", "Python exports"), ("rest_operations", "REST operations")):
        changes = diff[group]
        lines.append(
            f"{label}: {len(changes['added'])} added ({len(changes['calculation_added'])} in calculation scope), "
            f"{len(changes['removed'])} removed, {len(changes['changed'])} contracts changed, "
            f"{len(changes['rescoped'])} reclassified"
        )
        for name in ("added", "removed", "rescoped", "changed"):
            for surface in changes[name][:limit]:
                lines.append(f"  {name:9} {surface}")
            if len(changes[name]) > limit:
                lines.append(f"  {name:9} ... and {len(changes[name]) - limit} more")
    return "\n".join(lines)


def bind_baseline(baseline: Mapping[str, Any], *, version: str, fingerprint: str, parent: str, today: str) -> dict[str, Any]:
    """Set the baseline's identity fields. Thresholds and the review stay untouched."""
    bound = copy.deepcopy(dict(baseline))
    bound.update(
        baseline_date=today,
        source_parent_revision=parent,
        engine_version=version,
        inventory_fingerprint_sha256=fingerprint,
    )
    return bound


def bind_snapshot(snapshot: Mapping[str, Any], *, version: str, fingerprint: str) -> dict[str, Any]:
    """Set the snapshot's inventory binding. The audit, callsites and notes stay untouched."""
    bound = copy.deepcopy(dict(snapshot))
    bound.update(engine_version=version, inventory_fingerprint_sha256=fingerprint)
    return bound


def review_problems(
    head_baseline: Mapping[str, Any], baseline: Mapping[str, Any],
    head_snapshot: Mapping[str, Any], snapshot: Mapping[str, Any], version: str,
) -> list[str]:
    """List what the reviewer still has to write before the baseline may be committed."""
    problems = []
    review = baseline.get("review")
    if not isinstance(review, dict) or review == head_baseline.get("review"):
        problems.append(f"{BASELINE}: the review block still describes the previous release; rewrite it for {version}")
    elif review.get("from_baseline_date") != head_baseline.get("baseline_date"):
        problems.append(
            f"{BASELINE}: review.from_baseline_date must be the previous baseline date "
            f"{head_baseline.get('baseline_date')}"
        )
    notes = snapshot.get("limitations") or []
    if len(notes) <= len(head_snapshot.get("limitations") or []) or version not in str(notes[-1]):
        problems.append(
            f"{SNAPSHOT}: append a dated limitations note for {version} saying whether this is a "
            "reviewed rebind or a fresh consumer audit"
        )
    return problems


def unexpected_prepare_paths(changed: Iterable[str]) -> list[str]:
    """Return changed paths a prepare commit must not sweep up."""
    return sorted(
        path for path in changed
        if path != WIKI_GITLINK_PATH and path not in PREPARE_FILES and not path.startswith(PREPARE_PREFIX)
    )


def repository_slug(remote_url: str) -> str:
    """Extract owner/name from a GitHub remote URL."""
    match = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", remote_url.strip())
    if not match:
        raise ReleaseError(f"origin is not a GitHub repository: {remote_url!r}")
    return f"{match.group(1)}/{match.group(2)}"


def workflow_verdict(payload: Mapping[str, Any], workflow_path: str, sha: str) -> tuple[str, Mapping[str, Any] | None]:
    """Reduce a workflow-run listing to pending, success or failure for one commit."""
    runs = [
        run for run in payload.get("workflow_runs", [])
        if run.get("path") == workflow_path and run.get("head_sha") == sha
    ]
    if not runs:
        return "pending", None
    latest = max(runs, key=lambda run: (run.get("run_number", 0), run.get("run_attempt", 0)))
    if latest.get("status") != "completed":
        return "pending", latest
    return ("success" if latest.get("conclusion") == "success" else "failure"), latest


# --------------------------------------------------------------------------
# Repository and process access
# --------------------------------------------------------------------------

def git(*arguments: str, cwd: Path = ROOT, check: bool = True) -> str:
    """Run git and return its trimmed output."""
    process = subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False)
    if check and process.returncode:
        raise ReleaseError(f"git {' '.join(arguments)} failed in {cwd.name}:\n{process.stderr.strip()}")
    return process.stdout.strip()


def changed_paths(cwd: Path = ROOT) -> set[str]:
    """Tracked changes against HEAD plus untracked files."""
    tracked = git("diff", "--name-only", "-z", "HEAD", "--", cwd=cwd)
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", cwd=cwd)
    return {path for path in (tracked + "\0" + untracked).split("\0") if path}


def step(label: str, command: Sequence[str], *, allow_failure: bool = False) -> int:
    """Run one child with the release environment; stop the release if it fails."""
    print(f"\n== {label}", flush=True)
    environment = {**os.environ, **ENVIRONMENT}
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(ROOT), environment.get("PYTHONPATH", ""))))
    status = subprocess.run(list(command), cwd=ROOT, env=environment, check=False).returncode
    if status and not allow_failure:
        raise ReleaseError(f"{label} failed (exit {status}). Fix the cause, then run this command again.")
    return status


def script(name: str, *arguments: str) -> list[str]:
    """Command line for a repository script under the active interpreter."""
    return [sys.executable, str(ROOT / "scripts" / name), *arguments]


def read_text(path: str) -> tuple[str, bool]:
    """Read a repository file as LF text and remember whether it was CRLF."""
    raw = (ROOT / path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_text(path: str, text: str, crlf: bool) -> None:
    """Write LF text back in the file's own line-ending convention."""
    (ROOT / path).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def read_json(path: str) -> dict[str, Any]:
    """Load a repository JSON document."""
    return json.loads(read_text(path)[0])


def write_json(path: str, value: Mapping[str, Any]) -> None:
    """Write a reviewed JSON document in its existing two-space layout."""
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n", read_text(path)[1])


def head_json(path: str) -> dict[str, Any]:
    """Load a JSON document as committed at HEAD."""
    return json.loads(git("show", f"HEAD:{path}"))


def commit(message: str, trailers: Sequence[str], *, cwd: Path = ROOT) -> None:
    """Commit the staged index with optional trailers."""
    body = message + ("\n\n" + "\n".join(trailers) if trailers else "")
    git("-c", "core.safecrlf=false", "commit", "-q", "-m", body, cwd=cwd)
    print(f"Committed in {cwd.name}: {git('log', '-1', '--format=%h %s', cwd=cwd)}", flush=True)


def github(slug: str, resource: str) -> dict[str, Any]:
    """Read one GitHub REST resource; a token is optional for a public repository."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{slug}/{resource}",
        headers={"User-Agent": "moira-release", "Accept": "application/vnd.github+json"},
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_workflow(slug: str, workflow_path: str, sha: str, *, minutes: int, interval: int = 90) -> None:
    """Follow one workflow run for a commit until it passes; raise when it fails."""
    deadline = time.monotonic() + minutes * 60
    last = ""
    while True:
        try:
            verdict, run = workflow_verdict(github(slug, f"actions/runs?head_sha={sha}&per_page=50"), workflow_path, sha)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            verdict, run = "pending", None
            print(f"  GitHub not readable yet ({exc}); retrying", flush=True)
        state = f"{verdict}: {run.get('html_url')} ({run.get('status')})" if run else f"{verdict}: run not listed yet"
        if state != last:
            print(f"  {state}", flush=True)
            last = state
        if verdict == "success":
            return
        if verdict == "failure" and run is not None:
            try:
                jobs = github(slug, f"actions/runs/{run['id']}/jobs?per_page=100").get("jobs", [])
                failed = [job["name"] for job in jobs if job.get("conclusion") not in {"success", "skipped", None}]
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
                failed = []
            raise ReleaseError(
                f"{workflow_path} failed for {sha[:9]}: {run.get('html_url')}\n  failed jobs: "
                + (", ".join(failed) or "see the run")
            )
        if time.monotonic() > deadline:
            raise ReleaseError(f"{workflow_path} did not finish within {minutes} minutes; run this command again to keep watching.")
        time.sleep(interval)


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------

def require_release_documents(version: str) -> None:
    """Refuse to start until every hand-written release document exists."""
    failures = check_release_identity._check_release_documents(version, require_empty_unreleased=True)
    summaries = read_json(PUBLICATION).get("release_summaries", [])
    if not any(isinstance(entry, dict) and entry.get("version") == version for entry in summaries):
        failures.append(f"{PUBLICATION} has no release_summaries entry for {version}")
    if failures:
        raise ReleaseError("Write the release documents first:\n  - " + "\n  - ".join(failures))


def prepare(version: str, previous: str, trailers: Sequence[str]) -> None:
    """Bump, regenerate, bind, wait for the baseline review, then commit."""
    kind = release_kind(previous, version)
    require_release_documents(version)
    parent = git("rev-parse", "HEAD")
    for path, _, _ in VERSION_EDITS:
        text, crlf = read_text(path)
        try:
            write_text(path, bump_text(path, text, previous, version, kind), crlf)
        except ReleaseError:
            bump_text(path, text, version, version, kind)  # already bumped by an earlier run, or raise
    if importlib.metadata.version("moira-astro") != version:
        step("Refresh the installed package metadata", [sys.executable, "-m", "pip", "install", "-q", "--no-deps", "-e", "."])
    step("Check the schema renderer against the committed stamp", script("pin_schema_renderer.py"))
    step("Regenerate the Light Box inventory", script("generate_lightbox_calculation_inventory.py"))

    inventory = read_json(INVENTORY)
    fingerprint = inventory["structural_fingerprint_sha256"]
    head_baseline, head_snapshot = head_json(BASELINE), head_json(SNAPSHOT)
    rebinding = head_baseline["inventory_fingerprint_sha256"] != fingerprint
    if rebinding:
        if read_json(BASELINE)["inventory_fingerprint_sha256"] != fingerprint:
            today = datetime.date.today().isoformat()
            write_json(BASELINE, bind_baseline(read_json(BASELINE), version=version, fingerprint=fingerprint, parent=parent, today=today))
            write_json(SNAPSHOT, bind_snapshot(read_json(SNAPSHOT), version=version, fingerprint=fingerprint))
            print(f"\nBound the baseline and product-usage snapshot identity to {fingerprint[:12]}.", flush=True)
        print("\nPublic surface since the previous release:", flush=True)
        print(describe_surface_diff(surface_diff(head_json(INVENTORY), inventory)), flush=True)

    refresh = step("Refresh generated release metadata", script("maintain_generated.py", "--refresh"), allow_failure=True)
    problems = review_problems(head_baseline, read_json(BASELINE), head_snapshot, read_json(SNAPSHOT), version) if rebinding else []
    if refresh:
        problems.append(
            "generated maintenance stopped (see above); if a coverage denominator moved, review and "
            f"edit the thresholds in {BASELINE} by hand"
        )
    if problems:
        raise ReleaseError(
            "Baseline review needed before the prepare commit:\n  - " + "\n  - ".join(problems)
            + "\nThen run this command again."
        )

    step("Check release-facing documentation", script("check_doc_consistency.py"))
    step("Check release identity", script("check_release_identity.py", "--candidate"))
    stray = unexpected_prepare_paths(changed_paths())
    if stray:
        raise ReleaseError("Unrelated changes are in the worktree; commit or remove them first:\n  " + "\n  ".join(stray))
    wiki = ROOT / WIKI_GITLINK_PATH
    if git("status", "--porcelain", cwd=wiki):
        # The mirror is regenerated after the replay; the exact-source replay needs a clean tree now.
        git("stash", "push", "-u", "-q", "-m", f"release.py {version}: mirror output before the exact-source replay", cwd=wiki)
        print("Set the regenerated wiki mirror aside (git stash in moira.wiki) until after the replay.", flush=True)
    git("add", "-A", "--", ".", f":(exclude){WIKI_GITLINK_PATH}")
    commit(f"Prepare {kind} release {version}", trailers)


def attest(version: str, trailers: Sequence[str]) -> None:
    """Replay on the exact clean commit, regenerate the evidence, publish the wiki, commit."""
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("The exact-source replay needs a clean worktree:\n" + git("status", "--short"))
    step("Replay Light Box contracts on the exact source revision", script("replay_lightbox_receipts.py", "--require-exact-source"))
    step("Refresh generated release metadata", script("maintain_generated.py", "--refresh"))
    step("Check release-facing documentation", script("check_doc_consistency.py"))
    wiki = ROOT / WIKI_GITLINK_PATH
    if git("status", "--porcelain", cwd=wiki):
        git("add", "-A", cwd=wiki)
        commit(f"Align wiki with Moira {version}", trailers, cwd=wiki)
    git("push", "origin", "HEAD:master", cwd=wiki)
    for entry in git("stash", "list", "--format=%gd %gs", cwd=wiki).splitlines():
        if f"release.py {version}:" in entry:  # the pre-replay mirror, now superseded by the commit above
            git("stash", "drop", "-q", entry.split()[0], cwd=wiki)
            break
    changed = changed_paths()
    if changed not in (set(EVIDENCE_PATHS), set(ATTESTATION_PATHS)):
        raise ReleaseError(
            "The attestation may contain only the five evidence files and the wiki gitlink. Also changed:\n  "
            + "\n  ".join(sorted(changed - set(ATTESTATION_PATHS)) or sorted(set(EVIDENCE_PATHS) - changed))
        )
    git("add", "--", *sorted(changed))
    commit(f"Attest exact-source {version} release verification", trailers)
    step("Check the exact-release Light Box gate", script("check_lightbox_release_gate.py", "--exact-release"))
    step("Check generated artifacts", script("maintain_generated.py", "--check"))


def candidate(version: str, slug: str, *, skip_local_ci: bool, minutes: int) -> None:
    """Run the local plan, publish the source, and run the tag's gates before a tag exists."""
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("The candidate needs a clean worktree:\n" + git("status", "--short"))
    sha = git("rev-parse", "HEAD")
    try:
        verdict, _ = workflow_verdict(github(slug, f"actions/runs?head_sha={sha}&per_page=50"), CANDIDATE_WORKFLOW, sha)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        verdict = "pending"
    if verdict == "success":
        print(f"The release candidate gates already passed for {sha[:9]}.", flush=True)
        return
    if not skip_local_ci:
        step("Run the local CI verification plan", script("check_ci.py"))
    step("Check release identity", script("check_release_identity.py", "--tag", f"v{version}"))
    git("push", "origin", "HEAD:main")
    git("push", "--force", "origin", f"HEAD:refs/heads/{CANDIDATE_BRANCH}")
    print(f"\n== Release candidate gates on GitHub for {sha[:9]}", flush=True)
    try:
        wait_for_workflow(slug, CANDIDATE_WORKFLOW, sha, minutes=minutes)
    finally:
        git("push", "origin", f":refs/heads/{CANDIDATE_BRANCH}", check=False)


def publish(version: str, slug: str, *, minutes: int) -> None:
    """Tag the verified commit and follow the publication to PyPI."""
    tag = f"v{version}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False):
        git("tag", "-a", tag, "-m", f"Moira {version}")
    sha = git("rev-parse", f"{tag}^{{commit}}")
    git("push", "origin", tag)
    print(f"\n== PyPI publication for {tag} ({sha[:9]})", flush=True)
    wait_for_workflow(slug, PUBLISH_WORKFLOW, sha, minutes=minutes)
    with urllib.request.urlopen(
        urllib.request.Request("https://pypi.org/pypi/moira-astro/json", headers={"User-Agent": "moira-release"}), timeout=30,
    ) as response:
        published = json.load(response)["info"]["version"]
    print(f"PyPI latest: {published}" + ("" if published == version else f" (expected {version}; the index may lag)"), flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the next release phase for the requested version."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="The release to make, for example 6.14.0")
    parser.add_argument("--publish", action="store_true", help="After a green candidate, tag and publish to PyPI.")
    parser.add_argument("--reattest", action="store_true", help="Replay and attest again on the current commit after a late fix.")
    parser.add_argument("--skip-local-ci", action="store_true", help="Skip scripts/check_ci.py when it already passed on this commit.")
    parser.add_argument("--dry-run", action="store_true", help="Report the next phase without changing anything.")
    parser.add_argument("--trailer", action="append", default=[], help="Commit trailer line; may be repeated.")
    parser.add_argument("--wait-minutes", type=int, default=120, help="How long to follow a GitHub workflow run.")
    args = parser.parse_args(argv)
    try:
        parse_version(args.version)
        if sys.version_info[:2] != (3, 14):
            raise ReleaseError("Run this with the project .venv on Python 3.14, the authoritative release runtime.")
        if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
            raise ReleaseError("Releases are made from main.")
        git("fetch", "--quiet", "--tags", "origin")
        if int(git("rev-list", "--count", "HEAD..origin/main")):
            raise ReleaseError("main is behind origin/main; bring it up to date first.")
        wiki = ROOT / WIKI_GITLINK_PATH
        if git("rev-parse", "HEAD", cwd=wiki) != git("rev-parse", f"HEAD:{WIKI_GITLINK_PATH}") and not (
            changed_paths() <= set(ATTESTATION_PATHS)
        ):
            raise ReleaseError("moira.wiki has commits the parent repository does not record; resolve that first.")
        slug = repository_slug(git("remote", "get-url", "origin"))
        tagged = bool(git("rev-parse", "-q", "--verify", f"refs/tags/v{args.version}", check=False))
        head_version = check_release_identity.tomllib.loads(git("show", "HEAD:pyproject.toml"))["project"]["version"]
        phase = release_phase(
            args.version, head_version, git("log", "-1", "--format=%s"), tagged=tagged, reattest=args.reattest,
        )
        print(f"Moira {args.version}: next phase is {phase} (HEAD {git('rev-parse', '--short', 'HEAD')}, {head_version}).", flush=True)
        if args.dry_run:
            if phase == "prepare":
                print(f"Would prepare a {release_kind(head_version, args.version)} release from {head_version}.")
                require_release_documents(args.version)
            return 0
        if phase == "prepare":
            prepare(args.version, head_version, args.trailer)
            phase = "attest"
        if phase == "attest":
            attest(args.version, args.trailer)
            phase = "candidate"
        if phase == "candidate":
            candidate(args.version, slug, skip_local_ci=args.skip_local_ci, minutes=args.wait_minutes)
            if not args.publish:
                print(
                    f"\nMoira {args.version} is a verified release candidate at {git('rev-parse', '--short', 'HEAD')}.\n"
                    f"Publish it with: scripts/release.py {args.version} --publish",
                    flush=True,
                )
                return 0
        if not args.publish:
            print(f"v{args.version} is already tagged. Follow its publication with --publish.", flush=True)
            return 0
        publish(args.version, slug, minutes=args.wait_minutes)
        return 0
    except ReleaseError as exc:
        print(f"\nRelease stopped: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nRelease interrupted; run the command again to continue.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
