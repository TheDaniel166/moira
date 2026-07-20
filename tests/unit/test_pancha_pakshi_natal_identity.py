"""Stage 2G source mapping and modern natal-Moon composition contracts."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira._ephemeris_time as ephemeris_time
import moira._pancha_pakshi as internal
import moira.pancha_pakshi as pakshi
import moira.planets as planets
import moira.sidereal as sidereal
import moira.spk_reader as spk_reader
from moira.constants import Body


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_PATH = (
    _ROOT
    / "moira"
    / "data"
    / "pancha_pakshi_bogamuni_chennai_2024_nakshatra_natal_identity.json"
)
_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json"
)
_PROFILE_ID = "bogamuni_chennai_2024_nakshatra_natal_identity"
_DECISION_ID = "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20"
_CAPABILITIES = (
    pakshi.PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
    pakshi.PanchaPakshiCapability.NATAL_IDENTITY,
)
_JD_UT1 = 2_460_000.25
_JD_TT = 2_460_000.250_800_741


def _document() -> dict:
    return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))


def _canonical_bytes(path: Path) -> bytes:
    text = path.read_bytes().decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _parse(document: dict):
    return internal._parse_natal_identity_profile_document(
        document,
        admission_status=pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        default_selection_allowed=False,
        capabilities=_CAPABILITIES,
        admission_decision_id=_DECISION_ID,
    )


def _install_astronomy(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sun_longitude: float,
    moon_longitude: float,
    ayanamsa_deg: float,
) -> tuple[object, list, list, list]:
    reader = object()
    tt_calls: list[tuple[float, object]] = []
    planet_calls: list[tuple[Body, float, dict]] = []
    ayanamsa_calls: list[tuple[float, str, str]] = []

    def fake_tt(jd_ut1: float, selected_reader: object) -> float:
        tt_calls.append((jd_ut1, selected_reader))
        return _JD_TT

    def fake_planet_at(body: Body, jd_ut1: float, **kwargs):
        planet_calls.append((body, jd_ut1, kwargs))
        longitude = sun_longitude if body is Body.SUN else moon_longitude
        return SimpleNamespace(longitude=longitude)

    def fake_ayanamsa(jd_tt: float, system: str, mode: str) -> float:
        ayanamsa_calls.append((jd_tt, system, mode))
        return ayanamsa_deg

    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", fake_tt)
    monkeypatch.setattr(planets, "planet_at", fake_planet_at)
    monkeypatch.setattr(sidereal, "_ayanamsa_at_tt", fake_ayanamsa)
    monkeypatch.setattr(spk_reader, "get_reader", lambda: reader)
    return reader, tt_calls, planet_calls, ayanamsa_calls


def test_profile_is_separate_hash_verified_and_honest_about_original_pdf() -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)

    assert isinstance(profile, internal.PanchaPakshiNatalIdentityProfile)
    assert profile.product_kind == "natal_moon_bird_identity"
    assert profile.capabilities == _CAPABILITIES
    assert profile.default_selection_allowed is False
    assert profile.assembly_policy == "verse_precedence_for_nakshatra_partition"
    assert profile.source.archive_pdf_source_status == "internet_archive_original"
    assert profile.source.archive_pdf_md5 == "abe489a832ac38a0270335b7429776f3"
    assert profile.source.archive_pdf_sha1 == (
        "6ddad8f2577883f6859829f534e8ee7b8330ade8"
    )
    assert profile.source.locally_verified_pdf_sha256 == (
        "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990"
    )
    assert profile.source.archive_original_image_zip_md5 == "not_applicable"
    assert len(profile.nakshatra_bird_rules) == 54


def test_stage2g_admission_fixture_binds_source_table_and_modern_nonclaims() -> None:
    decision = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))

    assert hashlib.sha256(_canonical_bytes(_ADMISSION_PATH)).hexdigest() == (
        "3da998bc78c6c1fc4ec1c71629dc6b3872725ef25f73965474d5e894deec1575"
    )
    assert decision["decision_id"] == _DECISION_ID
    assert decision["profile_binding"] == {
        "path": (
            "moira/data/"
            "pancha_pakshi_bogamuni_chennai_2024_nakshatra_natal_identity.json"
        ),
        "sha256": hashlib.sha256(_canonical_bytes(_PROFILE_PATH)).hexdigest(),
        "admission_status": "source_scoped_public",
        "product_kind": "natal_moon_bird_identity",
        "default_selection_allowed": False,
        "capabilities": ["nakshatra_bird_mapping", "natal_identity"],
    }
    assert decision["manifest_binding"] == {
        "path": "moira/data/pancha_pakshi_manifest.json",
        "sha256": (
            "979bb6df8a31d0ff9603ef396b0f569f17ecca6f6dc21def220ad682a425eb61"
        ),
        "hash_canonicalization": (
            "UTF-8 text with CRLF and CR normalized to LF"
        ),
        "profile_entry_decision_id": _DECISION_ID,
    }
    assert decision["source_readings"]["amara_partition"][
        "assembly_policy"
    ] == "verse_precedence_for_nakshatra_partition"
    assert decision["computational_object"]["source_table_natal_status"] == (
        "not_explicitly_natal_moon"
    )
    assert decision["validation_evidence"]["exact_source_cells"] == 54
    assert any(
        "does not specify Lahiri" in nonclaim
        for nonclaim in decision["public_nonclaims"]
    )


def test_all_54_source_cells_are_exact_complete_and_use_only_governing_verse() -> None:
    purva = (
        [pakshi.PanchaPakshiBird.VULTURE] * 5
        + [pakshi.PanchaPakshiBird.OWL] * 6
        + [pakshi.PanchaPakshiBird.CROW] * 5
        + [pakshi.PanchaPakshiBird.COCK] * 5
        + [pakshi.PanchaPakshiBird.PEACOCK] * 6
    )
    amara = (
        [pakshi.PanchaPakshiBird.PEACOCK] * 5
        + [pakshi.PanchaPakshiBird.COCK] * 6
        + [pakshi.PanchaPakshiBird.CROW] * 5
        + [pakshi.PanchaPakshiBird.OWL] * 5
        + [pakshi.PanchaPakshiBird.VULTURE] * 6
    )

    mappings = []
    for profile_paksha, expected_birds, locator_id in (
        (pakshi.PanchaPakshiPaksha.PURVA, purva, "bogar_n52_purva"),
        (
            pakshi.PanchaPakshiPaksha.AMARA,
            amara,
            "bogar_n64_amara_verse",
        ),
    ):
        for nakshatra_index, expected_bird in enumerate(expected_birds):
            mapping = pakshi.pancha_pakshi_nakshatra_bird_mapping(
                _PROFILE_ID,
                profile_paksha=profile_paksha,
                nakshatra_index=nakshatra_index,
            )
            mappings.append(mapping)
            assert mapping.nakshatra == sidereal.NAKSHATRA_NAMES[nakshatra_index]
            assert mapping.bird is expected_bird
            assert tuple(x.locator_id for x in mapping.source_locators) == (
                locator_id,
            )
            assert all(
                x.locator_id != "bogar_n64_amara_commentary_conflict"
                for x in mapping.source_locators
            )
            assert mapping.source_table_semantics == (
                "nakshatra_bird_table_not_explicitly_natal_moon"
            )

    assert len(mappings) == 54
    assert len(
        {(mapping.profile_paksha, mapping.nakshatra_index) for mapping in mappings}
    ) == 54


def test_rejected_commentary_and_uromarisi_witness_contracts_are_visible() -> None:
    info = pakshi.pancha_pakshi_profile_info(_PROFILE_ID)

    assert tuple(x.witness_id for x in info.known_conflict_witnesses) == (
        "bogamuni_2024_adjacent_amara_commentary",
        "kvc-0354-vinaadi-pajasapatchi-mulamum-1934",
    )
    assert info.known_conflict_witnesses[0].runtime_status == (
        "rejected_by_declared_verse_precedence"
    )
    assert info.known_conflict_witnesses[1].record_url == (
        "https://archive.org/details/"
        "kvc-0354-vinaadi-pajasapatchi-mulamum-1934"
    )
    assert info.known_conflict_witnesses[1].conflict_locators == (
        "IA leaf n18: Purva corroboration",
        "IA leaf n61: malformed Amara commentary",
    )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda d: d["nakshatra_bird_mapping"]["entries"].pop(),
        lambda d: d["nakshatra_bird_mapping"]["entries"][-1].__setitem__(
            "bird", "peacock"
        ),
        lambda d: d["nakshatra_bird_mapping"].__setitem__(
            "assembly_policy", "symmetry_repair"
        ),
        lambda d: d["source"].__setitem__(
            "archive_pdf_source_status", "internet_archive_derivative"
        ),
        lambda d: d["research_conflict_ledger"][1].__setitem__(
            "witness_id", "arbitrary_second_row"
        ),
    ),
)
def test_strict_natal_parser_rejects_partition_or_provenance_drift(mutator) -> None:
    document = copy.deepcopy(_document())
    mutator(document)

    with pytest.raises(pakshi.PanchaPakshiDataError):
        _parse(document)


def test_natal_profile_cannot_enter_schedule_or_aksara_products() -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)

    with pytest.raises(TypeError, match="PanchaPakshiProfile"):
        internal.generate_pancha_pakshi_schedule(
            profile,
            paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )
    with pytest.raises(ValueError, match="does not admit 'nominal_schedule'"):
        pakshi.pancha_pakshi_schedule(
            _PROFILE_ID,
            paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )
    with pytest.raises(ValueError, match="does not admit 'aksara_identity'"):
        pakshi.pancha_pakshi_identity_from_initial_vowel(_PROFILE_ID, "A")
    with pytest.raises(ValueError, match="does not admit 'natal_identity'"):
        pakshi.pancha_pakshi_natal_moon_identity_at(
            "agastya_madras_1879_akshara_fixed_clock",
            _JD_UT1,
            reader=object(),
        )


@pytest.mark.parametrize("value", (True, math.nan, math.inf, -math.inf))
def test_natal_epoch_fails_closed_before_substrate_access(value) -> None:
    with pytest.raises((TypeError, ValueError)):
        pakshi.pancha_pakshi_natal_moon_identity_at(
            _PROFILE_ID,
            value,
            reader=object(),
        )


def test_natal_policy_is_immutable_and_names_the_modern_composition() -> None:
    policy = pakshi.PanchaPakshiNatalMoonIdentityPolicy()

    assert policy.composition_status == "modern_moira_policy_not_source_claim"
    assert policy.source_table_semantics == (
        "nakshatra_bird_table_not_explicitly_natal_moon"
    )
    assert policy.ayanamsa_system == "Lahiri"
    assert policy.ayanamsa_mode == "true"
    assert policy.ayanamsa_status == (
        "fixed_modern_moira_policy_not_source_attested"
    )
    assert policy.mapping_assembly_policy == (
        "verse_precedence_for_nakshatra_partition"
    )
    assert policy.schedule_selection_status == "not_performed"
    assert policy.materialization_status == "not_performed"
    assert policy.current_cell_status == "not_performed"
    assert policy.scoring_status == "not_performed"
    assert policy.forecast_status == "not_performed"
    with pytest.raises(FrozenInstanceError):
        policy.ayanamsa_system = "invented"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("moon_longitude", "expected_astronomical", "expected_profile", "locator"),
    (
        (
            0.0,
            pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA,
            pakshi.PanchaPakshiPaksha.PURVA,
            "bogar_n167_phase",
        ),
        (
            math.nextafter(180.0, -math.inf),
            pakshi.PanchaPakshiAstronomicalPaksha.SHUKLA,
            pakshi.PanchaPakshiPaksha.PURVA,
            "bogar_n167_phase",
        ),
        (
            180.0,
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
            "bogar_n167_phase",
        ),
        (
            math.nextafter(360.0, -math.inf),
            pakshi.PanchaPakshiAstronomicalPaksha.KRISHNA,
            pakshi.PanchaPakshiPaksha.AMARA,
            "bogar_n167_phase",
        ),
    ),
)
def test_natal_phase_mapping_owns_new_and_full_moon_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    moon_longitude: float,
    expected_astronomical: pakshi.PanchaPakshiAstronomicalPaksha,
    expected_profile: pakshi.PanchaPakshiPaksha,
    locator: str,
) -> None:
    reader, _, _, _ = _install_astronomy(
        monkeypatch,
        sun_longitude=0.0,
        moon_longitude=moon_longitude,
        ayanamsa_deg=0.0,
    )

    result = pakshi.pancha_pakshi_natal_moon_identity_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )

    assert result.astronomical_paksha is expected_astronomical
    assert result.profile_paksha is expected_profile
    assert tuple(x.locator_id for x in result.phase_mapping_source_locators) == (
        locator,
    )


def test_natal_computation_shares_one_reader_bound_tt_across_every_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, tt_calls, planet_calls, ayanamsa_calls = _install_astronomy(
        monkeypatch,
        sun_longitude=20.0,
        moon_longitude=100.0,
        ayanamsa_deg=20.0,
    )

    result = pakshi.pancha_pakshi_natal_moon_identity_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )

    assert tt_calls == [(_JD_UT1, reader)]
    assert [call[0] for call in planet_calls] == [Body.SUN, Body.MOON]
    for _, jd_ut1, kwargs in planet_calls:
        assert jd_ut1 == _JD_UT1
        assert kwargs["reader"] is reader
        assert kwargs["jd_tt"] == _JD_TT
        assert kwargs["center"] == result.policy.position_origin
        assert kwargs["frame"] == "ecliptic"
        assert kwargs["apparent"] is result.policy.apparent
        assert kwargs["aberration"] is result.policy.aberration
        assert kwargs["grav_deflection"] is result.policy.grav_deflection
        assert kwargs["nutation"] is result.policy.nutation
    assert ayanamsa_calls == [(_JD_TT, sidereal.Ayanamsa.LAHIRI, "true")]
    assert result.requested_jd_tt == _JD_TT
    assert result.moon_sidereal_longitude_deg == 80.0
    assert result.nakshatra_index == 6
    assert result.nakshatra == "Punarvasu"
    assert result.bird_mapping.bird is pakshi.PanchaPakshiBird.OWL
    assert result.bird_mapping.provenance is result.provenance
    assert result.policy.composition_status == "modern_moira_policy_not_source_claim"
    assert result.provenance.astronomical_routing_status == (
        "natal_moon_identity_performed_modern_lahiri_composition_no_schedule_"
        "materialization_current_cell_scoring_or_forecast"
    )

    with pytest.raises(FrozenInstanceError):
        result.bird = pakshi.PanchaPakshiBird.VULTURE  # type: ignore[misc]
    with pytest.raises(ValueError, match="bird mapping disagrees"):
        replace(result, bird=pakshi.PanchaPakshiBird.VULTURE)


def test_natal_vessel_rejects_self_consistent_false_index_and_bird(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, _, _, _ = _install_astronomy(
        monkeypatch,
        sun_longitude=20.0,
        moon_longitude=100.0,
        ayanamsa_deg=20.0,
    )
    result = pakshi.pancha_pakshi_natal_moon_identity_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )
    false_mapping = replace(
        pakshi.pancha_pakshi_nakshatra_bird_mapping(
            _PROFILE_ID,
            profile_paksha=result.profile_paksha,
            nakshatra_index=0,
        ),
        provenance=result.provenance,
    )

    assert false_mapping.nakshatra == "Ashwini"
    assert false_mapping.bird is pakshi.PanchaPakshiBird.VULTURE
    with pytest.raises(ValueError, match="shared sidereal classification"):
        replace(
            result,
            nakshatra_index=0,
            nakshatra="Ashwini",
            degrees_in_nakshatra=0.0,
            bird=false_mapping.bird,
            bird_mapping=false_mapping,
        )


@pytest.mark.parametrize("boundary_number", range(27))
def test_natal_route_uses_shared_exact_nakshatra_boundary_ownership(
    monkeypatch: pytest.MonkeyPatch,
    boundary_number: int,
) -> None:
    boundary = boundary_number * 40.0 / 3.0
    reader, _, _, _ = _install_astronomy(
        monkeypatch,
        sun_longitude=boundary,
        moon_longitude=boundary,
        ayanamsa_deg=0.0,
    )

    result = pakshi.pancha_pakshi_natal_moon_identity_at(
        _PROFILE_ID,
        _JD_UT1,
        reader=reader,
    )

    assert result.nakshatra_index == boundary_number
    assert result.nakshatra == sidereal.NAKSHATRA_NAMES[boundary_number]
    assert result.degrees_in_nakshatra == 0.0


@pytest.mark.requires_ephemeris
def test_de441_natal_route_is_structurally_coherent_not_a_pancha_oracle(
    reader: object,
) -> None:
    """Exercise substrate composition only; DE441 is not a doctrine witness."""

    result = pakshi.pancha_pakshi_natal_moon_identity_at(
        _PROFILE_ID,
        2_461_241.5,
        reader=reader,
    )
    pure_mapping = pakshi.pancha_pakshi_nakshatra_bird_mapping(
        _PROFILE_ID,
        profile_paksha=result.profile_paksha,
        nakshatra_index=result.nakshatra_index,
    )

    assert all(
        math.isfinite(value)
        for value in (
            result.requested_jd_ut1,
            result.requested_jd_tt,
            result.ayanamsa_deg,
            result.moon_sidereal_longitude_deg,
        )
    )
    assert result.requested_jd_tt > result.requested_jd_ut1
    assert 0.0 <= result.moon_sidereal_longitude_deg < 360.0
    assert result.bird is result.bird_mapping.bird
    assert result.bird is pure_mapping.bird
    assert result.bird_mapping.profile_paksha is pure_mapping.profile_paksha
    assert result.bird_mapping.nakshatra_index == pure_mapping.nakshatra_index
    assert result.bird_mapping.source_locators == pure_mapping.source_locators
