"""Website-only composition of admitted paran and fixed-star truth."""

from __future__ import annotations

from moira.heliacal import HeliacalEventKind, VisibilitySearchPolicy, visibility_event
from moira.parans import (
    _paran_crossing_cache_scope,
    natal_angular_contacts,
    natal_parans,
    natal_parans_with_inventory,
    paran_policy_preset,
)
from moira.spk_reader import MissingKernelError, use_reader_override
from moira.stars import star_name_resolves

from ..models.paran_packet import ParanPacketRequest, ParanPacketResponse
from ..models.phenomena import NatalAngularContactsResponse, ParanSearchResponse
from ..serializers.phenomena import (
    serialize_general_visibility_event,
    serialize_natal_angular_contact,
    serialize_paran,
    serialize_paran_body_crossing_inventory,
)
from .phenomena import get_paran_star_canon


_PACKET_HELIACAL_KINDS = frozenset(
    {
        HeliacalEventKind.HELIACAL_RISING.value,
        HeliacalEventKind.HELIACAL_SETTING.value,
    }
)


def compute_paran_packet(engine, request: ParanPacketRequest) -> ParanPacketResponse:
    """Compose existing engine results into one bounded Workspace packet."""

    if not request.bodies:
        raise ValueError("bodies must contain at least one target")
    policy = paran_policy_preset(request.policy_preset)
    canon = get_paran_star_canon(
        tiers=request.canon_tiers or None,
        available_only=True,
    )
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader), _paran_crossing_cache_scope():
        if request.include_crossing_inventory:
            detailed = natal_parans_with_inventory(
                request.bodies,
                request.natal_jd,
                request.lat,
                request.lon,
                orb_minutes=request.orb_minutes,
                policy=policy,
            )
            parans = ParanSearchResponse(
                events=[serialize_paran(event) for event in detailed.events],
                crossing_inventory=[
                    serialize_paran_body_crossing_inventory(inventory)
                    for inventory in detailed.crossing_inventory
                ],
                effective_policy_preset=request.policy_preset,
            )
        else:
            events = natal_parans(
                request.bodies,
                request.natal_jd,
                request.lat,
                request.lon,
                orb_minutes=request.orb_minutes,
                policy=policy,
            )
            parans = ParanSearchResponse(
                events=[serialize_paran(event) for event in events],
                effective_policy_preset=request.policy_preset,
            )

        angular_response = None
        if request.include_angular_contacts:
            contacts = natal_angular_contacts(
                request.bodies,
                request.natal_jd,
                request.lat,
                request.lon,
                orb_minutes=request.angular_orb_minutes,
            )
            angular_response = NatalAngularContactsResponse(
                contacts=[serialize_natal_angular_contact(contact) for contact in contacts]
            )

        warnings: list[str] = []
        heliacal_events = []
        if request.include_heliacal:
            if request.heliacal_kind not in _PACKET_HELIACAL_KINDS:
                allowed = ", ".join(sorted(_PACKET_HELIACAL_KINDS))
                raise ValueError(f"heliacal_kind must be one of: {allowed}")
            event_kind = HeliacalEventKind(request.heliacal_kind)
            star_bodies = [body for body in request.bodies if star_name_resolves(body)]
            if not star_bodies:
                warnings.append("heliacal_requested_without_fixed_star_targets")
            for body in star_bodies:
                try:
                    event = visibility_event(
                        body,
                        event_kind,
                        request.natal_jd,
                        request.lat,
                        request.lon,
                        search_policy=VisibilitySearchPolicy(
                            search_window_days=request.heliacal_search_window_days
                        ),
                    )
                except MissingKernelError:
                    warnings.append("heliacal_unavailable_missing_planetary_kernel")
                    break
                if event is None:
                    warnings.append(f"heliacal_event_not_found:{body}")
                else:
                    heliacal_events.append(serialize_general_visibility_event(event))

    return ParanPacketResponse(
        canon=canon,
        parans=parans,
        angular_contacts=angular_response,
        heliacal_events=heliacal_events,
        warnings=warnings,
        provenance={
            "parans": "moira.parans",
            "star_catalog": "moira.stars sovereign registry",
            "heliacal": "moira.heliacal visibility_event",
            "composition": "website transport only",
        },
    )


__all__ = ["compute_paran_packet"]
