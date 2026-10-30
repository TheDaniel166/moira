"""Packaged EOP loader must carry |UT1-UTC| up to the continuous-UTC bound (3600 s) unclipped."""
import pytest

from moira import julian as julian_module
from moira.julian import EOPRegistry, utc_to_ut1

_MJD = 61400


def _load_table(tmp_path, monkeypatch, dut1: float) -> None:
    path = tmp_path / "iers_eop.txt"
    path.write_text(
        "# test\n" + "".join(f"{_MJD + i} {dut1!r}\n" for i in range(6)), encoding="utf-8"
    )
    monkeypatch.setattr(EOPRegistry, "_path", path)
    monkeypatch.setattr(EOPRegistry, "_data", None)
    EOPRegistry._load()


@pytest.mark.parametrize("dut1", [1.0, -1.0, 100.0, -100.0, 3600.0, -3600.0])
def test_large_dut1_is_admitted_without_clipping(tmp_path, monkeypatch, dut1) -> None:
    _load_table(tmp_path, monkeypatch, dut1)
    jd_utc = _MJD + 2400000.5 + 2.37
    assert EOPRegistry.get_dut1(jd_utc) == pytest.approx(dut1, abs=1e-6)
    assert utc_to_ut1(jd_utc) - jd_utc == pytest.approx(dut1 / 86400.0, abs=1e-9)


@pytest.mark.parametrize("dut1", [3600.5, -3600.5, float("inf"), float("nan")])
def test_dut1_beyond_bound_or_nonfinite_is_rejected(tmp_path, monkeypatch, dut1) -> None:
    with pytest.raises(ValueError, match="DUT1 must be finite"):
        _load_table(tmp_path, monkeypatch, dut1)


def test_bound_is_the_adopted_continuous_utc_value() -> None:
    assert julian_module._MAX_ABS_DUT1_SECONDS == 3600.0
