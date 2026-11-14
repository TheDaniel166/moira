"""Transport models for the out-of-bounds declination endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutOfBoundsCrossingResponse(_StrictModel):
    """One solved entry or return, with the receipt needed to judge it."""

    kind: str = Field(description="'entry' or 'departure'.")
    jd_ut: float
    datetime_utc: str
    declination: float = Field(
        description="Geocentric apparent declination of date, degrees."
    )
    obliquity: float = Field(
        description="True obliquity of date at the crossing, degrees."
    )
    declination_rate_deg_per_day: float
    obliquity_rate_deg_per_day: float
    bound_rate_deg_per_day: float = Field(
        description=(
            "Rate of the quantity actually driven to zero, "
            "d/dt(|declination| - obliquity). This, not the declination rate "
            "alone, governs how a positional error maps onto a time error."
        ),
    )
    time_sensitivity_seconds_per_arcsec: float = Field(
        description=(
            "Seconds of time error produced by one arcsecond of declination "
            "error at this crossing. Spans more than two orders of magnitude "
            "between a lunar crossing and a Plutonian one."
        ),
    )
    achieved_tolerance_days: float = Field(
        description=(
            "Final bracket width of the solver, not the requested tolerance."
        ),
    )
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    conditioning: str = Field(
        description=(
            "'well_posed' (an arcsecond costs under a minute), 'sensitive' "
            "(under an hour), 'ill_conditioned' (more), or 'degenerate'."
        ),
    )


class OutOfBoundsCulminationResponse(_StrictModel):
    """The extremal declination magnitude reached inside one excursion."""

    jd_ut: float
    datetime_utc: str
    declination: float
    obliquity: float
    excess_deg: float = Field(
        description="|declination| - obliquity at the culmination, degrees."
    )
    at_boundary: bool = Field(
        description=(
            "True when the extremum sits on a window edge rather than at an "
            "interior critical point. This is the normal state of a clipped "
            "excursion."
        ),
    )
    boundary_edge: str | None = None
    interior_critical_points: int


class OutOfBoundsExcursionResponse(_StrictModel):
    """One maximal interval on which the body is out of bounds."""

    body: str
    hemisphere: str = Field(description="'north' or 'south'; constant across the excursion.")
    jd_start_observed: float
    jd_end_observed: float
    datetime_start_utc: str
    datetime_end_utc: str
    entry: OutOfBoundsCrossingResponse | None = None
    departure: OutOfBoundsCrossingResponse | None = None
    entry_clipped: bool = Field(
        description=(
            "True when the body was already out of bounds at the range start, "
            "so the entry lies before the requested window and is not solved."
        ),
    )
    departure_clipped: bool = Field(
        description=(
            "True when the body is still out of bounds at the range end, so "
            "the return lies after the requested window and is not solved."
        ),
    )
    culmination: OutOfBoundsCulminationResponse
    duration_hours: float
    duration_is_lower_bound: bool = Field(
        description=(
            "True when either edge is clipped. The duration is then 'at least "
            "this many hours', never the excursion's full length."
        ),
    )
    is_complete: bool


class OutOfBoundsPolicyResponse(_StrictModel):
    """The scan and solver doctrine actually applied."""

    angular_resolution_deg: float
    rate_safety_factor: float
    min_step_days: float
    max_step_days: float
    rate_probe_count: int
    solver_tolerance_days: float
    differentiation_step_days: float
    max_subdivision_depth: int
    close_approach_distance_au: float
    distance_change_trigger: float
    close_approach_refinement_depth: int
    culmination_probe_count: int
    max_declination_evaluations: int | None = None


class OutOfBoundsScanTruthResponse(_StrictModel):
    """How the scan was chosen and what it resolved."""

    coarse_step_days: float = Field(
        description=(
            "Derived from the body's own measured bound-function rate, never "
            "from a per-body table."
        ),
    )
    measured_max_rate_deg_per_day: float
    measured_median_rate_deg_per_day: float
    rate_bound_deg_per_day: float
    resolved_amplitude_floor_deg: float = Field(
        description=(
            "Shallowest excursion the coarse grid could have cleared on its "
            "own before refinement. Reported so the scan can be judged; it is "
            "not a guarantee."
        ),
    )
    coarse_node_count: int
    refined_interval_count: int
    unresolved_intervals: int = Field(
        description=(
            "Intervals that reached the subdivision limit without clearing. "
            "A nonzero count is a disclosed gap in capture, not a failure."
        ),
    )
    declination_evaluations: int
    policy: OutOfBoundsPolicyResponse


class OutOfBoundsSearchRequest(_StrictModel):
    body: str = Field(
        description=(
            "Sun through Pluto, or any globally unique or family-qualified "
            "asteroid/comet name ('asteroid:Name', 'comet:Name'). The lunar "
            "nodes and apogees are not admitted: Moira models them as "
            "longitude-only points, so they have no declination, and a node "
            "lies on the ecliptic by construction in any case."
        ),
    )
    jd_start: float
    jd_end: float
    angular_resolution_deg: float | None = Field(
        default=None,
        description=(
            "Degrees of bound-function travel admitted per coarse scan step. "
            "Smaller values scan more finely. Omit for the engine default."
        ),
    )
    max_step_days: float | None = Field(
        default=None,
        description="Ceiling on the coarse scan step, in days.",
    )
    solver_tolerance_days: float | None = Field(
        default=None,
        description="Bisection tolerance for crossings and culminations, in days.",
    )
    max_declination_evaluations: int | None = Field(
        default=None,
        description=(
            "Ceiling on declination evaluations for this search. Omit for the "
            "route's own default ceiling; a value above it is not accepted, "
            "since search cost is linear in the requested span."
        ),
    )


class OutOfBoundsSearchResponse(_StrictModel):
    body: str
    resolved_name: str
    resolved_kind: str = Field(
        description="'planet', 'asteroid', 'comet', or 'star'."
    )
    jd_start: float
    jd_end: float
    obliquity_at_start: float
    obliquity_at_end: float
    out_of_bounds_at_start: bool
    out_of_bounds_at_end: bool
    excursion_count: int
    excursions: list[OutOfBoundsExcursionResponse]
    scan_truth: OutOfBoundsScanTruthResponse


__all__ = [
    "OutOfBoundsCrossingResponse",
    "OutOfBoundsCulminationResponse",
    "OutOfBoundsExcursionResponse",
    "OutOfBoundsPolicyResponse",
    "OutOfBoundsScanTruthResponse",
    "OutOfBoundsSearchRequest",
    "OutOfBoundsSearchResponse",
]
