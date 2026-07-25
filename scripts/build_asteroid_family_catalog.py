"""Build Moira's normalized asteroid-family catalog from audited sources.

The current main-belt source is David Nesvorny's Proper25 distribution.
Proper25 explicitly excludes Hilda and Jupiter Trojan families, so those
populations are retained from the NASA PDS 2015 family tables only.

This script deliberately fails if the audited source shape changes.  A source
update must be reviewed rather than silently admitted into the bundled data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


PROPER25_URL = "https://www2.boulder.swri.edu/~davidn/Proper25/"
PROPER25_PAPER_URL = "https://arxiv.org/abs/2602.20382"
PDS_URL = "https://sbn.psi.edu/pds/resource/nesvornyfam.html"
PDS_BUNDLE_URN = "urn:nasa:pds:ast.nesvorny.families::2.0"
PDS_DOI = "10.26033/5hyq-6k90"

LEGACY_EXCLUDED_POPULATIONS = {
    "001": ("Hilda", "hilda"),
    "002": ("Schubart", "hilda"),
    "004": ("Hector", "jupiter_trojan"),
    "005": ("Eurybates", "jupiter_trojan"),
    "006": ("1996 RJ", "jupiter_trojan"),
    "008": ("Arkesilaos", "jupiter_trojan"),
    "009": ("Ennomos", "jupiter_trojan"),
    "010": ("2001 UV209", "jupiter_trojan"),
}

FAMILY_ALIASES = {
    "Koronis(2)": "Koronis2",
    "RJ": "1996 RJ",
    "UV209": "2001 UV209",
}


@dataclass(frozen=True, slots=True)
class Family:
    family_id: str
    family_name: str
    reference_number: int | None
    reported_member_count: int
    catalog_source: str
    population: str
    publication_code: str
    members: tuple[int, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _parse_proper25_ledger(path: Path) -> tuple[list[dict[str, int | str]], list[int]]:
    active: list[dict[str, int | str]] = []
    removed: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit() or len(fields) < 13:
            continue
        row: dict[str, int | str] = {
            "fin": int(fields[0]),
            "reference_number": int(fields[1]),
            "family_name": fields[2],
            "cutoff_m_per_s": int(fields[3]),
            "reported_member_count": int(fields[4]),
            "publication_code": fields[12],
        }
        if row["reported_member_count"] == -1:
            removed.append(int(row["fin"]))
        else:
            active.append(row)

    if len(active) != 334 or removed != [2003, 2027, 2028, 2031, 2036]:
        raise ValueError(
            "Proper25 ledger shape differs from the audited 334 active and "
            "five removed entries"
        )
    return active, removed


def _numbered_members(path: Path) -> tuple[int, ...]:
    members: set[int] = set()
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        fields = line.split()
        if fields and fields[-1].isdecimal():
            members.add(int(fields[-1]))
    return tuple(sorted(members))


def _proper25_families(root: Path) -> tuple[list[Family], dict[str, object]]:
    ledger_path = root / "list_of_families.txt"
    membership_dir = root / "Membership"
    active, removed = _parse_proper25_ledger(ledger_path)
    by_name = {_normalized_name(str(row["family_name"])): row for row in active}

    membership_files = sorted(membership_dir.glob("*.fam3"))
    if len(membership_files) != 335:
        raise ValueError(
            f"expected 335 Proper25 membership files, found {len(membership_files)}"
        )

    families: list[Family] = []
    unmatched: list[str] = []
    tree_digest = hashlib.sha256()
    for path in membership_files:
        try:
            file_family_name = path.stem.split("_", 2)[2]
        except IndexError as exc:
            raise ValueError(f"unrecognized Proper25 filename: {path.name}") from exc
        row = by_name.get(_normalized_name(file_family_name))
        if row is None:
            unmatched.append(path.name)
            continue

        file_hash = _sha256(path)
        tree_digest.update(path.name.encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(file_hash.encode("ascii"))
        tree_digest.update(b"\n")

        reference_number = int(row["reference_number"])
        families.append(
            Family(
                family_id=f"P25-{int(row['fin']):04d}",
                family_name=str(row["family_name"]),
                reference_number=reference_number if reference_number > 0 else None,
                reported_member_count=int(row["reported_member_count"]),
                catalog_source="Proper25_2026",
                population="main_belt",
                publication_code=str(row["publication_code"]),
                members=_numbered_members(path),
            )
        )

    if unmatched != ["middle_2344_Xizang.fam3"]:
        raise ValueError(
            "Proper25 unmatched files differ from the audited removed Xizang file: "
            f"{unmatched!r}"
        )
    if len(families) != 334:
        raise ValueError(f"expected 334 active Proper25 families, found {len(families)}")

    details: dict[str, object] = {
        "url": PROPER25_URL,
        "paper_url": PROPER25_PAPER_URL,
        "ledger_sha256": _sha256(ledger_path),
        "active_membership_tree_sha256": tree_digest.hexdigest(),
        "membership_file_count": len(membership_files),
        "active_membership_file_count": len(families),
        "active_family_count": len(families),
        "removed_fin": removed,
        "excluded_orphan_file": unmatched[0],
    }
    manifest_path = root / "source_manifest.json"
    if manifest_path.exists():
        details["retrieval_manifest_sha256"] = _sha256(manifest_path)
    return families, details


def _pds_excluded_population_families(
    archive_path: Path,
) -> tuple[list[Family], dict[str, object]]:
    selected: dict[str, str] = {}
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            basename = Path(name).name
            family_id = basename[:3]
            if (
                "/data/families_2015/" in name
                and basename.endswith(".tab")
                and family_id in LEGACY_EXCLUDED_POPULATIONS
            ):
                selected[family_id] = name

        if set(selected) != set(LEGACY_EXCLUDED_POPULATIONS):
            missing = sorted(set(LEGACY_EXCLUDED_POPULATIONS) - set(selected))
            raise ValueError(f"PDS archive is missing audited legacy families: {missing}")

        families: list[Family] = []
        for family_id, (family_name, population) in LEGACY_EXCLUDED_POPULATIONS.items():
            members: set[int] = set()
            reference_numbers: set[int] = set()
            text = archive.read(selected[family_id]).decode("ascii", errors="replace")
            for line in text.splitlines():
                fields = line.split()
                if not fields:
                    continue
                members.add(int(fields[0]))
                reference_numbers.add(int(fields[7]))
            if len(reference_numbers) != 1:
                raise ValueError(
                    f"PDS family {family_id} has inconsistent reference numbers"
                )
            families.append(
                Family(
                    family_id=f"PDS2015-{family_id}",
                    family_name=family_name,
                    reference_number=reference_numbers.pop(),
                    reported_member_count=len(members),
                    catalog_source="NASA_PDS_2015_excluded_population",
                    population=population,
                    publication_code="P1",
                    members=tuple(sorted(members)),
                )
            )

    return families, {
        "url": PDS_URL,
        "bundle_urn": PDS_BUNDLE_URN,
        "doi": PDS_DOI,
        "archive_sha256": _sha256(archive_path),
        "retained_family_count": len(families),
        "retention_scope": "Hilda and Jupiter Trojan populations excluded by Proper25",
    }


def _primary_family(number: int, families: list[Family]) -> Family:
    namesakes = [
        family for family in families if family.reference_number == number
    ]
    candidates = namesakes or families
    return min(
        candidates,
        key=lambda family: (
            family.reported_member_count,
            family.family_id,
        ),
    )


def _catalog_rows(families: list[Family]) -> tuple[list[dict[str, object]], dict[str, int]]:
    by_number: dict[int, list[Family]] = defaultdict(list)
    for family in families:
        for number in family.members:
            by_number[number].append(family)

    rows: list[dict[str, object]] = []
    for number, memberships in by_number.items():
        primary = _primary_family(number, memberships)
        for family in sorted(
            memberships,
            key=lambda item: (
                item is not primary,
                item.reported_member_count,
                item.family_id,
            ),
        ):
            rows.append(
                {
                    "asteroid_number": number,
                    "family_name": family.family_name,
                    "family_id": family.family_id,
                    "catalog_source": family.catalog_source,
                    "population": family.population,
                    "reported_family_member_count": family.reported_member_count,
                    "is_primary": "true" if family is primary else "false",
                }
            )

    rows.sort(
        key=lambda row: (
            int(row["asteroid_number"]),
            row["is_primary"] != "true",
            int(row["reported_family_member_count"]),
            str(row["family_id"]),
        )
    )
    multiplicities = [len(memberships) for memberships in by_number.values()]
    counts = {
        "membership_row_count": len(rows),
        "unique_numbered_asteroid_count": len(by_number),
        "multi_membership_asteroid_count": sum(value > 1 for value in multiplicities),
        "maximum_memberships_per_asteroid": max(multiplicities),
    }
    return rows, counts


def build_catalog(
    proper25_root: Path,
    pds_archive: Path,
    output_csv: Path,
    output_metadata: Path,
) -> None:
    proper_families, proper_details = _proper25_families(proper25_root)
    legacy_families, pds_details = _pds_excluded_population_families(pds_archive)
    families = proper_families + legacy_families
    rows, counts = _catalog_rows(families)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=[
                "asteroid_number",
                "family_name",
                "family_id",
                "catalog_source",
                "population",
                "reported_family_member_count",
                "is_primary",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "schema_version": 1,
        "catalog_id": "Moira_asteroid_families_Proper25_2026_plus_PDS_exclusions",
        "number_system": "MPC_catalog_number",
        "membership_semantics": (
            "Many-to-many HCM catalog membership; overlaps and nested families "
            "are preserved."
        ),
        "primary_display_policy": {
            "purpose": "Compatibility display selection, not exclusive physical membership",
            "rules": [
                "Prefer a family whose reference asteroid is the queried number.",
                "Then prefer the smallest source-reported family membership.",
                "Break ties by stable family identifier.",
            ],
        },
        "family_aliases": FAMILY_ALIASES,
        "sources": {
            "proper25": proper_details,
            "pds_legacy_excluded_populations": pds_details,
        },
        "counts": {
            **counts,
            "family_count": len(families),
            "proper25_numbered_membership_row_count": sum(
                len(family.members) for family in proper_families
            ),
            "pds_legacy_membership_row_count": sum(
                len(family.members) for family in legacy_families
            ),
        },
        "csv_sha256": _sha256(output_csv),
    }
    output_metadata.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proper25-root", type=Path, required=True)
    parser.add_argument("--pds-archive", type=Path, required=True)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("moira/data/asteroid_families.csv"),
    )
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=Path("moira/data/asteroid_families.metadata.json"),
    )
    args = parser.parse_args()
    build_catalog(
        args.proper25_root,
        args.pds_archive,
        args.output_csv,
        args.output_metadata,
    )


if __name__ == "__main__":
    main()
