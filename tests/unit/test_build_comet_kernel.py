from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from scripts import build_comet_kernel as builder


def test_horizons_command_uses_designation_search() -> None:
    assert builder._horizons_command("1P") == "'DES=1P;NOFRAG;CAP'"
    assert builder._horizons_command("67P") == "'DES=67P;NOFRAG;CAP'"


def test_fetch_vectors_uses_documented_comet_search(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = "\n".join(
        [
            "API VERSION: 1.2",
            "$$SOE",
            "2451545.0, A.D. 2000-Jan-01 00:00:00.0000, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0,",
            "$$EOE",
        ]
    )

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return raw.encode("utf-8")

    captured: dict[str, str] = {}

    def _fake_urlopen(url: str, timeout: int = 0):
        captured["url"] = url
        captured["timeout"] = str(timeout)
        return _Response()

    monkeypatch.setattr(builder.urllib.request, "urlopen", _fake_urlopen)

    epochs_jd, states = builder._fetch_vectors("1P", 2451545.0, 2451546.0, 1)

    parsed = urlparse(captured["url"])
    query = parse_qs(parsed.query)

    assert query["COMMAND"] == ["'DES=1P;NOFRAG;CAP'"]
    assert query["EPHEM_TYPE"] == ["VECTORS"]
    assert query["CENTER"] == ["500@10"]
    assert epochs_jd == [2451545.0]
    assert states == [[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]]