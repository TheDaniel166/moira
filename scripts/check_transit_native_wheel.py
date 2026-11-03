"""Exercise the installed transit fast path using a tiny synthetic SPK.

The linear Chebyshev states test execution and reuse, not astronomical accuracy.
No external kernel, optional package or network access is required. Release
wheels must execute the real compiled apparent evaluator, once per position,
without a full PlanetData/speed calculation or discarded geometric prepass.
"""
from __future__ import annotations

from collections import Counter
import gc
import math
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import moira
from moira import planets, transits, transits_aspects
from moira.constants import Body
from moira.spk_reader import SpkReader


JD = 2451545.0


def _write_synthetic_kernel(path: Path) -> None:
    """Write one valid type-2 record for every existing planetary route."""
    pairs = (
        (0, 10), (0, 3), (3, 399), (3, 301), (0, 1), (1, 199),
        (0, 2), (2, 299), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9),
    )
    half_span = 8.0 * 86400.0
    header = bytearray(5 * 1024)
    header[:8] = b"DAF/SPK "
    struct.pack_into("<ii", header, 8, 2, 6)
    header[16:76] = b"MOIRA SYNTHETIC TRANSIT TEST".ljust(60)
    header[88:96] = b"LTL-IEEE"
    struct.pack_into("<ddd", header, 3 * 1024, 0.0, 0.0, float(len(pairs)))
    words: list[float] = []
    for index, (center, target) in enumerate(pairs):
        if center:
            xyz = (380000.0, 30000.0, 10000.0) if target == 301 else (1000.0, 2000.0, 3000.0)
        else:
            angle = math.radians(23.0 * (index + 1))
            radius = 1.0e8 * (index + 1)
            xyz = (radius * math.cos(angle), radius * math.sin(angle), radius * 0.03)
        start = 641 + len(words)
        words.extend((0.0, half_span))
        for axis, value in enumerate(xyz):
            words.extend((value, 100000.0 * (axis + 1)))
        words.extend((-half_span, 2.0 * half_span, 8.0, 1.0))
        end = 640 + len(words)
        struct.pack_into("<ddiiiiii", header, 3 * 1024 + 24 + index * 40,
                         -half_span, half_span, target, center, 1, 2, start, end)
        offset = 4 * 1024 + index * 40
        header[offset:offset + 40] = b"MOIRA SYNTHETIC TRANSIT TEST".ljust(40)
    struct.pack_into("<iii", header, 76, 4, 4, 641 + len(words))
    payload = header + struct.pack(f"<{len(words)}d", *words)
    payload.extend(bytes(-len(payload) % 1024))
    path.write_bytes(payload)


def _check_reader(path: Path) -> None:
    with SpkReader(path) as reader:
        expected = {body: planets.planet_at(body, JD, reader=reader).longitude
                    for body in Body.ALL_PLANETS}
        evaluator = planets._get_native_planetary_evaluator(reader)
        assert evaluator is not None, "compiled planetary evaluator was not admitted"
        evaluations: list[float] = []

        class RecordedEvaluator:
            def evaluate_all_planets_apparent_geocentric_ecliptic(self, *args):
                evaluations.append(args[3])
                return evaluator.evaluate_all_planets_apparent_geocentric_ecliptic(*args)

        def reject_extra_work(*args, **kwargs):
            raise AssertionError("transit search performed unused scalar/rate/geometric work")

        canonical = transits_aspects._resolve_longitude
        samples: Counter[float] = Counter()

        def record_sample(body, jd, selected_reader):
            samples[jd] += 1
            return canonical(body, jd, selected_reader)

        with (
            patch.object(planets, "_get_native_planetary_evaluator", return_value=RecordedEvaluator()),
            patch.object(transits, "planet_at", side_effect=reject_extra_work),
            patch.object(transits_aspects, "_native_ecliptic_longitude_series", side_effect=reject_extra_work),
            patch.object(transits_aspects, "_native_small_body_series", side_effect=reject_extra_work),
            patch.object(transits_aspects, "_resolve_longitude", side_effect=record_sample),
        ):
            for body, longitude in expected.items():
                truth = transits._resolve_longitude_truth(body, JD, reader)
                assert abs((truth.longitude - longitude + 180.0) % 360.0 - 180.0) < 1e-12
            assert len(evaluations) == len(expected), "unused rate epochs were evaluated"
            events = transits_aspects.find_aspect_transits_to_longitudes(
                Body.MARS,
                [(expected[Body.MARS], 0.0, 0.01), (expected[Body.MARS] + 90.0, 0.0, 0.01)],
                JD - 1.0, JD + 1.0, step_days=0.25, reader=reader,
            )
        assert len(events) == 1 and abs(events[0].jd_exact - JD) < 1e-6
        assert max(samples.values()) == 1, "canonical positions were recomputed per target"
        assert len(evaluations) == len(expected) + len(samples), "unused position/rate work was performed"


def check_native_transit_path() -> None:
    """Reject lost native admission, unnecessary rates and duplicate samples."""
    with TemporaryDirectory(prefix="moira-transit-wheel-") as folder:
        path = Path(folder) / "linear.bsp"
        _write_synthetic_kernel(path)
        failure = None
        try:
            _check_reader(path)
        except Exception as exc:
            # Retaining a traceback also retains native mappings on Windows.
            failure = f"{type(exc).__name__}: {exc}"
        # Mock call histories can retain the reader until cyclic collection;
        # release those native mappings before Windows removes the test kernel.
        gc.collect()
        if failure is not None:
            raise AssertionError(failure)


if __name__ == "__main__":
    source_root = Path(__file__).resolve().parents[1]
    if "--allow-source-tree" not in sys.argv:
        assert source_root not in Path(moira.__file__).resolve().parents, "wheel check imported the source tree"
    check_native_transit_path()
    print(f"Moira {moira.__version__}: compiled transit path, position reuse and boundaries passed")
