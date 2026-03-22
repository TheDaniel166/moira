"""
Unit and property-based tests for the Fixed Stars API modules.

Unit tests (6.x): use mocking — no catalog file needed.
Property tests (8.x): marked @pytest.mark.requires_ephemeris — require sefstars.txt.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dummy_star(name: str = "Aldebaran"):
    """Return a minimal StarPosition-like mock."""
    from moira.fixed_stars import StarPosition
    return StarPosition(
        name=name,
        nomenclature="alTau",
        longitude=69.5,
        latitude=-5.5,
        magnitude=0.87,
    )


def _dummy_gaia_position(source_index: int = 7):
    from moira.gaia import GaiaStarPosition, StellarQuality
    return GaiaStarPosition(
        source_index=source_index,
        longitude=69.5,
        latitude=-5.5,
        magnitude=0.9,
        bp_rp=1.1,
        teff_k=5000.0,
        parallax_mas=10.0,
        distance_ly=326.156,
        quality=StellarQuality("Fire", "Sun", True, True),
        is_topocentric=False,
        is_true_pos=False,
    )


class TestPhase1TruthPreservation:
    def test_fixed_star_at_preserves_lookup_and_frame_truth(self):
        import moira.fixed_stars as fs

        record = fs._StarRecord(
            traditional_name="Algol",
            nomenclature="bePer",
            frame="2000",
            equinox_jd=2451545.0,
            ra_deg=10.0,
            dec_deg=20.0,
            pm_ra=0.0,
            pm_dec=0.0,
            parallax_mas=0.0,
            magnitude=2.1,
        )

        with patch.object(fs, "_ensure_loaded"), \
             patch.object(fs, "_catalog", {"algol": record}), \
             patch.object(fs, "_alt_index", {"beper": "algol"}), \
             patch.object(fs, "icrf_to_true_ecliptic", return_value=(123.0, 4.5, 1.0)):
            pos = fs.fixed_star_at("bePer", 2451545.0)

        assert pos.longitude == 123.0
        assert pos.latitude == 4.5
        assert pos.computation_truth is not None
        assert pos.computation_truth.lookup_mode == "nomenclature"
        assert pos.computation_truth.frame_path == "icrf_to_true_ecliptic"
        assert pos.computation_truth.parallax_applied is False
        assert pos.computation_truth.matched_name == "Algol"
        assert pos.classification is not None
        assert pos.classification.lookup_kind == "nomenclature"
        assert pos.classification.frame_kind == "icrf"
        assert pos.classification.parallax_state == "not_applied"

    def test_star_at_preserves_merge_truth(self):
        import moira.stars as stars

        with patch.object(stars._hip_mod, "_ensure_loaded"), \
             patch.object(
                 stars,
                 "fixed_star_at",
                 return_value=stars.StarPosition(
                     name="Aldebaran",
                     nomenclature="alTau",
                     longitude=69.5,
                     latitude=-5.5,
                     magnitude=0.87,
                 ),
             ), \
             patch.object(stars, "_find_gaia_match", return_value=_dummy_gaia_position()):
            result = stars.star_at("Aldebaran", 2451545.0)

        assert result.source == "both"
        assert result.computation_truth is not None
        assert result.computation_truth.lookup_kind == "named_lookup"
        assert result.computation_truth.gaia_match_status == "matched"
        assert result.computation_truth.gaia_source_index == 7
        assert result.classification is not None
        assert result.classification.lookup_kind == "named_lookup"
        assert result.classification.source_kind == "both"
        assert result.classification.merge_state == "matched"

    def test_heliacal_rising_event_preserves_search_truth_and_wrapper_semantics(self):
        import moira.fixed_stars as fs

        dummy_pos = fs.StarPosition(
            name="Sirius",
            nomenclature="alCMa",
            longitude=30.0,
            latitude=0.0,
            magnitude=1.0,
        )
        dummy_sun = MagicMock(longitude=0.0)

        with patch.object(fs, "star_magnitude", return_value=1.0), \
             patch.object(fs, "fixed_star_at", return_value=dummy_pos), \
             patch("moira.planets.planet_at", return_value=dummy_sun), \
             patch.object(fs, "_find_star_rise", return_value=100.25), \
             patch.object(fs, "_sun_altitude", return_value=-10.0):
            event = fs.heliacal_rising_event("Sirius", 100.0, 51.5, -0.1, search_days=3)
            jd = fs.heliacal_rising("Sirius", 100.0, 51.5, -0.1, search_days=3)

        assert event is not None
        assert jd == 100.25
        assert event.jd_ut == jd
        assert event.truth.event_kind == "rising"
        assert event.truth.star_name == "Sirius"
        assert event.truth.arcus_visionis == 10.0
        assert event.truth.qualifying_day_offset == 0
        assert event.classification is not None
        assert event.classification.event_kind == "rising"
        assert event.classification.visibility_basis == "heliacal_visibility"
        assert event.classification.threshold_mode == "first_visible"


class TestPhase3InspectabilityAndHardening:
    def test_convenience_properties_are_derived_from_star_truth(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        pos = fs.StarPosition(
            name="Algol",
            nomenclature="bePer",
            longitude=10.0,
            latitude=5.0,
            magnitude=2.1,
            computation_truth=fs.StarPositionTruth(
                queried_name="bePer",
                lookup_mode="nomenclature",
                matched_name="Algol",
                matched_nomenclature="bePer",
                source_frame="2000",
                frame_path="icrf_to_true_ecliptic",
                catalog_epoch_jd=2451545.0,
                parallax_applied=False,
            ),
            classification=fs.StarPositionClassification(
                lookup_kind="nomenclature",
                frame_kind="icrf",
                parallax_state="not_applied",
            ),
        )
        event = fs.HeliacalEvent(
            jd_ut=100.25,
            truth=fs.HeliacalEventTruth(
                event_kind="rising",
                star_name="Sirius",
                jd_start=100.0,
                search_days=3,
                arcus_visionis=10.0,
                elongation_threshold=12.0,
                conjunction_offset=0,
                qualifying_day_offset=0,
                qualifying_elongation=30.0,
                qualifying_sun_altitude=-10.0,
                event_jd_ut=100.25,
            ),
            classification=fs.HeliacalEventClassification(
                event_kind="rising",
                visibility_basis="heliacal_visibility",
                threshold_mode="first_visible",
            ),
        )
        star = stars.FixedStar(
            name="Aldebaran",
            nomenclature="alTau",
            longitude=69.5,
            latitude=-5.5,
            magnitude=0.87,
            source="both",
            is_topocentric=False,
            computation_truth=stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                gaia_source_index=7,
                is_topocentric=False,
                true_position=False,
                dedup_applied=False,
            ),
            classification=stars.FixedStarClassification(
                lookup_kind="named_lookup",
                source_kind="both",
                merge_state="matched",
                observer_mode="geocentric",
            ),
        )

        assert pos.lookup_kind == "nomenclature"
        assert pos.frame_kind == "icrf"
        assert pos.parallax_state == "not_applied"
        assert pos.source_frame == "2000"
        assert event.event_kind == "rising"
        assert event.visibility_basis == "heliacal_visibility"
        assert event.threshold_mode == "first_visible"
        assert event.found_event is True
        assert star.lookup_kind == "named_lookup"
        assert star.source_kind == "both"
        assert star.merge_state == "matched"
        assert star.observer_mode == "geocentric"
        assert star.gaia_match_status == "matched"
        assert star.dedup_applied is False

    def test_invalid_truth_or_classification_drift_fails_loudly(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="lookup_mode"):
            fs.StarPositionTruth(
                queried_name="Algol",
                lookup_mode="unsupported",
                matched_name="Algol",
                matched_nomenclature="bePer",
                source_frame="2000",
                frame_path="icrf_to_true_ecliptic",
                catalog_epoch_jd=2451545.0,
                parallax_applied=False,
            )

        with pytest.raises(ValueError, match="classification must match truth"):
            fs.HeliacalEvent(
                jd_ut=100.25,
                truth=fs.HeliacalEventTruth(
                    event_kind="rising",
                    star_name="Sirius",
                    jd_start=100.0,
                    search_days=3,
                    arcus_visionis=10.0,
                    elongation_threshold=12.0,
                    conjunction_offset=0,
                    qualifying_day_offset=0,
                    qualifying_elongation=30.0,
                    qualifying_sun_altitude=-10.0,
                    event_jd_ut=100.25,
                ),
                classification=fs.HeliacalEventClassification(
                    event_kind="setting",
                    visibility_basis="heliacal_visibility",
                    threshold_mode="last_visible",
                ),
            )

        with pytest.raises(ValueError, match="gaia_match_status"):
            stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="unsupported",
                is_topocentric=False,
            )


class TestPhase4PolicySurface:
    def test_narrower_lookup_policy_can_disable_prefix_resolution(self):
        import moira.fixed_stars as fs

        record = fs._StarRecord(
            traditional_name="Algol",
            nomenclature="bePer",
            frame="2000",
            equinox_jd=2451545.0,
            ra_deg=10.0,
            dec_deg=20.0,
            pm_ra=0.0,
            pm_dec=0.0,
            parallax_mas=0.0,
            magnitude=2.1,
        )

        with patch.object(fs, "_ensure_loaded"), \
             patch.object(fs, "_catalog", {"algol": record}), \
             patch.object(fs, "_alt_index", {}), \
             patch.object(fs, "icrf_to_true_ecliptic", return_value=(123.0, 4.5, 1.0)):
            default_result = fs.fixed_star_at("Alg", 2451545.0)
            with pytest.raises(KeyError):
                fs.fixed_star_at(
                    "Alg",
                    2451545.0,
                    policy=fs.FixedStarComputationPolicy(
                        lookup=fs.FixedStarLookupPolicy(allow_prefix_lookup=False),
                    ),
                )

        assert default_result.name == "Algol"

    def test_narrower_unified_policy_can_disable_gaia_enrichment(self):
        import moira.stars as stars

        with patch.object(stars._hip_mod, "_ensure_loaded"), \
             patch.object(
                 stars,
                 "fixed_star_at",
                 return_value=stars.StarPosition(
                     name="Aldebaran",
                     nomenclature="alTau",
                     longitude=69.5,
                     latitude=-5.5,
                     magnitude=0.87,
                 ),
             ), \
             patch.object(stars, "_find_gaia_match", return_value=_dummy_gaia_position()):
            default_result = stars.star_at("Aldebaran", 2451545.0)
            policy_result = stars.star_at(
                "Aldebaran",
                2451545.0,
                policy=stars.UnifiedStarComputationPolicy(
                    merge=stars.UnifiedStarMergePolicy(enable_gaia_enrichment=False),
                ),
            )

        assert default_result.source == "both"
        assert policy_result.source == "hipparcos"

    def test_invalid_star_policies_fail_clearly(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="allow_prefix_lookup"):
            fs.fixed_star_at(
                "Algol",
                2451545.0,
                policy=fs.FixedStarComputationPolicy(
                    lookup=fs.FixedStarLookupPolicy(allow_prefix_lookup="yes"),  # type: ignore[arg-type]
                ),
            )

        with pytest.raises(ValueError, match="max_gaia_magnitude"):
            stars.star_at(
                "Aldebaran",
                2451545.0,
                policy=stars.UnifiedStarComputationPolicy(
                    merge=stars.UnifiedStarMergePolicy(
                        min_gaia_magnitude=5.0,
                        max_gaia_magnitude=4.0,
                    ),
                ),
            )


class TestPhase5Relations:
    def test_star_position_and_heliacal_event_relations_are_explicit(self):
        import moira.fixed_stars as fs

        record = fs._StarRecord(
            traditional_name="Algol",
            nomenclature="bePer",
            frame="2000",
            equinox_jd=2451545.0,
            ra_deg=10.0,
            dec_deg=20.0,
            pm_ra=0.0,
            pm_dec=0.0,
            parallax_mas=0.0,
            magnitude=2.1,
        )

        with patch.object(fs, "_ensure_loaded"), \
             patch.object(fs, "_catalog", {"algol": record}), \
             patch.object(fs, "_alt_index", {"beper": "algol"}), \
             patch.object(fs, "icrf_to_true_ecliptic", return_value=(123.0, 4.5, 1.0)):
            pos = fs.fixed_star_at("bePer", 2451545.0)

        assert pos.relation is not None
        assert pos.relation.kind == "catalog_lookup"
        assert pos.relation.basis == "named_star_lookup"
        assert pos.relation.star_name == "Algol"

        dummy_pos = fs.StarPosition(
            name="Sirius",
            nomenclature="alCMa",
            longitude=30.0,
            latitude=0.0,
            magnitude=1.0,
        )
        dummy_sun = MagicMock(longitude=0.0)
        with patch.object(fs, "star_magnitude", return_value=1.0), \
             patch.object(fs, "fixed_star_at", return_value=dummy_pos), \
             patch("moira.planets.planet_at", return_value=dummy_sun), \
             patch.object(fs, "_find_star_rise", return_value=100.25), \
             patch.object(fs, "_sun_altitude", return_value=-10.0):
            event = fs.heliacal_rising_event("Sirius", 100.0, 51.5, -0.1, search_days=3)

        assert event is not None
        assert event.relation is not None
        assert event.relation.kind == "heliacal_event"
        assert event.relation.basis == "heliacal_visibility"
        assert event.relation.event_kind == "rising"

    def test_unified_star_relation_is_explicit(self):
        import moira.stars as stars

        with patch.object(stars._hip_mod, "_ensure_loaded"), \
             patch.object(
                 stars,
                 "fixed_star_at",
                 return_value=stars.StarPosition(
                     name="Aldebaran",
                     nomenclature="alTau",
                     longitude=69.5,
                     latitude=-5.5,
                     magnitude=0.87,
                 ),
             ), \
             patch.object(stars, "_find_gaia_match", return_value=_dummy_gaia_position()):
            result = stars.star_at("Aldebaran", 2451545.0)

        assert result.relation is not None
        assert result.relation.kind == "catalog_merge"
        assert result.relation.basis == "named_lookup"
        assert result.relation.source_kind == "both"
        assert result.relation.gaia_source_index == 7

    def test_relation_drift_fails_loudly(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="star position relation must match"):
            fs.StarPosition(
                name="Algol",
                nomenclature="bePer",
                longitude=10.0,
                latitude=5.0,
                magnitude=2.1,
                relation=fs.StarRelation(
                    kind="catalog_lookup",
                    basis="named_star_lookup",
                    star_name="Wrong",
                    reference="bePer",
                ),
            )

        with pytest.raises(ValueError, match="fixed star relation must match"):
            stars.FixedStar(
                name="Aldebaran",
                nomenclature="alTau",
                longitude=69.5,
                latitude=-5.5,
                magnitude=0.87,
                source="hipparcos",
                is_topocentric=False,
                computation_truth=stars.FixedStarTruth(
                    lookup_kind="named_lookup",
                    hipparcos_name="Aldebaran",
                    source_mode="hipparcos",
                    gaia_match_status="not_found",
                    is_topocentric=False,
                ),
                classification=stars.FixedStarClassification(
                    lookup_kind="named_lookup",
                    source_kind="hipparcos",
                    merge_state="unmatched",
                    observer_mode="geocentric",
                ),
                relation=stars.UnifiedStarRelation(
                    kind="catalog_merge",
                    basis="magnitude_search",
                    star_name="Aldebaran",
                    source_kind="hipparcos",
                ),
            )


class TestPhase6RelationInspectabilityAndHardening:
    def test_relation_helpers_are_derived_only(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        position_relation = fs.StarRelation(
            kind="catalog_lookup",
            basis="named_star_lookup",
            star_name="Algol",
            reference="bePer",
        )
        event_relation = fs.StarRelation(
            kind="heliacal_event",
            basis="heliacal_visibility",
            star_name="Sirius",
            event_kind="rising",
        )
        unified_relation = stars.UnifiedStarRelation(
            kind="catalog_merge",
            basis="named_lookup",
            star_name="Aldebaran",
            source_kind="both",
            gaia_source_index=7,
        )

        assert position_relation.is_catalog_lookup is True
        assert position_relation.is_heliacal_event is False
        assert event_relation.is_heliacal_event is True
        assert event_relation.is_catalog_lookup is False
        assert unified_relation.is_named_lookup is True
        assert unified_relation.is_search_relation is False
        assert unified_relation.is_merged_source is True

        position = fs.StarPosition(
            name="Algol",
            nomenclature="bePer",
            longitude=10.0,
            latitude=5.0,
            magnitude=2.1,
            relation=position_relation,
        )
        event = fs.HeliacalEvent(
            jd_ut=100.25,
            truth=fs.HeliacalEventTruth(
                event_kind="rising",
                star_name="Sirius",
                jd_start=100.0,
                search_days=3,
                arcus_visionis=10.0,
                elongation_threshold=12.0,
                conjunction_offset=0,
                qualifying_day_offset=0,
                qualifying_elongation=30.0,
                qualifying_sun_altitude=-10.0,
                event_jd_ut=100.25,
            ),
            relation=event_relation,
        )
        unified_star = stars.FixedStar(
            name="Aldebaran",
            nomenclature="alTau",
            longitude=69.5,
            latitude=-5.5,
            magnitude=0.87,
            source="both",
            is_topocentric=False,
            computation_truth=stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                gaia_source_index=7,
                is_topocentric=False,
            ),
            classification=stars.FixedStarClassification(
                lookup_kind="named_lookup",
                source_kind="both",
                merge_state="matched",
                observer_mode="geocentric",
            ),
            relation=unified_relation,
        )

        assert position.relation_kind == "catalog_lookup"
        assert position.relation_basis == "named_star_lookup"
        assert position.has_relation is True
        assert event.relation_kind == "heliacal_event"
        assert event.relation_basis == "heliacal_visibility"
        assert event.has_relation is True
        assert unified_star.relation_kind == "catalog_merge"
        assert unified_star.relation_basis == "named_lookup"
        assert unified_star.has_relation is True

    def test_invalid_relation_shapes_fail_loudly(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="must not carry event_kind"):
            fs.StarRelation(
                kind="catalog_lookup",
                basis="named_star_lookup",
                star_name="Algol",
                reference="bePer",
                event_kind="rising",
            )

        with pytest.raises(ValueError, match="must not carry lookup reference"):
            fs.StarRelation(
                kind="heliacal_event",
                basis="heliacal_visibility",
                star_name="Sirius",
                reference="alCMa",
                event_kind="rising",
            )

        with pytest.raises(ValueError, match="gaia-only unified star relation must preserve gaia_source_index"):
            stars.UnifiedStarRelation(
                kind="catalog_merge",
                basis="proximity_search",
                star_name="",
                source_kind="gaia",
            )


class TestPhase7ConditionProfiles:
    def test_condition_profiles_are_aligned_and_derived_only(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        position = fs.StarPosition(
            name="Algol",
            nomenclature="bePer",
            longitude=10.0,
            latitude=5.0,
            magnitude=2.1,
            computation_truth=fs.StarPositionTruth(
                queried_name="bePer",
                lookup_mode="nomenclature",
                matched_name="Algol",
                matched_nomenclature="bePer",
                source_frame="2000",
                frame_path="icrf_to_true_ecliptic",
                catalog_epoch_jd=2451545.0,
                parallax_applied=False,
            ),
            classification=fs.StarPositionClassification(
                lookup_kind="nomenclature",
                frame_kind="icrf",
                parallax_state="not_applied",
            ),
            relation=fs.StarRelation(
                kind="catalog_lookup",
                basis="named_star_lookup",
                star_name="Algol",
                reference="bePer",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="fixed_star_position",
                condition_state=fs.StarConditionState("catalog_position"),
                relation_kind="catalog_lookup",
                relation_basis="named_star_lookup",
                lookup_kind="nomenclature",
            ),
        )
        event = fs.HeliacalEvent(
            jd_ut=100.25,
            truth=fs.HeliacalEventTruth(
                event_kind="rising",
                star_name="Sirius",
                jd_start=100.0,
                search_days=3,
                arcus_visionis=10.0,
                elongation_threshold=12.0,
                conjunction_offset=0,
                qualifying_day_offset=0,
                qualifying_elongation=30.0,
                qualifying_sun_altitude=-10.0,
                event_jd_ut=100.25,
            ),
            classification=fs.HeliacalEventClassification(
                event_kind="rising",
                visibility_basis="heliacal_visibility",
                threshold_mode="first_visible",
            ),
            relation=fs.StarRelation(
                kind="heliacal_event",
                basis="heliacal_visibility",
                star_name="Sirius",
                event_kind="rising",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="heliacal_event",
                condition_state=fs.StarConditionState("heliacal_event"),
                relation_kind="heliacal_event",
                relation_basis="heliacal_visibility",
                event_kind="rising",
            ),
        )
        unified_star = stars.FixedStar(
            name="Aldebaran",
            nomenclature="alTau",
            longitude=69.5,
            latitude=-5.5,
            magnitude=0.87,
            source="both",
            is_topocentric=False,
            computation_truth=stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                gaia_source_index=7,
                is_topocentric=False,
            ),
            classification=stars.FixedStarClassification(
                lookup_kind="named_lookup",
                source_kind="both",
                merge_state="matched",
                observer_mode="geocentric",
            ),
            relation=stars.UnifiedStarRelation(
                kind="catalog_merge",
                basis="named_lookup",
                star_name="Aldebaran",
                source_kind="both",
                gaia_source_index=7,
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="unified_star",
                condition_state=fs.StarConditionState("unified_merge"),
                relation_kind="catalog_merge",
                relation_basis="named_lookup",
                lookup_kind="named_lookup",
                source_kind="both",
            ),
        )

        assert position.condition_state == "catalog_position"
        assert event.condition_state == "heliacal_event"
        assert unified_star.condition_state == "unified_merge"
        assert position.condition_profile is not None
        assert position.condition_profile.lookup_kind == "nomenclature"
        assert event.condition_profile is not None
        assert event.condition_profile.event_kind == "rising"
        assert unified_star.condition_profile is not None
        assert unified_star.condition_profile.source_kind == "both"

    def test_condition_profile_drift_fails_loudly(self):
        import moira.fixed_stars as fs

        with pytest.raises(ValueError, match="event_kind|condition profile must match"):
            fs.HeliacalEvent(
                jd_ut=100.25,
                truth=fs.HeliacalEventTruth(
                    event_kind="rising",
                    star_name="Sirius",
                    jd_start=100.0,
                    search_days=3,
                    arcus_visionis=10.0,
                    elongation_threshold=12.0,
                    conjunction_offset=0,
                    qualifying_day_offset=0,
                    qualifying_elongation=30.0,
                    qualifying_sun_altitude=-10.0,
                    event_jd_ut=100.25,
                ),
                condition_profile=fs.StarConditionProfile(
                    result_kind="heliacal_event",
                    condition_state=fs.StarConditionState("catalog_position"),
                    relation_kind="catalog_lookup",
                    relation_basis="named_star_lookup",
                ),
            )


class TestPhase8ChartConditionProfile:
    def test_chart_condition_profile_is_deterministic_and_aligned(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        position = fs.StarPosition(
            name="Algol",
            nomenclature="bePer",
            longitude=10.0,
            latitude=5.0,
            magnitude=2.1,
            computation_truth=fs.StarPositionTruth(
                queried_name="bePer",
                lookup_mode="nomenclature",
                matched_name="Algol",
                matched_nomenclature="bePer",
                source_frame="2000",
                frame_path="icrf_to_true_ecliptic",
                catalog_epoch_jd=2451545.0,
                parallax_applied=False,
            ),
            classification=fs.StarPositionClassification(
                lookup_kind="nomenclature",
                frame_kind="icrf",
                parallax_state="not_applied",
            ),
            relation=fs.StarRelation(
                kind="catalog_lookup",
                basis="named_star_lookup",
                star_name="Algol",
                reference="bePer",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="fixed_star_position",
                condition_state=fs.StarConditionState("catalog_position"),
                relation_kind="catalog_lookup",
                relation_basis="named_star_lookup",
                lookup_kind="nomenclature",
            ),
        )
        event = fs.HeliacalEvent(
            jd_ut=100.25,
            truth=fs.HeliacalEventTruth(
                event_kind="rising",
                star_name="Sirius",
                jd_start=100.0,
                search_days=3,
                arcus_visionis=10.0,
                elongation_threshold=12.0,
                conjunction_offset=0,
                qualifying_day_offset=0,
                qualifying_elongation=30.0,
                qualifying_sun_altitude=-10.0,
                event_jd_ut=100.25,
            ),
            relation=fs.StarRelation(
                kind="heliacal_event",
                basis="heliacal_visibility",
                star_name="Sirius",
                event_kind="rising",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="heliacal_event",
                condition_state=fs.StarConditionState("heliacal_event"),
                relation_kind="heliacal_event",
                relation_basis="heliacal_visibility",
                event_kind="rising",
            ),
        )
        unified_star = stars.FixedStar(
            name="Aldebaran",
            nomenclature="alTau",
            longitude=69.5,
            latitude=-5.5,
            magnitude=0.87,
            source="both",
            computation_truth=stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                gaia_source_index=7,
                is_topocentric=False,
            ),
            classification=stars.FixedStarClassification(
                lookup_kind="named_lookup",
                source_kind="both",
                merge_state="matched",
                observer_mode="geocentric",
            ),
            relation=stars.UnifiedStarRelation(
                kind="catalog_merge",
                basis="named_lookup",
                star_name="Aldebaran",
                source_kind="both",
                gaia_source_index=7,
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="unified_star",
                condition_state=fs.StarConditionState("unified_merge"),
                relation_kind="catalog_merge",
                relation_basis="named_lookup",
                lookup_kind="named_lookup",
                source_kind="both",
            ),
        )

        chart = fs.star_chart_condition_profile(
            positions=[position],
            heliacal_events=[event],
            unified_stars=[unified_star],
        )

        assert chart.profile_count == 3
        assert chart.catalog_position_count == 1
        assert chart.heliacal_event_count == 1
        assert chart.unified_merge_count == 1
        assert len(chart.strongest_profiles) == 1
        assert chart.strongest_profiles[0].condition_state.name == "unified_merge"
        assert len(chart.weakest_profiles) == 1
        assert chart.weakest_profiles[0].condition_state.name == "catalog_position"

    def test_chart_condition_profile_drift_fails_loudly(self):
        import moira.fixed_stars as fs

        profile = fs.StarConditionProfile(
            result_kind="heliacal_event",
            condition_state=fs.StarConditionState("heliacal_event"),
            relation_kind="heliacal_event",
            relation_basis="heliacal_visibility",
            event_kind="rising",
        )

        with pytest.raises(ValueError, match="must match profiles"):
            fs.StarChartConditionProfile(
                profiles=(profile,),
                catalog_position_count=1,
                heliacal_event_count=0,
                unified_merge_count=0,
                strongest_profiles=(profile,),
                weakest_profiles=(profile,),
            )


class TestPhase9ConditionNetworkProfile:
    def test_condition_network_profile_is_deterministic_and_aligned(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        position = fs.StarPosition(
            name="Algol",
            nomenclature="bePer",
            longitude=10.0,
            latitude=5.0,
            magnitude=2.1,
            computation_truth=fs.StarPositionTruth(
                queried_name="bePer",
                lookup_mode="nomenclature",
                matched_name="Algol",
                matched_nomenclature="bePer",
                source_frame="2000",
                frame_path="icrf_to_true_ecliptic",
                catalog_epoch_jd=2451545.0,
                parallax_applied=False,
            ),
            classification=fs.StarPositionClassification(
                lookup_kind="nomenclature",
                frame_kind="icrf",
                parallax_state="not_applied",
            ),
            relation=fs.StarRelation(
                kind="catalog_lookup",
                basis="named_star_lookup",
                star_name="Algol",
                reference="bePer",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="fixed_star_position",
                condition_state=fs.StarConditionState("catalog_position"),
                relation_kind="catalog_lookup",
                relation_basis="named_star_lookup",
                lookup_kind="nomenclature",
            ),
        )
        event = fs.HeliacalEvent(
            jd_ut=100.25,
            truth=fs.HeliacalEventTruth(
                event_kind="rising",
                star_name="Sirius",
                jd_start=100.0,
                search_days=3,
                arcus_visionis=10.0,
                elongation_threshold=12.0,
                conjunction_offset=0,
                qualifying_day_offset=0,
                qualifying_elongation=30.0,
                qualifying_sun_altitude=-10.0,
                event_jd_ut=100.25,
            ),
            relation=fs.StarRelation(
                kind="heliacal_event",
                basis="heliacal_visibility",
                star_name="Sirius",
                event_kind="rising",
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="heliacal_event",
                condition_state=fs.StarConditionState("heliacal_event"),
                relation_kind="heliacal_event",
                relation_basis="heliacal_visibility",
                event_kind="rising",
            ),
        )
        unified_star = stars.FixedStar(
            name="Aldebaran",
            nomenclature="alTau",
            longitude=69.5,
            latitude=-5.5,
            magnitude=0.87,
            source="both",
            computation_truth=stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                gaia_source_index=7,
                is_topocentric=False,
            ),
            classification=stars.FixedStarClassification(
                lookup_kind="named_lookup",
                source_kind="both",
                merge_state="matched",
                observer_mode="geocentric",
            ),
            relation=stars.UnifiedStarRelation(
                kind="catalog_merge",
                basis="named_lookup",
                star_name="Aldebaran",
                source_kind="both",
                gaia_source_index=7,
            ),
            condition_profile=fs.StarConditionProfile(
                result_kind="unified_star",
                condition_state=fs.StarConditionState("unified_merge"),
                relation_kind="catalog_merge",
                relation_basis="named_lookup",
                lookup_kind="named_lookup",
                source_kind="both",
            ),
        )

        network = fs.star_condition_network_profile(
            positions=[position],
            heliacal_events=[event],
            unified_stars=[unified_star],
        )

        assert len(network.nodes) == 6
        assert len(network.edges) == 3
        assert {edge.relation_kind for edge in network.edges} == {
            "catalog_lookup",
            "heliacal_event",
            "catalog_merge",
        }
        assert any(node.node_id == "star:Algol" for node in network.nodes)
        assert any(node.node_id == "star:Sirius" for node in network.nodes)
        assert any(node.node_id == "star:Aldebaran" for node in network.nodes)
        assert any(node.node_id == "source:catalog_lookup" for node in network.nodes)
        assert any(node.node_id == "source:both" for node in network.nodes)
        assert any(node.node_id == "event:rising" for node in network.nodes)

    def test_condition_network_profile_drift_fails_loudly(self):
        import moira.fixed_stars as fs

        node = fs.StarConditionNetworkNode(
            node_id="star:Algol",
            kind="star",
            incoming_count=0,
            outgoing_count=0,
        )
        edge = fs.StarConditionNetworkEdge(
            source_id="star:Algol",
            target_id="source:catalog_lookup",
            relation_kind="catalog_lookup",
            relation_basis="named_star_lookup",
            condition_state="catalog_position",
        )

        with pytest.raises(ValueError, match="must reference known nodes"):
            fs.StarConditionNetworkProfile(
                nodes=(node,),
                edges=(edge,),
                isolated_nodes=(),
                most_connected_nodes=(node,),
            )


class TestPhase10SubsystemHardening:
    def test_malformed_public_inputs_fail_deterministically(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="non-empty string"):
            fs.fixed_star_at("", 2451545.0)

        with pytest.raises(ValueError, match="jd_tt must be finite"):
            fs.fixed_star_at("Algol", float("nan"))

        with pytest.raises(ValueError, match="search_days must be a positive integer"):
            fs.heliacal_rising_event("Sirius", 100.0, 51.5, -0.1, search_days=0)

        with pytest.raises(ValueError, match="lat must be between -90 and 90"):
            fs.heliacal_setting_event("Sirius", 100.0, 95.0, -0.1)

        with pytest.raises(ValueError, match="observer_lat and observer_lon must be provided together"):
            stars.star_at("Aldebaran", 2451545.0, observer_lat=51.5)

        with pytest.raises(ValueError, match="orb must be positive"):
            stars.stars_near(15.0, 2451545.0, orb=0.0)

        with pytest.raises(ValueError, match="max_magnitude must be finite"):
            stars.stars_by_magnitude(2451545.0, max_magnitude=float("inf"))

    def test_policy_type_and_truth_misuse_fail_clearly(self):
        import moira.fixed_stars as fs
        import moira.stars as stars

        with pytest.raises(ValueError, match="FixedStarComputationPolicy"):
            fs.fixed_star_at("Algol", 2451545.0, policy="bad")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="UnifiedStarComputationPolicy"):
            stars.star_at("Aldebaran", 2451545.0, policy="bad")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must preserve gaia_source_index"):
            stars.FixedStarTruth(
                lookup_kind="named_lookup",
                hipparcos_name="Aldebaran",
                source_mode="both",
                gaia_match_status="matched",
                is_topocentric=False,
            )

        with pytest.raises(ValueError, match="must not preserve hipparcos_name"):
            stars.FixedStarTruth(
                lookup_kind="proximity_search",
                hipparcos_name="Aldebaran",
                source_mode="gaia",
                gaia_match_status="gaia_direct",
                gaia_source_index=7,
                is_topocentric=False,
            )

    def test_chart_and_network_directionality_invariants_fail_loudly(self):
        import moira.fixed_stars as fs

        profile = fs.StarConditionProfile(
            result_kind="unified_star",
            condition_state=fs.StarConditionState("unified_merge"),
            relation_kind="catalog_merge",
            relation_basis="named_lookup",
            lookup_kind="named_lookup",
            source_kind="both",
        )

        with pytest.raises(ValueError, match="counts must sum"):
            fs.StarChartConditionProfile(
                profiles=(profile,),
                catalog_position_count=0,
                heliacal_event_count=0,
                unified_merge_count=0,
                strongest_profiles=(profile,),
                weakest_profiles=(profile,),
            )

        source_node = fs.StarConditionNetworkNode(
            node_id="source:catalog_lookup",
            kind="source",
            incoming_count=0,
            outgoing_count=1,
        )
        star_node = fs.StarConditionNetworkNode(
            node_id="star:Algol",
            kind="star",
            incoming_count=1,
            outgoing_count=0,
        )
        bad_edge = fs.StarConditionNetworkEdge(
            source_id="star:Algol",
            target_id="source:catalog_lookup",
            relation_kind="catalog_lookup",
            relation_basis="named_star_lookup",
            condition_state="catalog_position",
        )

        with pytest.raises(ValueError, match="must originate from source nodes"):
            fs.StarConditionNetworkProfile(
                nodes=(source_node, star_node),
                edges=(bad_edge,),
                isolated_nodes=(),
                most_connected_nodes=(source_node, star_node),
            )


# ===========================================================================
# 6.1 — String constant values: tradition-based modules
# ===========================================================================

class TestRoyalStarConstants:
    def test_aldebaran(self):
        from moira.royal_stars import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_regulus(self):
        from moira.royal_stars import REGULUS
        assert REGULUS == "Regulus"

    def test_antares(self):
        from moira.royal_stars import ANTARES
        assert ANTARES == "Antares"

    def test_fomalhaut(self):
        from moira.royal_stars import FOMALHAUT
        assert FOMALHAUT == "Fomalhaut"


class TestBehenianStarConstants:
    def test_algol(self):
        from moira.behenian_stars import ALGOL
        assert ALGOL == "Algol"

    def test_alcyone(self):
        from moira.behenian_stars import ALCYONE
        assert ALCYONE == "Alcyone"

    def test_aldebaran(self):
        from moira.behenian_stars import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_capella(self):
        from moira.behenian_stars import CAPELLA
        assert CAPELLA == "Capella"

    def test_sirius(self):
        from moira.behenian_stars import SIRIUS
        assert SIRIUS == "Sirius"

    def test_procyon(self):
        from moira.behenian_stars import PROCYON
        assert PROCYON == "Procyon"

    def test_regulus(self):
        from moira.behenian_stars import REGULUS
        assert REGULUS == "Regulus"

    def test_algorab(self):
        from moira.behenian_stars import ALGORAB
        assert ALGORAB == "Algorab"

    def test_spica(self):
        from moira.behenian_stars import SPICA
        assert SPICA == "Spica"

    def test_arcturus(self):
        from moira.behenian_stars import ARCTURUS
        assert ARCTURUS == "Arcturus"

    def test_alphecca(self):
        from moira.behenian_stars import ALPHECCA
        assert ALPHECCA == "Alphecca"

    def test_antares(self):
        from moira.behenian_stars import ANTARES
        assert ANTARES == "Antares"

    def test_vega(self):
        from moira.behenian_stars import VEGA
        assert VEGA == "Vega"

    def test_algedi(self):
        from moira.behenian_stars import ALGEDI
        assert ALGEDI == "Algedi"

    def test_fomalhaut(self):
        from moira.behenian_stars import FOMALHAUT
        assert FOMALHAUT == "Fomalhaut"


class TestFixedStarGroupsConstants:
    def test_algol(self):
        from moira.fixed_star_groups import ALGOL
        assert ALGOL == "Algol"

    def test_vega(self):
        from moira.fixed_star_groups import VEGA
        assert VEGA == "Vega"

    def test_sirius(self):
        from moira.fixed_star_groups import SIRIUS
        assert SIRIUS == "Sirius"

    def test_ras_algethi(self):
        from moira.fixed_star_groups import RAS_ALGETHI
        assert RAS_ALGETHI == "Ras Algethi"

    def test_hyadum_i(self):
        from moira.fixed_star_groups import HYADUM_I
        assert HYADUM_I == "Hyadum I"

    def test_sterope(self):
        from moira.fixed_star_groups import STEROPE
        assert STEROPE == "Sterope I"


# ===========================================================================
# 6.2 — *_NAMES dict structure: tradition-based modules
# ===========================================================================

class TestRoyalStarNamesDict:
    def test_length(self):
        from moira.royal_stars import ROYAL_STAR_NAMES
        assert len(ROYAL_STAR_NAMES) == 4

    def test_keys_and_values(self):
        from moira.royal_stars import ROYAL_STAR_NAMES
        assert ROYAL_STAR_NAMES["Aldebaran"] == "Aldebaran"
        assert ROYAL_STAR_NAMES["Regulus"]   == "Regulus"
        assert ROYAL_STAR_NAMES["Antares"]   == "Antares"
        assert ROYAL_STAR_NAMES["Fomalhaut"] == "Fomalhaut"


class TestBehenianStarNamesDict:
    def test_length(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert len(BEHENIAN_STAR_NAMES) == 15

    def test_contains_algol(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert "Algol" in BEHENIAN_STAR_NAMES.values()

    def test_contains_spica(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert "Spica" in BEHENIAN_STAR_NAMES.values()


class TestFixedStarGroupsNamesDict:
    def test_contains_algol(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Algol" in FIXED_STAR_NAMES.values()

    def test_contains_vega(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Vega" in FIXED_STAR_NAMES.values()

    def test_contains_ras_algethi(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Ras Algethi" in FIXED_STAR_NAMES.values()

    def test_contains_hyadum_i(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Hyadum I" in FIXED_STAR_NAMES.values()


# ===========================================================================
# 6.3 — Group tuples in fixed_star_groups
# ===========================================================================

class TestGroupTuples:
    def test_pleiades(self):
        from moira.fixed_star_groups import PLEIADES
        assert PLEIADES == (
            "Alcyone", "Maia", "Electra", "Taygeta", "Merope", "Celaeno", "Sterope I",
        )

    def test_hyades(self):
        from moira.fixed_star_groups import HYADES
        assert HYADES == ("Ain", "Hyadum I", "Hyadum II")

    def test_ptolemy_stars_length(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert len(PTOLEMY_STARS) == 15

    def test_ptolemy_stars_contains_algol(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert "Algol" in PTOLEMY_STARS

    def test_ptolemy_stars_contains_fomalhaut(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert "Fomalhaut" in PTOLEMY_STARS


# ===========================================================================
# 6.4 — list_*() return types and contents
# ===========================================================================

class TestListFunctions:
    def test_list_royal_stars(self):
        from moira.royal_stars import list_royal_stars
        result = list_royal_stars()
        assert result == ["Aldebaran", "Regulus", "Antares", "Fomalhaut"]

    def test_list_behenian_stars_type_and_length(self):
        from moira.behenian_stars import list_behenian_stars
        result = list_behenian_stars()
        assert isinstance(result, list)
        assert len(result) == 15

    def test_list_behenian_stars_contains_algol(self):
        from moira.behenian_stars import list_behenian_stars
        assert "Algol" in list_behenian_stars()

    def test_list_behenian_stars_contains_spica(self):
        from moira.behenian_stars import list_behenian_stars
        assert "Spica" in list_behenian_stars()

    def test_list_pleiades(self):
        from moira.fixed_star_groups import list_pleiades, PLEIADES
        assert list_pleiades() == list(PLEIADES)

    def test_list_hyades(self):
        from moira.fixed_star_groups import list_hyades, HYADES
        assert list_hyades() == list(HYADES)

    def test_list_ptolemy_stars(self):
        from moira.fixed_star_groups import list_ptolemy_stars, PTOLEMY_STARS
        assert list_ptolemy_stars() == list(PTOLEMY_STARS)

    def test_list_taurus_stars_length(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        result = list_taurus_stars()
        assert isinstance(result, list)
        assert len(result) == 25

    def test_list_taurus_stars_contains_aldebaran(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        assert "Aldebaran" in list_taurus_stars()

    def test_list_taurus_stars_contains_alcyone(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        assert "Alcyone" in list_taurus_stars()

    def test_list_scorpius_stars_length(self):
        from moira.constellations.stars_scorpius import list_scorpius_stars
        result = list_scorpius_stars()
        assert isinstance(result, list)
        assert len(result) == 16

    def test_list_scorpius_stars_contains_antares(self):
        from moira.constellations.stars_scorpius import list_scorpius_stars
        assert "Antares" in list_scorpius_stars()


# ===========================================================================
# 6.5 — available_*() does not raise when catalog is empty
# ===========================================================================

class TestAvailableEmptyCatalog:
    def _patch_list_stars(self, module_path: str):
        return patch(f"{module_path}.list_stars", return_value=[])

    def test_available_royal_stars_empty(self):
        with patch("moira.royal_stars.list_stars", return_value=[]):
            from moira.royal_stars import available_royal_stars
            assert available_royal_stars() == []

    def test_available_behenian_stars_empty(self):
        with patch("moira.behenian_stars.list_stars", return_value=[]):
            from moira.behenian_stars import available_behenian_stars
            assert available_behenian_stars() == []

    def test_available_fixed_stars_empty(self):
        with patch("moira.fixed_star_groups.list_stars", return_value=[]):
            from moira.fixed_star_groups import available_fixed_stars
            assert available_fixed_stars() == []

    def test_available_taurus_stars_empty(self):
        with patch("moira.constellations.stars_taurus.list_stars", return_value=[]):
            from moira.constellations.stars_taurus import available_taurus_stars
            assert available_taurus_stars() == []

    def test_available_scorpius_stars_empty(self):
        with patch("moira.constellations.stars_scorpius.list_stars", return_value=[]):
            from moira.constellations.stars_scorpius import available_scorpius_stars
            assert available_scorpius_stars() == []

    def test_available_orion_stars_empty(self):
        with patch("moira.constellations.stars_orion.list_stars", return_value=[]):
            from moira.constellations.stars_orion import available_orion_stars
            assert available_orion_stars() == []


# ===========================================================================
# 6.6 — available_*() subset invariant with mocked catalog
# ===========================================================================

class TestAvailableSubsetInvariant:
    def test_royal_subset(self):
        partial = ["Aldebaran", "Vega", "Sirius"]
        with patch("moira.royal_stars.list_stars", return_value=partial):
            from moira.royal_stars import available_royal_stars, list_royal_stars
            avail = available_royal_stars()
            full  = list_royal_stars()
            assert set(avail) <= set(full)
            assert "Aldebaran" in avail
            assert "Vega" not in avail  # not in royal stars

    def test_behenian_subset(self):
        partial = ["Algol", "Spica", "Vega", "Sirius"]
        with patch("moira.behenian_stars.list_stars", return_value=partial):
            from moira.behenian_stars import available_behenian_stars, list_behenian_stars
            avail = available_behenian_stars()
            full  = list_behenian_stars()
            assert set(avail) <= set(full)

    def test_taurus_subset(self):
        partial = ["Aldebaran", "Alcyone", "Rigel"]
        with patch("moira.constellations.stars_taurus.list_stars", return_value=partial):
            from moira.constellations.stars_taurus import available_taurus_stars, list_taurus_stars
            avail = available_taurus_stars()
            full  = list_taurus_stars()
            assert set(avail) <= set(full)
            assert "Rigel" not in avail  # not a Taurus star

    def test_scorpius_subset(self):
        partial = ["Antares", "Shaula", "Vega"]
        with patch("moira.constellations.stars_scorpius.list_stars", return_value=partial):
            from moira.constellations.stars_scorpius import available_scorpius_stars, list_scorpius_stars
            avail = available_scorpius_stars()
            full  = list_scorpius_stars()
            assert set(avail) <= set(full)


# ===========================================================================
# 6.7 — Per-body function delegation (structural, no catalog)
# ===========================================================================

class TestPerBodyDelegation:
    def test_regulus_at_royal(self):
        dummy = _dummy_star("Regulus")
        with patch("moira.royal_stars.fixed_star_at", return_value=dummy):
            from moira.royal_stars import regulus_at
            result = regulus_at(2451545.0)
            assert result is dummy

    def test_algol_at_behenian(self):
        dummy = _dummy_star("Algol")
        with patch("moira.behenian_stars.fixed_star_at", return_value=dummy):
            from moira.behenian_stars import algol_at
            result = algol_at(2451545.0)
            assert result is dummy

    def test_aldebaran_at_taurus(self):
        dummy = _dummy_star("Aldebaran")
        with patch("moira.constellations.stars_taurus.fixed_star_at", return_value=dummy):
            from moira.constellations.stars_taurus import aldebaran_at
            result = aldebaran_at(2451545.0)
            assert result is dummy


# ===========================================================================
# 6.8 — String constant values: representative constellation modules
# ===========================================================================

class TestConstellationConstants:
    def test_taurus_aldebaran(self):
        from moira.constellations.stars_taurus import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_taurus_sterope_i(self):
        from moira.constellations.stars_taurus import STEROPE_I
        assert STEROPE_I == "Sterope I"

    def test_taurus_hyadum_i(self):
        from moira.constellations.stars_taurus import HYADUM_I
        assert HYADUM_I == "Hyadum I"

    def test_scorpius_antares(self):
        from moira.constellations.stars_scorpius import ANTARES
        assert ANTARES == "Antares"

    def test_orion_rigel(self):
        from moira.constellations.stars_orion import RIGEL
        assert RIGEL == "Rigel"

    def test_ursa_major_dubhe(self):
        from moira.constellations.stars_ursa_major import DUBHE
        assert DUBHE == "Dubhe"

    def test_draco_nodus_ii(self):
        from moira.constellations.stars_draco import NODUS_II
        assert NODUS_II == "Nodus II"

    def test_aquila_deneb_el_okab_borealis(self):
        from moira.constellations.stars_aquila import DENEB_EL_OKAB_BOREALIS
        assert DENEB_EL_OKAB_BOREALIS == "Deneb el Okab Borealis"


# ===========================================================================
# 6.9 — *_NAMES dict structure: representative constellation modules
# ===========================================================================

class TestConstellationNamesDicts:
    def test_taurus_length(self):
        from moira.constellations.stars_taurus import TAURUS_STAR_NAMES
        assert len(TAURUS_STAR_NAMES) == 25

    def test_scorpius_length(self):
        from moira.constellations.stars_scorpius import SCORPIUS_STAR_NAMES
        assert len(SCORPIUS_STAR_NAMES) == 16

    def test_orion_length(self):
        from moira.constellations.stars_orion import ORION_STAR_NAMES
        assert len(ORION_STAR_NAMES) == 12

    def test_ursa_major_length(self):
        from moira.constellations.stars_ursa_major import URSA_MAJOR_STAR_NAMES
        assert len(URSA_MAJOR_STAR_NAMES) == 17


# ===========================================================================
# 8.x — Property-based tests (require sefstars.txt)
# ===========================================================================

try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    given = settings = st = None
    _HYPOTHESIS_AVAILABLE = False

_JD_STRATEGY = (
    st.floats(min_value=2415020.5, max_value=2488069.5)
    if _HYPOTHESIS_AVAILABLE else None
)


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_royal_star_at_delegation_roundtrip(jd):
    """Property 1: royal_star_at delegates correctly to fixed_star_at."""
    from moira.royal_stars import royal_star_at, list_royal_stars
    from moira.fixed_stars import fixed_star_at
    for name in list_royal_stars():
        r1 = royal_star_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_behenian_star_at_delegation_roundtrip(jd):
    """Property 1: behenian_star_at delegates correctly to fixed_star_at."""
    from moira.behenian_stars import behenian_star_at, list_behenian_stars
    from moira.fixed_stars import fixed_star_at
    for name in list_behenian_stars():
        r1 = behenian_star_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_fixed_star_group_at_delegation_roundtrip(jd):
    """Property 1: fixed_star_group_at delegates correctly to fixed_star_at."""
    from moira.fixed_star_groups import fixed_star_group_at, list_fixed_stars
    from moira.fixed_stars import fixed_star_at
    # Sample a representative subset to keep test fast
    sample = ["Algol", "Aldebaran", "Sirius", "Vega", "Antares", "Fomalhaut"]
    for name in sample:
        r1 = fixed_star_group_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_constellation_dispatcher_delegation_roundtrip(jd):
    """Property 1: constellation dispatchers delegate correctly to fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.constellations.stars_taurus import taurus_star_at, list_taurus_stars
    from moira.constellations.stars_scorpius import scorpius_star_at, list_scorpius_stars
    from moira.constellations.stars_orion import orion_star_at, list_orion_stars
    from moira.constellations.stars_ursa_major import ursa_major_star_at, list_ursa_major_stars

    for dispatcher, names in [
        (taurus_star_at,     list_taurus_stars()),
        (scorpius_star_at,   list_scorpius_stars()),
        (orion_star_at,      list_orion_stars()),
        (ursa_major_star_at, list_ursa_major_stars()),
    ]:
        for name in names:
            r1 = dispatcher(name, jd)
            r2 = fixed_star_at(name, jd)
            assert r1.longitude == r2.longitude
            assert r1.latitude  == r2.latitude
            assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_royal_per_body_identity(jd):
    """Property 2: per-body functions return correct name and match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.royal_stars import (
        aldebaran_at, regulus_at, antares_at, fomalhaut_at,
        ALDEBARAN, REGULUS, ANTARES, FOMALHAUT,
    )
    for fn, const in [
        (aldebaran_at, ALDEBARAN),
        (regulus_at,   REGULUS),
        (antares_at,   ANTARES),
        (fomalhaut_at, FOMALHAUT),
    ]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_behenian_per_body_identity(jd):
    """Property 2: behenian per-body functions match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.behenian_stars import algol_at, spica_at, vega_at, ALGOL, SPICA, VEGA
    for fn, const in [(algol_at, ALGOL), (spica_at, SPICA), (vega_at, VEGA)]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_constellation_per_body_identity(jd):
    """Property 2: constellation per-body functions match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.constellations.stars_taurus import aldebaran_at as tau_aldebaran_at, ALDEBARAN as TAU_ALDEBARAN
    from moira.constellations.stars_scorpius import antares_at as sco_antares_at, ANTARES as SCO_ANTARES
    from moira.constellations.stars_orion import rigel_at, RIGEL

    for fn, const in [
        (tau_aldebaran_at, TAU_ALDEBARAN),
        (sco_antares_at,   SCO_ANTARES),
        (rigel_at,         RIGEL),
    ]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
def test_availability_subset_invariant():
    """Property 3: available_*() is always a subset of list_*()."""
    from moira.royal_stars import available_royal_stars, list_royal_stars
    from moira.behenian_stars import available_behenian_stars, list_behenian_stars
    from moira.fixed_star_groups import (
        available_fixed_stars, list_fixed_stars,
        available_pleiades, list_pleiades,
    )
    from moira.constellations.stars_taurus import available_taurus_stars, list_taurus_stars
    from moira.constellations.stars_scorpius import available_scorpius_stars, list_scorpius_stars

    assert set(available_royal_stars())    <= set(list_royal_stars())
    assert set(available_behenian_stars()) <= set(list_behenian_stars())
    assert set(available_fixed_stars())    <= set(list_fixed_stars())
    assert set(available_pleiades())       <= set(list_pleiades())
    assert set(available_taurus_stars())   <= set(list_taurus_stars())
    assert set(available_scorpius_stars()) <= set(list_scorpius_stars())
