"""Whole-box domain checks and bounded nonlinear uncertainty diagnostics."""

import math

import pytest

from moira.geodetic import geodetic_chart, geodetic_chart_sensitivity, GeodeticInputUncertainty as Errors
from moira.geodetic_uncertainty import GeodeticDiagnosticPolicy as Policy, diagnose_geodetic_uncertainty

EPS = 23.4392911


def test_interior_plane_coincidence_invalidates_local_box():
    chart = geodetic_chart(90, EPS-90+0.001, EPS)
    errors = Errors(longitude_deg=1e-6, latitude_deg=0.002)
    result = diagnose_geodetic_uncertainty(chart, errors, policy=Policy(1e-4))
    assert result.status == "domain_intersection"
    assert result.linear_estimate is None
    assert result.evaluations == 0
    assert "coincident_planes" in result.reasons
    assert result.base_geometry.is_defined
    with pytest.raises(ValueError, match="rising branch"):
        geodetic_chart_sensitivity(chart, errors)


def test_nonquadrant_branch_boundary_inside_box_is_also_detected():
    delta = math.degrees(math.asin(math.sin(math.radians(EPS))/math.sqrt(2)))
    chart = geodetic_chart(45, delta-90+0.002, EPS)
    result = diagnose_geodetic_uncertainty(chart, Errors(latitude_deg=0.003), policy=Policy(1e-4))
    assert result.status == "domain_intersection"
    assert "coincident_planes" not in result.reasons


def test_obliquity_range_participates_in_interior_boundary_test():
    chart = geodetic_chart(90, -66.55, 23.43)
    result = diagnose_geodetic_uncertainty(chart, Errors(obliquity_deg=0.03), policy=Policy(1e-4))
    assert "rising_branch_boundary" in result.reasons


def test_zero_box_and_circular_seam_have_explicit_sampled_semantics():
    chart = geodetic_chart(270.1, 0, EPS)
    result = diagnose_geodetic_uncertainty(chart, Errors(), policy=Policy(1e-4))
    assert result.status == "sampled_consistent"
    assert result.sampled_max_deviation_deg == 0
    assert result.sampled_arc.sweep_deg == 0
    assert "not_an_error_bound" in result.interpretation


def test_nonlinear_evidence_and_budget_exhaustion_are_distinguished():
    chart = geodetic_chart(45, 40, EPS)
    errors = Errors(20, 10, 0.1)
    complete = diagnose_geodetic_uncertainty(chart, errors, policy=Policy(1e-8, max_depth=0))
    assert complete.status == "nonlinear"
    limited = diagnose_geodetic_uncertainty(chart, errors, policy=Policy(1e-8, max_evaluations=1))
    assert limited.status == "sampling_incomplete"
    assert limited.evaluations == 1


def test_full_circle_longitude_box_includes_all_interior_extrema():
    chart = geodetic_chart(0, 70, EPS)
    result = diagnose_geodetic_uncertainty(chart, Errors(longitude_deg=180), policy=Policy(1e-4))
    assert result.status == "domain_intersection"


def test_huge_finite_longitude_uncertainty_is_circular_and_bounded_work():
    chart = geodetic_chart(90, 0, EPS)
    result = diagnose_geodetic_uncertainty(chart, Errors(longitude_deg=1.7e308), policy=Policy(1e-4, max_depth=0))
    assert result.status == "nonlinear"
    assert "circular_linearization_ambiguous" in result.reasons
    assert result.sampled_max_residual_deg <= 180
    assert result.evaluations <= 4096
