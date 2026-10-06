"""Typed named-attribute projections over canonical Gochara vessels.

Model fields are the explicit mapping. Shared snapshot back-references in
summary/network nodes are represented once at the profile root; position and
raw BAV context are represented once in the snapshot. No doctrine is rebuilt.
"""
from moira.gochara import GocharaResult, GocharaSubsystemProfile
from ..models.gochara import GocharaResultResponse, GocharaSubsystemProfileResponse


def serialize_gochara_result(result: GocharaResult) -> GocharaResultResponse:
    """Preserve source, policy, observations, relations and independent BAV."""
    return GocharaResultResponse.model_validate(result)


def serialize_gochara_profile(profile: GocharaSubsystemProfile) -> GocharaSubsystemProfileResponse:
    """Preserve local, aggregate and directed network products distinctly."""
    return GocharaSubsystemProfileResponse.model_validate(profile)
