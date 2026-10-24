"""Prepare release metadata by checking or refreshing generated artifacts.

Routine engine changes use focused tests; this repository-wide command is for
release preparation or an explicit metadata audit/publication, not every push.
Refresh writes mechanical generator outputs. Reviewed baselines, product-use
snapshots, conformance admissions, and execution receipts retain their existing
review/replay workflows. A blocked stage stops the command with its repair hint.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    """One existing generator or read-only governance gate."""

    name: str
    script: str
    repair_hint: str
    refresh_arguments: tuple[str, ...] = ()
    check_arguments: tuple[str, ...] = ("--check",)


# Runtime reference pages are inputs to the inventory's documentation index.
# The wiki mirror consumes every preceding canonical Markdown output.
STAGES = (
    Stage("REST reference", "sync_rest_api_reference.py", "Check the registered OpenAPI surface and generated reference blocks."),
    Stage("Hellenistic inventories", "generate_hellenistic_inventory.py", "Check the admitted family contracts and generated documentation."),
    Stage("Light Box inventory", "generate_lightbox_calculation_inventory.py", "Review added, removed, reclassified, or relocated public surfaces."),
    Stage("Light Box conformance", "generate_lightbox_conformance_manifest.py", "Review conformance inputs; admissions require their existing evidence review."),
    Stage("Light Box family register", "generate_lightbox_family_register.py", "Review the product-usage snapshot binding against the new inventory. Preserve its original audit provenance; rescan consumers when usage changed."),
    Stage("Light Box family assessment", "generate_lightbox_family_assessment.py", "Review the family register and existing assessment inputs."),
    Stage("Light Box assurance", "generate_lightbox_assurance_matrix.py", "Review receipt bindings and replay scripts/replay_lightbox_receipts.py when fresh execution evidence is required. Retain each execution's original source identity."),
    Stage("Light Box public status", "generate_lightbox_public_status.py", "Regenerate status from the reviewed manifest and actual assurance receipts."),
    Stage("Light Box source gate", "check_lightbox_release_gate.py", "Review LIGHT_BOX_RELEASE_BASELINE.json deliberately, including its identity and coverage thresholds. Review stale receipt or snapshot bindings; baseline and evidence inputs are not rewritten by this command.", check_arguments=()),
    Stage("Git wiki mirror", "sync_git_wiki.py", "Register newly authored canonical wiki pages for discovery and synchronize the mirror. Publish the wiki before committing an updated parent gitlink; routine source commits need no wiki publication.", refresh_arguments=("--no-prune",)),
)


def run_stages(*, check: bool) -> int:
    """Stop at the first failed stage, preserving the child's diagnostics."""
    environment = os.environ.copy()
    environment.update(MOIRA_NO_DOWNLOAD="1", MOIRA_TEST_MODE="1", MOIRA_STRICT_KNOWN_ISSUES="1", PYTHONUTF8="1")
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(REPO_ROOT), environment.get("PYTHONPATH", "")))
    )
    for stage in STAGES:
        arguments = stage.check_arguments if check else stage.refresh_arguments
        command = [sys.executable, str(REPO_ROOT / "scripts" / stage.script), *arguments]
        print(f"{'Check' if check else 'Refresh'}: {stage.name}", flush=True)
        try:
            result = subprocess.run(command, cwd=REPO_ROOT, env=environment, check=False)
        except OSError as exc:
            print(f"Could not run {stage.name}: {exc}", file=sys.stderr)
            return 1
        if result.returncode:
            print(f"Generated maintenance stopped at {stage.name} (exit {result.returncode}).", file=sys.stderr)
            print(stage.repair_hint, file=sys.stderr)
            if check:
                print("Refresh mechanical outputs with: python scripts/maintain_generated.py --refresh", file=sys.stderr)
            return result.returncode
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run release metadata checks or a mechanical refresh plus complete checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Check release metadata without writing it; not a routine push prerequisite.")
    mode.add_argument("--refresh", action="store_true", help="Prepare mechanical release metadata, stop on review/replay blockers, then check everything again.")
    args = parser.parse_args(argv)
    try:
        if args.refresh:
            status = run_stages(check=False)
            if status:
                return status
            print("Mechanical refresh complete; verifying generated artifacts.", flush=True)
        status = run_stages(check=True)
        if not status:
            print("Generated artifacts are current.", flush=True)
        return status
    except KeyboardInterrupt:
        print("Generated maintenance interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
