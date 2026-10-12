"""Read-only adapters to the public Gochara snapshot and catalogue engine."""
from moira.gochara import (
    GocharaPolicy, GocharaResult, gochara_from_positions,
    gochara_subsystem_profile, gochara_doctrine_options,
)
from moira.ashtakavarga import BhinnashtakavargaResult
from moira import Moira
from moira.gochara_dated import GocharaDatePolicy, GocharaBirthLocation, GocharaDateResult
from ..models.gochara_dated import GocharaEpochRequest, GocharaDatetimeRequest
from ..models.gochara import (
    GocharaSnapshotRequest, GocharaResultResponse, GocharaSubsystemProfileResponse,
    GocharaDoctrineOptionsResponse, GocharaDoctrineOptionResponse, GocharaTopic,
)
from ..serializers.gochara import serialize_gochara_result, serialize_gochara_profile


def compute_gochara_date(engine: Moira, request: GocharaEpochRequest | GocharaDatetimeRequest) -> GocharaDateResult:
    """Use the startup engine; caller-provided BAV is outside the dated contract."""
    policy = GocharaDatePolicy(
        request.policy.ayanamsa_system, request.policy.natal_bav_mode,
        GocharaPolicy(**request.policy.gochara_policy.model_dump()),
    )
    location = (GocharaBirthLocation(**request.birth_location.model_dump())
                if request.birth_location is not None else None)
    if isinstance(request, GocharaDatetimeRequest):
        return engine.gochara_for_datetimes(request.natal_dt, request.transit_dt,
                                          policy=policy, birth_location=location)
    return engine.gochara_at(request.natal_jd_ut1, request.transit_jd_ut1,
                            policy=policy, birth_location=location)


def compute_gochara_windows(engine, request):
    """Validated epochs are already converted once by the shared time owner."""
    from ..models.gochara_windows import GocharaWindowDatetimeRequest
    from moira.gochara_windows import _civil_receipt
    result = engine.gochara_windows(*request._epochs, **request.engine_options())
    if isinstance(request, GocharaWindowDatetimeRequest):
        result = _civil_receipt(result, (request.natal_dt, request.start_dt, request.end_dt))
    return result


def compute_gochara_snapshot(request: GocharaSnapshotRequest) -> GocharaResult:
    """Bind supplied positions and raw BAV without deriving astronomy."""
    bhinna = None if request.raw_bav is None else {
        planet: BhinnashtakavargaResult(planet, counts, sum(counts))
        for planet, counts in request.raw_bav.items()
    }
    return gochara_from_positions(
        request.natal_moon_sidereal_longitude, request.transit_sidereal_longitudes,
        bhinna=bhinna, policy=GocharaPolicy(**request.policy.model_dump()),
    )


def evaluate_gochara(request: GocharaSnapshotRequest) -> GocharaResultResponse:
    return serialize_gochara_result(compute_gochara_snapshot(request))


def profile_gochara(request: GocharaSnapshotRequest) -> GocharaSubsystemProfileResponse:
    return serialize_gochara_profile(gochara_subsystem_profile(compute_gochara_snapshot(request)))


def inspect_gochara_doctrine(topic: GocharaTopic | None = None) -> GocharaDoctrineOptionsResponse:
    return GocharaDoctrineOptionsResponse(options=tuple(
        GocharaDoctrineOptionResponse.model_validate(option)
        for option in gochara_doctrine_options(topic)
    ))
