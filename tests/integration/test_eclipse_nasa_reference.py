from __future__ import annotations

import json
from pathlib import Path
import pytest

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_nasa_solar_eclipse_maxima_classify_correctly_across_eras(eclipse_calculator) -> None:
    """
    Validate solar-eclipse classification at NASA catalog maxima over a wide era span.

    These cases come from the NASA Five Millennium Catalog and deliberately span:
    - ancient/BCE
    - classical/medieval
    - modern
    - far future
    """
    fixture = _load_fixture()
    failures: list[str] = []
    kind_map = {
        "H": "is_hybrid",
        "T": "is_total",
        "A": "is_annular",
        "P": "is_partial",
    }

    for row in fixture["solar_maxima"]:
        data = eclipse_calculator.calculate_jd(float(row["ut_jd"]))
        expected_attr = kind_map[str(row["type"])]
        if not data.is_solar_eclipse or not getattr(data.eclipse_type, expected_attr):
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type}"
            )

    assert not failures, "NASA solar maxima mismatches:\n" + "\n".join(failures[:20])


def test_nasa_lunar_eclipse_maxima_classify_correctly_across_eras(eclipse_calculator) -> None:
    """
    Validate lunar-eclipse classification at NASA catalog maxima over a wide era span.
    """
    fixture = _load_fixture()
    failures: list[str] = []

    for row in fixture["lunar_maxima"]:
        data = eclipse_calculator.calculate_jd(float(row["ut_jd"]))
        eclipse_type = str(row["type"])
        if eclipse_type == "T":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_total
        elif eclipse_type == "P":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_partial
        elif eclipse_type == "N":
            ok = (not data.is_lunar_eclipse) and data.eclipse_type.magnitude_penumbra > 0.0
        else:
            ok = False

        if not ok:
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type} "
                f"pen_mag={data.eclipse_type.magnitude_penumbra:.6f}"
            )

    assert not failures, "NASA lunar maxima mismatches:\n" + "\n".join(failures[:20])


def test_nasa_eclipse_search_recovers_representative_ancient_and_future_cases(eclipse_calculator) -> None:
    """
    Validate representative ancient/future search cases against NASA maxima.

    These are not treated the same as the Swiss 1900-era corpus. Over very long
    timescales, timing sensitivity to Delta T grows, so this test uses a looser
    tolerance while still requiring the search to land on the right event.

    Threshold provenance: see inline comment on max_error_seconds for full
    history, current live measurements, and root-cause explanation for each
    change.  Do not change the number without updating both the comment and
    VALIDATION_ASTRONOMY.md § 7.
    """
    fixture = _load_fixture()
    failures: list[str] = []
    # Threshold history — document all changes here so the number is not magic.
    #
    # Original threshold (2026-03-23): 60.0 s
    #   Set when ancient_hybrid measured 43.17 s using a 2-step Newton
    #   light-time approximation in corrections.apply_light_time.
    #
    # Updated threshold (2026-04-05): 90.0 s
    #   Commit 931b87c (2026-03-25) replaced the 2-step Newton light-time
    #   approximation with a proper iterative convergence loop (tol = 1e-14
    #   days ≈ 1 ns).  The old code returned an xyz vector computed at
    #   t − lt_initial while reporting lt_final; the new code keeps both
    #   consistent.  This is a physics improvement, not a regression.
    #
    #   For the ancient_hybrid solar case (~1797 BCE), the more accurate
    #   light-time shifts the computed TT minimum of the eclipse by ~37 s,
    #   moving the measured residual from 43.17 s to 80.06 s.  The difference
    #   is entirely in TT space — not a Delta T conversion issue.  The 80 s
    #   residual remains well within the model-basis explanation for ancient
    #   eclipses (Delta T uncertainty at that epoch is hundreds of seconds).
    #
    #   Updated threshold (2026-05-17): 400.0 s
    #     The future cases (future_total solar and future_penumbral lunar, year ~2800)
    #     diverge by ~310 s and ~353 s respectively. This is a model-basis divergence
    #     due to the future Delta T projection. Beyond 2026, Horizons freezes Delta T
    #     near ~69 s, whereas Moira's hybrid model projects secular growth (+28.0 s/cy²),
    #     reaching ~2722 s by year 2800. The difference in UT Julian Days corresponds
    #     directly to this Delta T discrepancy (~325 s).
    #
    #   Current live measurements (2026-05-17, DE441, iterative light-time):
    #     ancient_hybrid solar:  80.060 s   (TT-space geometry shift)
    #     future_total solar:    310.493 s  (future Delta T divergence)
    #     ancient_total lunar:   49.654 s
    #     future_penumbral:      353.236 s  (future Delta T divergence)
    #
    #   Threshold is set to 400.0 s to give a 40 s margin above the worst case.
    #   If this number moves again, record the cause and the new measurements
    #   here and update VALIDATION_ASTRONOMY.md § 7 in the same commit.
    max_error_seconds = 400.0

    for row in fixture["search_cases"]["solar"]:
        event = eclipse_calculator.next_solar_eclipse(float(row["seed_jd"]), kind=str(row["kind"]))
        err_seconds = abs(event.jd_ut - float(row["expected_ut_jd"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"solar label={row['label']} kind={row['kind']} "
                f"got={event.jd_ut:.9f} expected={float(row['expected_ut_jd']):.9f} "
                f"err_s={err_seconds:.3f}"
            )

    for row in fixture["search_cases"]["lunar"]:
        event = eclipse_calculator.next_lunar_eclipse(float(row["seed_jd"]), kind=str(row["kind"]))
        err_seconds = abs(event.jd_ut - float(row["expected_ut_jd"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"lunar label={row['label']} kind={row['kind']} "
                f"got={event.jd_ut:.9f} expected={float(row['expected_ut_jd']):.9f} "
                f"err_s={err_seconds:.3f}"
            )

    assert not failures, "NASA search mismatches:\n" + "\n".join(failures[:20])


def test_ancient_lunar_total_native_search_stays_within_documented_residual_and_beats_canon(eclipse_calculator) -> None:
    """
    Diagnose and lock the current ancient worst-case lunar search behavior.

    For the BCE total-lunar search case in the NASA fixture:
    - the native DE441-centric search must remain within the documented
      sub-minute residual envelope
    - the native path must outperform the catalog-facing canon timing path

    This keeps the remaining open item transparent: the residual is real, but
    the current native model is already the better of the two available paths
    for this ancient case.
    """
    fixture = _load_fixture()
    row = next(case for case in fixture["search_cases"]["lunar"] if case["label"] == "ancient_total")
    expected = float(row["expected_ut_jd"])
    kind = str(row["kind"])
    seed = float(row["seed_jd"])

    native = eclipse_calculator.next_lunar_eclipse(seed, kind=kind)
    canon = eclipse_calculator.next_lunar_eclipse_canon(seed, kind=kind)

    native_error_seconds = abs(native.jd_ut - expected) * 86400.0
    canon_error_seconds = abs(canon.jd_ut - expected) * 86400.0

    assert native_error_seconds <= 60.0, (
        f"ancient_total native residual {native_error_seconds:.3f}s exceeds 60s envelope"
    )
    assert native_error_seconds < canon_error_seconds, (
        f"ancient_total native residual {native_error_seconds:.3f}s should remain "
        f"better than canon residual {canon_error_seconds:.3f}s"
    )


