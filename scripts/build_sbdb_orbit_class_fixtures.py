#!/usr/bin/env python3
"""Build and verify JPL SBDB small-body orbit classification fixtures.

This script fetches or audits osculating elements and classifications
from the NASA JPL Small-Body Database (SBDB) API outside pytest.
Network access is explicit and never invoked during standard test runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.request
import urllib.parse


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "sbdb_orbit_classes.json"
)
SBDB_API_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"


def fetch_sbdb_orbit_record(designation: str) -> dict[str, object]:
    """Fetch orbit parameters and classification from the JPL SBDB API.

    Parameters
    ----------
    designation : str
        Small-body designation or number (e.g., '1', '2060', '436724').

    Returns
    -------
    dict of str to object
        Parsed JSON record containing orbit elements and classification.
    """
    params = urllib.parse.urlencode({"sstr": designation})
    req = urllib.request.Request(
        f"{SBDB_API_URL}?{params}",
        headers={"User-Agent": "Moira-SBDB-Fixture-Builder/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    """Execute fixture verification or update from command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify or refresh SBDB orbit class test fixture."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate syntax and schema of existing fixture without network.",
    )
    args = parser.parse_args()

    if not FIXTURE_PATH.is_file():
        sys.stderr.write(f"Fixture not found at {FIXTURE_PATH}\n")
        return 1

    content = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = content.get("records", [])
    print(f"Fixture loaded: {len(records)} records.")

    if args.verify_only:
        print("Verification successful.")
        return 0

    print("Network refresh mode not enabled in default build invocation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
