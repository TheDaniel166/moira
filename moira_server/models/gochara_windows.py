"""Strict window requests and typed, lossless canonical result projections."""
from dataclasses import fields
from datetime import datetime
import re
from types import UnionType
from typing import Annotated, Literal, Union, get_args, get_origin, get_type_hints

from pydantic import AwareDatetime, Field, PrivateAttr, StrictBool, StrictInt, create_model, field_validator, model_validator
from importlib import import_module
from moira.gochara import GocharaPolicy
from moira.gochara_policy import GocharaDoctrineOption
from moira.gochara_dated import GocharaDatePolicy, GocharaBirthLocation, GocharaEpoch
from moira.ashtakavarga import BhinnashtakavargaResult
from ._vedic_inputs import FiniteNumber, ClassicalPlanet
from .common import _StrictModel
from .gochara import _GocharaView, GocharaBavResponse, GocharaDoctrineOptionResponse
from .gochara_dated import (
    _GocharaDatedRequest, GocharaBirthLocationResponse,
    GocharaDatePolicyResponse, GocharaEpochResponse,
)

# import_module avoids the package's identically named public function.
W = import_module("moira.gochara_windows")


class GocharaWindowLimitsRequest(_StrictModel):
    max_range_days: StrictInt = Field(default=366, ge=1, le=366)
    max_evaluations: StrictInt = Field(default=2_000_000, ge=1, le=2_000_000)
    max_reader_calls: StrictInt = Field(default=20_000_000, ge=1, le=20_000_000)
    max_root_iterations: StrictInt = Field(default=500_000, ge=1, le=500_000)
    max_subdivisions: StrictInt = Field(default=500_000, ge=1, le=500_000)
    max_events: StrictInt = Field(default=8192, ge=1, le=8192)
    max_cells: StrictInt = Field(default=16384, ge=1, le=16384)
    max_samples: StrictInt = Field(default=16384, ge=1, le=16384)
    max_evidence: StrictInt = Field(default=500_000, ge=1, le=500_000)
    max_output_bytes: StrictInt = Field(default=32_000_000, ge=1, le=32_000_000)

    @model_validator(mode="after")
    def _valid(self):
        W.GocharaWindowSearchLimits(**self.model_dump())
        return self


class GocharaWindowSearchRequest(_StrictModel):
    boundary_tolerance_seconds: FiniteNumber = Field(default=1., ge=.01, le=60.)
    require_resolved: StrictBool = False
    limits: GocharaWindowLimitsRequest = Field(default_factory=GocharaWindowLimitsRequest)

    def to_engine(self):
        return W.GocharaWindowSearchPolicy(self.boundary_tolerance_seconds, self.require_resolved,
                                          W.GocharaWindowSearchLimits(**self.limits.model_dump()))

    @model_validator(mode="after")
    def _valid(self):
        self.to_engine()
        return self


class _WindowRequest(_GocharaDatedRequest):
    search_policy: GocharaWindowSearchRequest = Field(default_factory=GocharaWindowSearchRequest)
    subjects: Annotated[tuple[ClassicalPlanet, ...], Field(min_length=1, max_length=7)] | None = None
    _epochs: tuple[float, float, float] = PrivateAttr()

    def engine_options(self):
        return dict(
            birth_location=GocharaBirthLocation(**self.birth_location.model_dump()) if self.birth_location else None,
            policy=GocharaDatePolicy(self.policy.ayanamsa_system, self.policy.natal_bav_mode,
                                    GocharaPolicy(**self.policy.gochara_policy.model_dump())),
            search_policy=self.search_policy.to_engine(), subjects=self.subjects,
        )

    def _admit(self, epochs):
        opts = self.engine_options()
        self._epochs = tuple(epochs)
        W._admit(*epochs, opts["birth_location"], opts["policy"], opts["search_policy"], opts["subjects"])
        return self


class GocharaWindowEpochRequest(_WindowRequest):
    natal_jd_ut1: FiniteNumber
    start_jd_ut1: FiniteNumber
    end_jd_ut1: FiniteNumber

    @model_validator(mode="after")
    def _bounds(self):
        return self._admit((self.natal_jd_ut1, self.start_jd_ut1, self.end_jd_ut1))


class GocharaWindowDatetimeRequest(_WindowRequest):
    natal_dt: AwareDatetime
    start_dt: AwareDatetime
    end_dt: AwareDatetime

    @field_validator("natal_dt", "start_dt", "end_dt", mode="before")
    @classmethod
    def _civil(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("civil instants require timezone-aware datetime strings")
        if isinstance(value, str) and not re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}", value):
            # AwareDatetime also accepts numeric strings as Unix timestamps;
            # the public civil contract requires explicit ISO calendar input.
            raise ValueError("civil instants require an ISO calendar date and time with offset")
        return value

    @model_validator(mode="after")
    def _bounds(self):
        return self._admit(W._civil_epochs((self.natal_dt, self.start_dt, self.end_dt)))


# Generate response FIELD declarations, never computation, from the canonical
# frozen schema. All nested engine types map to typed response models; no Any
# or unconstrained dictionaries hide evidence from OpenAPI. Existing dated
# astronomy and policy projections keep their explicit models.
_types = {
    GocharaDoctrineOption: GocharaDoctrineOptionResponse,
    GocharaDatePolicy: GocharaDatePolicyResponse,
    GocharaBirthLocation: GocharaBirthLocationResponse,
    GocharaEpoch: GocharaEpochResponse,
    BhinnashtakavargaResult: GocharaBavResponse,
}


def _response_type(annotation):
    if annotation in _types:
        return _types[annotation]
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        return Union[tuple(_response_type(a) for a in args)]
    if origin is tuple:
        return tuple[tuple(_response_type(a) if a is not Ellipsis else a for a in args)]
    return annotation


_response_names = []
for _name in (
    "GocharaWindowSearchLimits", "GocharaWindowSearchPolicy", "GocharaNatalContext",
    "GocharaWindowWitness", "GocharaWindowPlanet", "GocharaWindowState",
    "GocharaWindowSample", "GocharaIngressEvent", "GocharaWindowRegion",
    "GocharaExclusionEvidence", "GocharaWindowCoverage", "GocharaWindowSubjectView", "GocharaWindowResult",
    "GocharaWindowCapabilities",
):
    _cls = getattr(W, _name)
    _annotations = get_type_hints(_cls)
    _model_name = _name + "Response"
    _spec = {f.name: (_response_type(_annotations[f.name]), ...) for f in fields(_cls) if f.metadata.get("wire", True)}
    if "schema" in _spec:
        _spec.pop("schema")
        _spec["schema_name"] = (Literal["moira.gochara.windows.v1"], Field(alias="schema"))
    _model = create_model(_model_name, __base__=_GocharaView, __module__=__name__, **_spec)
    _types[_cls] = _model
    globals()[_model_name] = _model
    _response_names.append(_model_name)


class GocharaWindowErrorResponse(_StrictModel):
    error_code: str
    message: str
    category: str
    request_id: str | None = None
    details: dict[str, str | int | float | tuple[str, ...]] | None = None


__all__ = ["GocharaWindowLimitsRequest", "GocharaWindowSearchRequest", "GocharaWindowEpochRequest",
           "GocharaWindowDatetimeRequest", "GocharaWindowErrorResponse", *_response_names]
