"""Offline tests for IERS sync: mirror failover, validation, and no silent substitution."""
import datetime

import pytest

from moira.tools import iers_sync as sync

TODAY = datetime.date(2026, 10, 30)
_MJD0 = 41684
_N = 20100  # reaches beyond TODAY (MJD 61343)


def _dut1(i: int) -> float:
    return round(0.8 - 0.00003 * i, 7)


def _csv() -> str:
    lines = ["Year;Month;Day;MJD;x_pole;y_pole;UT1-UTC"]
    for i in range(_N):
        lines.append(f"1973;1;1;{_MJD0 + i};0.120733;0.136966;{_dut1(i)}")
    return "\n".join(lines)


def _fixed() -> str:
    return "\n".join(
        f"73 1 1 {_MJD0 + i:8.2f}  I{0.120733:9.6f}{0.0001:9.6f} {0.136966:9.6f}{0.0001:9.6f}  I{_dut1(i):10.7f}"
        for i in range(_N)
    )


_LEAP_IERS = "41317.0    1  1 1972       10\n41499.0    7  1 1972       11\n"
_LEAP_NTP = "2272060800\t10\t# 1 Jan 1972\n2287785600\t11\t# 1 Jul 1972\n"


def _fetcher(payloads: dict[str, str]):
    def fetch(url: str) -> str:
        if url not in payloads:
            raise OSError(f"unreachable: {url}")
        return payloads[url]
    return fetch


def test_csv_and_fixed_width_parse_identically() -> None:
    a = sync.parse_finals(_csv(), today=TODAY)
    b = sync.parse_finals(_fixed(), today=TODAY)
    assert [(r.mjd, float(r.x_pole), float(r.y_pole), float(r.dut1)) for r in a] == [
        (r.mjd, float(r.x_pole), float(r.y_pole), float(r.dut1)) for r in b
    ]


def test_leap_formats_agree() -> None:
    assert sync.parse_leap_seconds(_LEAP_IERS) == pytest.approx(sync.parse_leap_seconds(_LEAP_NTP))


def test_primary_failure_uses_labelled_fallback() -> None:
    fetch = _fetcher({
        sync.LEAP_SOURCES[0]: _LEAP_IERS,
        sync.FINALS_SOURCES[1]: _fixed(),
    })
    out = sync.sync_all(fetch, today=TODAY, write=False)
    eop = out[sync._EOP_DATA_TXT]
    assert f"# Source: {sync.FINALS_SOURCES[1]}" in eop
    assert "# Source status: fallback; sha256 " in eop
    assert "primary" in out[sync._LEAP_SECONDS_PY]


def test_all_sources_failing_raises_instead_of_substituting() -> None:
    with pytest.raises(sync.SyncError):
        sync.sync_all(_fetcher({}), today=TODAY, write=False)


def test_stale_primary_falls_through_to_fresh_mirror() -> None:
    stale = "\n".join(_csv().splitlines()[:11000])
    fetch = _fetcher({
        sync.LEAP_SOURCES[0]: _LEAP_IERS,
        sync.FINALS_SOURCES[0]: stale,
        sync.FINALS_SOURCES[1]: _fixed(),
    })
    out = sync.sync_all(fetch, today=TODAY, write=False)
    assert "fallback" in out[sync._EOP_DATA_TXT]


@pytest.mark.parametrize("bad", ["dut1_out_of_range", "non_monotonic", "too_short"])
def test_invalid_payloads_are_rejected(bad: str) -> None:
    lines = _csv().splitlines()
    if bad == "dut1_out_of_range":
        lines[5] = "1973;1;1;41688;0.1;0.1;3600.5"
    elif bad == "non_monotonic":
        lines[5] = lines[4]
    else:
        lines = lines[:50]
    with pytest.raises(ValueError):
        sync.parse_finals("\n".join(lines), today=TODAY)


def test_loader_accepts_rendered_output(tmp_path, monkeypatch) -> None:
    from moira.julian import EOPRegistry

    src = sync.Fetched("x", "u", "0" * 64, "primary")
    rendered = sync.render_eop_dut1(sync.parse_finals(_csv(), today=TODAY), src)
    path = tmp_path / "iers_eop.txt"
    path.write_text(rendered, encoding="utf-8")
    monkeypatch.setattr(EOPRegistry, "_path", path)
    monkeypatch.setattr(EOPRegistry, "_data", None)
    EOPRegistry._load()
    assert len(EOPRegistry._data) == _N
