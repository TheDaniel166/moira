"""Chart-backed composition service for the unified Hellenistic profile."""

from __future__ import annotations

from moira import Moira
from moira.constants import HouseSystem
from moira.dignities import (
    AccidentalDignityPolicy,
    DignityComputationPolicy,
    EssentialDignityPolicy,
    MutualReceptionPolicy,
    SectHayzPolicy,
    SolarConditionPolicy,
)
from moira.egyptian_bounds import EgyptianBoundsPolicy
from moira.hellenistic import (
    HELLENISTIC_CLASSICAL_PLANETS,
    HellenisticChartProfile,
    HellenisticProfileOverlays,
    HellenisticProfilePolicy,
    HellenisticRevivalPolicy,
)
from moira.houses import HousePolicy
from moira.lots import (
    LotsComputationPolicy,
    LotsDerivedReferencePolicy,
    LotsExternalReferencePolicy,
)
from moira.timelords import DecennialPolicy, ZRYearPolicy

from ..models.hellenistic_profile import (
    HellenisticChartProfileRequest,
    HellenisticProfilePolicyRequest,
)
from ._shared import require_aware_datetime


def _policy_from_request(
    request: HellenisticProfilePolicyRequest,
) -> HellenisticProfilePolicy:
    dignity = request.dignity
    lots = request.lots
    return HellenisticProfilePolicy(
        dignity=DignityComputationPolicy(
            essential=EssentialDignityPolicy(
                doctrine=dignity.essential.doctrine,
            ),
            accidental=AccidentalDignityPolicy(
                include_house_strength=dignity.accidental.include_house_strength,
                include_motion=dignity.accidental.include_motion,
                include_oriental_occidental=(
                    dignity.accidental.include_oriental_occidental
                ),
                solar=SolarConditionPolicy(
                    include_cazimi=dignity.accidental.solar.include_cazimi,
                    include_combust=dignity.accidental.solar.include_combust,
                    include_under_sunbeams=(
                        dignity.accidental.solar.include_under_sunbeams
                    ),
                    include_for_luminaries=(
                        dignity.accidental.solar.include_for_luminaries
                    ),
                ),
                mutual_reception=MutualReceptionPolicy(
                    include_domicile=(
                        dignity.accidental.mutual_reception.include_domicile
                    ),
                    include_exaltation=(
                        dignity.accidental.mutual_reception.include_exaltation
                    ),
                ),
                sect=SectHayzPolicy(
                    doctrine=dignity.accidental.sect.doctrine,
                    mercury_sect_model=(
                        dignity.accidental.sect.mercury_sect_model
                    ),
                    include_hayz=dignity.accidental.sect.include_hayz,
                    include_halb=dignity.accidental.sect.include_halb,
                ),
            ),
        ),
        lots=LotsComputationPolicy(
            unresolved_reference_mode=lots.unresolved_reference_mode,
            derived=LotsDerivedReferencePolicy(
                include_fortune=lots.derived.include_fortune,
                include_spirit=lots.derived.include_spirit,
                include_eros_valens=lots.derived.include_eros_valens,
            ),
            external=LotsExternalReferencePolicy(
                include_syzygy=lots.external.include_syzygy,
                include_prenatal_new_moon=(
                    lots.external.include_prenatal_new_moon
                ),
                include_prenatal_full_moon=(
                    lots.external.include_prenatal_full_moon
                ),
                include_lord_of_hour=lots.external.include_lord_of_hour,
            ),
        ),
        triplicity_doctrine=request.triplicity_doctrine,
        bounds=EgyptianBoundsPolicy(doctrine=request.bounds.doctrine),
        decennials=DecennialPolicy(
            start_lord_basis=request.decennials.start_lord_basis,
            sequence_mode=request.decennials.sequence_mode,
            subperiod_mode=request.decennials.subperiod_mode,
            major_months=request.decennials.major_months,
            month_basis_days=request.decennials.month_basis_days,
            time_basis=request.decennials.time_basis,
            calendar_projection_basis=(
                request.decennials.calendar_projection_basis
            ),
        ),
        zr_year=ZRYearPolicy(year_days=request.zr_year.year_days),
        activation_orb_deg=request.activation_orb_deg,
        leap_day_policy=request.leap_day_policy,
        monthly_profection_interval_policy=(
            request.monthly_profection_interval_policy
        ),
        profection_ambiguous_time_policy=(
            request.profection_ambiguous_time_policy
        ),
        zr_lot_name=request.zr_lot_name,
        zr_levels=request.zr_levels,
        use_loosing_of_bond=request.use_loosing_of_bond,
        revival=HellenisticRevivalPolicy(
            dual_zr=request.revival.dual_zr,
            zr_peak_grades=request.revival.zr_peak_grades,
            zr_display_levels=request.revival.zr_display_levels,
            sign_per_month_profections=request.revival.sign_per_month_profections,
            label_overlays=request.revival.label_overlays,
        ),
        overlays=HellenisticProfileOverlays(
            supporting_lots=request.overlays.supporting_lots,
            assemble_condition=request.overlays.assemble_condition,
            twelfth_parts=request.overlays.twelfth_parts,
        ),
    )


def compute_hellenistic_chart_profile(
    engine: Moira,
    request: HellenisticChartProfileRequest,
) -> HellenisticChartProfile:
    """Build exact natal geometry and compose only admitted atomic receipts."""

    require_aware_datetime(request.natal_dt)
    require_aware_datetime(request.current_dt)
    chart = engine.chart(
        request.natal_dt,
        bodies=list(HELLENISTIC_CLASSICAL_PLANETS),
        include_nodes=False,
    )
    houses = engine.houses(
        request.natal_dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        system=HouseSystem.WHOLE_SIGN,
        policy=HousePolicy.strict(),
    )
    return engine.hellenistic_chart_profile(
        chart,
        houses,
        request.natal_dt,
        request.current_dt,
        civil_timezone=request.civil_timezone,
        policy=_policy_from_request(request.policy),
        syzygy=request.syzygy,
        prenatal_new_moon=request.prenatal_new_moon,
        prenatal_full_moon=request.prenatal_full_moon,
        lord_of_hour=request.lord_of_hour,
        observer_latitude=request.observer_lat,
        observer_longitude=request.observer_lon,
        observer_elevation_m=request.observer_elev_m,
        position_frame=(
            "apparent_geocentric_true_ecliptic_of_date_"
            "positions_and_longitude_rates"
        ),
    )


__all__ = ["compute_hellenistic_chart_profile"]
