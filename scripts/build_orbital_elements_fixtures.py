#!/usr/bin/env python3
"""Build disjoint exact-JDTDB Horizons orbital-element candidates.

Network access is intentional and belongs outside pytest. Both VECTORS and
ELEMENTS requests use the same discrete TDB instant. Accepted fixtures are
copied into ``tests/fixtures`` only after human review.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "tests"))

from tools.horizons import (  # noqa: E402
    _orbital_elements_tdb_parameters,
    _parse_orbital_elements,
    _parse_vector_state,
    _vector_state_tdb_parameters,
    orbital_elements_response_tdb,
    vector_state_response_tdb,
)


GENERATOR_VERSION = "moira-horizons-orbital-elements-builder-v1"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


@dataclass(frozen=True, slots=True)
class Case:
    body: str
    body_naif_id: int
    command: str
    center: str
    center_naif_id: int
    jd_tdb: float

    @property
    def key(self) -> str:
        return f"{self.body_naif_id}:{self.center_naif_id}:{self.jd_tdb:.12f}"


CALIBRATION = (
    Case("Mercury", 199, "199", "500@10", 10, 2_451_545.0),
    Case("Earth", 399, "399", "500@10", 10, 2_460_676.5),
    Case("Jupiter", 5, "5", "500@10", 10, 2_470_171.5),
    Case("Moon", 301, "301", "500@399", 399, 2_461_298.5),
)

PLANET_HOLDOUT = (
    Case("Venus", 299, "299", "500@10", 10, 2_433_282.5),
    Case("Earth-Moon Barycenter", 3, "3", "500@10", 10, 2_451_910.5),
    Case("Mars", 4, "4", "500@10", 10, 2_461_298.5),
    Case("Saturn", 6, "6", "500@10", 10, 2_470_171.5),
    Case("Uranus", 7, "7", "500@10", 10, 2_451_544.5),
    Case("Neptune", 8, "8", "500@10", 10, 2_460_676.5),
    Case("Pluto", 9, "9", "500@10", 10, 2_433_282.5),
)

CATALOG_HOLDOUT = (
    Case("Ceres", 2_000_001, "1;", "500@10", 10, 2_451_545.0),
    Case("Hektor", 2_000_624, "624;", "500@10", 10, 2_460_676.5),
    Case("Atira", 2_163_693, "163693;", "500@10", 10, 2_461_298.5),
    Case("Apophis", 2_099_942, "99942;", "500@10", 10, 2_458_850.5),
    Case(
        "1P/Halley",
        1_000_001,
        "DES=1P;NOFRAG;CAP",
        "500@10",
        10,
        2_460_676.5,
    ),
    Case(
        "2P/Encke",
        1_000_002,
        "DES=2P;NOFRAG;CAP",
        "500@10",
        10,
        2_460_676.5,
    ),
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return None if match is None else match.group(1).strip()


def _authority_metadata(elements_text: str) -> dict[str, Any]:
    gm_text = _first_match(
        r"^Keplerian GM\s*:\s*([+\-0-9.Ee]+)\s+au\^3/d\^2", elements_text
    )
    target_source = _first_match(
        r"^Target body name:.*?\{source:\s*([^}]+)\}", elements_text
    )
    return {
        "api_version": _first_match(r"^API VERSION:\s*(.+)$", elements_text),
        "api_source": _first_match(r"^API SOURCE:\s*(.+)$", elements_text),
        "target_body_line": _first_match(r"^(Target body name:.+)$", elements_text),
        "center_body_line": _first_match(r"^(Center body name:.+)$", elements_text),
        "target_solution": target_source,
        "solution_date": _first_match(r"Solution date:\s*(.+?)\s*$", elements_text),
        "keplerian_gm_au3_day2": None if gm_text is None else float(gm_text),
        "output_type": _first_match(r"^Output type\s*:\s*(.+)$", elements_text),
        "reference_frame": _first_match(r"^Reference frame\s*:\s*(.+)$", elements_text),
    }


def _record(case: Case, retrieved_utc: str) -> dict[str, Any]:
    vector_request = _vector_state_tdb_parameters(
        case.command, case.jd_tdb, case.center
    )
    elements_request = _orbital_elements_tdb_parameters(
        case.command, case.jd_tdb, case.center
    )
    vector_text = vector_state_response_tdb(
        case.command, case.jd_tdb, case.center
    )
    elements_text = orbital_elements_response_tdb(
        case.command, case.jd_tdb, case.center
    )
    vector = _parse_vector_state(case.command, vector_text)
    elements = _parse_orbital_elements(case.command, elements_text)
    return {
        "case_key": case.key,
        "fixture_role": "exact_jdtdb_vectors_and_elements",
        "body": case.body,
        "body_naif_id": case.body_naif_id,
        "center_naif_id": case.center_naif_id,
        "jd_tdb": case.jd_tdb,
        "source": {
            "owner": "NASA/JPL Solar System Dynamics",
            "source_url": HORIZONS_URL,
            "retrieved_utc": retrieved_utc,
            "generator_version": GENERATOR_VERSION,
        },
        "requests": {
            "vectors": vector_request,
            "elements": elements_request,
        },
        "responses": {
            "vectors_sha256": _sha256_text(vector_text),
            "vectors_byte_count": len(vector_text.encode("utf-8")),
            "elements_sha256": _sha256_text(elements_text),
            "elements_byte_count": len(elements_text.encode("utf-8")),
        },
        "authority": _authority_metadata(elements_text),
        "vector_icrf_km_km_s": asdict(vector),
        "elements_j2000_ecliptic_au_day": asdict(elements),
    }


def _payload(role: str, cases: tuple[Case, ...], retrieved_utc: str) -> dict[str, Any]:
    return {
        "schema_version": "moira.horizons-orbital-elements.v1",
        "generator_version": GENERATOR_VERSION,
        "fixture_role": role,
        "source_url": HORIZONS_URL,
        "records": [_record(case, retrieved_utc) for case in cases],
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    tracked_fixture_dir = (REPOSITORY_ROOT / "tests" / "fixtures").resolve()
    if output_dir == tracked_fixture_dir or tracked_fixture_dir in output_dir.parents:
        raise SystemExit("candidate output must not be inside tests/fixtures")
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    files = (
        (
            "horizons_orbital_elements_calibration.json",
            "calibration",
            CALIBRATION,
        ),
        (
            "horizons_orbital_elements_holdout.json",
            "planet_holdout",
            PLANET_HOLDOUT,
        ),
        (
            "horizons_orbital_elements_catalog_holdout.json",
            "catalog_holdout",
            CATALOG_HOLDOUT,
        ),
    )
    for filename, role, cases in files:
        _write(output_dir / filename, _payload(role, cases, retrieved_utc))
    print(f"wrote Horizons candidates to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
