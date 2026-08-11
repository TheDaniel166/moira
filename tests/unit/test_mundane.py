"""Pure atomic tests for neutral Mundane event/chart receipt composition."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

import moira.mundane as mundane
from moira.constants import Body, HouseSystem
from moira.cycles import great_conjunctions
from moira.eclipse import EclipseCalculator
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.mundane import (
    CardinalIngress,
    CardinalIngressReceipt,
    CardinalIngressSelectionEvidence,
    CardinalIngressSelectionPolicy,
    EclipseAnchorEpoch,
    EclipseContactEpochReceipt,
    EclipseContactKind,
    EclipseEventReceipt,
    EclipseKind,
    EclipseNamedEpochReceipt,
    JupiterSaturnConjunctionDefinition,
    JupiterSaturnConjunctionReceipt,
    JupiterSaturnConjunctionSequenceReceipt,
    MundaneEpoch,
    MundaneAngularRootToleranceReceipt,
    MundaneAscendantReceipt,
    MundaneEvaluationStatus,
    MundaneEventClockReceipt,
    MundaneEventChartProfile,
    MundaneEventEvidence,
    MundaneEventProvenance,
    MundaneHouseComputationReceipt,
    MundaneLocalProjectionEvidence,
    MundaneLocalProjectionReceipt,
    MundaneLocationRole,
    MundaneLocationSelectionReceipt,
    MundaneLongitudeDefinition,
    MundaneMotionState,
    MundaneNotEvaluable,
    MundaneNotEvaluableReason,
    MundaneProfileComponent,
    MundaneProfileProvenance,
    MundaneProvenanceMode,
    MundaneSearchInterval,
    MundaneTimescale,
    MundaneUtcRealizationStatus,
    MundaneZodiacModality,
    PrecedingSyzygyEvidence,
    PrecedingSyzygySelectionReceipt,
    PrimarySyzygyPhase,
    PrimarySyzygyReceipt,
    RameseyIngressCadenceReceipt,
    assess_transit_cardinal_ingress,
    assess_transit_primary_syzygy,
    assess_ramesey_ingress_cadence,
    build_mundane_event_clock,
    build_mundane_local_projection,
    compose_mundane_event_chart_profile,
    eclipse_receipt_from_event,
    jupiter_saturn_sequence_from_series,
    select_cardinal_ingresses,
    select_strictly_preceding_primary_syzygy,
)
from moira.transits import find_ingresses


USNO_SEASONS_2025 = "USNO Earth seasons, 2025 table"
USNO_PHASES_2025 = "USNO Moon phase API, 2025"
NASA_2024_ECLIPSE = "NASA/GSFC 2024-04-08 Besselian elements"
IMCCE_2020_CONJUNCTION = "IMCCE Jupiter-Saturn conjunction note, 2020"
MOIRA_SOLAR_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_solar_longitude_"
    "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
PRIMARY_SYZYGY_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_sun_moon_longitude_"
    "difference_iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
MOIRA_TRUE_OF_DATE_FRAME = (
    "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
MOIRA_SUN_MOON_CORRECTIONS = (
    "geocentric_apparent_light_time_annual_aberration_iau2006_frame_bias_"
    "precession_iau2000a_nutation_true_ecliptic_projection"
)
USNO_2025_COMPARISON_FAMILY = "usno_2025_season_phase_rounded_ut"
USNO_ROUNDED_SOLVER_SEMANTICS = "authority_epoch_rounded_to_minute_no_solver_claim"
JUPITER_SATURN_PRODUCT = (
    "moira_geocentric_apparent_jupiter_saturn_ecliptic_longitude_difference_"
    "true_ecliptic_of_date"
)
JUPITER_SATURN_FRAME = MOIRA_TRUE_OF_DATE_FRAME
JUPITER_SATURN_CORRECTIONS = (
    "geocentric_apparent_light_time_deflection_aberration_nutation"
)
TRACK_B_REFERENCE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "mundane_track_b_reference.json"
    ).read_text(encoding="utf-8")
)


class _ForgedEqualityString(str):
    """A hostile string whose equality claims every semantic identity matches."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


class _AlwaysEqualCardinalIngressReceipt(CardinalIngressReceipt):
    """A hostile receipt subtype that attempts to defeat anchor equality."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = None


class _HostileFloat(float):
    """A numeric subtype that lies about every ordering/equality relation."""

    def __lt__(self, other: object) -> bool:
        return True

    def __le__(self, other: object) -> bool:
        return True

    def __gt__(self, other: object) -> bool:
        return True

    def __ge__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = float.__hash__


def _always_equal_ingress(receipt: CardinalIngressReceipt):
    return _AlwaysEqualCardinalIngressReceipt(
        ingress=receipt.ingress,
        epoch=receipt.epoch,
        sun_longitude_deg=receipt.sun_longitude_deg,
        root_residual_deg=receipt.root_residual_deg,
        solver_tolerance_days=receipt.solver_tolerance_days,
        angular_root_tolerance=receipt.angular_root_tolerance,
        provenance=receipt.provenance,
        clock=receipt.clock,
        search_truth=receipt.search_truth,
    )


def _utc_jd(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
) -> float:
    """Encode a published UTC label as JD using the Unix epoch identity."""

    whole_second = int(second)
    fraction = second - whole_second
    instant = datetime(
        year,
        month,
        day,
        hour,
        minute,
        whole_second,
        tzinfo=timezone.utc,
    )
    return 2440587.5 + (instant.timestamp() + fraction) / 86400.0


def _external_provenance(
    source: str,
    *,
    method: str,
    mode: MundaneProvenanceMode = MundaneProvenanceMode.EXTERNAL_AUTHORITY,
    provenance_family: str | None = None,
    longitude_product: str = "authority_specific_longitude_product",
    reference_frame: str = "authority_specific_reference_frame",
    correction_regime: str = "authority_specific_correction_regime",
    solver_semantics: str = "authority_specific_epoch_semantics",
) -> MundaneEventProvenance:
    return MundaneEventProvenance(
        mode=mode,
        source_id=source,
        method_id=method,
        provenance_family_id=provenance_family or source,
        longitude_product_id=longitude_product,
        reference_frame=reference_frame,
        correction_regime=correction_regime,
        solver_semantics=solver_semantics,
        source_refs=(source,),
    )


def _root_tolerance(
    maximum_abs_residual_deg: float = 1e-8,
    *,
    basis: str = "synthetic exact-root composition fixture",
) -> MundaneAngularRootToleranceReceipt:
    return MundaneAngularRootToleranceReceipt(
        maximum_abs_residual_deg=maximum_abs_residual_deg,
        basis=basis,
    )


def _ingress(
    ingress: CardinalIngress,
    jd: float,
    *,
    source: str = USNO_SEASONS_2025,
) -> CardinalIngressReceipt:
    return CardinalIngressReceipt(
        ingress=ingress,
        epoch=MundaneEpoch(jd, MundaneTimescale.UTC),
        sun_longitude_deg=ingress.target_longitude_deg,
        root_residual_deg=0.0,
        solver_tolerance_days=60.0 / 86400.0,
        angular_root_tolerance=_root_tolerance(),
        provenance=_external_provenance(
            f"synthetic composition fixture using {source}",
            method="published_seasonal_anchor",
            mode=MundaneProvenanceMode.CALLER_ASSERTED,
            provenance_family=USNO_2025_COMPARISON_FAMILY,
            longitude_product=MOIRA_SOLAR_PRODUCT,
            reference_frame=MOIRA_TRUE_OF_DATE_FRAME,
            correction_regime=MOIRA_SUN_MOON_CORRECTIONS,
            solver_semantics=USNO_ROUNDED_SOLVER_SEMANTICS,
        ),
    )


def _syzygy(
    phase: PrimarySyzygyPhase,
    jd: float,
    *,
    timescale: MundaneTimescale = MundaneTimescale.UTC,
) -> PrimarySyzygyReceipt:
    sun = 353.0
    moon = 353.0 if phase is PrimarySyzygyPhase.NEW_MOON else 173.0
    return PrimarySyzygyReceipt(
        phase=phase,
        epoch=MundaneEpoch(jd, timescale),
        sun_longitude_deg=sun,
        moon_longitude_deg=moon,
        root_residual_deg=0.0,
        solver_tolerance_days=60.0 / 86400.0,
        angular_root_tolerance=_root_tolerance(),
        provenance=_external_provenance(
            f"synthetic composition fixture using {USNO_PHASES_2025}",
            method="published_primary_phase_anchor",
            mode=MundaneProvenanceMode.CALLER_ASSERTED,
            provenance_family=USNO_2025_COMPARISON_FAMILY,
            longitude_product=PRIMARY_SYZYGY_PRODUCT,
            reference_frame=MOIRA_TRUE_OF_DATE_FRAME,
            correction_regime=MOIRA_SUN_MOON_CORRECTIONS,
            solver_semantics=USNO_ROUNDED_SOLVER_SEMANTICS,
        ),
    )


def _jupiter_provenance(
    *,
    family: str = "jupiter_saturn_ecliptic_longitude_v1",
) -> MundaneEventProvenance:
    return MundaneEventProvenance(
        mode=MundaneProvenanceMode.CALLER_ASSERTED,
        source_id=IMCCE_2020_CONJUNCTION,
        method_id="published_or_moira_ecliptic_longitude_root",
        provenance_family_id=family,
        longitude_product_id=JUPITER_SATURN_PRODUCT,
        reference_frame=JUPITER_SATURN_FRAME,
        correction_regime=JUPITER_SATURN_CORRECTIONS,
        solver_semantics="synthetic_ecliptic_longitude_root_fixture",
        source_refs=(IMCCE_2020_CONJUNCTION,),
    )


def _interval(
    start_jd: float,
    end_jd: float,
    timescale: MundaneTimescale = MundaneTimescale.UTC,
) -> MundaneSearchInterval:
    return MundaneSearchInterval(
        MundaneEpoch(start_jd, timescale),
        MundaneEpoch(end_jd, timescale),
    )


def _eclipse_named_epoch(
    eclipse_id: str,
    eclipse_kind: EclipseKind,
    epoch_kind: EclipseAnchorEpoch,
    epoch: MundaneEpoch,
    provenance: MundaneEventProvenance,
) -> EclipseNamedEpochReceipt:
    return EclipseNamedEpochReceipt(
        eclipse_id=eclipse_id,
        eclipse_kind=eclipse_kind,
        epoch_kind=epoch_kind,
        epoch=epoch,
        provenance=provenance,
    )


def _anchor_evidence(receipt) -> MundaneEventEvidence:
    return MundaneEventEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        receipt=receipt,
        issue=None,
    )


def _not_evaluable_ingress_selection() -> CardinalIngressSelectionEvidence:
    return CardinalIngressSelectionEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        selection=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
            reason=MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
            missing_inputs=("complete_cardinal_ingress_cycle",),
            detail="No complete cardinal ingress selection was supplied for this fixture.",
        ),
    )


def _not_evaluable_syzygy() -> PrecedingSyzygyEvidence:
    return PrecedingSyzygyEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        selection=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY,
            reason=MundaneNotEvaluableReason.NO_STRICTLY_PRECEDING_SYZYGY,
            missing_inputs=("strictly_earlier_exact_new_or_full_moon",),
            detail="No preceding syzygy receipt was supplied for this fixture.",
        ),
    )


def _not_evaluable_projection(
    reason: MundaneNotEvaluableReason = MundaneNotEvaluableReason.MISSING_LOCATION,
) -> MundaneLocalProjectionEvidence:
    return MundaneLocalProjectionEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        receipt=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.LOCAL_CHART_PROJECTION,
            reason=reason,
            missing_inputs=("explicit_location", "explicit_house_system"),
            detail="No local chart is fabricated without caller-owned location policy.",
        ),
    )


def _whole_sign_houses() -> HouseCusps:
    return HouseCusps(
        system=HouseSystem.WHOLE_SIGN,
        cusps=tuple(float(value) for value in range(0, 360, 30)),
        asc=12.0,
        mc=281.0,
        armc=280.0,
        effective_system=HouseSystem.WHOLE_SIGN,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(HouseSystem.WHOLE_SIGN),
        policy=HousePolicy.strict(),
    )


def _local_projection_receipt(
    anchor_event,
    location: MundaneLocationSelectionReceipt,
    chart_epoch_kind: EclipseAnchorEpoch | None,
) -> MundaneLocalProjectionReceipt:
    if isinstance(anchor_event, EclipseEventReceipt):
        named_epoch = anchor_event.named_epoch_receipt(chart_epoch_kind)
        assert named_epoch is not None
        event_epoch = named_epoch.epoch
    else:
        event_epoch = anchor_event.event_epoch
    return MundaneLocalProjectionReceipt(
        anchor_event=anchor_event,
        house_computation=MundaneHouseComputationReceipt(
            event_epoch=event_epoch,
            location=location,
            requested_house_system=HouseSystem.WHOLE_SIGN,
        ),
        chart_epoch_kind=chart_epoch_kind,
    )


def test_event_receipts_are_frozen_and_reject_derived_residual_mismatch() -> None:
    receipt = _ingress(CardinalIngress.ARIES, 2460754.875)

    assert (
        receipt.longitude_definition
        is MundaneLongitudeDefinition.SUN_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_EQUINOX_OF_DATE
    )
    assert receipt.provenance.longitude_product_id == MOIRA_SOLAR_PRODUCT
    assert receipt.provenance.reference_frame == MOIRA_TRUE_OF_DATE_FRAME
    assert receipt.provenance.correction_regime == MOIRA_SUN_MOON_CORRECTIONS
    with pytest.raises(FrozenInstanceError):
        receipt.root_residual_deg = 1.0  # type: ignore[misc]
    with pytest.raises(ValueError, match="derive from longitude"):
        CardinalIngressReceipt(
            ingress=CardinalIngress.ARIES,
            epoch=receipt.epoch,
            sun_longitude_deg=0.0,
            root_residual_deg=0.1,
            solver_tolerance_days=1e-6,
            angular_root_tolerance=_root_tolerance(),
            provenance=receipt.provenance,
        )


def test_exact_root_receipts_reject_derived_but_nonzero_residuals() -> None:
    ingress = _ingress(CardinalIngress.ARIES, 2460754.875)
    with pytest.raises(ValueError, match="exceeds its admitted angular"):
        replace(
            ingress,
            sun_longitude_deg=10.0,
            root_residual_deg=10.0,
        )

    syzygy = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)
    with pytest.raises(ValueError, match="exceeds its admitted angular"):
        replace(
            syzygy,
            moon_longitude_deg=172.99,
            root_residual_deg=-0.01,
        )

    conjunction = JupiterSaturnConjunctionReceipt(
        event_id="synthetic_nonroot_guard",
        epoch=MundaneEpoch(2459205.25, MundaneTimescale.UTC),
        jupiter_longitude_deg=300.0,
        saturn_longitude_deg=300.0,
        root_residual_deg=0.0,
        jupiter_motion=MundaneMotionState.DIRECT,
        saturn_motion=MundaneMotionState.DIRECT,
        solver_tolerance_days=1e-8,
        angular_root_tolerance=_root_tolerance(),
        provenance=_jupiter_provenance(),
    )
    with pytest.raises(ValueError, match="exceeds its admitted angular"):
        replace(
            conjunction,
            jupiter_longitude_deg=320.0,
            root_residual_deg=20.0,
        )


def test_root_tolerance_cannot_be_widened_to_admit_a_nonroot() -> None:
    with pytest.raises(ValueError, match="no greater than"):
        MundaneAngularRootToleranceReceipt(
            maximum_abs_residual_deg=1.0,
            basis="caller-selected broad tolerance",
        )


def test_tuple_valued_receipts_reject_mutable_lists() -> None:
    with pytest.raises(TypeError, match="source_refs must be a built-in tuple"):
        MundaneEventProvenance(
            mode=MundaneProvenanceMode.CALLER_ASSERTED,
            source_id="fixture",
            method_id="fixture",
            provenance_family_id="fixture",
            longitude_product_id="fixture",
            reference_frame="fixture",
            correction_regime="fixture",
            solver_semantics="fixture",
            source_refs=["mutable"],  # type: ignore[arg-type]
        )


def test_semantic_identity_strings_reject_hostile_str_subclasses() -> None:
    ingress = _ingress(CardinalIngress.ARIES, 2460754.875)
    forged = _ForgedEqualityString("forged")

    with pytest.raises(ValueError, match="built-in string"):
        replace(
            ingress,
            provenance=replace(
                ingress.provenance,
                longitude_product_id=forged,
            ),
        )
    with pytest.raises(ValueError, match="built-in string"):
        replace(ingress.provenance, source_refs=(forged,))
    with pytest.raises(ValueError, match="built-in string"):
        replace(ingress, root_direction=forged)


def test_semantic_numbers_reject_hostile_float_subclasses_before_ordering() -> None:
    with pytest.raises(TypeError, match="built-in int or float"):
        MundaneEpoch(_HostileFloat(200.0), MundaneTimescale.UTC)
    with pytest.raises(TypeError, match="built-in int or float"):
        MundaneLocationSelectionReceipt(
            label="Impossible hostile location",
            latitude_deg=_HostileFloat(1000.0),
            longitude_deg_east=_HostileFloat(1000.0),
            role=MundaneLocationRole.USER_SPECIFIED,
            source_id="hostile numeric fixture",
        )

    anchor = _ingress(CardinalIngress.ARIES, 100.0)
    normal = _syzygy(PrimarySyzygyPhase.NEW_MOON, 90.0)
    forged_future = _syzygy(PrimarySyzygyPhase.FULL_MOON, 200.0)
    object.__setattr__(forged_future.epoch, "jd", _HostileFloat(200.0))
    with pytest.raises(TypeError, match="built-in int or float"):
        select_strictly_preceding_primary_syzygy(
            anchor,
            (normal, forged_future),
        )


def test_root_search_copy_rejects_non_builtin_numeric_truth() -> None:
    from moira.transits import CrossingSearchTruth

    truth = CrossingSearchTruth(
        search_start_jd_ut=2459999.0,
        search_end_jd_ut=2460001.0,
        step_days=1.0,
        bracket_start_jd_ut=2459999.999999,
        bracket_end_jd_ut=2460000.000001,
        crossing_jd_ut=2460000.0,
        solver_tolerance_days=1e-5,
    )
    truth.step_days = _HostileFloat(1.0)

    with pytest.raises(TypeError, match="exact built-in float fields"):
        mundane._root_search_receipt_from_truth(
            truth,
            reader=object(),
            residual_at=lambda jd: jd - 2460000.0,
            search_kind="hostile_numeric_fixture",
            solver_method_id="hostile_numeric_fixture",
            target_angle_deg=0.0,
        )


def test_primary_syzygy_adapter_rejects_non_exact_policy_before_reader_use() -> None:
    with pytest.raises(TypeError, match="exact TransitComputationPolicy"):
        assess_transit_primary_syzygy(
            _ingress(CardinalIngress.ARIES, 2460000.0),
            reader=object(),
            policy=object(),
        )


def test_evaluated_evidence_requires_exact_receipts_and_profile_revalidates() -> None:
    with pytest.raises(ValueError, match="requires only a receipt"):
        CardinalIngressSelectionEvidence(
            status=MundaneEvaluationStatus.EVALUATED,
            selection=object(),  # type: ignore[arg-type]
            issue=None,
        )


def test_receipt_subclass_cannot_forge_syzygy_or_profile_anchor_binding() -> None:
    original = _ingress(CardinalIngress.ARIES, 2460754.875)
    different = _ingress(CardinalIngress.CANCER, 2460754.875)
    candidate = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)
    forged = _always_equal_ingress(original)

    with pytest.raises(TypeError, match="anchor event must be a cardinal ingress"):
        PrecedingSyzygySelectionReceipt(
            anchor_event=forged,
            candidates=(candidate,),
            selected=candidate,
            comparison_timescale=MundaneTimescale.UTC,
        )
    with pytest.raises(TypeError, match="anchor_event must be a Mundane event receipt"):
        select_strictly_preceding_primary_syzygy(forged, (candidate,))

    evidence = select_strictly_preceding_primary_syzygy(original, (candidate,))
    assert evidence.selection is not None
    object.__setattr__(evidence.selection, "anchor_event", forged)
    with pytest.raises(TypeError, match="anchor event must be a cardinal ingress"):
        compose_mundane_event_chart_profile(
            anchor_event=_anchor_evidence(different),
            cardinal_ingress_selection=_not_evaluable_ingress_selection(),
            preceding_syzygy=evidence,
            local_projection=_not_evaluable_projection(),
        )
    with pytest.raises(ValueError, match="requires only a selection"):
        PrecedingSyzygyEvidence(
            status=MundaneEvaluationStatus.EVALUATED,
            selection=object(),  # type: ignore[arg-type]
            issue=None,
        )

    events = tuple(
        _ingress(ingress, 2460000.0 + index * 90.0)
        for index, ingress in enumerate(CardinalIngress)
    )
    selection = select_cardinal_ingresses(
        events,
        policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
        search_interval=_interval(2459999.0, 2460300.0),
    )
    object.__setattr__(selection, "selection", object())
    with pytest.raises(ValueError, match="requires only a receipt"):
        compose_mundane_event_chart_profile(
            anchor_event=_anchor_evidence(events[0]),
            cardinal_ingress_selection=selection,
            preceding_syzygy=_not_evaluable_syzygy(),
            local_projection=_not_evaluable_projection(),
        )
    with pytest.raises(TypeError, match="source_refs must be a built-in tuple"):
        MundaneProfileProvenance(source_refs=["mutable"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="missing_inputs must be a built-in tuple"):
        MundaneNotEvaluable(
            component=MundaneProfileComponent.ANCHOR_EVENT,
            reason=MundaneNotEvaluableReason.GLOBAL_EVENT_UNAVAILABLE,
            missing_inputs=["mutable"],  # type: ignore[arg-type]
            detail="Mutable receipt fixture.",
        )


def test_moira_provenance_cannot_be_faked_with_a_caller_asserted_digest() -> None:
    with pytest.raises(ValueError, match="content-derived reader identity"):
        MundaneEventProvenance(
            mode=MundaneProvenanceMode.MOIRA_EPHEMERIS,
            source_id="caller",
            method_id="caller",
            provenance_family_id="caller",
            longitude_product_id="caller",
            reference_frame="caller",
            correction_regime="caller",
            solver_semantics="caller",
            source_refs=("caller",),
            caller_asserted_artifact_id="DE441",
            caller_asserted_artifact_sha256="a" * 64,
        )


def test_neutral_ingress_enumeration_retains_all_four_supplied_roots() -> None:
    events = tuple(
        _ingress(ingress, 2460000.0 + index * 90.0)
        for index, ingress in enumerate(CardinalIngress)
    )

    evidence = select_cardinal_ingresses(
        events,
        policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
        search_interval=_interval(2459999.0, 2460300.0),
    )

    assert evidence.status is MundaneEvaluationStatus.EVALUATED
    assert evidence.selection is not None
    assert evidence.selection.all_events == events
    assert evidence.selection.selected_events == events
    with pytest.raises(ValueError, match="source reference is fixed"):
        replace(evidence.selection, source_reference="forged selection authority")


def test_all_four_ingress_receipt_rejects_a_selected_subset() -> None:
    events = tuple(
        _ingress(ingress, 2460000.0 + index * 90.0)
        for index, ingress in enumerate(CardinalIngress)
    )

    with pytest.raises(ValueError, match="must select all events"):
        replace(
            select_cardinal_ingresses(
                events,
                policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
                search_interval=_interval(2459999.0, 2460300.0),
            ).selection,
            selected_events=(events[0],),
        )
    selection = select_cardinal_ingresses(
        events,
        policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
        search_interval=_interval(2459999.0, 2460300.0),
    ).selection
    assert selection is not None
    with pytest.raises(TypeError, match="all_events must be a built-in tuple"):
        replace(
            selection,
            all_events=list(events),  # type: ignore[arg-type]
            selected_events=list(events),  # type: ignore[arg-type]
        )


def test_all_four_ingress_selection_rejects_cross_year_provenance_splice() -> None:
    events = tuple(
        _ingress(ingress, 2460000.0 + index * 90.0)
        for index, ingress in enumerate(CardinalIngress)
    )
    spliced = events[:-1] + (
        replace(
            events[-1],
            provenance=replace(
                events[-1].provenance,
                source_id="different source under same caller family",
                method_id="different method under same caller family",
                source_refs=("different source reference",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="homogeneous provenance"):
        select_cardinal_ingresses(
            spliced,
            policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
            search_interval=_interval(2459999.0, 2460300.0),
        )
    with pytest.raises(ValueError, match="limited to one cycle"):
        select_cardinal_ingresses(
            events,
            policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
            search_interval=_interval(2459500.0, 2460500.0),
        )

    mixed_tolerance = events[:-1] + (
        replace(
            events[-1],
            angular_root_tolerance=_root_tolerance(
                1e-7,
                basis="different root certification",
            ),
        ),
    )
    with pytest.raises(ValueError, match="one angular root tolerance"):
        select_cardinal_ingresses(
            mixed_tolerance,
            policy=CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1,
            search_interval=_interval(2459999.0, 2460300.0),
        )


def test_usno_fixture_selects_strictly_preceding_full_moon() -> None:
    # USNO rounded almanac anchors: equinox 2025-03-20 09:01 UTC and the
    # immediately preceding full Moon 2025-03-14 06:55 UTC.  This test proves
    # event ordering and policy selection, not minute-rounded root accuracy.
    equinox_jd = _utc_jd(2025, 3, 20, 9, 1)
    full_moon_jd = _utc_jd(2025, 3, 14, 6, 55)
    anchor = _ingress(CardinalIngress.ARIES, equinox_jd)
    preceding = _syzygy(PrimarySyzygyPhase.FULL_MOON, full_moon_jd)
    equal_to_anchor = _syzygy(PrimarySyzygyPhase.NEW_MOON, equinox_jd)
    following = _syzygy(
        PrimarySyzygyPhase.NEW_MOON,
        _utc_jd(2025, 3, 29, 10, 58),
    )

    evidence = select_strictly_preceding_primary_syzygy(
        anchor,
        (preceding, equal_to_anchor, following),
    )

    assert anchor.provenance.longitude_product_id == MOIRA_SOLAR_PRODUCT
    assert preceding.provenance.longitude_product_id == PRIMARY_SYZYGY_PRODUCT
    assert (
        anchor.provenance.longitude_product_id
        != preceding.provenance.longitude_product_id
    )
    assert evidence.status is MundaneEvaluationStatus.EVALUATED
    assert evidence.selection is not None
    assert evidence.selection.selected is preceding
    assert evidence.selection.selected.phase is PrimarySyzygyPhase.FULL_MOON
    assert evidence.selection.selected.epoch.jd < evidence.selection.anchor_epoch.jd


def test_equal_syzygy_does_not_count_as_strictly_preceding() -> None:
    jd = _utc_jd(2025, 3, 20, 9, 1)
    evidence = select_strictly_preceding_primary_syzygy(
        _ingress(CardinalIngress.ARIES, jd),
        (_syzygy(PrimarySyzygyPhase.NEW_MOON, jd),),
    )

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.NO_STRICTLY_PRECEDING_SYZYGY


def test_preceding_syzygy_receipt_rejects_a_non_nearest_direct_selection() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    older = _syzygy(PrimarySyzygyPhase.NEW_MOON, 2460734.0)
    nearer = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)
    evidence = select_strictly_preceding_primary_syzygy(anchor, (older, nearer))
    assert evidence.selection is not None

    with pytest.raises(ValueError, match="nearest strictly earlier"):
        replace(evidence.selection, selected=older)
    with pytest.raises(TypeError, match="candidates must be a built-in tuple"):
        replace(
            evidence.selection,
            candidates=[older, nearer],  # type: ignore[arg-type]
        )


def test_mixed_timescales_fail_closed_without_conversion_receipt() -> None:
    evidence = select_strictly_preceding_primary_syzygy(
        _ingress(CardinalIngress.ARIES, 2460754.875),
        (
            _syzygy(
                PrimarySyzygyPhase.FULL_MOON,
                2460748.75,
                timescale=MundaneTimescale.TT,
            ),
        ),
    )

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.NO_COMMON_TIMESCALE


@pytest.mark.parametrize(
    ("field", "replacement_value", "expected_reason"),
    (
        (
            "provenance_family_id",
            "unrelated_authority_product",
            MundaneNotEvaluableReason.INCOMPATIBLE_PROVENANCE,
        ),
        (
            "mode",
            MundaneProvenanceMode.HISTORICAL_TABLE,
            MundaneNotEvaluableReason.INCOMPATIBLE_PROVENANCE,
        ),
    ),
)
def test_syzygy_selection_fails_closed_on_comparison_contract_mismatch(
    field: str,
    replacement_value: str | MundaneProvenanceMode,
    expected_reason: MundaneNotEvaluableReason,
) -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    candidate = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)
    incompatible = replace(
        candidate,
        provenance=replace(
            candidate.provenance,
            **{field: replacement_value},
        ),
    )

    evidence = select_strictly_preceding_primary_syzygy(anchor, (incompatible,))

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.selection is None
    assert evidence.issue is not None
    assert evidence.issue.reason is expected_reason


def test_syzygy_candidates_require_complete_homogeneous_provenance() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    older = _syzygy(PrimarySyzygyPhase.NEW_MOON, 2460734.0)
    nearer = replace(
        _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75),
        provenance=replace(
            older.provenance,
            source_id="different source under same family",
            method_id="different method under same family",
            source_refs=("different source reference",),
        ),
    )

    evidence = select_strictly_preceding_primary_syzygy(anchor, (older, nearer))

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.INCOMPATIBLE_PROVENANCE


def test_syzygy_selection_fails_closed_on_caller_asserted_artifact_mismatch() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    candidate = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)
    anchor = replace(
        anchor,
        provenance=replace(
            anchor.provenance,
            caller_asserted_artifact_id="authority-table",
            caller_asserted_artifact_sha256="a" * 64,
        ),
    )
    candidate = replace(
        candidate,
        provenance=replace(
            candidate.provenance,
            caller_asserted_artifact_id="authority-table",
            caller_asserted_artifact_sha256="b" * 64,
        ),
    )

    evidence = select_strictly_preceding_primary_syzygy(anchor, (candidate,))

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.INCOMPATIBLE_KERNEL_IDENTITY


def test_primary_syzygy_rejects_an_invalid_longitude_product() -> None:
    receipt = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)

    with pytest.raises(ValueError, match="Primary syzygy provenance"):
        replace(
            receipt,
            provenance=replace(
                receipt.provenance,
                longitude_product_id=MOIRA_SOLAR_PRODUCT,
            ),
        )


@pytest.mark.parametrize(
    ("field", "replacement_value"),
    (
        ("reference_frame", "different_ecliptic_frame"),
        ("correction_regime", "geometric_not_apparent"),
    ),
)
def test_primary_syzygy_rejects_frame_or_correction_semantic_drift(
    field: str,
    replacement_value: str,
) -> None:
    receipt = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)

    with pytest.raises(ValueError, match="Primary syzygy provenance"):
        replace(
            receipt,
            provenance=replace(
                receipt.provenance,
                **{field: replacement_value},
            ),
        )


def test_syzygy_selection_allows_distinct_ingress_and_phase_solver_tolerances() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    candidate = replace(
        _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75),
        solver_tolerance_days=1.0 / 86400.0,
    )

    evidence = select_strictly_preceding_primary_syzygy(anchor, (candidate,))

    assert evidence.status is MundaneEvaluationStatus.EVALUATED
    assert evidence.selection is not None
    assert evidence.selection.selected is candidate


def test_syzygy_candidates_require_one_phase_solver_tolerance() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    new_moon = _syzygy(PrimarySyzygyPhase.NEW_MOON, 2460734.0)
    full_moon = replace(
        _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75),
        solver_tolerance_days=1.0 / 86400.0,
    )

    evidence = select_strictly_preceding_primary_syzygy(
        anchor,
        (new_moon, full_moon),
    )

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.INCOMPATIBLE_SOLVER_SEMANTICS


def test_syzygy_selection_requires_a_cardinal_ingress_anchor() -> None:
    anchor = _syzygy(PrimarySyzygyPhase.NEW_MOON, 2460754.875)
    candidate = _syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75)

    evidence = select_strictly_preceding_primary_syzygy(anchor, (candidate,))

    assert evidence.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert evidence.issue is not None
    assert evidence.issue.reason is MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH


def test_profile_rejects_syzygy_selection_from_different_same_epoch_anchor() -> None:
    anchor_jd = 2460754.875
    original_anchor = _ingress(CardinalIngress.ARIES, anchor_jd)
    selected = select_strictly_preceding_primary_syzygy(
        original_anchor,
        (_syzygy(PrimarySyzygyPhase.FULL_MOON, 2460748.75),),
    )
    different_anchor = _ingress(CardinalIngress.CANCER, anchor_jd)

    with pytest.raises(ValueError, match="complete profile anchor receipt"):
        MundaneEventChartProfile(
            anchor_event=_anchor_evidence(different_anchor),
            cardinal_ingress_selection=_not_evaluable_ingress_selection(),
            preceding_syzygy=selected,
            local_projection=_not_evaluable_projection(),
        )


def test_nasa_eclipse_fixture_preserves_three_noninterchangeable_epochs() -> None:
    greatest = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UTC
    )
    ecliptic = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 20, 49.7), MundaneTimescale.UTC
    )
    equatorial = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 36, 7.6), MundaneTimescale.UTC
    )

    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    receipt = EclipseEventReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=provenance,
        named_epochs=(
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
                ecliptic,
                provenance,
            ),
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.EQUATORIAL_CONJUNCTION,
                equatorial,
                provenance,
            ),
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.GREATEST_ECLIPSE,
                greatest,
                provenance,
            ),
        ),
    )

    assert receipt.event_epoch is greatest
    assert receipt.greatest_eclipse_epoch != receipt.ecliptic_syzygy_epoch
    assert receipt.ecliptic_syzygy_epoch != receipt.equatorial_conjunction_epoch
    assert (ecliptic.jd - greatest.jd) * 86400.0 == pytest.approx(211.4, abs=5e-5)
    assert (equatorial.jd - ecliptic.jd) * 86400.0 == pytest.approx(917.9, abs=5e-5)


def test_profile_source_inventory_retains_eclipse_subreceipt_sources() -> None:
    outer = _external_provenance(
        "outer eclipse catalog",
        method="catalog_event_identity",
        provenance_family="shared_eclipse_family",
    )
    named = _external_provenance(
        "named greatest-epoch solver",
        method="named_epoch_method",
        provenance_family="shared_eclipse_family",
    )
    receipt = EclipseEventReceipt(
        eclipse_id="source_inventory_eclipse",
        eclipse_kind=EclipseKind.SOLAR,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=outer,
        named_epochs=(
            _eclipse_named_epoch(
                "source_inventory_eclipse",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.GREATEST_ECLIPSE,
                MundaneEpoch(2460000.0, MundaneTimescale.UTC),
                named,
            ),
        ),
    )

    profile = compose_mundane_event_chart_profile(
        anchor_event=_anchor_evidence(receipt),
        cardinal_ingress_selection=_not_evaluable_ingress_selection(),
        preceding_syzygy=_not_evaluable_syzygy(),
        local_projection=_not_evaluable_projection(),
    )

    assert "outer eclipse catalog" in profile.provenance.source_refs
    assert "named greatest-epoch solver" in profile.provenance.source_refs


def test_eclipse_anchor_must_name_a_supplied_epoch() -> None:
    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    with pytest.raises(ValueError, match="selected eclipse anchor epoch"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.EQUATORIAL_CONJUNCTION,
            provenance=provenance,
            named_epochs=(
                _eclipse_named_epoch(
                    "nasa_se2024apr08",
                    EclipseKind.SOLAR,
                    EclipseAnchorEpoch.GREATEST_ECLIPSE,
                    MundaneEpoch(
                        _utc_jd(2024, 4, 8, 18, 17, 18.3),
                        MundaneTimescale.UTC,
                    ),
                    provenance,
                ),
            ),
        )


def test_eclipse_receipt_rejects_cross_event_epoch_splicing() -> None:
    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    greatest = _eclipse_named_epoch(
        "different_eclipse",
        EclipseKind.SOLAR,
        EclipseAnchorEpoch.GREATEST_ECLIPSE,
        MundaneEpoch(_utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UTC),
        provenance,
    )

    with pytest.raises(ValueError, match="belong to this eclipse"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=(greatest,),
        )

    same_id_greatest = replace(greatest, eclipse_id="nasa_se2024apr08")
    distant_syzygy = _eclipse_named_epoch(
        "nasa_se2024apr08",
        EclipseKind.SOLAR,
        EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
        MundaneEpoch(_utc_jd(2025, 4, 8, 18, 20), MundaneTimescale.UTC),
        provenance,
    )
    with pytest.raises(ValueError, match="bounded event window"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=(same_id_greatest, distant_syzygy),
        )


def test_eclipse_receipt_rejects_mutable_epoch_and_contact_lists() -> None:
    provenance = _external_provenance(
        NASA_2024_ECLIPSE,
        method="published_besselian_epoch_labels",
    )
    greatest = _eclipse_named_epoch(
        "nasa_se2024apr08",
        EclipseKind.SOLAR,
        EclipseAnchorEpoch.GREATEST_ECLIPSE,
        MundaneEpoch(_utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UTC),
        provenance,
    )
    with pytest.raises(TypeError, match="named_epochs must be a built-in tuple"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=[greatest],  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="global_contacts must be a built-in tuple"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=(greatest,),
            global_contacts=[],  # type: ignore[arg-type]
        )


def test_eclipse_receipt_rejects_wrong_contact_family_and_order() -> None:
    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    greatest = _eclipse_named_epoch(
        "nasa_se2024apr08",
        EclipseKind.SOLAR,
        EclipseAnchorEpoch.GREATEST_ECLIPSE,
        MundaneEpoch(_utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UTC),
        provenance,
    )
    with pytest.raises(ValueError, match="contact family"):
        EclipseContactEpochReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            contact=EclipseContactKind.U1,
            epoch=MundaneEpoch(
                _utc_jd(2024, 4, 8, 17, 0),
                MundaneTimescale.UTC,
            ),
            provenance=provenance,
        )

    c4 = EclipseContactEpochReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        contact=EclipseContactKind.C4,
        epoch=MundaneEpoch(_utc_jd(2024, 4, 8, 20, 0), MundaneTimescale.UTC),
        provenance=provenance,
    )
    c1 = EclipseContactEpochReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        contact=EclipseContactKind.C1,
        epoch=MundaneEpoch(_utc_jd(2024, 4, 8, 16, 0), MundaneTimescale.UTC),
        provenance=provenance,
    )
    with pytest.raises(ValueError, match="canonical order"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=(greatest,),
            global_contacts=(c4, c1),
        )


def test_eclipse_contacts_must_be_on_the_correct_side_of_greatest() -> None:
    provenance = _external_provenance(
        NASA_2024_ECLIPSE,
        method="published_besselian_epoch_labels",
    )
    greatest = _eclipse_named_epoch(
        "nasa_se2024apr08",
        EclipseKind.SOLAR,
        EclipseAnchorEpoch.GREATEST_ECLIPSE,
        MundaneEpoch(_utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UTC),
        provenance,
    )
    late_c1 = EclipseContactEpochReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        contact=EclipseContactKind.C1,
        epoch=MundaneEpoch(_utc_jd(2024, 4, 8, 19, 0), MundaneTimescale.UTC),
        provenance=provenance,
    )

    with pytest.raises(ValueError, match="must precede greatest"):
        EclipseEventReceipt(
            eclipse_id="nasa_se2024apr08",
            eclipse_kind=EclipseKind.SOLAR,
            anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
            provenance=provenance,
            named_epochs=(greatest,),
            global_contacts=(late_c1,),
        )


def test_imcce_fixture_rejects_ra_and_minimum_elongation_as_event_definition() -> None:
    # IMCCE publishes three different UTC anchors.  Only 18:20:29 is the
    # ecliptic-longitude conjunction admitted by this receipt type.
    ra_epoch = _utc_jd(2020, 12, 21, 13, 31, 56)
    ecliptic_epoch = _utc_jd(2020, 12, 21, 18, 20, 29)
    minimum_elongation_epoch = _utc_jd(2020, 12, 21, 18, 22, 30)
    common = dict(
        event_id="imcce_2020_ecliptic_longitude_root",
        epoch=MundaneEpoch(ecliptic_epoch, MundaneTimescale.UTC),
        jupiter_longitude_deg=300.0,
        saturn_longitude_deg=300.0,
        root_residual_deg=0.0,
        jupiter_motion=MundaneMotionState.DIRECT,
        saturn_motion=MundaneMotionState.DIRECT,
        solver_tolerance_days=1.0 / 86400.0,
        angular_root_tolerance=_root_tolerance(),
        provenance=_jupiter_provenance(),
    )

    receipt = JupiterSaturnConjunctionReceipt(**common)

    assert receipt.epoch.jd == ecliptic_epoch
    assert receipt.epoch.jd != ra_epoch
    assert receipt.epoch.jd != minimum_elongation_epoch
    assert (
        receipt.definition
        is JupiterSaturnConjunctionDefinition.ECLIPTIC_LONGITUDE
    )
    for wrong_definition in (
        JupiterSaturnConjunctionDefinition.RIGHT_ASCENSION,
        JupiterSaturnConjunctionDefinition.MINIMUM_ELONGATION,
    ):
        with pytest.raises(ValueError, match="only Jupiter-Saturn ecliptic-longitude"):
            JupiterSaturnConjunctionReceipt(
                **common,
                definition=wrong_definition,
            )


def test_triple_jupiter_saturn_sequence_retains_each_root_without_grouping() -> None:
    provenance = _jupiter_provenance()
    roots = tuple(
        JupiterSaturnConjunctionReceipt(
            event_id=f"triple_root_{index}",
            epoch=MundaneEpoch(2450000.0 + index, MundaneTimescale.TT),
            jupiter_longitude_deg=120.0,
            saturn_longitude_deg=120.0,
            root_residual_deg=0.0,
            jupiter_motion=(
                MundaneMotionState.DIRECT
                if index != 1
                else MundaneMotionState.RETROGRADE
            ),
            saturn_motion=MundaneMotionState.DIRECT,
            solver_tolerance_days=1e-6,
            angular_root_tolerance=_root_tolerance(),
            provenance=provenance,
        )
        for index in range(3)
    )

    sequence = JupiterSaturnConjunctionSequenceReceipt(
        search_interval=_interval(
            2449999.0,
            2450004.0,
            MundaneTimescale.TT,
        ),
        roots=roots,
    )

    assert sequence.roots == roots
    assert len(sequence.roots) == 3
    assert {item.event_id for item in sequence.roots} == {
        "triple_root_0",
        "triple_root_1",
        "triple_root_2",
    }
    with pytest.raises(TypeError, match="roots must be a built-in tuple"):
        JupiterSaturnConjunctionSequenceReceipt(
            search_interval=sequence.search_interval,
            roots=list(roots),  # type: ignore[arg-type]
        )


def test_jupiter_saturn_receipt_rejects_product_semantic_relabeling() -> None:
    with pytest.raises(ValueError, match="admitted geocentric apparent"):
        JupiterSaturnConjunctionReceipt(
            event_id="bad_product",
            epoch=MundaneEpoch(2459205.25, MundaneTimescale.UTC),
            jupiter_longitude_deg=300.0,
            saturn_longitude_deg=300.0,
            root_residual_deg=0.0,
            jupiter_motion=MundaneMotionState.DIRECT,
            saturn_motion=MundaneMotionState.DIRECT,
            solver_tolerance_days=1e-8,
            angular_root_tolerance=_root_tolerance(),
            provenance=replace(
                _jupiter_provenance(),
                longitude_product_id="right_ascension_conjunction",
            ),
        )


def test_jupiter_saturn_sequence_rejects_mixed_provenance_and_end_boundary() -> None:
    provenance = _jupiter_provenance()

    def root(event_id: str, jd: float, event_provenance) -> JupiterSaturnConjunctionReceipt:
        return JupiterSaturnConjunctionReceipt(
            event_id=event_id,
            epoch=MundaneEpoch(jd, MundaneTimescale.UTC),
            jupiter_longitude_deg=300.0,
            saturn_longitude_deg=300.0,
            root_residual_deg=0.0,
            jupiter_motion=MundaneMotionState.DIRECT,
            saturn_motion=MundaneMotionState.DIRECT,
            solver_tolerance_days=1e-8,
            angular_root_tolerance=_root_tolerance(),
            provenance=event_provenance,
        )

    interval = _interval(2459200.0, 2459210.0)
    with pytest.raises(ValueError, match="homogeneous provenance"):
        JupiterSaturnConjunctionSequenceReceipt(
            search_interval=interval,
            roots=(
                root("first", 2459204.0, provenance),
                root(
                    "second",
                    2459205.0,
                    replace(
                        provenance,
                        source_id="other source under same family",
                        method_id="other method under same family",
                        source_refs=("other source reference",),
                    ),
                ),
            ),
        )
    with pytest.raises(ValueError, match="half-open search interval"):
        JupiterSaturnConjunctionSequenceReceipt(
            search_interval=interval,
            roots=(root("end", interval.end.jd, provenance),),
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        JupiterSaturnConjunctionSequenceReceipt(
            search_interval=interval,
            roots=(
                root("same_epoch_first", 2459205.0, provenance),
                root("same_epoch_second", 2459205.0, provenance),
            ),
        )


def test_institutional_location_validity_is_half_open_and_supports_open_end() -> None:
    start = MundaneEpoch(2450000.0, MundaneTimescale.UTC)
    end = MundaneEpoch(2460000.0, MundaneTimescale.UTC)
    bounded = MundaneLocationSelectionReceipt(
        label="Explicit institutional seat",
        latitude_deg=38.9,
        longitude_deg_east=-77.0,
        role=MundaneLocationRole.SEAT_OF_GOVERNMENT,
        source_id="caller-supplied institutional source",
        valid_from=start,
        valid_until=end,
    )
    open_ended = MundaneLocationSelectionReceipt(
        label="Explicit constitutional capital",
        latitude_deg=-25.7,
        longitude_deg_east=28.2,
        role=MundaneLocationRole.CONSTITUTIONAL_CAPITAL,
        source_id="caller-supplied institutional source",
        valid_from=start,
        valid_until=None,
    )

    assert bounded.valid_at(start) is True
    assert bounded.valid_at(MundaneEpoch(end.jd - 1e-9, MundaneTimescale.UTC)) is True
    assert bounded.valid_at(end) is False
    assert open_ended.valid_at(MundaneEpoch(2500000.0, MundaneTimescale.UTC)) is True


def test_global_event_remains_evaluated_when_local_projection_is_not_evaluable() -> None:
    anchor = _ingress(CardinalIngress.ARIES, 2460754.875)
    profile = MundaneEventChartProfile(
        anchor_event=_anchor_evidence(anchor),
        cardinal_ingress_selection=_not_evaluable_ingress_selection(),
        preceding_syzygy=_not_evaluable_syzygy(),
        local_projection=_not_evaluable_projection(),
    )

    assert profile.status is MundaneEvaluationStatus.EVALUATED
    assert profile.anchor_event.receipt is anchor
    assert MundaneProfileComponent.LOCAL_CHART_PROJECTION not in profile.included_components
    assert {issue.component for issue in profile.not_evaluable} == {
        MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
        MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY,
        MundaneProfileComponent.LOCAL_CHART_PROJECTION,
    }
    assert profile.complete_mundane_judgement is False
    assert profile.scoring == "not_provided"
    assert profile.advice_language == "not_provided"
    with pytest.raises(
        TypeError,
        match="additional_not_evaluable must be a built-in tuple",
    ):
        MundaneEventChartProfile(
            anchor_event=_anchor_evidence(anchor),
            cardinal_ingress_selection=_not_evaluable_ingress_selection(),
            preceding_syzygy=_not_evaluable_syzygy(),
            local_projection=_not_evaluable_projection(),
            additional_not_evaluable=[],  # type: ignore[arg-type]
        )


def test_local_projection_factory_binds_strict_existing_house_computation() -> None:
    anchor = replace(
        _ingress(CardinalIngress.ARIES, 2460754.875),
        epoch=MundaneEpoch(2460754.875, MundaneTimescale.UT1),
    )
    location = MundaneLocationSelectionReceipt(
        label="Caller-selected location",
        latitude_deg=51.5,
        longitude_deg_east=-0.1,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    projection_evidence = build_mundane_local_projection(
        anchor,
        location,
        HouseSystem.WHOLE_SIGN,
        chart_epoch_kind=None,
    )
    assert projection_evidence.status is MundaneEvaluationStatus.EVALUATED
    assert projection_evidence.receipt is not None
    projection = projection_evidence.receipt
    profile = MundaneEventChartProfile(
        anchor_event=_anchor_evidence(anchor),
        cardinal_ingress_selection=_not_evaluable_ingress_selection(),
        preceding_syzygy=_not_evaluable_syzygy(),
        local_projection=projection_evidence,
    )

    assert profile.local_projection.receipt is projection
    assert profile.local_projection.receipt.houses is projection.houses
    assert profile.local_projection.receipt.houses.policy == HousePolicy.strict()
    assert MundaneProfileComponent.LOCAL_CHART_PROJECTION in profile.included_components


def test_eclipse_projection_requires_explicit_matching_chart_epoch_kind() -> None:
    greatest = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UT1
    )
    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    ecliptic = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 20, 49.7), MundaneTimescale.UT1
    )
    eclipse = EclipseEventReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=provenance,
        named_epochs=(
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.GREATEST_ECLIPSE,
                greatest,
                provenance,
            ),
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
                ecliptic,
                provenance,
            ),
        ),
    )
    location = MundaneLocationSelectionReceipt(
        label="Caller-selected location",
        latitude_deg=40.0,
        longitude_deg_east=-75.0,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    with pytest.raises(ValueError, match="epoch must match its explicit chart epoch kind"):
        MundaneLocalProjectionReceipt(
            anchor_event=eclipse,
            house_computation=MundaneHouseComputationReceipt(
                event_epoch=greatest,
                location=location,
                requested_house_system=HouseSystem.WHOLE_SIGN,
            ),
            chart_epoch_kind=EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
        )


def test_eclipse_projection_may_explicitly_select_a_non_anchor_named_epoch() -> None:
    greatest = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 17, 18.3), MundaneTimescale.UT1
    )
    ecliptic = MundaneEpoch(
        _utc_jd(2024, 4, 8, 18, 20, 49.7), MundaneTimescale.UT1
    )
    provenance = _external_provenance(
        NASA_2024_ECLIPSE, method="published_besselian_epoch_labels"
    )
    eclipse = EclipseEventReceipt(
        eclipse_id="nasa_se2024apr08",
        eclipse_kind=EclipseKind.SOLAR,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=provenance,
        named_epochs=(
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.GREATEST_ECLIPSE,
                greatest,
                provenance,
            ),
            _eclipse_named_epoch(
                "nasa_se2024apr08",
                EclipseKind.SOLAR,
                EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
                ecliptic,
                provenance,
            ),
        ),
    )
    projection = _local_projection_receipt(
        eclipse,
        MundaneLocationSelectionReceipt(
            label="Caller-selected location",
            latitude_deg=40.0,
            longitude_deg_east=-75.0,
            role=MundaneLocationRole.USER_SPECIFIED,
            source_id="caller_input",
        ),
        EclipseAnchorEpoch.ECLIPTIC_SYZYGY,
    )

    profile = MundaneEventChartProfile(
        anchor_event=_anchor_evidence(eclipse),
        cardinal_ingress_selection=_not_evaluable_ingress_selection(),
        preceding_syzygy=_not_evaluable_syzygy(),
        local_projection=MundaneLocalProjectionEvidence(
            status=MundaneEvaluationStatus.EVALUATED,
            receipt=projection,
            issue=None,
        ),
    )

    assert profile.anchor_event.receipt.event_epoch is greatest
    assert profile.local_projection.receipt.event_epoch is ecliptic
    assert (
        profile.local_projection.receipt.chart_epoch_kind
        is EclipseAnchorEpoch.ECLIPTIC_SYZYGY
    )


def test_missing_eclipse_chart_epoch_kind_has_no_constructor_default() -> None:
    event_epoch = MundaneEpoch(2460000.0, MundaneTimescale.UT1)
    location = MundaneLocationSelectionReceipt(
        label="Caller-selected location",
        latitude_deg=0.0,
        longitude_deg_east=0.0,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    with pytest.raises(TypeError, match="chart_epoch_kind"):
        MundaneLocalProjectionReceipt(  # type: ignore[call-arg]
            anchor_event=replace(
                _ingress(CardinalIngress.ARIES, event_epoch.jd),
                epoch=event_epoch,
            ),
            house_computation=MundaneHouseComputationReceipt(
                event_epoch=event_epoch,
                location=location,
                requested_house_system=HouseSystem.WHOLE_SIGN,
            ),
        )


def test_house_fallback_is_rejected_instead_of_hidden(monkeypatch) -> None:
    houses = HouseCusps(
        system=HouseSystem.PLACIDUS,
        cusps=tuple(float(value) for value in range(0, 360, 30)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=HouseSystem.WHOLE_SIGN,
        fallback=True,
        fallback_reason="high_latitude_failure",
        classification=classify_house_system(HouseSystem.WHOLE_SIGN),
        policy=HousePolicy.strict(),
    )
    monkeypatch.setattr(mundane, "calculate_houses", lambda *_args, **_kwargs: houses)
    with pytest.raises(ValueError, match="silent house-system fallback"):
        MundaneHouseComputationReceipt(
            event_epoch=MundaneEpoch(2460000.0, MundaneTimescale.UT1),
            location=MundaneLocationSelectionReceipt(
                label="Caller-selected location",
                latitude_deg=75.0,
                longitude_deg_east=20.0,
                role=MundaneLocationRole.USER_SPECIFIED,
                source_id="caller_input",
            ),
            requested_house_system=HouseSystem.PLACIDUS,
        )


def test_local_projection_rejects_permissive_house_policy_even_without_fallback(
    monkeypatch,
) -> None:
    permissive_houses = replace(_whole_sign_houses(), policy=HousePolicy.default())
    monkeypatch.setattr(
        mundane,
        "calculate_houses",
        lambda *_args, **_kwargs: permissive_houses,
    )
    with pytest.raises(ValueError, match="exact strict computation policy"):
        MundaneHouseComputationReceipt(
            event_epoch=MundaneEpoch(2460000.0, MundaneTimescale.UT1),
            location=MundaneLocationSelectionReceipt(
                label="Caller-selected location",
                latitude_deg=0.0,
                longitude_deg_east=0.0,
                role=MundaneLocationRole.USER_SPECIFIED,
                source_id="caller_input",
            ),
            requested_house_system=HouseSystem.WHOLE_SIGN,
        )


def test_house_receipt_rejects_non_ut1_and_cannot_accept_prebuilt_houses() -> None:
    location = MundaneLocationSelectionReceipt(
        label="Caller-selected location",
        latitude_deg=0.0,
        longitude_deg_east=0.0,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    with pytest.raises(ValueError, match="explicit UT1 epoch"):
        MundaneHouseComputationReceipt(
            event_epoch=MundaneEpoch(2460000.0, MundaneTimescale.UTC),
            location=location,
            requested_house_system=HouseSystem.WHOLE_SIGN,
        )
    with pytest.raises(TypeError, match="unexpected keyword argument 'houses'"):
        MundaneHouseComputationReceipt(  # type: ignore[call-arg]
            event_epoch=MundaneEpoch(2460000.0, MundaneTimescale.UT1),
            location=location,
            requested_house_system=HouseSystem.WHOLE_SIGN,
            houses=_whole_sign_houses(),
        )


def test_house_receipt_replace_recomputes_epoch_and_location_binding() -> None:
    first_location = MundaneLocationSelectionReceipt(
        label="First location",
        latitude_deg=0.0,
        longitude_deg_east=0.0,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    second_location = MundaneLocationSelectionReceipt(
        label="Second location",
        latitude_deg=40.0,
        longitude_deg_east=-75.0,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="caller_input",
    )
    original = MundaneHouseComputationReceipt(
        event_epoch=MundaneEpoch(2460000.0, MundaneTimescale.UT1),
        location=first_location,
        requested_house_system=HouseSystem.WHOLE_SIGN,
    )
    rebound = replace(
        original,
        event_epoch=MundaneEpoch(2460001.0, MundaneTimescale.UT1),
        location=second_location,
    )
    expected = mundane.calculate_houses(
        rebound.event_epoch.jd,
        second_location.latitude_deg,
        second_location.longitude_deg_east,
        HouseSystem.WHOLE_SIGN,
        policy=HousePolicy.strict(),
    )

    assert rebound.houses == expected
    assert rebound.houses != original.houses
    assert rebound.policy == HousePolicy.strict()


def test_profile_rejects_local_projection_from_different_same_epoch_anchor() -> None:
    epoch = MundaneEpoch(2460754.875, MundaneTimescale.UT1)
    original_anchor = replace(
        _ingress(CardinalIngress.ARIES, epoch.jd),
        epoch=epoch,
    )
    different_anchor = replace(
        _ingress(CardinalIngress.CANCER, epoch.jd),
        epoch=epoch,
    )
    projection = build_mundane_local_projection(
        original_anchor,
        MundaneLocationSelectionReceipt(
            label="Caller-selected location",
            latitude_deg=0.0,
            longitude_deg_east=0.0,
            role=MundaneLocationRole.USER_SPECIFIED,
            source_id="caller_input",
        ),
        HouseSystem.WHOLE_SIGN,
        chart_epoch_kind=None,
    )
    assert projection.status is MundaneEvaluationStatus.EVALUATED

    with pytest.raises(ValueError, match="complete profile anchor receipt"):
        MundaneEventChartProfile(
            anchor_event=_anchor_evidence(different_anchor),
            cardinal_ingress_selection=_not_evaluable_ingress_selection(),
            preceding_syzygy=_not_evaluable_syzygy(),
            local_projection=projection,
        )


def test_profile_exclusions_are_closed_and_noninterpretive() -> None:
    profile = MundaneEventChartProfile(
        anchor_event=_anchor_evidence(_ingress(CardinalIngress.ARIES, 2460754.875)),
        cardinal_ingress_selection=_not_evaluable_ingress_selection(),
        preceding_syzygy=_not_evaluable_syzygy(),
        local_projection=_not_evaluable_projection(),
    )

    exclusion_values = {item.value for item in profile.excluded_components}
    assert "political_prediction" in exclusion_values
    assert "economic_prediction" in exclusion_values
    assert "weather_prediction" in exclusion_values
    assert "great_mutation_interpretation" in exclusion_values
    assert "ramesey_1653_ingress_selection_unadmitted" not in exclusion_values


@pytest.mark.requires_ephemeris
def test_reader_bound_solar_ingress_is_evaluated_and_cross_model_checked(
    reader,
) -> None:
    authority_jd = _utc_jd(2025, 3, 20, 9, 1)
    events = find_ingresses(
        Body.SUN,
        _utc_jd(2025, 3, 15),
        _utc_jd(2025, 4, 1),
        reader=reader,
    )
    event = next(item for item in events if item.sign == "Aries")

    # USNO is a rounded timing corroborator, not the authority for Moira's
    # longitude product or root receipt.
    assert abs(event.jd_ut - authority_jd) * 86400.0 <= 60.0
    assessment = assess_transit_cardinal_ingress(event, reader=reader)
    assert assessment.status is MundaneEvaluationStatus.EVALUATED
    assert isinstance(assessment.receipt, CardinalIngressReceipt)
    receipt = assessment.receipt
    assert receipt.ingress is CardinalIngress.ARIES
    assert receipt.clock is not None
    assert receipt.search_truth is not None
    assert receipt.search_truth.search_interval.contains(receipt.epoch)
    assert receipt.search_truth.bracket_start.jd <= receipt.epoch.jd
    assert receipt.epoch.jd <= receipt.search_truth.bracket_end.jd
    assert receipt.provenance.reference_frame == MOIRA_TRUE_OF_DATE_FRAME
    assert "deflection" not in receipt.provenance.correction_regime
    assert abs(receipt.root_residual_deg) <= (
        receipt.angular_root_tolerance.maximum_abs_residual_deg
    )
    horizons = TRACK_B_REFERENCE["cardinal_ingress"]["jpl_horizons"]
    assert "IAU76/80" in horizons["product"]
    assert horizons["product"] != receipt.provenance.longitude_product_id
    assert receipt.clock.utc is not None
    horizons_crossing = _utc_jd(2025, 3, 20, 9, 1, 30.061)
    # Labeled cross-model tolerance: Horizons Q31 corroborates timing only;
    # it is not asserted to be frame/product parity with Moira.
    assert abs(receipt.clock.utc.jd - horizons_crossing) * 86400.0 <= 2.0


@pytest.mark.requires_ephemeris
def test_ingress_adapter_rejects_nonroot_and_copies_mutable_transit_truth(
    reader,
) -> None:
    event = next(
        item
        for item in find_ingresses(
            Body.SUN,
            _utc_jd(2025, 3, 15),
            _utc_jd(2025, 4, 1),
            reader=reader,
        )
        if item.sign == "Aries"
    )
    incomplete = replace(event, computation_truth=None)
    refused = assess_transit_cardinal_ingress(incomplete, reader=reader)
    assert refused.status is MundaneEvaluationStatus.NOT_EVALUABLE
    assert refused.issue is not None
    assert refused.issue.reason is MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE

    raw_enum_event = deepcopy(event)
    assert raw_enum_event.classification is not None
    assert raw_enum_event.relation is not None
    assert raw_enum_event.condition_profile is not None
    raw_enum_event.classification.search.search_kind = (
        raw_enum_event.classification.search.search_kind.value
    )
    raw_enum_event.classification.search.wrapper_kind = (
        raw_enum_event.classification.search.wrapper_kind.value
    )
    raw_enum_event.relation.relation_kind = raw_enum_event.relation.relation_kind.value
    raw_enum_event.relation.basis = raw_enum_event.relation.basis.value
    raw_enum_event.condition_profile.wrapper_kind = (
        raw_enum_event.condition_profile.wrapper_kind.value
    )
    raw_enum_event.condition_profile.search_kind = (
        raw_enum_event.condition_profile.search_kind.value
    )
    raw_enum_event.condition_profile.relation_kind = (
        raw_enum_event.condition_profile.relation_kind.value
    )
    raw_enum_event.condition_profile.relation_basis = (
        raw_enum_event.condition_profile.relation_basis.value
    )
    raw_enum_event.condition_profile.condition_state = (
        raw_enum_event.condition_profile.condition_state.value
    )
    with pytest.raises(TypeError, match="exact concrete transit truth types"):
        assess_transit_cardinal_ingress(raw_enum_event, reader=reader)

    adapted = assess_transit_cardinal_ingress(event, reader=reader)
    assert isinstance(adapted.receipt, CardinalIngressReceipt)
    assert adapted.receipt.search_truth is not None
    assert event.computation_truth is not None
    forged_history = replace(
        event,
        computation_truth=replace(
            event.computation_truth,
            search_truth=replace(
                event.computation_truth.search_truth,
                search_start_jd_ut=(
                    event.computation_truth.search_truth.search_start_jd_ut - 100.0
                ),
                step_days=99.0,
            ),
        ),
    )
    with pytest.raises(ValueError, match="complete search history"):
        assess_transit_cardinal_ingress(forged_history, reader=reader)

    copied_start = adapted.receipt.search_truth.search_interval.start.jd
    event.computation_truth.search_truth.search_start_jd_ut += 0.25
    assert adapted.receipt.search_truth.search_interval.start.jd == copied_start

    original_truth = event.computation_truth
    fake_jd = event.jd_ut + 0.01
    fake_search = replace(
        original_truth.search_truth,
        search_start_jd_ut=fake_jd - 0.1,
        search_end_jd_ut=fake_jd + 0.1,
        bracket_start_jd_ut=fake_jd - 1e-7,
        bracket_end_jd_ut=fake_jd + 1e-7,
        crossing_jd_ut=fake_jd,
    )
    fake_event = replace(
        event,
        jd_ut=fake_jd,
        computation_truth=replace(original_truth, search_truth=fake_search),
    )
    with pytest.raises(
        ValueError,
        match="complete search history|sign crossing|root residual|increasing",
    ):
        assess_transit_cardinal_ingress(fake_event, reader=reader)
    with pytest.raises(ValueError, match="exact root epoch"):
        replace(
            adapted.receipt,
            epoch=MundaneEpoch(event.jd_ut + 1.0, MundaneTimescale.UT1),
        )
    with pytest.raises(ValueError, match="bind its exact target"):
        replace(
            adapted.receipt,
            ingress=CardinalIngress.CANCER,
            sun_longitude_deg=90.0,
            root_residual_deg=0.0,
        )
    with pytest.raises(ValueError, match="must be engine-produced"):
        replace(adapted.receipt.provenance, source_id="forged.moira.source")


@pytest.mark.requires_ephemeris
def test_reader_bound_primary_syzygy_builds_both_candidates_and_selects_nearest(
    reader,
    monkeypatch,
) -> None:
    import moira.transits as transits
    from moira.transits import CrossingSearchTruth

    authority_jd = _utc_jd(2025, 3, 14, 6, 55)
    event = next(
        item
        for item in find_ingresses(
            Body.SUN,
            _utc_jd(2025, 3, 15),
            _utc_jd(2025, 4, 1),
            reader=reader,
        )
        if item.sign == "Aries"
    )
    anchor_evidence = assess_transit_cardinal_ingress(event, reader=reader)
    assert isinstance(anchor_evidence.receipt, CardinalIngressReceipt)
    assessment = assess_transit_primary_syzygy(
        anchor_evidence.receipt,
        reader=reader,
    )
    assert assessment.status is MundaneEvaluationStatus.EVALUATED
    assert assessment.selection is not None
    assert assessment.selection.selected.phase is PrimarySyzygyPhase.FULL_MOON
    assert len(assessment.selection.candidates) == 2
    assert abs(assessment.selection.selected.epoch.jd - authority_jd) * 86400.0 <= 60.0
    assert {
        candidate.search_truth.search_kind
        for candidate in assessment.selection.candidates
        if candidate.search_truth is not None
    } == {"preceding_new_moon", "preceding_full_moon"}
    assert all(
        candidate.search_truth is not None
        and candidate.search_truth.search_interval.end
        == anchor_evidence.receipt.epoch
        for candidate in assessment.selection.candidates
    )
    assert (
        assessment.selection.selected.provenance.solver_semantics
        != anchor_evidence.receipt.provenance.solver_semantics
    )
    selected_clock = assessment.selection.selected.clock
    assert selected_clock is not None and selected_clock.utc is not None
    horizons = TRACK_B_REFERENCE["preceding_primary_syzygy"]["jpl_horizons"]
    assert "IAU76/80" in horizons["product"]
    horizons_crossing = _utc_jd(2025, 3, 14, 6, 54, 39.191)
    # Again this is a cross-model timing bound, not exact longitude parity.
    assert abs(selected_clock.utc.jd - horizons_crossing) * 86400.0 <= 2.0

    def source_truth(candidate: PrimarySyzygyReceipt) -> CrossingSearchTruth:
        search = candidate.search_truth
        assert search is not None
        return CrossingSearchTruth(
            search_start_jd_ut=search.search_interval.start.jd,
            search_end_jd_ut=search.search_interval.end.jd,
            step_days=search.step_days,
            bracket_start_jd_ut=search.bracket_start.jd,
            bracket_end_jd_ut=search.bracket_end.jd,
            crossing_jd_ut=search.root_epoch.jd,
            solver_tolerance_days=search.solver_tolerance_days,
        )

    new_candidate = next(
        item
        for item in assessment.selection.candidates
        if item.phase is PrimarySyzygyPhase.NEW_MOON
    )
    full_candidate = next(
        item
        for item in assessment.selection.candidates
        if item.phase is PrimarySyzygyPhase.FULL_MOON
    )
    new_truth = source_truth(new_candidate)
    full_truth = source_truth(full_candidate)
    monkeypatch.setattr(
        transits,
        "_last_new_moon_search_truth",
        lambda _jd, _reader, _policy: (new_candidate.epoch.jd + 0.01, new_truth),
    )
    monkeypatch.setattr(
        transits,
        "_last_full_moon_search_truth",
        lambda _jd, _reader, _policy: (full_candidate.epoch.jd, full_truth),
    )
    with pytest.raises(ValueError, match="root must exactly match its search truth"):
        assess_transit_primary_syzygy(
            anchor_evidence.receipt,
            reader=reader,
        )


@pytest.mark.requires_ephemeris
def test_event_clock_refuses_historical_utc_proxy_and_is_not_replace_forgeable(
    reader,
) -> None:
    modern = build_mundane_event_clock(_utc_jd(2025, 3, 20), reader=reader)
    assert isinstance(modern, MundaneEventClockReceipt)
    assert modern.utc_realization_status is (
        MundaneUtcRealizationStatus.REALIZED_POST_1972_ATOMIC
    )
    assert modern.utc is not None
    assert modern.tt.jd == pytest.approx(
        modern.ut1.jd + modern.delta_t_seconds / 86400.0,
        abs=1e-12,
    )
    assert modern.delta_t_source_product
    assert modern.delta_t_retarget_mode in {
        "declared",
        "basis_neutral",
        "policy_locked",
    }
    with pytest.raises(ValueError, match="must be produced by the engine"):
        replace(modern, delta_t_seconds=modern.delta_t_seconds + 1.0)

    historical = build_mundane_event_clock(2300000.0, reader=reader)
    assert historical.utc is None
    assert historical.utc_realization_status is (
        MundaneUtcRealizationStatus.NOT_REALIZED_HISTORICAL_UT1_PROXY
    )
    assert "no UTC label emitted" in historical.utc_realization_detail


@pytest.mark.requires_ephemeris
def test_event_clock_rejects_forged_reader_identity_and_dispatch_owners(reader) -> None:
    from moira.spk_reader import KernelPool

    class ForgedIdentityProxy:
        def __init__(self, delegate) -> None:
            self._delegate = delegate

        def __getattr__(self, name: str):
            return getattr(self._delegate, name)

        def _ephemeris_kernel_identity_at(self, jd_tt: float):
            del jd_tt
            return replace(
                self._delegate._kernel_identity,
                summary_label="FORGED-NOT-FROM-CONTENT",
            )

    with pytest.raises(TypeError, match="concrete SpkReader or KernelPool"):
        build_mundane_event_clock(
            2460000.0,
            reader=ForgedIdentityProxy(reader),
        )

    class IdentitylessPriorityOverride:
        _kernel_identity = None

        def __init__(self, delegate) -> None:
            self._delegate = delegate

        def has_segment_at(self, center: int, target: int, jd_tt: float) -> bool:
            return self._delegate.has_segment_at(center, target, jd_tt)

        def position(self, center: int, target: int, jd_tt: float):
            vector = self._delegate.position(center, target, jd_tt)
            if (center, target) == (0, 10):
                return (vector[0] + 1.0e8, vector[1], vector[2])
            return vector

        def position_and_velocity(self, center: int, target: int, jd_tt: float):
            return self._delegate.position_and_velocity(center, target, jd_tt)

    pool = KernelPool((IdentitylessPriorityOverride(reader), reader))
    with pytest.raises(TypeError, match="dispatch owner must be a concrete SpkReader"):
        build_mundane_event_clock(2460000.0, reader=pool)

    genuine_identity = reader._kernel_identity
    reader._kernel_identity = replace(
        genuine_identity,
        summary_label="DE-9999LE-9999",
        planetary_ephemeris="DE9999",
        lunar_ephemeris="LE9999",
        lunar_tidal_acceleration_arcsec_per_cy2=None,
    )
    try:
        with pytest.raises(ValueError, match="does not match its active kernel content"):
            build_mundane_event_clock(2460000.0, reader=reader)
    finally:
        reader._kernel_identity = genuine_identity


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_ut1", (10_000_000.0, 30_000_000.0))
def test_event_clock_rejects_epochs_outside_reader_coverage(reader, jd_ut1) -> None:
    with pytest.raises(ValueError, match="does not cover every required"):
        build_mundane_event_clock(jd_ut1, reader=reader)


@pytest.mark.requires_ephemeris
def test_ramesey_cadence_and_profile_composer_bind_exact_engine_receipts(
    reader,
) -> None:
    search_start = _utc_jd(2025, 3, 15)
    search_end = _utc_jd(2026, 1, 15)
    transit_events = find_ingresses(
        Body.SUN,
        search_start,
        search_end,
        reader=reader,
    )
    adapted = []
    for ingress in CardinalIngress:
        event = next(
            item
            for item in transit_events
            if item.sign == ingress.value.capitalize()
        )
        evidence = assess_transit_cardinal_ingress(event, reader=reader)
        assert isinstance(evidence.receipt, CardinalIngressReceipt)
        adapted.append(evidence.receipt)
    events = tuple(adapted)
    aries = events[0]
    location = MundaneLocationSelectionReceipt(
        label="Explicit London test location",
        latitude_deg=51.5074,
        longitude_deg_east=-0.1278,
        role=MundaneLocationRole.USER_SPECIFIED,
        source_id="test.location.london",
    )
    cadence_evidence = assess_ramesey_ingress_cadence(aries, location)
    assert cadence_evidence.status is MundaneEvaluationStatus.EVALUATED
    assert cadence_evidence.cadence is not None
    cadence = cadence_evidence.cadence
    assert isinstance(cadence, RameseyIngressCadenceReceipt)
    assert isinstance(cadence.ascendant, MundaneAscendantReceipt)
    expected = {
        MundaneZodiacModality.CARDINAL: tuple(CardinalIngress),
        MundaneZodiacModality.MUTABLE: (
            CardinalIngress.ARIES,
            CardinalIngress.LIBRA,
        ),
        MundaneZodiacModality.FIXED: (CardinalIngress.ARIES,),
    }[cadence.ascendant.ascendant_modality]
    assert cadence.selected_ingresses == expected
    assert cadence.chart_count == len(expected)
    with pytest.raises(ValueError, match="must be produced by the engine"):
        replace(
            cadence.ascendant,
            ascendant_longitude_deg=(cadence.ascendant.ascendant_longitude_deg + 1.0)
            % 360.0,
        )
    with pytest.raises(TypeError, match="must be a built-in tuple"):
        replace(
            cadence,
            selected_ingresses=[CardinalIngress.ARIES],  # type: ignore[arg-type]
        )

    selection = select_cardinal_ingresses(
        events,
        policy=CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1,
        search_interval=_interval(
            search_start,
            search_end,
            MundaneTimescale.UT1,
        ),
        ramesey_cadence=cadence,
    )
    assert selection.status is MundaneEvaluationStatus.EVALUATED
    assert selection.selection is not None
    assert tuple(item.ingress for item in selection.selection.selected_events) == expected

    syzygy = assess_transit_primary_syzygy(aries, reader=reader)
    profile = compose_mundane_event_chart_profile(
        anchor_event=_anchor_evidence(aries),
        cardinal_ingress_selection=selection,
        preceding_syzygy=syzygy,
        local_projection=_not_evaluable_projection(),
    )
    assert profile.provenance.source_refs == tuple(
        sorted(profile.provenance.source_refs)
    )
    assert "moira.transits.find_ingresses" in profile.provenance.source_refs
    assert "moira.houses._local_angles_at" in profile.provenance.source_refs
    assert "test.location.london" in profile.provenance.source_refs
    with pytest.raises(ValueError, match="selected ingress receipts|complete profile anchor"):
        replace(
            profile,
            anchor_event=_anchor_evidence(
                _ingress(CardinalIngress.ARIES, aries.epoch.jd)
            ),
        )
    with pytest.raises(TypeError, match="init=False"):
        replace(
            profile,
            provenance=MundaneProfileProvenance(source_refs=("forged",)),
        )


@pytest.mark.requires_ephemeris
def test_existing_eclipse_solver_matches_nasa_greatest_epoch_and_adapts_only_that_epoch(
    reader,
) -> None:
    authority_jd = _utc_jd(2024, 4, 8, 18, 17, 18.3)
    calculator = EclipseCalculator(reader=reader)
    event = calculator.next_solar_eclipse(
        _utc_jd(2024, 4, 1)
    )

    raw_boolean_event = replace(
        event,
        data=replace(event.data, is_solar_eclipse=1),  # type: ignore[arg-type]
    )
    with pytest.raises(
        TypeError,
        match="exact engine scalar|exact built-in booleans",
    ):
        eclipse_receipt_from_event(
            raw_boolean_event,
            eclipse_id="raw_boolean_eclipse",
            reader=reader,
        )

    # NASA/GSFC gives greatest eclipse to 0.1 second. This threshold covers the
    # present model residual and UT1-versus-published-UT labeling explicitly.
    assert abs(event.jd_ut - authority_jd) * 86400.0 <= 5.0
    receipt = eclipse_receipt_from_event(
        event,
        eclipse_id="moira_se2024apr08",
        reader=reader,
    )
    assert receipt.anchor_epoch_kind is EclipseAnchorEpoch.GREATEST_ECLIPSE
    assert receipt.greatest_eclipse_epoch == MundaneEpoch(
        event.jd_ut, MundaneTimescale.UT1
    )
    assert receipt.ecliptic_syzygy_epoch is None
    assert receipt.provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS
    assert receipt.provenance.verified_reader_identity is not None
    assert receipt.clock is not None
    assert receipt.clock.ut1 == receipt.event_epoch
    assert receipt.clock.tt.timescale is MundaneTimescale.TT
    assert receipt.clock.utc is not None
    assert (
        receipt.provenance.verified_reader_identity.summary_label
        == reader._kernel_identity.summary_label
    )
    with pytest.raises(ValueError, match="must be produced from the active reader"):
        replace(
            receipt.provenance.verified_reader_identity,
            summary_label="forged-reader-label",
        )

    non_greatest_jd = event.jd_ut + 0.01
    forged = replace(
        event,
        jd_ut=non_greatest_jd,
        data=calculator.calculate_jd(non_greatest_jd),
    )
    with pytest.raises(ValueError, match="not the reader-recomputed greatest"):
        eclipse_receipt_from_event(
            forged,
            eclipse_id="forged_non_greatest",
            reader=reader,
        )


@pytest.mark.requires_ephemeris
def test_existing_jupiter_saturn_solver_matches_imcce_and_adapter_preserves_root(
    reader,
) -> None:
    authority_jd = _utc_jd(2020, 12, 21, 18, 20, 29)
    series = great_conjunctions(
        _utc_jd(2020, 12, 1),
        _utc_jd(2021, 1, 1),
        reader=reader,
    )

    assert series.count == 1
    assert abs(series.conjunctions[0].jd_ut - authority_jd) * 86400.0 <= 15.0
    adapted = jupiter_saturn_sequence_from_series(
        series,
        reader=reader,
    )
    assert len(adapted.roots) == 1
    assert adapted.roots[0].epoch.jd == series.conjunctions[0].jd_ut
    assert abs(adapted.roots[0].root_residual_deg) < 1e-7
    assert adapted.roots[0].provenance.verified_reader_identity is not None
    assert adapted.roots[0].clock is not None
    assert adapted.roots[0].clock.ut1 == adapted.roots[0].epoch
    assert adapted.roots[0].clock.tt.timescale is MundaneTimescale.TT
    assert adapted.roots[0].clock.utc is not None
    assert (
        adapted.roots[0].provenance.verified_reader_identity.summary_label
        == reader._kernel_identity.summary_label
    )


@pytest.mark.requires_ephemeris
def test_jupiter_saturn_adapter_rejects_an_omitted_root_subset(reader) -> None:
    complete = great_conjunctions(
        _utc_jd(1999, 1, 1),
        _utc_jd(2022, 1, 1),
        reader=reader,
    )
    assert complete.count == 2
    retained = complete.conjunctions[-1]
    forged_subset = replace(
        complete,
        conjunctions=(retained,),
        count=1,
        elements_represented=(retained.element,),
    )

    with pytest.raises(ValueError, match="reader-recomputed complete search result"):
        jupiter_saturn_sequence_from_series(forged_subset, reader=reader)
