"""
Build and verify a standalone type-13 asteroid kernel from JPL Horizons.

Default target:
    594913 'Aylo'chaxnim (2020 AV2)

The script writes:
    tests/artifacts/kernels/aylochaxnim_type13_test.bsp
    tests/artifacts/kernels/aylochaxnim_type13_test.metadata.json

The payload is fetched from the official JPL Horizons API and written through
Moira's own DAF/type-13 writer, then verified both at its written nodes and
at an off-node epoch against an independently fetched Horizons vector — see
scripts/_type13_kernel_common.py for the shared fetch/parse/verify logic
this and build_custom_type13_kaepaokaawela_kernel.py both use.

Sampling note:
    'Aylo'chaxnim is the first known Vatira (orbit entirely interior to
    Venus's, semi-major axis ~0.555 AU) — its orbital period is only ~151
    days, so a 5-day step keeps roughly 30 nodes per orbit for the Hermite
    interpolation, well above the 30-day step used for the slower Toutatis
    demo target.

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
OUTPUT_BSP = OUTPUT_DIR / "aylochaxnim_type13_test.bsp"
OUTPUT_META = OUTPUT_DIR / "aylochaxnim_type13_test.metadata.json"

TARGET = {
    "name": "Aylochaxnim",
    "naif_id": 2594913,
    "command": "594913;",
    "center": 10,
    "frame": 1,
}


def main() -> None:
    payload = build_and_verify(TARGET, OUTPUT_BSP, OUTPUT_META, step_days=5, root=ROOT)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
