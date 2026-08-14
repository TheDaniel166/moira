import pytest

from moira.asteroids import asteroid_at
from moira._wheel_asteroid_catalog import EPHEMERIDES_URL, FULL_CATALOG_VERSION


def test_known_catalog_miss_names_full_archive(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise KeyError("No segment found for center=0, target=2307261")

    # asteroid_at builds Earth state before the apparent-vector call; a bare
    # object() has no SPK surface. Stub only that reader method so the miss
    # path under test is the KeyError from the monkeypatched vector call.
    class _StubReader:
        def position_and_velocity(self, *args, **kwargs):
            zero = (0.0, 0.0, 0.0)
            return zero, zero

    monkeypatch.setattr("moira.asteroids._asteroid_apparent_equatorial_vector", boom)
    with pytest.raises(KeyError, match=FULL_CATALOG_VERSION) as captured:
        asteroid_at("Mani", 2448058.0, reader=_StubReader())
    text = str(captured.value)
    assert EPHEMERIDES_URL in text
    assert "centaurs.bsp" not in text
    assert "2307261" in text or "Mani" in text
