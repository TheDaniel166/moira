"""Strict opt-in requests for bounded eclipse products; legacy models are stable."""
from typing import Literal

from pydantic import Field,model_validator

from .eclipse_diagnostics import DiagnosticModel,JdUt1


class SolarBoundedEvidenceRequest(DiagnosticModel):
    """Explicit UT1 event domain and independent product work allocations."""

    jd_ut1: JdUt1
    offset_days: list[float] = Field(default=[-1/6,1/6],min_length=2,max_length=2)
    products: list[Literal['occurrence','central_path','surface_topology','swept_region','geographic_width']] = Field(
        default=['geographic_width'],min_length=1,max_length=5)
    max_evaluations: int = Field(default=256,ge=0,le=4096,
        description='Deterministic per-product limit; initialization counters are separate.')
    tolerance_seconds: float = Field(default=.1,ge=.001,le=86400)
    width_tolerance_km: float = Field(default=1.,gt=0,le=100)

    @model_validator(mode='after')
    def check_domain(self):
        lo,hi = self.offset_days
        if not lo <= 0 <= hi or hi-lo > 1:
            raise ValueError('ordered domain must include zero and span at most one day')
        if len(set(self.products)) != len(self.products):
            raise ValueError('duplicate products are not allowed')
        return self


class LunarBoundedEvidenceRequest(DiagnosticModel):
    """Geometric-Moon reference policy on TT, distinct from legacy canon modes."""

    jd_tt: JdUt1
    offset_days: list[float] = Field(default=[-1/6,1/6],min_length=2,max_length=2)
    policy: Literal['danjon_angular','static_finite_cone'] = 'danjon_angular'
    earth_radius_scale: float = Field(default=1.,gt=0,le=10)
    products: list[Literal['occurrence','contacts','extrema']] = Field(
        default=['occurrence','contacts'],min_length=1,max_length=3)
    max_evaluations: int = Field(default=256,ge=0,le=4096)
    tolerance_seconds: float = Field(default=.1,ge=.001,le=86400)

    @model_validator(mode='after')
    def check_domain(self):
        lo,hi = self.offset_days
        if not lo <= 0 <= hi or hi-lo > 34:
            raise ValueError('ordered TT domain must include zero and span at most 34 days')
        if len(set(self.products)) != len(self.products):
            raise ValueError('duplicate products are not allowed')
        if self.policy == 'danjon_angular' and self.earth_radius_scale != 1.:
            raise ValueError('radius scale applies only to static_finite_cone')
        return self
