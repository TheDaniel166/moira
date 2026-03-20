from __future__ import annotations

from pathlib import Path

from moira.houses import calculate_houses
from scripts.compare_swetest import PASS_THRESHOLD, _angular_diff, _parse_iterations


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def test_house_systems_match_offline_swiss_reference() -> None:
    """
    Validate all Swiss-mapped house systems against the cached offline fixture.

    This keeps the external-reference house validation inside pytest instead of
    leaving it only in the standalone comparison script.
    """
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    iterations = _parse_iterations(fixture_text)

    failures: list[str] = []
    for it in iterations:
        result = calculate_houses(it["jd_ut"], it["lat"], it["lon"], it["hsys"])
        diffs = [_angular_diff(result.cusps[i], it["cusps"][i]) for i in range(12)]
        max_diff = max(diffs)
        if max_diff > PASS_THRESHOLD:
            failures.append(
                f"jd={it['jd_ut']:.6f} sys={it['hsys']} lat={it['lat']:.2f} "
                f"lon={it['lon']:.2f} max_diff={max_diff:.6f}"
            )

    assert not failures, "House validation mismatches:\n" + "\n".join(failures[:20])
