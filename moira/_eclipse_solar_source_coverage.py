"""Conditional source-vector adapter for the real solar-axis reference.

Input domains contain represented UT1 values and an explicitly supplied TT
enclosure, with all existing Earth-fixed source/arithmetic premises retained.
Successful-output boxes are not a continuous native route or a physical
time certificate. In particular, this adapter supplies no root derivative
or real-continuity assertion and cannot admit H2/H3 by itself.
"""
from ._eclipse_earth_fixed_bounds import bound_conditional_earth_fixed_solar_vectors
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_solar_axis_reference import bound_solar_axis_reference
from ._eclipse_solar_coverage import cover_solar_central_path


def cover_conditional_solar_source(
    reader, ut1_anchor_jd: float, domain: I, *, tt_anchor_jd: float,
    tt_enclosure, tolerance, arithmetic_premises: dict,
    max_evaluations: int = 4096, max_depth: int = 80,
):
    """Cover every requested cell, retaining unsupported source/time branches.

    ``tt_enclosure`` must enclose all represented TT offsets corresponding
    to each UT1 offset cell; this adapter never substitutes UT1 offsets for
    TT silently. The caller also supplies the explicit arithmetic premise
    dictionary required by the Earth-fixed adapter. Its flags and this
    provider do not attest their own truth. Radius/axis results concern the
    exact geometry of these enclosed vectors and are not a binary64
    enclosure of every operation in the legacy shadow intersection solver.
    """
    if not isinstance(arithmetic_premises, dict):
        raise TypeError('explicit Earth-fixed arithmetic premise dictionary required')

    def enclosure(box):
        tt = tt_enclosure(box)
        if not isinstance(tt, I):
            raise TypeError('TT enclosure must return rational offset intervals')
        vectors = bound_conditional_earth_fixed_solar_vectors(
            reader, ut1_anchor_jd, box, tt_anchor_jd, tt, **arithmetic_premises,
        )
        if vectors.moon_xyz_itrf_km is None:
            raise EnclosureUnavailable('Earth-fixed Moon vector unavailable')
        return bound_solar_axis_reference(
            box, vectors.sun_xyz_itrf_km, vectors.moon_xyz_itrf_km,
            continuous_model=False,
        )

    return cover_solar_central_path(
        domain, enclosure, tolerance=tolerance, continuity_assumed=False,
        max_evaluations=max_evaluations, max_depth=max_depth,
    )


def cover_native_solar_source(reader, ut1_anchor_jd: float, domain: I, *,
                              tolerance, arithmetic_premises: dict,
                              max_evaluations: int = 4096, max_depth: int = 80,
                              require_clock_totality: bool = False):
    """Connect the conditional native forward clock without equating UT1/TT.

    Each requested UT1 box is mapped by the existing complete-input clock
    dispatcher. Its normalized anchor is included when translating to TT
    offsets. Unavailable clock branches stay unresolved. Requesting totality
    deliberately rejects branches for which that separate proof is absent.
    Successful-output clock/ephemeris bounds still supply no real-continuity
    or solar-root derivative proof, and cannot by themselves admit H2/H3.
    """
    def tt_enclosure(box):
        receipt = bound_native_ut1_to_tt(reader, ut1_anchor_jd, box,
                                         require_totality=require_clock_totality)
        return I.point(receipt.bounds.anchor_jd)+receipt.bounds.output_offset_days-ut1_anchor_jd

    return cover_conditional_solar_source(
        reader, ut1_anchor_jd, domain, tt_anchor_jd=ut1_anchor_jd,
        tt_enclosure=tt_enclosure, tolerance=tolerance,
        arithmetic_premises=arithmetic_premises,
        max_evaluations=max_evaluations, max_depth=max_depth,
    )
