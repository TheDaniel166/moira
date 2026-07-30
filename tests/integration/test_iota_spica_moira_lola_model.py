from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.lunar_limb import LunarLimbAssetIdentity
from moira.lunar_occultation_contacts import (
    ContactSearchPolicy,
    LunarContactProfilePolicy,
    lunar_contact_star_at,
    lunar_star_topographic_contacts,
    prepare_lola_rdr_lunar_star_contact_profile,
)
from tests.tools.iota_contact_matching import (
    TimedContactWitness,
    minimum_residual_monotone_same_kind_match,
)


_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
_MODEL_FIXTURE = _FIXTURE_ROOT / "iota_spica_2024_moira_lola_model.json"
_OBSERVED_FIXTURE = _FIXTURE_ROOT / "iota_spica_2024_observed_contacts.json"
_SECONDS_PER_DAY = 86_400.0


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _site(payload: dict[str, object], site_id: str) -> dict[str, object]:
    return next(
        site for site in payload["sites"] if site["site_id"] == site_id
    )


def _expected_lola_assets(
    model: dict[str, object],
) -> tuple[LunarLimbAssetIdentity, ...]:
    return tuple(
        LunarLimbAssetIdentity(**cell["asset"])
        for cell in model["lola_stac_cells"]
    )


def _profile_policy(model: dict[str, object]) -> LunarContactProfilePolicy:
    payload = model["profile_policy"]
    return LunarContactProfilePolicy(
        trajectory_step_seconds=payload["trajectory_step_seconds"],
        position_angle_guard_deg=payload["position_angle_guard_deg"],
        profile_time_step_seconds=payload["profile_time_step_seconds"],
        pa_bin_width_deg=payload["pa_bin_width_deg"],
        max_pa_interpolation_gap_deg=payload["max_pa_interpolation_gap_deg"],
        lola_query_floor_km=payload["lola_query_floor_km"],
    )


def _relative_utc_seconds(value: str, origin_jd_utc: float) -> float:
    return (jd_from_datetime(_utc(value)) - origin_jd_utc) * _SECONDS_PER_DAY


def test_iota_spica_moira_model_fixture_keeps_evidence_classes_separate() -> None:
    model = _load(_MODEL_FIXTURE)
    observed = _load(_OBSERVED_FIXTURE)
    boundary = model["authority_boundary"]
    site = model["sites"][0]
    profile = model["profile_policy"]
    envelope = site["regression_envelope"]

    assert model["schema_version"] == 2
    assert set(model["evidence_classes"]) == {
        "authority_validation",
        "regression_parity",
        "physical_or_geometric_invariants",
    }
    evidence_scope = model["evidence_scope_by_class"]
    assert "does not supply a model residual tolerance" in evidence_scope[
        "authority_validation"
    ]
    assert "Moira-owned gates" in evidence_scope["regression_parity"]
    assert "solver residual/bracket contracts" in evidence_scope[
        "physical_or_geometric_invariants"
    ]
    assert model["product"] == (
        "moira_de441_lola_rdr_profile_conditioned_lunar_contact_chronology"
    )
    assert boundary["source_supplies_model_tolerance"] is False
    assert boundary["observational_uncertainties_are_model_tolerances"] is False
    assert boundary["grazprep_equivalence"] is False
    assert "not published" in boundary["grazprep_role"]
    assert "no absolute model-accuracy tolerance" in boundary["accuracy_claim"]
    assert "individual signed timing residuals" in boundary["authority_validation_scope"]
    assert observed["comparison_policy"]["model_comparison_status"] == (
        "admitted_in_separate_model_fixture"
    )
    assert observed["comparison_policy"]["model_comparison_fixture"] == (
        "tests/fixtures/iota_spica_2024_moira_lola_model.json"
    )
    assert observed["comparison_policy"]["model_contact_gate_s"] is None
    assert observed["comparison_policy"]["source_supplies_model_tolerance"] is False
    assert model["resource_admission"]["lola_asset_identity_retrieved_on"] == (
        "2026-07-18"
    )
    assert "not publisher-supplied checksums" in model["resource_admission"][
        "byte_identity_role"
    ]

    assets = _expected_lola_assets(model)
    assert len(assets) == 16
    assert len({asset.url for asset in assets}) == 16
    assert all(asset.url.startswith("https://asc-moon.s3-us-west-2.amazonaws.com/") for asset in assets)

    resource = model["resource_admission"]
    relief = resource["relief_envelope"]
    assert relief["nasa_lro_observed_highest_km"] == 10.786
    assert relief["nasa_lola_observed_approximate_absolute_km"] == 10.0
    assert relief["moira_max_absolute_relief_km"] == 12.0
    assert relief["missing_intersecting_cell_policy"] == "fail_closed"
    assert len(relief["observation_sources"]) == 2
    assert resource["work_bounds"] == {
        "maximum_profile_slices": 4096,
        "maximum_tiles": 96,
        "maximum_points_per_tile": 32_000_000,
        "maximum_cumulative_copc_node_points": 384_000_000,
        "maximum_tile_slice_projections": 320,
        "maximum_cumulative_point_projection_visits": 6_100_000_000,
    }
    assert len(resource["full_asset_set_sha256"]) == 64

    assert profile["profile_time_step_seconds"] == 15.0
    assert profile["pa_bin_width_deg"] == 0.002
    assert profile["max_pa_interpolation_gap_deg"] == profile["pa_bin_width_deg"]
    assert profile["silhouette_model"].endswith(
        "CENTER_SAMPLE_LINEAR_RECONSTRUCTION"
    )
    assert profile["sub_bin_topography_claim"] is False
    assert profile["mean_sphere_pa_bin_arc_m"] == pytest.approx(
        60.6467008483,
        abs=1.0e-6,
    )
    assert profile["empty_bin_policy"].startswith("fail_closed")
    assert _profile_policy(model).profile_time_step_seconds == 15.0
    assert [item["site_id"] for item in model["sites"]] == ["Dunham1", "Dunham2"]
    assert all(
        "not asserted as an exact WGS84" in item["observer_elevation_semantics"]
        for item in model["sites"]
    )
    assert site["height_sensitivity"]["role"].startswith("measured close-proxy")

    for admitted_site in model["sites"]:
        admitted_envelope = admitted_site["regression_envelope"]
        components = admitted_envelope["budget_components_s"]
        assert components["frozen_baseline_characterization"] >= admitted_site[
            "contact_regression"
        ]["matched_maximum_absolute_residual_s"]
        assert components["measured_height_endpoint_allowance"] == admitted_site[
            "height_sensitivity"
        ]["admitted_maximum_matched_feature_shift_s"]
        assert components["measured_height_endpoint_allowance"] >= admitted_site[
            "height_sensitivity"
        ]["measured_maximum_matched_feature_shift_s"]
        assert components["declared_root_polish_tolerance"] == model[
            "contact_search_policy"
        ]["time_tolerance_seconds"]
        assert components["reserved_reporting_and_model_drift_margin"] > 0.0
        assert sum(components.values()) == pytest.approx(
            admitted_envelope["maximum_absolute_observed_residual_s"],
            abs=1.0e-12,
        )
    assert "an absolute accuracy tolerance" in envelope["role"]
    assert model["extension_scope"]["admitted_sites"] == ["Dunham1", "Dunham2"]
    assert "Both published observing sites" in model["extension_scope"]["status"]
    assert all("height_sensitivity" in item for item in model["sites"])
    dunham2 = model["sites"][1]
    dunham2_topology = dunham2["topology_characterization"]
    assert dunham2_topology["required_extra_model_indices"] == [0, 1]
    assert "retained and required" in dunham2_topology["extra_contact_semantics"]
    first, second = dunham2["contact_regression"]["contacts"][:2]
    assert [first["kind"], second["kind"]] == [
        "disappearance",
        "reappearance",
    ]
    assert first["observed_match"] is None
    assert second["observed_match"] is None
    micro_pair_duration_s = (
        _utc(second["timestamp_utc"]) - _utc(first["timestamp_utc"])
    ).total_seconds()
    assert micro_pair_duration_s > model["contact_search_policy"][
        "scan_step_seconds"
    ]
    assert micro_pair_duration_s == pytest.approx(
        dunham2_topology["required_extra_pair_duration_s"],
        abs=dunham2_topology["required_extra_pair_duration_tolerance_s"],
    )
    assert dunham2_topology["required_extra_pair_duration_tolerance_s"] == (
        2.0 * model["contact_search_policy"]["time_tolerance_seconds"]
    )


@pytest.mark.integration
@pytest.mark.external_network
@pytest.mark.lola
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.serial
@pytest.mark.parametrize("site_id", ("Dunham1", "Dunham2"))
def test_iota_spica_moira_topology_regression(
    site_id: str,
    reader,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_property,
) -> None:
    """Run the full model while keeping authority timing and regression apart."""

    pytest.importorskip("requests")
    pytest.importorskip("laspy")
    pytest.importorskip("spiceypy")
    from moira import lunar_limb as lunar_limb_module

    model = _load(_MODEL_FIXTURE)
    observed = _load(_OBSERVED_FIXTURE)
    model_site = _site(model, site_id)
    observed_site = _site(observed, model_site["observed_site_id"])
    expected_assets = _expected_lola_assets(model)

    # A fresh bounded cache forces the official STAC mapping to be refreshed.
    # The full profile then uses the ordinary persistent cache, but each COPC
    # file is admitted against the exact frozen length and SHA-256 below.
    monkeypatch.delenv("MOIRA_NO_DOWNLOAD", raising=False)
    lunar_limb_module._lola_tile_asset_url.cache_clear()
    live_stac_urls = tuple(
        lunar_limb_module._lola_tile_asset_url(
            cell["lon_bin_deg"],
            cell["lat_bin_deg"],
            str(tmp_path / "fresh_stac"),
        )
        for cell in model["lola_stac_cells"]
    )
    assert live_stac_urls == tuple(asset.url for asset in expected_assets)

    window = model_site["search_window_utc"]
    jd_start_utc = jd_from_datetime(_utc(window["start"]))
    jd_end_utc = jd_from_datetime(_utc(window["end"]))
    # These are the only UTC -> UT1 crossings for model inputs.
    jd_start_ut1 = utc_to_ut1(jd_start_utc)
    jd_end_ut1 = utc_to_ut1(jd_end_utc)
    jd_reference_tt = _ut1_to_ephemeris_tt(
        (jd_start_ut1 + jd_end_ut1) / 2.0,
        reader,
    )
    target = lunar_contact_star_at(model["target"]["name"], jd_reference_tt)
    assert target.parallax_mas == model["target"]["parallax_mas"]
    assert target.barycentric_distance_km == pytest.approx(
        model["target"]["barycentric_distance_km"],
        rel=1.0e-15,
    )
    assert model["target"]["catalog_identity_contains"] in target.catalog_identifier
    assert target.coordinate_frame == model["target"]["coordinate_frame"]
    assert target.origin == model["target"]["origin"]

    profile_policy = _profile_policy(model)
    profile = prepare_lola_rdr_lunar_star_contact_profile(
        target,
        jd_start_ut1,
        jd_end_ut1,
        model_site["latitude_deg"],
        model_site["longitude_deg"],
        observer_elevation_m=model_site["observer_elevation_m"],
        reader=reader,
        policy=profile_policy,
        expected_lola_assets=expected_assets,
    )
    admitted_lola_assets = tuple(
        asset for asset in profile.source.assets if asset.url.endswith(".copc.laz")
    )
    assert {
        (asset.url, asset.byte_length, asset.sha256)
        for asset in admitted_lola_assets
    } == {
        (asset.url, asset.byte_length, asset.sha256)
        for asset in expected_assets
    }
    relief = model["resource_admission"]["relief_envelope"]
    assert profile.source.reference_radius_km == relief["reference_radius_km"]
    assert profile.source.relief_observed_highest_km == (
        relief["nasa_lro_observed_highest_km"]
    )
    assert profile.source.relief_observed_approximate_absolute_km == (
        relief["nasa_lola_observed_approximate_absolute_km"]
    )
    assert profile.source.relief_observation_sources == tuple(
        relief["observation_sources"]
    )
    assert profile.source.relief_acquisition_policy == (
        relief["moira_acquisition_policy"]
    )
    assert profile.source.max_absolute_relief_km == (
        relief["moira_max_absolute_relief_km"]
    )
    assert profile.source.silhouette_model == model["profile_policy"][
        "silhouette_model"
    ]
    assert len(profile.source.assets) == len(expected_assets) + 2
    assert profile.max_time_interpolation_gap_days == pytest.approx(
        profile_policy.profile_time_step_seconds / _SECONDS_PER_DAY,
        abs=1.0e-15,
    )
    profile_characterization = model_site["profile_characterization"]
    assert len(profile.slices) == profile_characterization["slice_count"]
    maximum_actual_slice_step_s = max(
        (right.jd_ut1 - left.jd_ut1) * _SECONDS_PER_DAY
        for left, right in zip(profile.slices, profile.slices[1:])
    )
    assert maximum_actual_slice_step_s == pytest.approx(
        profile_characterization["maximum_actual_slice_step_s"],
        abs=2.0e-6,
    )
    assert {
        len(profile_slice.position_angles_unwrapped_deg)
        for profile_slice in profile.slices
    } == {profile_characterization["bin_count_per_slice"]}
    if profile_characterization["all_bins_contiguous"]:
        assert all(
            all(
                right - left == pytest.approx(
                    profile_policy.pa_bin_width_deg,
                    abs=1.0e-12,
                )
                for left, right in zip(
                    profile_slice.position_angles_unwrapped_deg,
                    profile_slice.position_angles_unwrapped_deg[1:],
                )
            )
            for profile_slice in profile.slices
        )
    assert profile.slices[0].position_angle_start_unwrapped_deg == pytest.approx(
        profile_characterization["position_angle_start_unwrapped_deg"],
        abs=1.0e-12,
    )
    assert profile.slices[0].position_angle_end_unwrapped_deg == pytest.approx(
        profile_characterization["position_angle_end_unwrapped_deg"],
        abs=1.0e-12,
    )
    assert profile.source.spatial_query_half_width_km == pytest.approx(
        profile_characterization["spatial_query_half_width_km"],
        abs=1.0e-9,
    )
    for actual, expected in zip(
        profile.source.spatial_query_bounds_moon_xyz_km,
        profile_characterization["spatial_query_bounds_moon_xyz_km"],
    ):
        assert actual == pytest.approx(expected, abs=1.0e-9)
    assert [item.source_point_count for item in profile.slices] == (
        profile_characterization["source_point_counts"]
    )
    assert min(min(item.radii_km) for item in profile.slices) == pytest.approx(
        profile_characterization["minimum_radius_km"],
        abs=1.0e-9,
    )
    assert max(max(item.radii_km) for item in profile.slices) == pytest.approx(
        profile_characterization["maximum_radius_km"],
        abs=1.0e-9,
    )

    contact_policy = ContactSearchPolicy(**model["contact_search_policy"])
    result = lunar_star_topographic_contacts(
        target,
        jd_start_ut1,
        jd_end_ut1,
        model_site["latitude_deg"],
        model_site["longitude_deg"],
        observer_elevation_m=model_site["observer_elevation_m"],
        profile=profile,
        reader=reader,
        policy=contact_policy,
    )
    assert result.geometry_mode.value == model_site["geometry"]["mode"]
    assert model_site["geometry"]["provenance_contains"] in (
        result.geometry_provenance
    )
    assert result.profile_model == model["profile_policy"]["silhouette_model"]
    assert (
        "asset_set_sha256="
        + model["resource_admission"]["full_asset_set_sha256"]
    ) in result.profile_provenance
    assert (
        "realized_profile_sha256="
        + profile_characterization["realized_profile_sha256"]
    ) in result.profile_provenance

    topology = model_site["topology_characterization"]
    contact_regression = model_site["contact_regression"]
    assert "not external timing authority" in contact_regression["role"]
    required_contacts = result.contacts
    required_kinds = tuple(contact.kind.value for contact in required_contacts)
    assert all(
        abs(contact.signed_clearance_deg)
        <= contact_policy.clearance_tolerance_deg
        for contact in result.contacts
    )
    assert all(
        (contact.bracket_end_jd_ut1 - contact.bracket_start_jd_ut1)
        * _SECONDS_PER_DAY
        <= contact_policy.time_tolerance_seconds + 1.0e-12
        for contact in result.contacts
    )
    assert len(required_contacts) == topology["required_model_contact_count"]
    assert required_kinds == tuple(topology["required_model_kind_sequence"])
    assert len(contact_regression["contacts"]) == len(required_contacts)
    for contact, expected in zip(required_contacts, contact_regression["contacts"]):
        assert contact.kind.value == expected["kind"]
        expected_jd_utc = jd_from_datetime(_utc(expected["timestamp_utc"]))
        assert (contact.jd_utc - expected_jd_utc) * _SECONDS_PER_DAY == pytest.approx(
            0.0,
            abs=contact_regression["instant_tolerance_s"],
        )

    observed_witnesses = tuple(
        TimedContactWitness(
            label=contact["label"],
            kind=contact["kind"],
            epoch_seconds=_relative_utc_seconds(
                contact["timestamp_utc"],
                jd_start_utc,
            ),
        )
        for contact in observed_site["contacts"]
    )
    model_witnesses = tuple(
        TimedContactWitness(
            label=f"model-{index + 1}",
            kind=contact.kind.value,
            epoch_seconds=(contact.jd_utc - jd_start_utc) * _SECONDS_PER_DAY,
        )
        for index, contact in enumerate(required_contacts)
    )
    matched = minimum_residual_monotone_same_kind_match(
        observed_witnesses,
        model_witnesses,
    )
    assert matched.optimum_is_unique is topology["matching_optimum_is_unique"]
    assert matched.second_best_total_absolute_residual_seconds == (
        topology["second_best_total_absolute_residual_s"]
    )
    assert matched.second_best_margin_seconds == topology[
        "second_best_margin_s"
    ]
    assert tuple(match.model_index for match in matched.matches) == tuple(
        topology["observed_to_required_model_indices"]
    )
    assert matched.extra_model_indices == tuple(
        topology["required_extra_model_indices"]
    )
    if matched.extra_model_indices:
        assert matched.extra_model_indices == (0, 1)
        first_extra, second_extra = (
            required_contacts[index] for index in matched.extra_model_indices
        )
        assert (first_extra.kind.value, second_extra.kind.value) == (
            "disappearance",
            "reappearance",
        )
        extra_pair_duration_s = (
            second_extra.jd_ut1 - first_extra.jd_ut1
        ) * _SECONDS_PER_DAY
        assert extra_pair_duration_s > contact_policy.scan_step_seconds
        assert extra_pair_duration_s == pytest.approx(
            topology["required_extra_pair_duration_s"],
            abs=topology["required_extra_pair_duration_tolerance_s"],
        )
    assert tuple(
        None
        if expected["observed_match"] is None
        else expected["observed_match"]
        for expected in contact_regression["contacts"]
    ) == tuple(
        next(
            (
                match.observed_label
                for match in matched.matches
                if match.model_index == model_index
            ),
            None,
        )
        for model_index in range(len(required_contacts))
    )

    baseline_feature_epochs = {
        match.observed_label: required_contacts[match.model_index].jd_utc
        for match in matched.matches
    }
    height_sensitivity = model_site["height_sensitivity"]
    maximum_height_shift_s = 0.0
    for alternative_elevation_m in height_sensitivity[
        "tested_elevation_interval_m"
    ]:
        frozen_profile = replace(
            profile,
            observer_elevation_m=alternative_elevation_m,
        )
        alternative_result = lunar_star_topographic_contacts(
            target,
            jd_start_ut1,
            jd_end_ut1,
            model_site["latitude_deg"],
            model_site["longitude_deg"],
            observer_elevation_m=alternative_elevation_m,
            profile=frozen_profile,
            reader=reader,
            policy=contact_policy,
        )
        alternative_kinds = tuple(
            contact.kind.value for contact in alternative_result.contacts
        )
        assert alternative_kinds == required_kinds, (
            "observer-height endpoint changed the frozen model topology"
        )
        alternative_witnesses = tuple(
            TimedContactWitness(
                label=f"height-{index + 1}",
                kind=contact.kind.value,
                epoch_seconds=(contact.jd_utc - jd_start_utc) * _SECONDS_PER_DAY,
            )
            for index, contact in enumerate(alternative_result.contacts)
        )
        alternative_match = minimum_residual_monotone_same_kind_match(
            observed_witnesses,
            alternative_witnesses,
        )
        assert alternative_match.optimum_is_unique
        assert tuple(
            match.model_index for match in alternative_match.matches
        ) == tuple(match.model_index for match in matched.matches), (
            "observer-height endpoint changed observed-to-model root identity"
        )
        assert alternative_match.extra_model_indices == matched.extra_model_indices
        for match in alternative_match.matches:
            shifted_jd_utc = alternative_result.contacts[match.model_index].jd_utc
            maximum_height_shift_s = max(
                maximum_height_shift_s,
                abs(
                    shifted_jd_utc - baseline_feature_epochs[match.observed_label]
                )
                * _SECONDS_PER_DAY,
            )
    assert maximum_height_shift_s == pytest.approx(
        height_sensitivity["measured_maximum_matched_feature_shift_s"],
        abs=contact_regression["instant_tolerance_s"],
    )
    assert maximum_height_shift_s <= height_sensitivity[
        "admitted_maximum_matched_feature_shift_s"
    ]

    regression_envelope = model_site["regression_envelope"]
    assert matched.maximum_absolute_residual_seconds <= regression_envelope[
        "maximum_absolute_observed_residual_s"
    ], (
        "Moira's frozen topology-characterization envelope changed; this is "
        "not an IOTA accuracy gate"
    )
    assert matched.maximum_absolute_residual_seconds == pytest.approx(
        contact_regression["matched_maximum_absolute_residual_s"],
        abs=contact_regression["instant_tolerance_s"],
    )
    assert (
        matched.total_absolute_residual_seconds / len(matched.matches)
    ) == pytest.approx(
        contact_regression["matched_mean_absolute_residual_s"],
        abs=contact_regression["instant_tolerance_s"],
    )

    receipt = {
        "evidence_role": regression_envelope["role"],
        "authority_supplies_model_tolerance": False,
        "grazprep_equivalence": False,
        "site_id": site_id,
        "model_contacts": [
            {
                "index": index,
                "kind": contact.kind.value,
                "timestamp_utc": contact.datetime_utc.isoformat(
                    timespec="microseconds"
                ).replace("+00:00", "Z"),
            }
            for index, contact in enumerate(result.contacts)
        ],
        "matches": [
            {
                "observed_label": match.observed_label,
                "model_index": match.model_index,
                "kind": match.kind,
                "residual_seconds": match.residual_seconds,
            }
            for match in matched.matches
        ],
        "extra_model_contacts": [
            {
                "index": index,
                "kind": required_contacts[index].kind.value,
                "timestamp_utc": required_contacts[index].datetime_utc.isoformat(
                    timespec="microseconds"
                ).replace("+00:00", "Z"),
            }
            for index in matched.extra_model_indices
        ],
        "total_absolute_residual_seconds": (
            matched.total_absolute_residual_seconds
        ),
        "maximum_absolute_residual_seconds": (
            matched.maximum_absolute_residual_seconds
        ),
        "matching_optimum_is_unique": matched.optimum_is_unique,
        "maximum_frozen_profile_height_shift_seconds": (
            maximum_height_shift_s
        ),
        "geometry_mode": result.geometry_mode.value,
        "profile_model": result.profile_model,
    }
    record_property(
        f"iota_spica_{site_id.lower()}_moira_model_receipt",
        json.dumps(receipt, sort_keys=True),
    )
