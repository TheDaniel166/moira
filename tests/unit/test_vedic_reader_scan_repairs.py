"""VA-09/10: borrowed-reader scope and work-bounded finite progress."""

import pytest
from moira.sade_sati import sade_sati_windows, SadeSatiBudgetError
from moira.upagrahas import kalavela_upagrahas
from moira.spk_reader import use_reader_override, get_active_reader


@pytest.mark.parametrize(
    "step", [0.0, -1.0, 1e-300, float("nan"), float("inf"), True, 6.0]
)
def test_bad_steps_fail_before_ephemeris(monkeypatch, step):
    def forbidden(*a):
        pytest.fail("invalid scan reached ephemeris")

    monkeypatch.setattr("moira.sade_sati._saturn_sidereal_sign", forbidden)
    with pytest.raises(ValueError):
        sade_sati_windows(0.0, 2451545.0, 2451546.0, scan_step_days=step)


def test_preflight_and_runtime_budgets(monkeypatch):
    calls = []

    def sample(jd, *args):
        calls.append(jd)
        return 0 if jd < 2451547.5 else 1

    monkeypatch.setattr("moira.sade_sati._saturn_sidereal_sign", sample)
    with pytest.raises(SadeSatiBudgetError) as exc:
        sade_sati_windows(0.0, 2451545.0, 2451645.0, max_evaluations=2)
    assert exc.value.stage == "preflight" and not calls
    with pytest.raises(SadeSatiBudgetError) as exc:
        sade_sati_windows(0.0, 2451545.0, 2451550.0, max_evaluations=3)
    assert exc.value.evaluations == 3 and len(calls) == 3
    calls.clear()
    result = sade_sati_windows(0.0, 2451545.0, 2451550.0, max_evaluations=100)
    assert result.evaluations == len(calls) < 100
    assert result.windows[0].end_jd == pytest.approx(2451547.5, abs=0.001)


@pytest.mark.parametrize("fail", [False, True])
def test_kalavela_entire_composition_binds_and_restores(monkeypatch, fail):
    outer, borrowed = object(), object()
    observed = []

    def frame(*args):
        observed.append(get_active_reader())
        return (2451544.75, 2451545.25, 2451545.75)

    def asc(*args):
        observed.append(get_active_reader())
        if fail:
            raise RuntimeError("injected angle failure")
        return (10.0, 34.0)

    monkeypatch.setattr("moira.upagrahas._solar_frame", frame)
    monkeypatch.setattr("moira.upagrahas._ascendant_at", asc)
    with use_reader_override(outer):
        if fail:
            with pytest.raises(RuntimeError, match="injected"):
                kalavela_upagrahas(2451545.0, 28.6, 77.2, reader=borrowed)
        else:
            kalavela_upagrahas(2451545.0, 28.6, 77.2, reader=borrowed)
        assert get_active_reader() is outer
    assert observed and all(r is borrowed for r in observed)


@pytest.mark.parametrize(
    "start,end,step",
    [
        (True, 2.0, 1.0),
        (0.0, float("inf"), 1.0),
        (0.0, 10**1000, 1.0),
        (0.0, 1.0, 10**1000),
        (0.0, 1.0, "1"),
        (1.0, 1.0, 1.0),
        (1.0, 0.0, 1.0),
    ],
)
def test_range_and_overflow_reject_without_ephemeris(monkeypatch, start, end, step):
    monkeypatch.setattr(
        "moira.sade_sati._saturn_sidereal_sign",
        lambda *a: pytest.fail("unexpected ephemeris"),
    )
    with pytest.raises(ValueError):
        sade_sati_windows(0.0, start, end, scan_step_days=step)
