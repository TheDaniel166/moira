"""Stage 2I source-scoped first-samam EAT-seed contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json"
)
_PRIOR_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20.json"
)
_DECISION_ID = "pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20"
_MANIFEST_SHA256 = (
    "d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8"
)
_ADMISSION_SHA256 = (
    "83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807"
)
_PRIOR_ADMISSION_SHA256 = (
    "9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd"
)
_SEMANTICS = (
    "profile_paksha_half_weekday_first_samam_eat_seed_not_padu_"
    "authority_condition_or_score"
)
_EXPECTED = {
    (pakshi.PanchaPakshiPaksha.PURVA, pakshi.PanchaPakshiHalf.DAY): (
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.PEACOCK,
    ),
    (pakshi.PanchaPakshiPaksha.PURVA, pakshi.PanchaPakshiHalf.NIGHT): (
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.OWL,
    ),
    (pakshi.PanchaPakshiPaksha.AMARA, pakshi.PanchaPakshiHalf.DAY): (
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.PEACOCK,
    ),
    (pakshi.PanchaPakshiPaksha.AMARA, pakshi.PanchaPakshiHalf.NIGHT): (
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.COCK,
    ),
}
_GENERATOR_LOCATORS = {
    (pakshi.PanchaPakshiPaksha.PURVA, pakshi.PanchaPakshiHalf.DAY): (
        "ia_n10",
        "ia_n16",
        "ia_n19_n20",
    ),
    (pakshi.PanchaPakshiPaksha.PURVA, pakshi.PanchaPakshiHalf.NIGHT): (
        "ia_n21",
        "ia_n22",
        "ia_n22_n25",
        "ia_n23",
    ),
    (pakshi.PanchaPakshiPaksha.AMARA, pakshi.PanchaPakshiHalf.DAY): (
        "ia_n26",
        "ia_n27_n30",
        "ia_n28",
    ),
    (pakshi.PanchaPakshiPaksha.AMARA, pakshi.PanchaPakshiHalf.NIGHT): (
        "ia_n31",
        "ia_n32",
        "ia_n32_n35",
        "ia_n33",
    ),
}


def _digest(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stage2i_manifest_bytes() -> bytes:
    """Project the append-only live manifest back to Stage 2I exactly."""

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20T23:28:13Z"
    manifest["profiles"] = [
        entry
        for entry in manifest["profiles"]
        if entry["profile_id"]
        != "bogamuni_chennai_2024_sookshma_temporal_selector"
    ]
    manifest["profiles"][0]["sha256"] = (
        "4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64"
    )
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def _mapping(
    *,
    profile_paksha: pakshi.PanchaPakshiPaksha = (
        pakshi.PanchaPakshiPaksha.PURVA
    ),
    half: pakshi.PanchaPakshiHalf = pakshi.PanchaPakshiHalf.DAY,
    weekday: pakshi.PanchaPakshiWeekday = pakshi.PanchaPakshiWeekday.SUNDAY,
) -> pakshi.PanchaPakshiFirstEatBirdMapping:
    return pakshi.pancha_pakshi_first_eat_bird_mapping(
        _PROFILE_ID,
        profile_paksha=profile_paksha,
        half=half,
        weekday=weekday,
    )


def test_stage2i_admission_chains_stage2h_and_binds_live_manifest() -> None:
    decision = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))

    assert hashlib.sha256(_stage2i_manifest_bytes()).hexdigest() == (
        _MANIFEST_SHA256
    )
    assert _digest(_ADMISSION_PATH) == _ADMISSION_SHA256
    assert _digest(_PRIOR_ADMISSION_PATH) == _PRIOR_ADMISSION_SHA256
    assert decision["decision_id"] == _DECISION_ID
    assert decision["prior_admission"] == {
        "decision_id": (
            "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20"
        ),
        "fixture_path": (
            "tests/fixtures/"
            "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20.json"
        ),
        "fixture_sha256": _PRIOR_ADMISSION_SHA256,
        "relationship": (
            "append_only_manifest_transition_on_existing_profile_after_stage_2h"
        ),
    }
    assert decision["manifest_transition"]["current_sha256"] == (
        _MANIFEST_SHA256
    )
    assert decision["manifest_transition"]["added_capability"] == (
        "first_eat_bird_mapping"
    )
    assert decision["manifest_transition"]["profile_count_changed"] is False
    assert decision["manifest_transition"]["profile_content_changed"] is False
    assert decision["computational_object"] == {
        "engine_function": "pancha_pakshi_first_eat_bird_mapping",
        "facade_method": "Moira.pancha_pakshi_first_eat_bird_mapping",
        "rest_route": "POST /v1/pancha-pakshi/schedule/first-eat-bird",
        "result_vessel": "PanchaPakshiFirstEatBirdMapping",
        "source_owned_object": "named_schedule_generator_first_samam_eat_seed",
        "input_axes": [
            "explicit_profile_id",
            "explicit_profile_paksha",
            "explicit_day_or_night_half",
            "explicit_weekday",
        ],
        "output": "one_first_eat_bird",
        "source_table_semantics": _SEMANTICS,
        "schedule_materialization": "not_performed",
        "temporal_routing": "not_performed",
        "profile_composition": "not_performed",
    }
    assert decision["validation_evidence"]["exact_source_cells"] == 28


def test_all_28_first_eat_cells_are_exact_and_match_nominal_schedules() -> None:
    results = []
    for (profile_paksha, half), expected_birds in _EXPECTED.items():
        for weekday, expected_bird in zip(
            pakshi.PanchaPakshiWeekday,
            expected_birds,
            strict=True,
        ):
            result = _mapping(
                profile_paksha=profile_paksha,
                half=half,
                weekday=weekday,
            )
            schedule = pakshi.pancha_pakshi_schedule(
                _PROFILE_ID,
                paksha=profile_paksha,
                half=half,
                weekday=weekday,
            )
            results.append(result)
            assert result.generator_id == schedule.generator_id
            assert result.first_eat_bird is expected_bird
            assert result.first_eat_bird is schedule.first_eat_bird
            assert schedule.cells[0].activity is pakshi.PanchaPakshiActivity.EAT
            assert schedule.cells[0].bird is result.first_eat_bird
            assert result.mapping_status == "direct_source_attested"
            assert result.source_table_semantics == _SEMANTICS
            assert tuple(
                locator.locator_id for locator in result.source_locators
            ) == _GENERATOR_LOCATORS[(profile_paksha, half)]
            assert all(
                locator.witness_id == result.provenance.source.witness_id
                for locator in result.source_locators
            )
            assert result.provenance.astronomical_routing_status == "not_performed"
            assert (
                pakshi.PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING
                in result.provenance.capabilities
            )

    assert len(results) == 28
    assert len(
        {
            (result.profile_paksha, result.half, result.weekday)
            for result in results
        }
    ) == 28


def test_first_eat_lookup_does_not_materialize_a_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("schedule materialization is outside this lookup")

    monkeypatch.setattr(
        internal,
        "generate_pancha_pakshi_schedule",
        fail_if_called,
    )

    result = _mapping()

    assert result.first_eat_bird is pakshi.PanchaPakshiBird.VULTURE


def test_first_eat_lookup_has_only_explicit_source_table_axes() -> None:
    signature = inspect.signature(pakshi.pancha_pakshi_first_eat_bird_mapping)

    assert tuple(signature.parameters) == (
        "profile_id",
        "profile_paksha",
        "half",
        "weekday",
    )
    for name in ("profile_paksha", "half", "weekday"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert not {
        "dt",
        "jd_ut1",
        "jd_utc",
        "latitude",
        "longitude",
        "natal_bird",
        "padu_bird",
        "authority_bird",
        "condition",
        "score",
    } & set(signature.parameters)


def test_first_eat_vessel_is_immutable_and_canonically_validated() -> None:
    result = _mapping()

    assert tuple(field.name for field in fields(result)) == (
        "profile_id",
        "generator_id",
        "profile_paksha",
        "half",
        "weekday",
        "first_eat_bird",
        "mapping_status",
        "source_table_semantics",
        "source_locators",
        "provenance",
    )
    with pytest.raises(FrozenInstanceError):
        result.first_eat_bird = pakshi.PanchaPakshiBird.OWL  # type: ignore[misc]
    with pytest.raises(ValueError, match="canonical source table"):
        replace(result, first_eat_bird=pakshi.PanchaPakshiBird.OWL)
    with pytest.raises(ValueError, match="generator_id disagrees"):
        replace(result, generator_id="purva_night")
    with pytest.raises(ValueError, match="not canonical generator locators"):
        replace(result, source_locators=tuple(reversed(result.source_locators)))
    with pytest.raises(ValueError, match="source_table_semantics"):
        replace(result, source_table_semantics="generic_authority_bird")
    with pytest.raises(ValueError, match="provenance is not canonical"):
        replace(
            result,
            provenance=replace(
                result.provenance,
                product_kind="forged_product_kind",
            ),
        )


@pytest.mark.parametrize(
    ("profile_paksha", "half", "weekday"),
    (
        (
            "purva",
            pakshi.PanchaPakshiHalf.DAY,
            pakshi.PanchaPakshiWeekday.SUNDAY,
        ),
        (
            pakshi.PanchaPakshiPaksha.PURVA,
            "day",
            pakshi.PanchaPakshiWeekday.SUNDAY,
        ),
        (
            pakshi.PanchaPakshiPaksha.PURVA,
            pakshi.PanchaPakshiHalf.DAY,
            "sunday",
        ),
    ),
)
def test_first_eat_lookup_rejects_untyped_axes(
    profile_paksha,
    half,
    weekday,
) -> None:
    with pytest.raises(TypeError):
        pakshi.pancha_pakshi_first_eat_bird_mapping(
            _PROFILE_ID,
            profile_paksha=profile_paksha,
            half=half,
            weekday=weekday,
        )


def test_first_eat_capability_is_isolated_to_the_1879_schedule_profile() -> None:
    descriptors = {
        descriptor.profile_id: descriptor
        for descriptor in pakshi.available_pancha_pakshi_profiles()
    }
    capability = pakshi.PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING

    assert capability in descriptors[_PROFILE_ID].capabilities
    assert capability not in descriptors[
        "bogamuni_chennai_2024_nakshatra_natal_identity"
    ].capabilities
    assert capability not in descriptors[
        "bogamuni_chennai_2024_padu_bird_mapping"
    ].capabilities
    with pytest.raises(ValueError, match="does not admit 'first_eat_bird_mapping'"):
        pakshi.pancha_pakshi_first_eat_bird_mapping(
            "bogamuni_chennai_2024_padu_bird_mapping",
            profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )


def test_first_eat_public_exports_and_facade_share_the_engine_contract() -> None:
    names = (
        "PanchaPakshiFirstEatBirdMapping",
        "pancha_pakshi_first_eat_bird_mapping",
    )
    for name in names:
        expected = getattr(pakshi, name)
        assert getattr(moira, name) is expected
        assert getattr(facade, name) is expected
        assert getattr(vedic, name) is expected

    method_signature = inspect.signature(
        facade.Moira.pancha_pakshi_first_eat_bird_mapping
    )
    assert tuple(method_signature.parameters) == (
        "self",
        "profile_id",
        "profile_paksha",
        "half",
        "weekday",
    )
    engine = object.__new__(facade.Moira)
    assert facade.Moira.pancha_pakshi_first_eat_bird_mapping(
        engine,
        _PROFILE_ID,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        half=pakshi.PanchaPakshiHalf.DAY,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
    ) == _mapping()


def test_first_eat_is_neither_padu_nor_authority_capability() -> None:
    result = _mapping()

    assert result.source_table_semantics == _SEMANTICS
    assert result.provenance.product_kind == "aksara_prasna_operating_schedule"
    assert pakshi.PanchaPakshiCapability.PADU_BIRD_MAPPING not in (
        result.provenance.capabilities
    )
    assert pakshi.PanchaPakshiCapability.AUTHORITY_BIRDS not in (
        result.provenance.capabilities
    )
    assert pakshi.PanchaPakshiCapability.CONDITION not in (
        result.provenance.capabilities
    )
    assert pakshi.PanchaPakshiCapability.SCORING not in (
        result.provenance.capabilities
    )
