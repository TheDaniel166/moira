"""Stage 2 apsidal passage semantics on the admitted DE441 state surface."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import Body
from moira.orbits import (
    APSIDAL_ALGORITHM_VERSION,
    APSIDAL_ROOT_TOLERANCE_DAYS,
    ApsidalDirection,
    ApsidalPassageStatus,
    ApsidalPassages,
    OrbitalCenter,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalFrame,
    OrbitalInputError,
    OrbitalSearchError,
    OrbitShape,
    apsidal_passages,
    distance_extremes_at,
    osculating_elements,
)
from moira.phenomena import aphelion, perihelion
from moira.spk_reader import (
    KernelPool,
    OutOfRangeError,
    _EphemerisKernelIdentity,
    _KernelSourceIdentity,
    _RoutedState,
    _SpkSegmentReceipt,
)


_START_JD_UT1 = 2451513.5


@dataclass
class _AnalyticReader:
    label: str
    target_interval: tuple[float, float]
    offset_km: float = 0.0
    flat: bool = False
    velocity_multiplier: float = 1.0

    def __post_init__(self) -> None:
        self._source_identity = _KernelSourceIdentity(
            label=self.label,
            sha256=(self.label.encode().hex() + "0" * 64)[:64],
            byte_length=1,
            planetary_ephemeris="DE441",
        )
        self._kernel_identity = _EphemerisKernelIdentity(
            summary_label="DE-0441LE-0441",
            planetary_ephemeris="DE441",
            lunar_ephemeris="LE441",
            lunar_tidal_acceleration_arcsec_per_cy2=-25.936,
        )
        self._clock_pairs = ((0, 3), (3, 399), (3, 301), (0, 10))

    def _coverage_pairs_tdb(self):
        return (*self._clock_pairs, (10, 199))

    def coverage_intervals_tdb(self, center: int, target: int):
        pair = (center, target)
        if pair in self._clock_pairs:
            return ((2_400_000.0, 2_500_000.0),)
        if pair == (10, 199):
            return (self.target_interval,)
        return ()

    def has_segment_at_tdb(self, center: int, target: int, epoch_tdb: float):
        return any(
            start <= epoch_tdb <= end
            for start, end in self.coverage_intervals_tdb(center, target)
        )

    def position_and_velocity_tdb_with_receipt(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
        *,
        pool_index: int = 0,
    ):
        intervals = self.coverage_intervals_tdb(center, target)
        interval = next(
            (
                pair
                for pair in intervals
                if pair[0] <= epoch_tdb <= pair[1]
            ),
            None,
        )
        if interval is None:
            raise OutOfRangeError("outside analytic coverage", True)
        if (center, target) == (10, 199):
            if self.flat:
                position = (1_000_000.0 + self.offset_km, 0.0, 0.0)
                velocity = (0.0, 1_000.0, 0.0)
            else:
                phase = 2.0 * math.pi * (epoch_tdb - 2_451_545.0) / 20.0
                angular_rate = 2.0 * math.pi / 20.0
                position = (
                    1_000_000.0 * math.cos(phase) + self.offset_km,
                    700_000.0 * math.sin(phase),
                    0.0,
                )
                velocity = (
                    -1_000_000.0
                    * angular_rate
                    * math.sin(phase)
                    * self.velocity_multiplier,
                    700_000.0
                    * angular_rate
                    * math.cos(phase)
                    * self.velocity_multiplier,
                    0.0,
                )
        else:
            position = (0.0, 0.0, 0.0)
            velocity = (0.0, 0.0, 0.0)
        receipt = _SpkSegmentReceipt(
            center=center,
            target=target,
            data_type=2,
            coverage_start_tdb=interval[0],
            coverage_end_tdb=interval[1],
            source=self._source_identity,
            pool_index=pool_index,
        )
        return _RoutedState(
            position_km=position,
            velocity_km_per_day=velocity,
            epoch_tdb=epoch_tdb,
            legs=(receipt,),
            covered_intervals_tdb=(interval,),
        )

    def close(self) -> None:
        pass


@pytest.fixture(scope="module")
def earth_next(planetary_reader):
    return apsidal_passages(
        Body.EARTH,
        _START_JD_UT1,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=planetary_reader,
    )


@pytest.mark.requires_ephemeris
def test_next_earth_passages_are_typed_two_sided_events(earth_next) -> None:
    assert isinstance(earth_next, ApsidalPassages)
    assert earth_next.pericenter.status is ApsidalPassageStatus.FOUND
    assert earth_next.apocenter.status is ApsidalPassageStatus.FOUND
    assert earth_next.pericenter.epoch_tdb < earth_next.apocenter.epoch_tdb
    assert earth_next.pericenter.distance_au == pytest.approx(0.9833, abs=0.003)
    assert earth_next.apocenter.distance_au == pytest.approx(1.0167, abs=0.003)
    for outcome in (earth_next.pericenter, earth_next.apocenter):
        assert outcome.epoch_tdb is not None
        assert outcome.epoch_tt is not None
        assert outcome.jd_ut is not None
        assert outcome.distance_au is not None
        assert outcome.coverage_edge_tdb is None
        assert outcome.detail == "TWO_SIDED_RADIAL_VELOCITY_ROOT"


@pytest.mark.requires_ephemeris
def test_provenance_freezes_route_and_algorithm(earth_next) -> None:
    receipt = earth_next.provenance
    assert receipt.algorithm_version == APSIDAL_ALGORITHM_VERSION
    assert receipt.refinement_tolerance_days == APSIDAL_ROOT_TOLERANCE_DAYS
    assert receipt.witness_root_tolerance_factor == 8.0
    assert receipt.witness_minimum_step_fraction == 0.1
    assert receipt.witness_motion_timescale_fraction == 1.0e-4
    assert receipt.witness_maximum_offset_days == 1.0
    assert len(receipt.route_plan_identity) == 64
    assert receipt.route_schedule
    assert receipt.segment_usage
    assert all(
        0 < usage.evaluations <= receipt.total_evaluations
        for usage in receipt.segment_usage
    )
    assert receipt.total_evaluations <= receipt.evaluation_budget
    assert receipt.searched_interval_tdb[0] == pytest.approx(
        earth_next.start_epoch_tdb
    )


@pytest.mark.requires_ephemeris
def test_explicit_window_returns_field_exclusive_no_result(planetary_reader) -> None:
    result = apsidal_passages(
        Body.EARTH,
        _START_JD_UT1,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=1.0,
        reader=planetary_reader,
    )
    for outcome in (result.pericenter, result.apocenter):
        assert outcome.status is ApsidalPassageStatus.NOT_IN_WINDOW
        assert outcome.detail == "EXPLICIT_MAX_DAYS"
        assert outcome.epoch_tdb is None
        assert outcome.epoch_tt is None
        assert outcome.jd_ut is None
        assert outcome.distance_au is None
        assert outcome.coverage_edge_tdb is None


@pytest.mark.requires_ephemeris
def test_previous_search_returns_nearest_events_in_reverse_direction(
    planetary_reader,
) -> None:
    result = apsidal_passages(
        Body.EARTH,
        2451900.5,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.PREVIOUS,
        reader=planetary_reader,
    )
    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.apocenter.status is ApsidalPassageStatus.FOUND
    assert result.pericenter.epoch_tdb < result.start_epoch_tdb
    assert result.apocenter.epoch_tdb < result.start_epoch_tdb


@pytest.mark.requires_ephemeris
def test_exact_start_is_inclusive_when_two_sided_witnesses_exist(
    earth_next,
    planetary_reader,
) -> None:
    assert earth_next.pericenter.jd_ut is not None
    repeated = apsidal_passages(
        Body.EARTH,
        earth_next.pericenter.jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=10.0,
        reader=planetary_reader,
    )
    assert repeated.pericenter.status is ApsidalPassageStatus.FOUND
    assert repeated.pericenter.epoch_tdb == pytest.approx(
        earth_next.pericenter.epoch_tdb,
        abs=APSIDAL_ROOT_TOLERANCE_DAYS,
    )

    previous = apsidal_passages(
        Body.EARTH,
        earth_next.pericenter.jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.PREVIOUS,
        max_days=10.0,
        reader=planetary_reader,
    )
    assert previous.pericenter.status is ApsidalPassageStatus.FOUND
    assert previous.pericenter.epoch_tdb == pytest.approx(
        earth_next.pericenter.epoch_tdb,
        abs=APSIDAL_ROOT_TOLERANCE_DAYS,
    )


@pytest.mark.requires_ephemeris
def test_legacy_distance_extremes_fields_are_tt(
    earth_next,
    planetary_reader,
) -> None:
    legacy = distance_extremes_at(
        Body.EARTH, _START_JD_UT1, planetary_reader
    )
    assert legacy.perihelion_jd == earth_next.pericenter.epoch_tt
    assert legacy.aphelion_jd == earth_next.apocenter.epoch_tt


@pytest.mark.requires_ephemeris
def test_phenomena_fields_remain_verified_ut1(
    earth_next,
    planetary_reader,
) -> None:
    peri = perihelion(Body.EARTH, _START_JD_UT1, planetary_reader)
    aphe = aphelion(Body.EARTH, _START_JD_UT1, planetary_reader)
    assert peri is not None and aphe is not None
    assert peri.jd_ut == earth_next.pericenter.jd_ut
    assert aphe.jd_ut == earth_next.apocenter.jd_ut
    assert _ut1_to_ephemeris_tt(peri.jd_ut, planetary_reader) == pytest.approx(
        earth_next.pericenter.epoch_tt,
        abs=4.0 * math.ulp(earth_next.pericenter.epoch_tt),
    )


@pytest.mark.requires_ephemeris
def test_moon_uses_earth_center(planetary_reader) -> None:
    result = apsidal_passages(
        Body.MOON,
        2451545.0,
        center=OrbitalCenter.EARTH,
        direction=ApsidalDirection.NEXT,
        reader=planetary_reader,
    )
    assert result.center is OrbitalCenter.EARTH
    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.apocenter.status is ApsidalPassageStatus.FOUND


@pytest.mark.requires_ephemeris
def test_moon_phenomena_adapter_uses_earth_center(planetary_reader) -> None:
    event = perihelion(Body.MOON, 2451545.0, planetary_reader)
    assert event is not None
    assert event.body == Body.MOON
    assert event.phenomenon == "Perihelion"
    assert event.value < 0.003


@pytest.mark.requires_ephemeris
def test_center_policy_is_explicit(planetary_reader) -> None:
    with pytest.raises(OrbitalCenterNotAllowedError):
        apsidal_passages(
            Body.MOON,
            2451545.0,
            center=OrbitalCenter.SUN,
            direction=ApsidalDirection.NEXT,
            reader=planetary_reader,
        )


@pytest.mark.parametrize("bad", (True, 0.0, -1.0, math.nan, math.inf, "1"))
def test_max_days_rejects_non_positive_non_finite_and_boolean(bad) -> None:
    with pytest.raises(OrbitalInputError) as caught:
        apsidal_passages(
            Body.EARTH,
            2451545.0,
            center=OrbitalCenter.SUN,
            direction=ApsidalDirection.NEXT,
            max_days=bad,
            reader=None,
        )
    assert caught.value.parameter == "max_days"


def test_direction_rejects_unknown_policy_before_reader_binding() -> None:
    with pytest.raises(OrbitalInputError) as caught:
        apsidal_passages(
            Body.EARTH,
            2451545.0,
            center=OrbitalCenter.SUN,
            direction="FORWARD",
            reader=None,
        )
    assert caught.value.parameter == "direction"


def test_start_outside_exact_route_coverage_raises() -> None:
    reader = _AnalyticReader("later", (2_451_600.0, 2_451_700.0))
    with pytest.raises(OrbitalCoverageError):
        apsidal_passages(
            Body.MERCURY,
            2_451_545.0,
            center=OrbitalCenter.SUN,
            direction=ApsidalDirection.NEXT,
            reader=reader,
        )


def test_continuous_source_seam_is_admitted_and_exact_seam_event_is_found() -> None:
    pool = KernelPool(
        (
            _AnalyticReader("left", (2_451_500.0, 2_451_550.0)),
            _AnalyticReader("right", (2_451_550.0, 2_451_600.0)),
        )
    )
    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=15.0,
        reader=pool,
    )

    assert len(result.provenance.route_schedule) == 2
    assert len(result.provenance.seam_continuity) == 1
    seam = result.provenance.seam_continuity[0]
    assert seam.epoch_tdb == 2_451_550.0
    assert seam.admitted is True
    assert seam.position_residual_km == 0.0
    assert seam.velocity_residual_km_per_day == 0.0
    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.pericenter.epoch_tdb == pytest.approx(
        2_451_550.0, abs=APSIDAL_ROOT_TOLERANCE_DAYS
    )
    assert result.apocenter.status is ApsidalPassageStatus.FOUND


def test_explicit_window_endpoint_is_inclusive_with_outside_guard() -> None:
    reader = _AnalyticReader(
        "explicit-endpoint", (2_451_500.0, 2_451_600.0)
    )
    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=5.0,
        reader=reader,
    )

    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.pericenter.epoch_tdb == pytest.approx(
        2_451_550.0, abs=APSIDAL_ROOT_TOLERANCE_DAYS
    )
    assert result.apocenter.status is ApsidalPassageStatus.NOT_IN_WINDOW
    assert result.apocenter.detail == "EXPLICIT_MAX_DAYS"


def test_discontinuous_source_seam_is_a_visible_coverage_boundary() -> None:
    pool = KernelPool(
        (
            _AnalyticReader("left", (2_451_500.0, 2_451_550.0)),
            _AnalyticReader(
                "shifted", (2_451_550.0, 2_451_600.0), offset_km=100.0
            ),
        )
    )
    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=15.0,
        reader=pool,
    )

    assert len(result.provenance.route_schedule) == 1
    seam = result.provenance.seam_continuity[0]
    assert seam.admitted is False
    assert seam.position_residual_km > seam.position_tolerance_km
    for outcome in (result.pericenter, result.apocenter):
        assert outcome.status is ApsidalPassageStatus.BEYOND_COVERAGE
        assert outcome.coverage_edge_tdb == 2_451_550.0
        assert outcome.detail == "UNADMITTED_SOURCE_SEAM"


def test_coverage_gap_is_not_flattened_into_an_ephemeris_edge() -> None:
    pool = KernelPool(
        (
            _AnalyticReader("left", (2_451_500.0, 2_451_549.0)),
            _AnalyticReader("later", (2_451_551.0, 2_451_600.0)),
        )
    )
    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=15.0,
        reader=pool,
    )

    assert not result.provenance.seam_continuity
    for outcome in (result.pericenter, result.apocenter):
        assert outcome.status is ApsidalPassageStatus.BEYOND_COVERAGE
        assert outcome.coverage_edge_tdb == 2_451_549.0
        assert outcome.detail == "UNADMITTED_SOURCE_SEAM"


def test_flat_radius_returns_no_isolated_extremum() -> None:
    reader = _AnalyticReader(
        "flat", (2_451_500.0, 2_451_600.0), flat=True
    )
    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=5.0,
        reader=reader,
    )

    for outcome in (result.pericenter, result.apocenter):
        assert outcome.status is ApsidalPassageStatus.NOT_IN_WINDOW
        assert outcome.detail == "NO_ISOLATED_EXTREMUM"
        assert outcome.epoch_tdb is None
        assert outcome.coverage_edge_tdb is None


def test_starting_unbound_shape_does_not_short_circuit_n_body_search() -> None:
    reader = _AnalyticReader(
        "unbound",
        (2_451_500.0, 2_451_600.0),
        velocity_multiplier=300.0,
    )
    elements = osculating_elements(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        reader=reader,
    )
    assert elements.shape is OrbitShape.HYPERBOLIC

    result = apsidal_passages(
        Body.MERCURY,
        2_451_545.0,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        max_days=15.0,
        reader=reader,
    )
    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.apocenter.status is ApsidalPassageStatus.FOUND


def test_fixed_evaluation_budget_raises_computational_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira.orbits.APSIDAL_EVALUATION_BUDGET", 2)
    reader = _AnalyticReader("budget", (2_451_500.0, 2_451_600.0))

    with pytest.raises(OrbitalSearchError) as caught:
        apsidal_passages(
            Body.MERCURY,
            2_451_545.0,
            center=OrbitalCenter.SUN,
            direction=ApsidalDirection.NEXT,
            max_days=15.0,
            reader=reader,
        )

    assert caught.value.evaluations == 2
    assert caught.value.algorithm_version == APSIDAL_ALGORITHM_VERSION
