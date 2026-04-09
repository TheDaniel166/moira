from __future__ import annotations

from pathlib import Path

from moira.houses import calculate_houses
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from scripts.compare_swetest import PASS_THRESHOLD, _angular_diff, _parse_iterations


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def _polar_iterations() -> list[dict]:
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    iterations = _parse_iterations(fixture_text)
    return [
        it
        for it in iterations
        if abs(it["lat"]) >= 90.0 - true_obliquity(ut_to_tt(it["jd_ut"]))
    ]


def test_supported_polar_house_systems_match_offline_swiss_reference() -> None:
    """
    Validate supra-critical latitude house figures against the cached Swiss fixture.

    This slice exercises only the systems that remain defined at extreme latitudes
    in the external oracle. Fallback doctrine for unsupported semi-arc systems is
    proved separately in the dedicated polar-house gauntlets.
    """
    iterations = _polar_iterations()
    assert iterations, "Expected polar house cases in the cached Swiss fixture"

    failures: list[str] = []
    for it in iterations:
        result = calculate_houses(it["jd_ut"], it["lat"], it["lon"], it["hsys"])
        diffs = [_angular_diff(result.cusps[i], it["cusps"][i]) for i in range(12)]
        max_diff = max(diffs)
        if max_diff > PASS_THRESHOLD:
            failures.append(
                f"jd={it['jd_ut']:.6f} sys={it['hsys']} lat={it['lat']:.1f} "
                f"lon={it['lon']:.1f} max_diff={max_diff:.6f}"
            )

    assert not failures, "Polar Swiss house mismatches:\n" + "\n".join(failures[:20])
