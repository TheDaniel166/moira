"""Missing small-body data is translated without masking unrelated failures."""

from types import SimpleNamespace

import pytest

from moira.small_body_identity import resolve_small_body_identity
from moira_server.models.transits import NatalAspectSearchRequest
from moira_server.services.transits import compute_natal_aspect_transits


def _request(body):
    return NatalAspectSearchRequest(
        body=body, natal_longitudes=[10.0], aspect_angles=[0.0],
        jd_start=2451545.0, jd_end=2451555.0,
    )


def _failing_engine(error):
    def search(*args, **kwargs):
        raise error
    return SimpleNamespace(natal_aspect_transits=search)


@pytest.mark.parametrize("body", ["Ceres", "Pallas", "Vesta"])
def test_missing_mover_segment_reports_required_small_body_resource(body):
    identity = resolve_small_body_identity(body)
    error = KeyError(f"No segment found for target={identity.naif_id}, center=10")
    with pytest.raises(ValueError, match="small-body kernel covering") as caught:
        compute_natal_aspect_transits(_failing_engine(error), _request(body))
    assert identity.qualified_name in str(caught.value)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("Ceres", "unrelated internal lookup"),
        ("Ceres", "No segment found for target=10, center=0"),
        ("Ceres", "No segment found for target=20000010, center=10"),
        ("Jupiter", "No segment found for target=5, center=0"),
    ],
)
def test_unrelated_key_errors_remain_identical(body, message):
    error = KeyError(message)
    with pytest.raises(KeyError) as caught:
        compute_natal_aspect_transits(_failing_engine(error), _request(body))
    assert caught.value is error


@pytest.mark.parametrize("body", ["asteroid:Ceres", "comet:Halley"])
def test_resource_error_translation_does_not_expand_mover_admission(body):
    with pytest.raises(ValueError, match="unsupported natal-aspect mover"):
        compute_natal_aspect_transits(_failing_engine(AssertionError("must not search")), _request(body))
