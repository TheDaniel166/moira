from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.eclipse import LocalContactCircumstances
import moira_server.serializers.phenomena as serializers


def test_local_contact_serializer_converts_ut1_back_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    expected = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    contact = LocalContactCircumstances(
        jd_ut=100.25,
        azimuth=180.0,
        altitude=30.0,
        visible=True,
    )

    # The serializer hands the UT1 value to the leap-second-aware UT1 -> UTC helper; it never
    # decodes a UT1 Julian Day as if it were already UTC.
    monkeypatch.setattr(
        serializers,
        "utc_datetime_from_ut1",
        lambda jd: received.append(jd) or expected,
    )

    response = serializers.serialize_local_contact(contact)

    assert response.datetime_utc == expected.isoformat()
    assert received == [100.25]
