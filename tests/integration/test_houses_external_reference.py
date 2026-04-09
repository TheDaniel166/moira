from __future__ import annotations

from pathlib import Path

from moira.houses import calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from scripts.compare_swetest import (
    PASS_THRESHOLD,
    _angular_diff,
    _parse_armc_iterations,
    _parse_iterations,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def test_house_systems_match_offline_swiss_reference() -> None:
    """
    Validate all Swiss-mapped house systems against the cached offline fixture.

    Covers standard (JD + lat/lon) iterations from the Swiss setest/t.exp corpus,
    including iflag=0 blocks (swe_houses_ex with no special mode), which produce
    degree output identical to the no-flag swe_houses() blocks.
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


def test_house_systems_match_armc_direct_swiss_reference() -> None:
    """
    Validate houses_from_armc() against the Swiss setest/t.exp ARMC-direct corpus.

    These blocks exercise Swiss swe_houses_armc(): the ARMC is provided directly
    from the fixture (degrees) rather than derived from JD + geographic longitude.
    Obliquity is computed independently from JD_UT using Moira's own pipeline.

    5376 iterations across the full range of supported house systems.
    """
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    iterations = _parse_armc_iterations(fixture_text)

    failures: list[str] = []
    for it in iterations:
        jd_tt     = ut_to_tt(it["jd_ut"])
        obliquity = true_obliquity(jd_tt)
        result    = houses_from_armc(it["armc"], obliquity, it["lat"], it["hsys"])
        diffs     = [_angular_diff(result.cusps[i], it["cusps"][i]) for i in range(12)]
        max_diff  = max(diffs)
        if max_diff > PASS_THRESHOLD:
            failures.append(
                f"armc={it['armc']:.6f} sys={it['hsys']} lat={it['lat']:.2f} "
                f"lon={it['lon']:.2f} max_diff={max_diff:.6f}"
            )

    assert not failures, "ARMC-direct house validation mismatches:\n" + "\n".join(failures[:20])
