#!/usr/bin/env python
"""
Compare supported lunar NASA-compat canon methods against published modern
NASA Five Millennium catalog rows.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moira.eclipse import EclipseCalculator
from moira.eclipse_canon import LunarCanonValidationCase, compare_lunar_canon_methods


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "eclipse_nasa_reference.json"


def load_cases() -> tuple[LunarCanonValidationCase, ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(
        LunarCanonValidationCase(
            label=str(row["label"]),
            nasa_ut=float(row["ut_jd"]),
            nasa_gamma_earth_radii=float(row["gamma"]),
            eclipse_type=str(row["type"]),
        )
        for row in payload["lunar_modern_validation"]
    )


def main() -> None:
    calc = EclipseCalculator()
    comparisons = compare_lunar_canon_methods(calc, load_cases())

    for comparison in comparisons:
        print(comparison.method)
        print(f"  source_model: {comparison.source_model}")
        print(
            "  aggregate: "
            f"mean_timing={comparison.mean_timing_residual_seconds:.2f}s "
            f"max_timing={comparison.max_timing_residual_seconds:.2f}s "
            f"max_gamma={comparison.max_gamma_residual_earth_radii:.6f}"
        )
        for case in comparison.case_residuals:
            print(
                "  "
                f"{case.label}: "
                f"timing={case.timing_residual_seconds:+.2f}s "
                f"gamma={case.gamma_residual_earth_radii:+.6f}"
            )
        print()


if __name__ == "__main__":
    main()
