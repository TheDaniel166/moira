"""Prepare version 1 Moira satellite-only SPKs from the pinned JPL sources.

CSPICE is required by this offline tool. The moon module reads the outputs
through Moira's native reader.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract(spice, source, output, allowed):
    source_handle = spice.dafopr(str(source))
    output_handle = spice.spkopn(str(output), "Moira Planetary Moons v1", 0)
    copied = set()
    try:
        spice.dafbfs(source_handle)
        while spice.daffna():
            descriptor = spice.dafgs(5)
            bounds, integers = spice.dafus(descriptor, 2, 6)
            target, center, frame, data_type = map(int, integers[:4])
            if (center, target) not in allowed:
                continue
            if frame != 1 or data_type not in (2, 3):
                raise ValueError(f"Unsupported segment for {center} to {target}")
            spice.spksub(source_handle, descriptor, spice.dafgn(),
                         float(bounds[0]), float(bounds[1]), output_handle)
            spice.dafcs(source_handle)
            copied.add((center, target))
        if copied != allowed:
            raise ValueError(f"Missing required pairs {sorted(allowed - copied)}")
    finally:
        spice.spkcls(output_handle)
        spice.dafcls(source_handle)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from moira._planetary_moon_data import (
        NAIF_SATELLITES, PCK_SHA256, PCK_URL, RADII_URL, SYSTEMS,
        segment_pairs, segment_receipt,
    )
    from moira.spk_reader import SpkReader
    import spiceypy as spice

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jup365", type=Path)
    parser.add_argument("--sat441", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="A new directory")
    args = parser.parse_args()
    sources = dict(zip((system.name for system in SYSTEMS), (args.jup365, args.sat441)))
    if not any(sources.values()):
        parser.error("Provide --jup365, --sat441, or both")
    destination = args.output.resolve()
    if destination.exists():
        parser.error(f"Output directory already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".moira-moons-") as scratch:
        stage = Path(scratch) / "data"
        stage.mkdir()
        records = {}
        for system in SYSTEMS:
            source = sources[system.name]
            if source is None:
                continue
            if _sha256(source) != system.source_sha256:
                raise ValueError(f"Source does not match the pinned {system.source}")
            name = f"{Path(system.source).stem}-moons.bsp"
            _extract(spice, source.resolve(), stage / name, segment_pairs(system))
            with SpkReader(stage / name) as reader:
                records[system.name] = {
                    "source_url": NAIF_SATELLITES + system.source,
                    "source_sha256": system.source_sha256,
                    "filename": name,
                    "sha256": reader._source_identity.sha256,
                    "bytes": reader._source_identity.byte_length,
                    "segments": segment_receipt(reader._kernel.catalog),
                }
        manifest = {
            "schema": 1,
            "frame": "ICRF",
            "epoch": "TDB seconds past J2000",
            "pck_source": PCK_URL,
            "pck_sha256": PCK_SHA256,
            "moon_radii_source": RADII_URL,
            "source_terms": "https://naif.jpl.nasa.gov/naif/rules.html",
            "systems": records,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    print(destination / "manifest.json")


if __name__ == "__main__":
    main()
