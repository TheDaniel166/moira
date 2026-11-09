"""Keep the generated-artifact gate on the schema renderer the release recorded.

The Light Box inventory stamps the FastAPI and Pydantic versions that rendered
it.  A newer renderer published between release preparation and the tag would
change that stamp and fail the byte-for-byte generated check, although no
Moira surface changed.  This script reads the committed stamp and either
verifies the active environment against it or installs exactly those versions.

Upgrading the renderer stays a deliberate release-preparation act: upgrade the
project environment, run ``scripts/maintain_generated.py --refresh``, review
the diff, and commit the new stamp.  Uses only the standard library.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
PACKAGES = ("fastapi", "pydantic")


def recorded_renderer(path: Path = INVENTORY_PATH) -> dict[str, str]:
    """Return the renderer versions stamped in the committed inventory."""
    stamp = json.loads(path.read_text(encoding="utf-8")).get("schema_renderer")
    if not isinstance(stamp, dict) or set(stamp) != set(PACKAGES):
        raise ValueError(f"{path.name} has no schema_renderer stamp for {', '.join(PACKAGES)}")
    for package, version in stamp.items():
        if not isinstance(version, str) or not re.fullmatch(r"[0-9][0-9A-Za-z.+!-]*", version):
            raise ValueError(f"{path.name} records an unusable {package} version: {version!r}")
    return {package: stamp[package] for package in PACKAGES}


def active_renderer() -> dict[str, str | None]:
    """Return the renderer versions installed in the running interpreter."""
    versions: dict[str, str | None] = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def differences(recorded: Mapping[str, str], active: Mapping[str, str | None]) -> list[str]:
    """Describe every package whose active version differs from the stamp."""
    return [
        f"{package}: recorded {recorded[package]}, active {active[package] or 'not installed'}"
        for package in PACKAGES
        if active[package] != recorded[package]
    ]


def install_command(recorded: Mapping[str, str]) -> list[str]:
    """Build the exact-version installation for the running interpreter."""
    return [sys.executable, "-m", "pip", "install", *(f"{package}=={recorded[package]}" for package in PACKAGES)]


def main(argv: Sequence[str] | None = None) -> int:
    """Verify the active renderer, or install the recorded one with ``--install``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Install the recorded versions instead of only checking.")
    args = parser.parse_args(argv)
    try:
        recorded = recorded_renderer()
    except (OSError, ValueError) as exc:
        print(f"Cannot read the recorded schema renderer: {exc}", file=sys.stderr)
        return 1
    if args.install:
        status = subprocess.run(install_command(recorded), check=False).returncode
        if status:
            return status
    mismatches = differences(recorded, active_renderer())
    if mismatches:
        print("Schema renderer differs from the committed inventory stamp:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  {mismatch}", file=sys.stderr)
        print("Run scripts/pin_schema_renderer.py --install, or refresh generated artifacts deliberately.", file=sys.stderr)
        return 1
    print("Schema renderer matches the inventory stamp: " + ", ".join(f"{p} {recorded[p]}" for p in PACKAGES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
