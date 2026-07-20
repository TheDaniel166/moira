"""Stage 2F astronomical Paksha inference engine and facade contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import math
from types import SimpleNamespace

import pytest

import moira
import moira._ephemeris_time as ephemeris_time
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.planets as planets
import moira.spk_reader as spk_reader
import moira.vedic as vedic
from moira.constants import Body
from moira.julian import jd_from_datetime, utc_to_ut1


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_JD_UT1 = 2_460_000.25
_JD_TT = 2_460_000.250_800_741


def _install_planetary_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sun_longitude: float,
    moon_longitude: float,
    resolved_reader: object,
) -> tuple[list[tuple[float, object]], list[tuple[Body, float, dict[str, object]]]]:
    tt_calls: list[tuple[float, object]] = []
    planet_calls: list[tuple[Body, float, dict[str, object]]] = []

    def fake_ut1_to_tt(jd_ut1: float, reader: object) -> float:
        tt_calls.append((jd_ut1, reader))
        return _JD_TT

    def fake_planet_at(
        body: Body,
        jd_ut1: float,
        **kwargs: object,
    ) -> SimpleNamespace:
        planet_calls.append((body, jd_ut1, kwargs))
        longitude = sun_longitude if body is Body.SUN else moon_longitude
        return SimpleNamespace(longitude=longitude)

    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", fake_ut1_to_tt)
    monkeypatch.setattr(planets, "planet_at", fake_planet_at)
    monkeypatch.setattr(spk_reader, "get_reader", lambda: resolved_reader)
    return tt_calls, planet_calls


def _synthetic_inference(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sun_longitude: float = 0.0,
    moon_longitude: float = 0.0,
) -> pakshi.PanchaPakshiAstronomicalPakshaInference:
    reader = object()
    _install_planetary_stubs(
        monkeypatch,
        sun_longitude=sun_longitude,
        moon_longitude=moon_longitude,
        resolved_reader=reader,
    )
    return pakshi.pancha_pakshi_astronomical_paksha_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )


def test_stage2f_policy_is_immutable_and_exhaustively_names_its_doctrine() -> None:
    policy = pakshi.PanchaPakshiAstronomicalPakshaInferencePolicy()
    expected = {
        "policy_id": (
            "apparent_geocentric_moon_sun_longitude_paksha_half_open_v1"
        ),
        "input_time_scale": "ut1",
        "ephemeris_time_scale": "reader_bound_tt",
        "position_origin": "geocentric",
        "position_frame": "true_ecliptic_of_date",
        "apparent": True,
        "aberration": True,
        "grav_deflection": True,
        "nutation": True,
        "elongation_definition": (
            "normalized_moon_longitude_minus_sun_longitude"
        ),
        "elongation_domain": "degrees_half_open_0_360",
        "shukla_interval": "0_inclusive_180_exclusive",
        "krishna_interval": "180_inclusive_360_exclusive",
        "boundary_tolerance_degrees": 0.0,
        "ayanamsa_status": "not_applied_common_longitude_offset_cancels",
        "profile_mapping_basis": "direct_source_attested_waxing_waning",
        "purva_source_locator_id": "ia_n16",
        "amara_source_locator_id": "ia_n26",
        "schedule_selection_status": "not_performed",
        "materialization_status": "not_performed",
        "natal_identity_status": "not_performed",
    }

    assert tuple(field.name for field in fields(policy)) == tuple(expected)
    assert {name: getattr(policy, name) for name in expected} == expected
    with pytest.raises(FrozenInstanceError):
        policy.apparent = False  # type: ignore[misc]
    with pytest.raises(TypeError):
        pakshi.PanchaPakshiAstronomicalPakshaInferencePolicy(apparent=False)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    (
        "elongation",
        "expected_astronomical",
        "expected_profile",
        "expected_locator_id",
    ),
    (
        (
            0.0,
            pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA,
            pakshi.PanchaPakshiPaksha.PURVA,
            "ia_n16",
        ),
        (
            math.nextafter(180.0, -math.inf),
            pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA,
            pakshi.PanchaPakshiPaksha.PURVA,
            "ia_n16",
        ),
        (
            180.0,
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
            "ia_n26",
        ),
        (
            math.nextafter(180.0, math.inf),
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
            "ia_n26",
        ),
        (
            math.nextafter(360.0, -math.inf),
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
            "ia_n26",
        ),
    ),
)
def test_half_open_boundaries_are_exact_and_exhaustive(
    monkeypatch: pytest.MonkeyPatch,
    elongation: float,
    expected_astronomical: pakshi.PanchaPakshiAstronomicalPaksha,
    expected_profile: pakshi.PanchaPakshiPaksha,
    expected_locator_id: str,
) -> None:
    result = _synthetic_inference(
        monkeypatch,
        moon_longitude=elongation,
    )

    assert result.moon_minus_sun_elongation_deg == elongation
    assert result.astronomical_paksha is expected_astronomical
    assert result.profile_paksha is expected_profile
    assert tuple(
        locator.locator_id for locator in result.mapping_source_locators
    ) == (expected_locator_id,)


@pytest.mark.parametrize(
    (
        "sun_longitude",
        "moon_longitude",
        "expected_sun",
        "expected_moon",
        "expected_elongation",
        "expected_paksha",
    ),
    (
        (
            350.0,
            370.0,
            350.0,
            10.0,
            20.0,
            pakshi.PanchaPakshiPaksha.PURVA,
        ),
        (
            370.0,
            -10.0,
            10.0,
            350.0,
            340.0,
            pakshi.PanchaPakshiPaksha.AMARA,
        ),
        (
            -360.0,
            360.0,
            0.0,
            0.0,
            0.0,
            pakshi.PanchaPakshiPaksha.PURVA,
        ),
    ),
)
def test_substrate_longitudes_and_elongation_are_normalized_half_open(
    monkeypatch: pytest.MonkeyPatch,
    sun_longitude: float,
    moon_longitude: float,
    expected_sun: float,
    expected_moon: float,
    expected_elongation: float,
    expected_paksha: pakshi.PanchaPakshiPaksha,
) -> None:
    result = _synthetic_inference(
        monkeypatch,
        sun_longitude=sun_longitude,
        moon_longitude=moon_longitude,
    )

    assert result.sun_longitude_deg == expected_sun
    assert result.moon_longitude_deg == expected_moon
    assert result.moon_minus_sun_elongation_deg == expected_elongation
    assert result.profile_paksha is expected_paksha


@pytest.mark.parametrize(
    ("moon_longitude", "locator_id", "label_fragment", "phase_word"),
    (
        (0.0, "ia_n16", "waxing/Purva", "explicit_lunar_phase_half_mapping"),
        (180.0, "ia_n26", "waning/Amara", "explicit_lunar_phase_half_mapping"),
    ),
)
def test_each_source_mapping_returns_only_its_direct_locator(
    monkeypatch: pytest.MonkeyPatch,
    moon_longitude: float,
    locator_id: str,
    label_fragment: str,
    phase_word: str,
) -> None:
    result = _synthetic_inference(
        monkeypatch,
        moon_longitude=moon_longitude,
    )

    assert len(result.mapping_source_locators) == 1
    locator = result.mapping_source_locators[0]
    assert locator.locator_id == locator_id
    assert locator.witness_id == "dli.rmrl.000451_images"
    assert label_fragment in locator.label
    assert locator.url == (
        "https://archive.org/details/dli.rmrl.000451_images/"
        f"page/{locator_id.removeprefix('ia_')}/mode/1up"
    )
    assert phase_word in locator.evidence_role


def test_one_reader_bound_tt_conversion_is_shared_by_both_body_evaluations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    tt_calls, planet_calls = _install_planetary_stubs(
        monkeypatch,
        sun_longitude=25.0,
        moon_longitude=75.0,
        resolved_reader=reader,
    )

    def unexpected_reader_lookup() -> object:
        raise AssertionError("an explicitly supplied reader must be reused")

    monkeypatch.setattr(spk_reader, "get_reader", unexpected_reader_lookup)
    result = pakshi.pancha_pakshi_astronomical_paksha_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )

    assert result.requested_jd_tt == _JD_TT
    assert tt_calls == [(_JD_UT1, reader)]
    assert [call[0] for call in planet_calls] == [Body.SUN, Body.MOON]
    for body, jd_ut1, kwargs in planet_calls:
        assert body in (Body.SUN, Body.MOON)
        assert jd_ut1 == _JD_UT1
        assert kwargs == {
            "reader": reader,
            "apparent": True,
            "aberration": True,
            "grav_deflection": True,
            "nutation": True,
            "center": "geocentric",
            "frame": "ecliptic",
            "observer_lat": None,
            "observer_lon": None,
            "observer_elev_m": 0.0,
            "lst_deg": None,
            "jd_tt": _JD_TT,
        }


def test_omitted_reader_is_resolved_once_then_reused_everywhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    get_reader_calls: list[None] = []
    tt_calls, planet_calls = _install_planetary_stubs(
        monkeypatch,
        sun_longitude=25.0,
        moon_longitude=225.0,
        resolved_reader=reader,
    )

    def fake_get_reader() -> object:
        get_reader_calls.append(None)
        return reader

    monkeypatch.setattr(spk_reader, "get_reader", fake_get_reader)
    pakshi.pancha_pakshi_astronomical_paksha_at(_PROFILE_ID, _JD_UT1)

    assert get_reader_calls == [None]
    assert tt_calls == [(_JD_UT1, reader)]
    assert [call[2]["reader"] for call in planet_calls] == [reader, reader]


def test_unknown_profile_fails_before_any_kernel_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("profile admission must precede kernel access")

    monkeypatch.setattr(spk_reader, "get_reader", forbidden)
    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", forbidden)
    monkeypatch.setattr(planets, "planet_at", forbidden)

    with pytest.raises(ValueError, match="unknown Pancha Pakshi profile"):
        pakshi.pancha_pakshi_astronomical_paksha_at(
            "not_an_admitted_profile",
            _JD_UT1,
        )


def test_capability_gate_fails_before_any_kernel_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    restricted_profile = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability
            is not pakshi.PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE
        ),
    )

    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: restricted_profile,
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("capability admission must precede kernel access")

    monkeypatch.setattr(spk_reader, "get_reader", forbidden)
    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", forbidden)
    monkeypatch.setattr(planets, "planet_at", forbidden)

    with pytest.raises(
        ValueError,
        match="does not admit 'astronomical_paksha_inference'",
    ):
        pakshi.pancha_pakshi_astronomical_paksha_at(
            _PROFILE_ID,
            _JD_UT1,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "requested_jd_ut1",
        "requested_jd_tt",
        "sun_longitude_deg",
        "moon_longitude_deg",
        "moon_minus_sun_elongation_deg",
    ),
)
@pytest.mark.parametrize("nonfinite", (math.nan, math.inf, -math.inf))
def test_result_rejects_nonfinite_numeric_fields(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    nonfinite: float,
) -> None:
    result = _synthetic_inference(monkeypatch, moon_longitude=90.0)
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        replace(result, **{field_name: nonfinite})


def test_result_rejects_incorrect_astronomical_and_profile_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _synthetic_inference(monkeypatch, moon_longitude=90.0)

    with pytest.raises(ValueError, match="astronomical_paksha disagrees"):
        replace(
            result,
            astronomical_paksha=(
                pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA
            ),
        )
    with pytest.raises(ValueError, match="profile_paksha disagrees"):
        replace(result, profile_paksha=pakshi.PanchaPakshiPaksha.AMARA)
    with pytest.raises(ValueError, match="elongation_deg disagrees"):
        replace(result, moon_minus_sun_elongation_deg=89.0)


def test_result_rejects_wrong_or_malformed_mapping_locator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _synthetic_inference(monkeypatch, moon_longitude=90.0)
    profile_info = pakshi.pancha_pakshi_profile_info(_PROFILE_ID)
    amara_locator = next(
        locator
        for locator in profile_info.source_locators
        if locator.locator_id == "ia_n26"
    )

    with pytest.raises(ValueError, match="source locator disagrees"):
        replace(result, mapping_source_locators=(amara_locator,))
    with pytest.raises(TypeError, match="must contain one source locator"):
        replace(result, mapping_source_locators=())
    with pytest.raises(TypeError, match="must contain one source locator"):
        replace(result, mapping_source_locators=list(result.mapping_source_locators))  # type: ignore[arg-type]

    forged_locator = replace(
        result.mapping_source_locators[0],
        label="fabricated source label",
        url="https://example.invalid/fabricated",
        evidence_role="fabricated_evidence_role",
    )
    with pytest.raises(ValueError, match="canonical profile locator"):
        replace(result, mapping_source_locators=(forged_locator,))


def test_result_rejects_incoherent_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _synthetic_inference(monkeypatch, moon_longitude=90.0)

    with pytest.raises(ValueError, match="provenance profile disagrees"):
        replace(
            result,
            provenance=replace(result.provenance, profile_id="another_profile"),
        )
    with pytest.raises(ValueError, match="does not admit astronomical paksha"):
        replace(
            result,
            provenance=replace(
                result.provenance,
                capabilities=tuple(
                    capability
                    for capability in result.provenance.capabilities
                    if capability
                    is not pakshi.PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE
                ),
            ),
        )
    with pytest.raises(ValueError, match="does not describe the astronomical"):
        replace(
            result,
            provenance=replace(
                result.provenance,
                astronomical_routing_status="not_performed",
            ),
        )


def test_facade_normalizes_an_aware_datetime_and_delegates_its_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    reader = object()
    engine._reader_obj = reader
    dt = datetime(
        2024,
        4,
        15,
        8,
        30,
        tzinfo=timezone(timedelta(hours=-4)),
    )
    expected_jd_utc = facade.jd_from_datetime(dt)
    sentinel = object()
    calls: list[tuple[str, float, object]] = []

    def fake_from_utc(
        profile_id: str,
        jd_utc: float,
        *,
        reader: object,
    ) -> object:
        calls.append((profile_id, jd_utc, reader))
        return sentinel

    monkeypatch.setattr(
        pakshi,
        "_pancha_pakshi_astronomical_paksha_from_utc",
        fake_from_utc,
    )

    assert engine.pancha_pakshi_astronomical_paksha(_PROFILE_ID, dt) is sentinel
    assert calls == [(_PROFILE_ID, expected_jd_utc, reader)]


def test_facade_rejects_a_naive_datetime_before_astronomical_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = object()

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("naive datetime must fail before Stage 2F routing")

    monkeypatch.setattr(
        pakshi,
        "_pancha_pakshi_astronomical_paksha_from_utc",
        forbidden,
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_astronomical_paksha(
            _PROFILE_ID,
            datetime(2024, 4, 15, 12, 0),
        )


@pytest.mark.parametrize(
    "name",
    (
        "PanchaPakshiAstronomicalPaksha",
        "PanchaPakshiAstronomicalPakshaInference",
        "PanchaPakshiAstronomicalPakshaInferencePolicy",
        "pancha_pakshi_astronomical_paksha_at",
    ),
)
def test_stage2f_exports_share_identity_across_public_surfaces(name: str) -> None:
    expected = getattr(pakshi, name)
    for surface in (moira, facade, vedic):
        assert name in surface.__all__
        assert getattr(surface, name) is expected


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("dt", "expected_astronomical", "expected_profile"),
    (
        (
            datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc),
            pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA,
            pakshi.PanchaPakshiPaksha.PURVA,
        ),
        (
            datetime(2024, 4, 30, 12, 0, tzinfo=timezone.utc),
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
        ),
    ),
)
def test_de441_well_inside_each_lunar_half_is_classified_coherently(
    reader: object,
    dt: datetime,
    expected_astronomical: pakshi.PanchaPakshiAstronomicalPaksha,
    expected_profile: pakshi.PanchaPakshiPaksha,
) -> None:
    jd_ut1 = utc_to_ut1(jd_from_datetime(dt))
    result = pakshi.pancha_pakshi_astronomical_paksha_at(
        _PROFILE_ID,
        jd_ut1,
        reader=reader,
    )

    assert result.astronomical_paksha is expected_astronomical
    assert result.profile_paksha is expected_profile
    if expected_astronomical is pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA:
        assert 0.0 <= result.moon_minus_sun_elongation_deg < 180.0
    else:
        assert 180.0 <= result.moon_minus_sun_elongation_deg < 360.0
