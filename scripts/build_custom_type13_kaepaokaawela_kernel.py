"""
Build and verify a standalone type-13 asteroid kernel from JPL Horizons.

Default target:
    514107 Ka`epaoka`awela (2015 BZ509)

The script writes:
    tests/artifacts/kernels/kaepaokaawela_type13_test.bsp
    tests/artifacts/kernels/kaepaokaawela_type13_test.metadata.json

The payload is fetched from the official JPL Horizons API and written through
Moira's own DAF/type-13 writer, then verified both at its written nodes and
at an off-node epoch against an independently fetched Horizons vector — see
scripts/_type13_kernel_common.py for the shared fetch/parse/verify logic
this and build_custom_type13_aylochaxnim_kernel.py both use.

Sampling note:
    Ka`epaoka`awela is a retrograde 1:-1 co-orbital of Jupiter (period ~11.65
    years) — angular motion is slow relative to its orbital period, so a 5-day
    step gives ample margin for the Hermite interpolation between nodes.

Important unit law:
    Horizons VECTORS with ``OUT_UNITS=KM-S`` yields positions in km and
    velocities in km/s. Moira's type-13 Hermite path is seconds-based, so the
    written velocity samples must remain in km/s.
"""

from __future__ import annotations

import json
from pathlib import Path

from _type13_kernel_common import build_and_verify

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tests" / "artifacts" / "kernels"
OUTPUT_BSP = OUTPUT_DIR / "kaepaokaawela_type13_test.bsp"
OUTPUT_META = OUTPUT_DIR / "kaepaokaawela_type13_test.metadata.json"

TARGET = {
    "name": "Kaepaokaawela",
    "naif_id": 2514107,
    "command": "514107;",
    "center": 10,
    "frame": 1,
}


def main() -> None:
    payload = build_and_verify(TARGET, OUTPUT_BSP, OUTPUT_META, step_days=5, root=ROOT)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
