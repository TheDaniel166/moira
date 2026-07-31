"""Phase 2 numerical composition for physical point-source visibility.

This internal module combines already response-integrated photometric
quantities.  It does not contain CIE source tables, search for a data pack,
resolve target identities, calculate sky geometry, choose public policy, or
solve visibility events.

The admitted equations are:

* CIE 191:2010 MES2 equations 2, 4, and 5, as summarized by CIE
  TN 004:2016 and TN 007:2017; and
* Crumey (2014) equations 28 and 34 for the full-range Blackwell
  point-source threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._visibility_lut import (
    VisibilityDataPack,
    VisibilityDataPackReceipt,
    VisibilityDirectExtinctionSpectrum,
    VisibilityRadianceSample,
)


_COMPOSITE_MODEL_ID = "clear_sky_naked_eye_point_source_v1"
_ATMOSPHERE_MODEL_ID = "libradtran_2_0_6_mystic_spherical_v1"
_THRESHOLD_MODEL_ID = (
    "blackwell_crumey_full_range_point_source_v1"
)
_SPECTRAL_RESPONSE_MODEL_ID = "cie_mes2_2010_v1"
_OBSERVER_PROTOCOL_ID = (
    "known_location_directed_averted_observation_v1"
)
_MODELED_BACKGROUND_ID = (
    "modeled_twilight_plus_measured_dark_sky_v1"
)
_MODELED_COMPONENT_BACKGROUND_ID = (
    "modeled_twilight_plus_declared_background_components_v1"
)
_MEASURED_BACKGROUND_ID = (
    "measured_directional_photopic_scotopic_v1"
)
_SQM_TRANSFORM_ID = "crumey_2014_v_equivalent_sqm_transform_v1"
_ERROR_BUDGET_METHOD_ID = (
    "phase2_data_pack_declared_numerical_error_envelope_v1"
)

_CIE_PHOTOPIC_EFFICACY_LM_W = 683.0
_CIE_SCOTOPIC_EFFICACY_LM_W = 1700.0
_CIE_V_PRIME_555 = (
    _CIE_PHOTOPIC_EFFICACY_LM_W
    / _CIE_SCOTOPIC_EFFICACY_LM_W
)
_CIE_MES2_A = 0.7670
_CIE_MES2_B = 0.3334
_CIE_SCOTOPIC_MAX_CD_M2 = 0.005
_CIE_PHOTOPIC_MIN_CD_M2 = 5.0
_CIE_MES2_TOLERANCE = 1.0e-12
_CIE_MES2_MAX_ITERATIONS = 100

_CRUMEY_A1 = 5.949e-8
_CRUMEY_A2 = -2.389e-7
_CRUMEY_A3 = 2.459e-7
_CRUMEY_A4 = 4.120e-4
_CRUMEY_A5 = -4.225e-4
_CRUMEY_FIELD_FACTOR = 2.0
_CRUMEY_ZERO_POINT_LUX = 2.54e-6
_CRUMEY_BACKGROUND_MIN_CD_M2 = 3.426e-5
_CRUMEY_BACKGROUND_MAX_CD_M2 = 3426.0
_CRUMEY_SQM_ZERO_POINT = 12.58

_SPECTRAL_BIN_COUNT = 400
_HEX_DIGITS = frozenset("0123456789abcdef")
_SEPARATELY_MODELED_BACKGROUND_COMPONENT_IDS = frozenset({
    "airglow",
    "zodiacal_light",
    "integrated_starlight",
    "artificial_light",
})


class PhysicalVisibilityCompositionError(ValueError):
    """Typed fail-closed error consumed by the public orchestration layer."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class SpectralComponentReceipt:
    """One exact resolved component of the internal physical model."""

    role: str
    component_id: str
    source_ids: tuple[str, ...]
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MesopicAdaptationState:
    """CIE MES2 adaptation result for one directional background."""

    model_id: str
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    scotopic_to_photopic_ratio: float
    adaptation_coefficient: float
    mesopic_luminance_cd_m2: float
    weighting_state: str
    solver_method: str
    iterations: int
    fixed_point_residual: float


@dataclass(frozen=True, slots=True)
class FullRangePointSourceThreshold:
    """Crumey full-range point-source threshold in one mesopic field."""

    model_id: str
    background_luminance_cd_m2: float
    field_factor: float
    threshold_illuminance_lux: float
    limiting_magnitude: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    equation_receipt: str


@dataclass(frozen=True, slots=True)
class DirectionalLuminance:
    """Source-identified photopic/scotopic directional background pair."""

    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    scope: str
    component_ids: tuple[str, ...]
    source_id: str
    source_receipt_sha256: str
    method_id: str
    component_inventory_complete: bool = False

    def __post_init__(self) -> None:
        _positive_finite(
            self.photopic_luminance_cd_m2,
            "photopic_luminance_cd_m2",
        )
        _positive_finite(
            self.scotopic_luminance_cd_m2,
            "scotopic_luminance_cd_m2",
        )
        if self.scope not in {"total_background", "dark_sky_anchor"}:
            raise ValueError(
                "scope must be total_background or dark_sky_anchor"
            )
        if (
            not self.component_ids
            or any(not value for value in self.component_ids)
            or len(set(self.component_ids)) != len(self.component_ids)
        ):
            raise ValueError(
                "component_ids must be nonempty and unique"
            )
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        _require_sha256(
            self.source_receipt_sha256,
            "source_receipt_sha256",
        )
        if not self.method_id:
            raise ValueError("method_id must not be empty")
        if not isinstance(self.component_inventory_complete, bool):
            raise TypeError(
                "component_inventory_complete must be a bool"
            )


@dataclass(frozen=True, slots=True)
class ModeledDirectionalBackgroundComponent:
    """One caller-supplied, source-receipted background-model output."""

    component_id: str
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    model_id: str
    source_ids: tuple[str, ...]
    source_receipt_sha256: str
    spatial_applicability_id: str
    temporal_applicability_id: str
    direction_receipt_id: str
    validity_domain_id: str
    uncertainty_authority_id: str

    def __post_init__(self) -> None:
        if (
            self.component_id
            not in _SEPARATELY_MODELED_BACKGROUND_COMPONENT_IDS
        ):
            raise ValueError(
                "component_id must identify airglow, zodiacal_light, "
                "integrated_starlight, or artificial_light"
            )
        _positive_finite(
            self.photopic_luminance_cd_m2,
            "photopic_luminance_cd_m2",
        )
        _positive_finite(
            self.scotopic_luminance_cd_m2,
            "scotopic_luminance_cd_m2",
        )
        if not isinstance(self.model_id, str) or not self.model_id:
            raise ValueError("model_id must not be empty")
        try:
            source_ids = tuple(self.source_ids)
        except TypeError as exc:
            raise TypeError(
                "source_ids must be an iterable of strings"
            ) from exc
        if (
            not source_ids
            or any(
                not isinstance(source_id, str) or not source_id
                for source_id in source_ids
            )
            or len(set(source_ids)) != len(source_ids)
        ):
            raise ValueError(
                "source_ids must be nonempty, unique strings"
            )
        object.__setattr__(self, "source_ids", source_ids)
        _require_sha256(
            self.source_receipt_sha256,
            "source_receipt_sha256",
        )
        qualifiers = (
            self.spatial_applicability_id,
            self.temporal_applicability_id,
            self.direction_receipt_id,
            self.validity_domain_id,
            self.uncertainty_authority_id,
        )
        if any(
            not isinstance(value, str) or not value
            for value in qualifiers
        ):
            raise ValueError(
                "modeled background components require spatial, temporal, "
                "directional, validity-domain, and uncertainty qualifiers"
            )


@dataclass(frozen=True, slots=True)
class BackgroundComposition:
    """Resolved non-overlapping background used for adaptation."""

    authority_id: str
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    component_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    modeled_twilight: VisibilityRadianceSample | None
    photopic_solver_relative_standard_error_bound: float | None
    scotopic_solver_relative_standard_error_bound: float | None
    solver_uncertainty_bound_method: str | None
    photopic_interpolation_maximum_error_mag: float | None
    photopic_interpolation_p95_error_mag: float | None
    scotopic_interpolation_maximum_error_mag: float | None
    scotopic_interpolation_p95_error_mag: float | None
    storage_maximum_error_mag: float | None
    component_inventory_complete: bool = False
    modeled_components: tuple[
        ModeledDirectionalBackgroundComponent,
        ...,
    ] = ()


@dataclass(frozen=True, slots=True)
class TargetSpectralProfile:
    """Source-identified target photometry and extinction-response weights.

    The two extinction-weight arrays are normalized response integrands over
    the pack's 380--780 nm, 1 nm bins.  The engine validates but never invents
    or silently normalizes them.
    """

    target_id: str
    top_of_atmosphere_visual_magnitude: float
    scotopic_to_photopic_ratio: float
    photopic_extinction_weights: tuple[float, ...]
    scotopic_extinction_weights: tuple[float, ...]
    photometry_model_id: str
    photometry_source_ids: tuple[str, ...]
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    spectral_model_details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id must not be empty")
        _finite(
            self.top_of_atmosphere_visual_magnitude,
            "top_of_atmosphere_visual_magnitude",
        )
        _positive_finite(
            self.scotopic_to_photopic_ratio,
            "scotopic_to_photopic_ratio",
        )
        _validate_response_weights(
            self.photopic_extinction_weights,
            "photopic_extinction_weights",
        )
        _validate_response_weights(
            self.scotopic_extinction_weights,
            "scotopic_extinction_weights",
        )
        if not self.photometry_model_id:
            raise ValueError("photometry_model_id must not be empty")
        _validate_source_ids(
            self.photometry_source_ids,
            "photometry_source_ids",
        )
        if not self.spectral_profile_id:
            raise ValueError("spectral_profile_id must not be empty")
        _validate_source_ids(
            self.spectral_source_ids,
            "spectral_source_ids",
        )
        _require_sha256(
            self.spectral_source_receipt_sha256,
            "spectral_source_receipt_sha256",
        )
        detail_keys: list[str] = []
        for detail in self.spectral_model_details:
            if (
                not isinstance(detail, tuple)
                or len(detail) != 2
                or not all(
                    isinstance(value, str) and value
                    for value in detail
                )
            ):
                raise ValueError(
                    "spectral_model_details must contain nonempty "
                    "string pairs"
                )
            detail_keys.append(detail[0])
        if len(detail_keys) != len(set(detail_keys)):
            raise ValueError(
                "spectral_model_details keys must be unique"
            )


@dataclass(frozen=True, slots=True)
class ConditionedTarget:
    """Target illuminance after response-specific direct transmission."""

    target_id: str
    top_of_atmosphere_visual_magnitude: float
    top_of_atmosphere_photopic_illuminance_lux: float
    top_of_atmosphere_scotopic_illuminance_lux: float
    photopic_transmission: float
    scotopic_transmission: float
    conditioned_photopic_illuminance_lux: float
    conditioned_scotopic_illuminance_lux: float
    conditioned_mesopic_illuminance_lux: float
    conditioned_target_magnitude: float
    direct_interpolation_maximum_error_mag: float
    direct_interpolation_p95_error_mag: float
    storage_maximum_error_mag: float


@dataclass(frozen=True, slots=True)
class VisibilityMarginErrorBudget:
    """Declared pack-numerical envelope around one nominal margin.

    This is deliberately not a scientific-confidence interval.  It propagates
    the admitted one-relative-standard-error solver term plus maximum
    interpolation and binary-storage errors owned by the data pack.
    Source-model, observer-population, measurement, and real-atmosphere
    uncertainty remain named but unquantified.
    """

    method_id: str
    background_error_authority: str
    solver_relative_standard_error_multiplier: float | None
    background_mesopic_luminance_envelope_lower_cd_m2: float
    background_mesopic_luminance_envelope_upper_cd_m2: float
    limiting_magnitude_envelope_lower: float
    limiting_magnitude_envelope_upper: float
    conditioned_target_magnitude_maximum_pack_error: float
    visibility_margin_envelope_lower_magnitude: float
    visibility_margin_envelope_upper_magnitude: float
    visibility_margin_envelope_maximum_deviation_magnitude: float
    visibility_classification_within_data_pack_envelope: str
    included_error_sources: tuple[str, ...]
    unquantified_error_sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.method_id:
            raise ValueError("method_id must not be empty")
        if not self.background_error_authority:
            raise ValueError(
                "background_error_authority must not be empty"
            )
        if self.solver_relative_standard_error_multiplier is not None:
            _positive_finite(
                self.solver_relative_standard_error_multiplier,
                "solver_relative_standard_error_multiplier",
            )
        lower_luminance = _positive_finite(
            self.background_mesopic_luminance_envelope_lower_cd_m2,
            "background_mesopic_luminance_envelope_lower_cd_m2",
        )
        upper_luminance = _positive_finite(
            self.background_mesopic_luminance_envelope_upper_cd_m2,
            "background_mesopic_luminance_envelope_upper_cd_m2",
        )
        if lower_luminance > upper_luminance:
            raise ValueError(
                "background mesopic luminance bounds are reversed"
            )
        lower_limit = _finite(
            self.limiting_magnitude_envelope_lower,
            "limiting_magnitude_envelope_lower",
        )
        upper_limit = _finite(
            self.limiting_magnitude_envelope_upper,
            "limiting_magnitude_envelope_upper",
        )
        if lower_limit > upper_limit:
            raise ValueError("limiting-magnitude bounds are reversed")
        _nonnegative_finite(
            self.conditioned_target_magnitude_maximum_pack_error,
            "conditioned_target_magnitude_maximum_pack_error",
        )
        lower_margin = _finite(
            self.visibility_margin_envelope_lower_magnitude,
            "visibility_margin_envelope_lower_magnitude",
        )
        upper_margin = _finite(
            self.visibility_margin_envelope_upper_magnitude,
            "visibility_margin_envelope_upper_magnitude",
        )
        if lower_margin > upper_margin:
            raise ValueError("visibility-margin bounds are reversed")
        _nonnegative_finite(
            self.visibility_margin_envelope_maximum_deviation_magnitude,
            "visibility_margin_envelope_maximum_deviation_magnitude",
        )
        expected_classification = (
            "visible"
            if lower_margin >= 0.0
            else "not_visible"
            if upper_margin < 0.0
            else "indeterminate"
        )
        if (
            self.visibility_classification_within_data_pack_envelope
            != expected_classification
        ):
            raise ValueError(
                "visibility classification contradicts margin bounds"
            )
        _validate_source_ids(
            self.included_error_sources,
            "included_error_sources",
        )
        _validate_source_ids(
            self.unquantified_error_sources,
            "unquantified_error_sources",
        )


@dataclass(frozen=True, slots=True)
class SpectralSingleEpochTruth:
    """Evaluated truth for the internal Phase 2 numerical contract."""

    composite_model_id: str
    observer_protocol_id: str
    data_pack_receipt: VisibilityDataPackReceipt
    background: BackgroundComposition
    adaptation: MesopicAdaptationState
    threshold: FullRangePointSourceThreshold
    target: ConditionedTarget
    visibility_margin_magnitude: float
    visible: bool
    error_budget: VisibilityMarginErrorBudget
    components: tuple[SpectralComponentReceipt, ...]


def cie_mes2_adaptation(
    photopic_luminance_cd_m2: float,
    scotopic_luminance_cd_m2: float,
) -> MesopicAdaptationState:
    """Solve CIE MES2 equations 4 and 5 for one adaptation field."""

    photopic = _positive_finite(
        photopic_luminance_cd_m2,
        "photopic_luminance_cd_m2",
    )
    scotopic = _positive_finite(
        scotopic_luminance_cd_m2,
        "scotopic_luminance_cd_m2",
    )

    coefficient = 0.5
    for iteration in range(1, _CIE_MES2_MAX_ITERATIONS + 1):
        mesopic = _mesopic_quantity(
            photopic,
            scotopic,
            coefficient,
        )
        updated = _mes2_coefficient(mesopic)
        residual = abs(updated - coefficient)
        if residual <= _CIE_MES2_TOLERANCE:
            coefficient = updated
            mesopic = _mesopic_quantity(
                photopic,
                scotopic,
                coefficient,
            )
            return _adaptation_state(
                photopic,
                scotopic,
                coefficient,
                mesopic,
                "cie_191_2010_fixed_point_m0_0_5",
                iteration,
            )
        coefficient = updated

    coefficient, iterations = _mes2_bisection(photopic, scotopic)
    mesopic = _mesopic_quantity(photopic, scotopic, coefficient)
    return _adaptation_state(
        photopic,
        scotopic,
        coefficient,
        mesopic,
        "bracketed_fallback_same_cie_equations",
        iterations,
    )


def blackwell_crumey_full_range_threshold(
    background_luminance_cd_m2: float,
) -> FullRangePointSourceThreshold:
    """Evaluate Crumey (2014) equations 28 and 34 with fixed ``F=2``."""

    background = _positive_finite(
        background_luminance_cd_m2,
        "background_luminance_cd_m2",
    )
    if not (
        _CRUMEY_BACKGROUND_MIN_CD_M2
        <= background
        <= _CRUMEY_BACKGROUND_MAX_CD_M2
    ):
        raise PhysicalVisibilityCompositionError(
            "criterion_out_of_domain",
            (
                f"background_luminance_cd_m2={background} is outside "
                f"[{_CRUMEY_BACKGROUND_MIN_CD_M2}, "
                f"{_CRUMEY_BACKGROUND_MAX_CD_M2}]"
            ),
        )
    radicand = (
        _CRUMEY_A1 * background**0.5
        + _CRUMEY_A2 * background**0.75
        + _CRUMEY_A3 * background
    )
    if radicand < 0.0:
        raise PhysicalVisibilityCompositionError(
            "criterion_out_of_domain",
            "Crumey equation 34 radicand is negative",
        )
    base_threshold = (
        math.sqrt(radicand)
        + _CRUMEY_A4 * background**0.25
        + _CRUMEY_A5 * background**0.5
    ) ** 2
    threshold = _CRUMEY_FIELD_FACTOR * base_threshold
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise PhysicalVisibilityCompositionError(
            "criterion_out_of_domain",
            "Crumey equation 34 returned a nonpositive threshold",
        )
    return FullRangePointSourceThreshold(
        model_id=_THRESHOLD_MODEL_ID,
        background_luminance_cd_m2=background,
        field_factor=_CRUMEY_FIELD_FACTOR,
        threshold_illuminance_lux=threshold,
        limiting_magnitude=-2.5
        * math.log10(threshold / _CRUMEY_ZERO_POINT_LUX),
        valid_background_min_cd_m2=_CRUMEY_BACKGROUND_MIN_CD_M2,
        valid_background_max_cd_m2=_CRUMEY_BACKGROUND_MAX_CD_M2,
        equation_receipt="crumey_2014_equations_28_34_field_factor_2",
    )


def sqm_directional_luminance(
    sqm_mag_arcsec2: float,
    *,
    scotopic_to_photopic_ratio: float,
    scope: str,
    component_ids: tuple[str, ...],
    measurement_source_id: str,
    measurement_receipt_sha256: str,
    device_bandpass_id: str,
    pointing_receipt_id: str,
    temporal_applicability_id: str,
    spectral_ratio_source_id: str,
    component_inventory_complete: bool = False,
) -> DirectionalLuminance:
    """Transform a fully qualified SQM/V-equivalent measurement.

    The approximation follows Crumey (2014), section 1.3:
    ``mu_V = -2.5 log10(B) + 12.58``.  Required device, direction,
    temporal, and S/P receipts prevent an unqualified scalar from entering.
    """

    sqm = _finite(sqm_mag_arcsec2, "sqm_mag_arcsec2")
    ratio = _positive_finite(
        scotopic_to_photopic_ratio,
        "scotopic_to_photopic_ratio",
    )
    qualifiers = (
        device_bandpass_id,
        pointing_receipt_id,
        temporal_applicability_id,
        spectral_ratio_source_id,
    )
    if any(not value for value in qualifiers):
        raise ValueError(
            "SQM input requires bandpass, pointing, temporal, and S/P receipts"
        )
    photopic = 10.0 ** (
        (_CRUMEY_SQM_ZERO_POINT - sqm) / 2.5
    )
    return DirectionalLuminance(
        photopic_luminance_cd_m2=photopic,
        scotopic_luminance_cd_m2=photopic * ratio,
        scope=scope,
        component_ids=component_ids,
        source_id=measurement_source_id,
        source_receipt_sha256=measurement_receipt_sha256,
        method_id=(
            f"{_SQM_TRANSFORM_ID}:{device_bandpass_id}:"
            f"{pointing_receipt_id}:{temporal_applicability_id}:"
            f"{spectral_ratio_source_id}"
        ),
        component_inventory_complete=component_inventory_complete,
    )


def compose_directional_background(
    *,
    measured_total: DirectionalLuminance | None = None,
    modeled_twilight: VisibilityRadianceSample | None = None,
    dark_sky_anchor: DirectionalLuminance | None = None,
    modeled_components: tuple[
        ModeledDirectionalBackgroundComponent,
        ...,
    ] = (),
) -> BackgroundComposition:
    """Resolve exactly one background authority without double counting."""

    try:
        components = tuple(modeled_components)
    except TypeError as exc:
        raise TypeError(
            "modeled_components must be an iterable of "
            "ModeledDirectionalBackgroundComponent values"
        ) from exc
    if any(
        not isinstance(
            component,
            ModeledDirectionalBackgroundComponent,
        )
        for component in components
    ):
        raise TypeError(
            "modeled_components must contain only "
            "ModeledDirectionalBackgroundComponent values"
        )
    components = tuple(
        sorted(components, key=lambda component: component.component_id)
    )
    modeled_component_ids = tuple(
        component.component_id for component in components
    )
    if len(set(modeled_component_ids)) != len(modeled_component_ids):
        raise PhysicalVisibilityCompositionError(
            "background_components_conflict",
            "a modeled background component kind was supplied more than once",
        )

    if measured_total is not None:
        if (
            modeled_twilight is not None
            or dark_sky_anchor is not None
            or components
        ):
            raise PhysicalVisibilityCompositionError(
                "background_components_conflict",
                "measured total background cannot be combined with models",
            )
        if measured_total.scope != "total_background":
            raise PhysicalVisibilityCompositionError(
                "background_input_incomplete",
                "measured total background has the wrong scope",
            )
        return BackgroundComposition(
            authority_id=_MEASURED_BACKGROUND_ID,
            photopic_luminance_cd_m2=(
                measured_total.photopic_luminance_cd_m2
            ),
            scotopic_luminance_cd_m2=(
                measured_total.scotopic_luminance_cd_m2
            ),
            component_ids=measured_total.component_ids,
            source_ids=(measured_total.source_id,),
            modeled_twilight=None,
            photopic_solver_relative_standard_error_bound=None,
            scotopic_solver_relative_standard_error_bound=None,
            solver_uncertainty_bound_method=None,
            photopic_interpolation_maximum_error_mag=None,
            photopic_interpolation_p95_error_mag=None,
            scotopic_interpolation_maximum_error_mag=None,
            scotopic_interpolation_p95_error_mag=None,
            storage_maximum_error_mag=None,
            component_inventory_complete=True,
        )

    if modeled_twilight is None or dark_sky_anchor is None:
        raise PhysicalVisibilityCompositionError(
            "background_input_incomplete",
            (
                "modeled twilight requires a source-identified "
                "dark-sky anchor"
            ),
        )
    if dark_sky_anchor.scope != "dark_sky_anchor":
        raise PhysicalVisibilityCompositionError(
            "background_components_conflict",
            "modeled twilight requires dark_sky_anchor scope",
        )
    if components and not dark_sky_anchor.component_inventory_complete:
        raise PhysicalVisibilityCompositionError(
            "background_component_inventory_incomplete",
            (
                "a dark-sky anchor combined with modeled components must "
                "declare a complete component inventory"
            ),
        )
    supplied_model_ids = {
        "solar_twilight",
        *modeled_component_ids,
    }
    overlap = supplied_model_ids.intersection(
        dark_sky_anchor.component_ids
    )
    if overlap:
        raise PhysicalVisibilityCompositionError(
            "background_components_conflict",
            f"background component supplied twice: {sorted(overlap)}",
        )
    photopic_luminance = math.fsum((
        modeled_twilight.photopic_luminance_cd_m2,
        dark_sky_anchor.photopic_luminance_cd_m2,
        *(
            component.photopic_luminance_cd_m2
            for component in components
        ),
    ))
    scotopic_luminance = math.fsum((
        modeled_twilight.scotopic_luminance_cd_m2,
        dark_sky_anchor.scotopic_luminance_cd_m2,
        *(
            component.scotopic_luminance_cd_m2
            for component in components
        ),
    ))
    source_ids = tuple(dict.fromkeys((
        dark_sky_anchor.source_id,
        *(
            source_id
            for component in components
            for source_id in component.source_ids
        ),
    )))
    return BackgroundComposition(
        authority_id=(
            _MODELED_COMPONENT_BACKGROUND_ID
            if components
            else _MODELED_BACKGROUND_ID
        ),
        photopic_luminance_cd_m2=photopic_luminance,
        scotopic_luminance_cd_m2=scotopic_luminance,
        component_ids=(
            "solar_twilight",
            *dark_sky_anchor.component_ids,
            *modeled_component_ids,
        ),
        source_ids=source_ids,
        modeled_twilight=modeled_twilight,
        photopic_solver_relative_standard_error_bound=(
            modeled_twilight
            .photopic_solver_relative_standard_error_bound
        ),
        scotopic_solver_relative_standard_error_bound=(
            modeled_twilight
            .scotopic_solver_relative_standard_error_bound
        ),
        solver_uncertainty_bound_method=(
            modeled_twilight.solver_uncertainty_bound_method
        ),
        photopic_interpolation_maximum_error_mag=(
            modeled_twilight.photopic_interpolation_maximum_error_mag
        ),
        photopic_interpolation_p95_error_mag=(
            modeled_twilight.photopic_interpolation_p95_error_mag
        ),
        scotopic_interpolation_maximum_error_mag=(
            modeled_twilight.scotopic_interpolation_maximum_error_mag
        ),
        scotopic_interpolation_p95_error_mag=(
            modeled_twilight.scotopic_interpolation_p95_error_mag
        ),
        storage_maximum_error_mag=(
            modeled_twilight.storage_maximum_error_mag
        ),
        component_inventory_complete=(
            dark_sky_anchor.component_inventory_complete
        ),
        modeled_components=components,
    )


def condition_target(
    profile: TargetSpectralProfile,
    direct: VisibilityDirectExtinctionSpectrum,
    adaptation_coefficient: float,
) -> ConditionedTarget:
    """Condition target illuminance through the admitted spectral path."""

    coefficient = _unit_interval(
        adaptation_coefficient,
        "adaptation_coefficient",
    )
    if direct.spectral_bin_start_nm != tuple(
        float(value) for value in range(380, 780)
    ):
        raise PhysicalVisibilityCompositionError(
            "target_spectral_profile_missing",
            "direct-transmission spectral bins are not 380--780 nm",
        )
    photopic_transmission = math.fsum(
        weight * transmission
        for weight, transmission in zip(
            profile.photopic_extinction_weights,
            direct.transmission,
        )
    )
    scotopic_transmission = math.fsum(
        weight * transmission
        for weight, transmission in zip(
            profile.scotopic_extinction_weights,
            direct.transmission,
        )
    )
    if (
        photopic_transmission <= 0.0
        or scotopic_transmission <= 0.0
    ):
        raise PhysicalVisibilityCompositionError(
            "target_spectral_profile_missing",
            "response-weighted target transmission is nonpositive",
        )
    top_photopic = _CRUMEY_ZERO_POINT_LUX * 10.0 ** (
        -0.4 * profile.top_of_atmosphere_visual_magnitude
    )
    top_scotopic = (
        top_photopic * profile.scotopic_to_photopic_ratio
    )
    conditioned_photopic = top_photopic * photopic_transmission
    conditioned_scotopic = top_scotopic * scotopic_transmission
    conditioned_mesopic = _mesopic_quantity(
        conditioned_photopic,
        conditioned_scotopic,
        coefficient,
    )
    return ConditionedTarget(
        target_id=profile.target_id,
        top_of_atmosphere_visual_magnitude=(
            profile.top_of_atmosphere_visual_magnitude
        ),
        top_of_atmosphere_photopic_illuminance_lux=top_photopic,
        top_of_atmosphere_scotopic_illuminance_lux=top_scotopic,
        photopic_transmission=photopic_transmission,
        scotopic_transmission=scotopic_transmission,
        conditioned_photopic_illuminance_lux=conditioned_photopic,
        conditioned_scotopic_illuminance_lux=conditioned_scotopic,
        conditioned_mesopic_illuminance_lux=conditioned_mesopic,
        conditioned_target_magnitude=-2.5
        * math.log10(conditioned_mesopic / _CRUMEY_ZERO_POINT_LUX),
        direct_interpolation_maximum_error_mag=(
            direct.interpolation_maximum_error_mag
        ),
        direct_interpolation_p95_error_mag=(
            direct.interpolation_p95_error_mag
        ),
        storage_maximum_error_mag=direct.storage_maximum_error_mag,
    )


def _visibility_margin_error_budget(
    background: BackgroundComposition,
    target: ConditionedTarget,
    nominal_margin: float,
) -> VisibilityMarginErrorBudget:
    """Propagate the pack's declared numerical terms to one margin envelope."""

    nominal = _finite(nominal_margin, "nominal_margin")
    (
        photopic_lower,
        photopic_upper,
        scotopic_lower,
        scotopic_upper,
        authority,
        included_background_sources,
        unquantified_background_sources,
    ) = _background_luminance_error_bounds(background)

    mesopic_values: list[float] = []
    limiting_magnitudes: list[float] = []
    for photopic in (photopic_lower, photopic_upper):
        for scotopic in (scotopic_lower, scotopic_upper):
            adaptation = cie_mes2_adaptation(photopic, scotopic)
            threshold = blackwell_crumey_full_range_threshold(
                adaptation.mesopic_luminance_cd_m2
            )
            mesopic_values.append(adaptation.mesopic_luminance_cd_m2)
            limiting_magnitudes.append(threshold.limiting_magnitude)

    limiting_lower = min(limiting_magnitudes)
    limiting_upper = max(limiting_magnitudes)
    target_error = _nonnegative_finite(
        target.direct_interpolation_maximum_error_mag,
        "direct_interpolation_maximum_error_mag",
    ) + _nonnegative_finite(
        target.storage_maximum_error_mag,
        "direct_storage_maximum_error_mag",
    )
    _finite(target_error, "conditioned target maximum error")
    target_lower = _finite(
        target.conditioned_target_magnitude - target_error,
        "conditioned target lower magnitude",
    )
    target_upper = _finite(
        target.conditioned_target_magnitude + target_error,
        "conditioned target upper magnitude",
    )
    margin_lower = _finite(
        limiting_lower - target_upper,
        "visibility margin lower bound",
    )
    margin_upper = _finite(
        limiting_upper - target_lower,
        "visibility margin upper bound",
    )
    if not margin_lower <= nominal <= margin_upper:
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            "nominal visibility margin falls outside its numerical envelope",
        )
    margin_error = max(
        nominal - margin_lower,
        margin_upper - nominal,
    )
    classification = (
        "visible"
        if margin_lower >= 0.0
        else "not_visible"
        if margin_upper < 0.0
        else "indeterminate"
    )
    return VisibilityMarginErrorBudget(
        method_id=_ERROR_BUDGET_METHOD_ID,
        background_error_authority=authority,
        solver_relative_standard_error_multiplier=(
            1.0 if background.modeled_twilight is not None else None
        ),
        background_mesopic_luminance_envelope_lower_cd_m2=min(
            mesopic_values
        ),
        background_mesopic_luminance_envelope_upper_cd_m2=max(
            mesopic_values
        ),
        limiting_magnitude_envelope_lower=limiting_lower,
        limiting_magnitude_envelope_upper=limiting_upper,
        conditioned_target_magnitude_maximum_pack_error=target_error,
        visibility_margin_envelope_lower_magnitude=margin_lower,
        visibility_margin_envelope_upper_magnitude=margin_upper,
        visibility_margin_envelope_maximum_deviation_magnitude=(
            margin_error
        ),
        visibility_classification_within_data_pack_envelope=classification,
        included_error_sources=(
            *included_background_sources,
            "pack_direct_extinction_interpolation_maximum_error",
            "pack_direct_extinction_storage_maximum_error",
        ),
        unquantified_error_sources=(
            *unquantified_background_sources,
            "planetary_photometry_model_uncertainty",
            "planetary_spectral_profile_source_uncertainty",
            "cie_mes2_model_uncertainty",
            "blackwell_crumey_observer_population_uncertainty",
            "actual_atmospheric_state_variability",
        ),
    )


def _background_luminance_error_bounds(
    background: BackgroundComposition,
) -> tuple[
    float,
    float,
    float,
    float,
    str,
    tuple[str, ...],
    tuple[str, ...],
]:
    """Return photopic/scotopic bounds without inventing input uncertainty."""

    twilight = background.modeled_twilight
    if twilight is None:
        return (
            background.photopic_luminance_cd_m2,
            background.photopic_luminance_cd_m2,
            background.scotopic_luminance_cd_m2,
            background.scotopic_luminance_cd_m2,
            "caller_measured_total_background_no_pack_error_envelope",
            (),
            ("measured_total_background_input_uncertainty",),
        )

    required_values = (
        background.photopic_solver_relative_standard_error_bound,
        background.scotopic_solver_relative_standard_error_bound,
        background.photopic_interpolation_maximum_error_mag,
        background.scotopic_interpolation_maximum_error_mag,
        background.storage_maximum_error_mag,
    )
    if any(value is None for value in required_values):
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            "modeled twilight is missing a numerical-error input",
        )
    (
        photopic_rse_value,
        scotopic_rse_value,
        photopic_interpolation_value,
        scotopic_interpolation_value,
        storage_value,
    ) = required_values
    if (
        photopic_rse_value is None
        or scotopic_rse_value is None
        or photopic_interpolation_value is None
        or scotopic_interpolation_value is None
        or storage_value is None
    ):
        raise AssertionError("error inputs were narrowed above")

    photopic_anchor = _background_anchor_component(
        background.photopic_luminance_cd_m2,
        twilight.photopic_luminance_cd_m2,
        "photopic",
    )
    scotopic_anchor = _background_anchor_component(
        background.scotopic_luminance_cd_m2,
        twilight.scotopic_luminance_cd_m2,
        "scotopic",
    )
    photopic_twilight_lower, photopic_twilight_upper = (
        _luminance_error_bounds(
            twilight.photopic_luminance_cd_m2,
            photopic_rse_value,
            photopic_interpolation_value,
            storage_value,
            "photopic twilight",
        )
    )
    scotopic_twilight_lower, scotopic_twilight_upper = (
        _luminance_error_bounds(
            twilight.scotopic_luminance_cd_m2,
            scotopic_rse_value,
            scotopic_interpolation_value,
            storage_value,
            "scotopic twilight",
        )
    )
    return (
        _positive_finite(
            photopic_anchor + photopic_twilight_lower,
            "photopic background lower bound",
        ),
        _positive_finite(
            photopic_anchor + photopic_twilight_upper,
            "photopic background upper bound",
        ),
        _positive_finite(
            scotopic_anchor + scotopic_twilight_lower,
            "scotopic background lower bound",
        ),
        _positive_finite(
            scotopic_anchor + scotopic_twilight_upper,
            "scotopic background upper bound",
        ),
        "data_pack_modeled_twilight_declared_error_envelope",
        (
            "pack_twilight_solver_relative_standard_error",
            "pack_twilight_interpolation_maximum_error",
            "pack_twilight_storage_maximum_error",
        ),
        (
            "dark_sky_anchor_input_uncertainty",
            *(
                (
                    "modeled_background_component:"
                    f"{component.component_id}:input_uncertainty"
                )
                for component in background.modeled_components
            ),
        ),
    )


def _background_anchor_component(
    total: float,
    modeled_twilight: float,
    label: str,
) -> float:
    anchor = math.fsum((total, -modeled_twilight))
    tolerance = math.ulp(max(abs(total), abs(modeled_twilight), 1.0))
    if anchor < -tolerance:
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            f"{label} background composition has a negative anchor",
        )
    return max(0.0, anchor)


def _luminance_error_bounds(
    nominal_luminance: float,
    relative_standard_error: float,
    interpolation_error_mag: float,
    storage_error_mag: float,
    label: str,
) -> tuple[float, float]:
    nominal = _positive_finite(nominal_luminance, label)
    relative_error = _relative_standard_error_bound(
        relative_standard_error,
        f"{label} relative standard error",
    )
    magnitude_error = _nonnegative_finite(
        interpolation_error_mag,
        f"{label} interpolation error",
    ) + _nonnegative_finite(
        storage_error_mag,
        f"{label} storage error",
    )
    try:
        magnitude_factor = 10.0 ** (0.4 * magnitude_error)
    except OverflowError as exc:
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            f"{label} magnitude-error factor overflowed",
        ) from exc
    lower = nominal * (1.0 - relative_error) / magnitude_factor
    upper = nominal * (1.0 + relative_error) * magnitude_factor
    if (
        not math.isfinite(lower)
        or not math.isfinite(upper)
        or lower <= 0.0
        or upper < lower
    ):
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            f"{label} numerical-error bounds are inadmissible",
        )
    return lower, upper


def spectral_single_epoch_truth(
    pack: VisibilityDataPack,
    profile: TargetSpectralProfile,
    *,
    target_true_altitude_deg: float,
    measured_total_background: DirectionalLuminance | None = None,
    solar_center_altitude_deg: float | None = None,
    relative_solar_azimuth_deg: float | None = None,
    dark_sky_anchor: DirectionalLuminance | None = None,
    modeled_background_components: tuple[
        ModeledDirectionalBackgroundComponent,
        ...,
    ] = (),
) -> SpectralSingleEpochTruth:
    """Evaluate the Phase 2 numerical truth without geometry or event search."""

    direct = pack.interpolate_direct_extinction_spectrum(
        target_true_altitude_deg=target_true_altitude_deg
    )
    if measured_total_background is not None:
        if (
            solar_center_altitude_deg is not None
            or relative_solar_azimuth_deg is not None
            or dark_sky_anchor is not None
            or modeled_background_components
        ):
            raise PhysicalVisibilityCompositionError(
                "background_components_conflict",
                "measured total background conflicts with modeled inputs",
            )
        background = compose_directional_background(
            measured_total=measured_total_background,
            modeled_components=modeled_background_components,
        )
    else:
        if (
            solar_center_altitude_deg is None
            or relative_solar_azimuth_deg is None
        ):
            raise PhysicalVisibilityCompositionError(
                "background_input_incomplete",
                "modeled twilight geometry is incomplete",
            )
        twilight = pack.interpolate_twilight_luminance(
            solar_center_altitude_deg=solar_center_altitude_deg,
            target_true_altitude_deg=target_true_altitude_deg,
            relative_solar_azimuth_deg=relative_solar_azimuth_deg,
        )
        background = compose_directional_background(
            modeled_twilight=twilight,
            dark_sky_anchor=dark_sky_anchor,
            modeled_components=modeled_background_components,
        )

    adaptation = cie_mes2_adaptation(
        background.photopic_luminance_cd_m2,
        background.scotopic_luminance_cd_m2,
    )
    threshold = blackwell_crumey_full_range_threshold(
        adaptation.mesopic_luminance_cd_m2
    )
    target = condition_target(
        profile,
        direct,
        adaptation.adaptation_coefficient,
    )
    margin = (
        threshold.limiting_magnitude
        - target.conditioned_target_magnitude
    )
    error_budget = _visibility_margin_error_budget(
        background,
        target,
        margin,
    )
    components = (
        SpectralComponentReceipt(
            role="directional_atmosphere",
            component_id=_ATMOSPHERE_MODEL_ID,
            source_ids=(
                "libRadtran:2.0.6",
                "REPTRAN:libradtran_reptran_2024_all",
            ),
            details=(
                ("pack_id", pack.receipt.pack_id),
                ("pack_version", pack.receipt.version),
                ("manifest_sha256", pack.receipt.manifest_sha256),
                ("luminance_units", "cd_m-2"),
                ("direct_extinction_units", "magnitude"),
            ),
        ),
        SpectralComponentReceipt(
            role="spectral_response",
            component_id=_SPECTRAL_RESPONSE_MODEL_ID,
            source_ids=(
                "CIE:191:2010",
                "CIE:TN004:2016",
                "CIE:TN007:2017",
            ),
            details=(
                (
                    "adaptation_coefficient",
                    format(adaptation.adaptation_coefficient, ".17g"),
                ),
                ("weighting_state", adaptation.weighting_state),
                ("adaptation_luminance_units", "cd_m-2"),
            ),
        ),
        SpectralComponentReceipt(
            role="point_source_detection",
            component_id=_THRESHOLD_MODEL_ID,
            source_ids=(
                "Crumey:2014:equations_28_34",
                "Tousey_Koomen:1953:table_I",
            ),
            details=(
                ("field_factor", "2"),
                ("threshold_illuminance_units", "lux"),
                ("limiting_magnitude_units", "magnitude"),
            ),
        ),
        SpectralComponentReceipt(
            role="observer_protocol",
            component_id=_OBSERVER_PROTOCOL_ID,
            source_ids=(
                "CIE:TN007:2017:clause_6",
                "Blackwell:1946",
            ),
            details=(
                ("task", "known_target_directed_averted_detection"),
                ("optical_aid", "none"),
                (
                    "detection_field_factor_model_id",
                    "crumey_2014_equation_53_fixed_notional_f2_v1",
                ),
                ("detection_field_factor_value", "2"),
                ("detection_field_factor_mutable", "false"),
                ("probabilistic_detection_claimed", "false"),
            ),
        ),
        SpectralComponentReceipt(
            role="background_authority",
            component_id=background.authority_id,
            source_ids=background.source_ids,
            details=tuple(
                ("component", value)
                for value in background.component_ids
            )
            + (("luminance_units", "cd_m-2"),),
        ),
        *(
            SpectralComponentReceipt(
                role="modeled_background_component",
                component_id=component.model_id,
                source_ids=component.source_ids,
                details=(
                    ("background_component_id", component.component_id),
                    (
                        "photopic_luminance_cd_m2",
                        format(
                            component.photopic_luminance_cd_m2,
                            ".17g",
                        ),
                    ),
                    (
                        "scotopic_luminance_cd_m2",
                        format(
                            component.scotopic_luminance_cd_m2,
                            ".17g",
                        ),
                    ),
                    (
                        "source_receipt_sha256",
                        component.source_receipt_sha256,
                    ),
                    (
                        "spatial_applicability_id",
                        component.spatial_applicability_id,
                    ),
                    (
                        "temporal_applicability_id",
                        component.temporal_applicability_id,
                    ),
                    (
                        "direction_receipt_id",
                        component.direction_receipt_id,
                    ),
                    (
                        "validity_domain_id",
                        component.validity_domain_id,
                    ),
                    (
                        "uncertainty_authority_id",
                        component.uncertainty_authority_id,
                    ),
                ),
            )
            for component in background.modeled_components
        ),
        SpectralComponentReceipt(
            role="target_photometry",
            component_id=profile.photometry_model_id,
            source_ids=profile.photometry_source_ids,
            details=(
                ("target_id", profile.target_id),
                ("visual_magnitude_units", "magnitude"),
            ),
        ),
        SpectralComponentReceipt(
            role="target_spectral_profile",
            component_id=profile.spectral_profile_id,
            source_ids=profile.spectral_source_ids,
            details=(
                ("target_id", profile.target_id),
                (
                    "source_receipt_sha256",
                    profile.spectral_source_receipt_sha256,
                ),
                ("response_weight_units", "normalized_dimensionless"),
            )
            + profile.spectral_model_details,
        ),
        SpectralComponentReceipt(
            role="numerical_error_propagation",
            component_id=error_budget.method_id,
            source_ids=(
                (
                    "visibility_data_pack_manifest:"
                    f"{pack.receipt.manifest_sha256}"
                ),
            ),
            details=tuple(
                ("included_error_source", value)
                for value in error_budget.included_error_sources
            )
            + tuple(
                ("unquantified_error_source", value)
                for value in error_budget.unquantified_error_sources
            )
            + (
                (
                    "classification_within_data_pack_envelope",
                    error_budget
                    .visibility_classification_within_data_pack_envelope,
                ),
            ),
        ),
    )
    return SpectralSingleEpochTruth(
        composite_model_id=_COMPOSITE_MODEL_ID,
        observer_protocol_id=_OBSERVER_PROTOCOL_ID,
        data_pack_receipt=pack.receipt,
        background=background,
        adaptation=adaptation,
        threshold=threshold,
        target=target,
        visibility_margin_magnitude=margin,
        visible=margin >= 0.0,
        error_budget=error_budget,
        components=components,
    )


def _adaptation_state(
    photopic: float,
    scotopic: float,
    coefficient: float,
    mesopic: float,
    method: str,
    iterations: int,
) -> MesopicAdaptationState:
    if coefficient == 0.0:
        weighting_state = "scotopic"
    elif coefficient == 1.0:
        weighting_state = "photopic"
    else:
        weighting_state = "mesopic"
    return MesopicAdaptationState(
        model_id=_SPECTRAL_RESPONSE_MODEL_ID,
        photopic_luminance_cd_m2=photopic,
        scotopic_luminance_cd_m2=scotopic,
        scotopic_to_photopic_ratio=scotopic / photopic,
        adaptation_coefficient=coefficient,
        mesopic_luminance_cd_m2=mesopic,
        weighting_state=weighting_state,
        solver_method=method,
        iterations=iterations,
        fixed_point_residual=abs(
            coefficient - _mes2_coefficient(mesopic)
        ),
    )


def _mesopic_quantity(
    photopic: float,
    scotopic: float,
    coefficient: float,
) -> float:
    denominator = (
        coefficient
        + (1.0 - coefficient) * _CIE_V_PRIME_555
    )
    return (
        coefficient * photopic
        + (1.0 - coefficient)
        * scotopic
        * _CIE_V_PRIME_555
    ) / denominator


def _mes2_coefficient(mesopic_luminance: float) -> float:
    if mesopic_luminance <= _CIE_SCOTOPIC_MAX_CD_M2:
        return 0.0
    if mesopic_luminance >= _CIE_PHOTOPIC_MIN_CD_M2:
        return 1.0
    coefficient = (
        _CIE_MES2_A
        + _CIE_MES2_B * math.log10(mesopic_luminance)
    )
    # CIE 191 publishes A and B at finite decimal precision.  Their rounded
    # values evaluate slightly below zero immediately above 0.005 cd/m2 and
    # slightly above one immediately below 5 cd/m2.  Preserve the declared
    # piecewise boundary values instead of leaking that coefficient-rounding
    # artifact as an invalid adaptation state.
    return min(1.0, max(0.0, coefficient))


def _mes2_bisection(
    photopic: float,
    scotopic: float,
) -> tuple[float, int]:
    low = 0.0
    high = 1.0
    for iteration in range(1, _CIE_MES2_MAX_ITERATIONS + 1):
        coefficient = (low + high) / 2.0
        residual = coefficient - _mes2_coefficient(
            _mesopic_quantity(photopic, scotopic, coefficient)
        )
        if abs(residual) <= _CIE_MES2_TOLERANCE:
            return coefficient, iteration
        if residual < 0.0:
            low = coefficient
        else:
            high = coefficient
    raise PhysicalVisibilityCompositionError(
        "adaptation_state_incomplete",
        "CIE MES2 adaptation coefficient did not converge",
    )


def _validate_source_ids(
    values: tuple[str, ...],
    label: str,
) -> None:
    if (
        not isinstance(values, tuple)
        or not values
        or any(
            not isinstance(value, str) or not value
            for value in values
        )
        or len(set(values)) != len(values)
    ):
        raise ValueError(
            f"{label} must contain unique nonempty source identifiers"
        )


def _validate_response_weights(
    values: tuple[float, ...],
    label: str,
) -> None:
    if not isinstance(values, tuple) or len(values) != _SPECTRAL_BIN_COUNT:
        raise ValueError(f"{label} must contain exactly 400 values")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0.0
        for value in values
    ):
        raise ValueError(
            f"{label} must contain finite nonnegative values"
        )
    if not math.isclose(
        math.fsum(values),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError(f"{label} must sum to exactly one within 1e-12")


def _finite(value: float, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _positive_finite(value: float, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be > 0")
    return result


def _nonnegative_finite(value: float, label: str) -> float:
    result = _finite(value, label)
    if result < 0.0:
        raise ValueError(f"{label} must be >= 0")
    return result


def _relative_standard_error_bound(
    value: float,
    label: str,
) -> float:
    result = _nonnegative_finite(value, label)
    if result >= 1.0:
        raise PhysicalVisibilityCompositionError(
            "error_budget_not_evaluable",
            f"{label} must be below 1",
        )
    return result


def _unit_interval(value: float, label: str) -> float:
    result = _finite(value, label)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must be in [0, 1]")
    return result


def _require_sha256(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or bool(set(value) - _HEX_DIGITS)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
