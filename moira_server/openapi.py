"""OpenAPI discovery metadata for the Moira REST access surface."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


OPENAPI_FAMILY_ORDER: tuple[str, ...] = (
    "operational",
    "core",
    "profile-bundles",
    "predictive",
    "relationship",
    "classical-vedic",
    "spatial",
    "phenomena",
    "catalogs",
    "website",
    "other",
)

FAMILY_LABELS: dict[str, str] = {
    "operational": "Operational and Discovery",
    "core": "Core Chart and Position Truth",
    "profile-bundles": "Profile Bundles",
    "predictive": "Predictive Timing",
    "relationship": "Relationship and Pattern Analysis",
    "classical-vedic": "Classical and Vedic Doctrine",
    "spatial": "Spatial and Local Frames",
    "phenomena": "Phenomena and Visibility",
    "catalogs": "Bodies and Catalogs",
    "website": "Website and Batch Support",
    "other": "Other",
}

_TAG_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "name": "meta",
        "x-displayName": "Meta",
        "description": "Operational readiness, version, kernel status, and REST route discovery.",
        "x-family": "operational",
    },
    {
        "name": "chart",
        "x-displayName": "Charts and Houses",
        "description": "Core chart construction, reductions, house cusps, and house fallback truth.",
        "x-family": "core",
    },
    {
        "name": "positions",
        "x-displayName": "Positions",
        "description": "Canonical body position and reduction surfaces.",
        "x-family": "core",
    },
    {
        "name": "positions-frame",
        "x-displayName": "Frame Positions",
        "description": "Frame-specific heliocentric, planetocentric, barycentric, and light-time products.",
        "x-family": "core",
    },
    {
        "name": "western-profile",
        "x-displayName": "Western Profile Bundles",
        "description": "Composed Western chart profile bundles for frontend and workspace callers.",
        "x-family": "profile-bundles",
    },
    {
        "name": "vedic-profile",
        "x-displayName": "Vedic Profile Bundles",
        "description": "Composed Vedic chart profile bundles for frontend and workspace callers.",
        "x-family": "profile-bundles",
    },
    {
        "name": "dasha",
        "x-displayName": "Vimshottari Dasha",
        "description": "Vimshottari sequence, balance, active period, and profile surfaces.",
        "x-family": "predictive",
    },
    {
        "name": "alternate-dashas",
        "x-displayName": "Alternate Dashas",
        "description": "Ashtottari and Yogini dasha sequence, profile, and chart-backed surfaces.",
        "x-family": "predictive",
    },
    {
        "name": "predictive",
        "x-displayName": "Transits and Returns",
        "description": "Transit, ingress, lunar phase, and planetary return surfaces.",
        "x-family": "predictive",
    },
    {
        "name": "progressions",
        "x-displayName": "Progressions",
        "description": "Progressed charts, reductions, house frames, arcs, and condition profiles.",
        "x-family": "predictive",
    },
    {
        "name": "primary-directions",
        "x-displayName": "Primary Directions",
        "description": "Primary direction keys, arcs, directed charts, and house-context products.",
        "x-family": "predictive",
    },
    {
        "name": "timelords",
        "x-displayName": "Time Lords",
        "description": "Profections, Firdaria, Decennials, and Zodiacal Releasing time-lord surfaces.",
        "x-family": "predictive",
    },
    {
        "name": "varshaphal",
        "x-displayName": "Varshaphal",
        "description": "Annual chart, Mudda, Tasira, topic, window, and year-summary surfaces.",
        "x-family": "predictive",
    },
    {
        "name": "electional",
        "x-displayName": "Electional Scans",
        "description": "Bounded scan witnesses and server-defined electional predicate profiles.",
        "x-family": "predictive",
    },
    {
        "name": "relationship",
        "x-displayName": "Relationship",
        "description": "Synastry, composite, Davison, chart-shape, pattern, and midpoint surfaces.",
        "x-family": "relationship",
    },
    {
        "name": "antiscia",
        "x-displayName": "Antiscia",
        "description": "Ordinary antiscia reflections and contact searches.",
        "x-family": "relationship",
    },
    {
        "name": "draconic",
        "x-displayName": "Draconic",
        "description": "Node-anchored draconic longitude rotations and chart materialization.",
        "x-family": "relationship",
    },
    {
        "name": "harmonics",
        "x-displayName": "Harmonics",
        "description": "Direct harmonic projections, age charts, conjunctions, aspects, sweeps, and fingerprints.",
        "x-family": "relationship",
    },
    {
        "name": "harmograms",
        "x-displayName": "Harmograms",
        "description": "Harmogram vectors, spectra, projections, and trace products.",
        "x-family": "relationship",
    },
    {
        "name": "huber",
        "x-displayName": "Huber",
        "description": "Huber house-frame direct and chart-backed profile surfaces.",
        "x-family": "relationship",
    },
    {
        "name": "lord-of-the-orb",
        "x-displayName": "Lord of the Orb",
        "description": "Caller-seeded Lord of the Orb profile surfaces.",
        "x-family": "relationship",
    },
    {
        "name": "lord-of-the-turn",
        "x-displayName": "Lord of the Turn",
        "description": "Caller-supplied Lord of the Turn profile surface.",
        "x-family": "relationship",
    },
    {
        "name": "nine-parts",
        "x-displayName": "Nine Parts",
        "description": "Abu Ma'shar Nine Parts aggregate profile surface.",
        "x-family": "relationship",
    },
    {
        "name": "panchanga",
        "x-displayName": "Panchanga",
        "description": "Panchanga direct, chart-backed, Nakshatra, and profile surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "shadbala",
        "x-displayName": "Shadbala",
        "description": "Shadbala result, profile, network, condition, and Bhava Bala (house strength) surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "jaimini",
        "x-displayName": "Jaimini",
        "description": "Jaimini karaka, arudha, rashi dasha, aspect, and profile surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "dignities",
        "x-displayName": "Dignities",
        "description": "Essential dignity, reception, condition, profile, and network surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "lots",
        "x-displayName": "Lots",
        "description": "Classical lot catalog, chart, dependency, condition, profile, and network surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "triplicity",
        "x-displayName": "Triplicity",
        "description": "Triplicity table, assignment, and score surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "egyptian-bounds",
        "x-displayName": "Egyptian Bounds",
        "description": "Egyptian bound table, classification, relation, condition, aggregate, and network surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "vedic-dignities",
        "x-displayName": "Vedic Dignities",
        "description": "Vedic dignity, relationship, condition, and chart-backed profile surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "ashtakavarga",
        "x-displayName": "Ashtakavarga",
        "description": "Ashtakavarga result, profile, sign strength, and transit-strength surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "varga",
        "x-displayName": "Varga",
        "description": "Generic, named, batch, and chart-backed divisional chart surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "decanates",
        "x-displayName": "Decanates",
        "description": "Decanate table, lookup, classification, condition, aggregate, and network surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "hermetic-decans",
        "x-displayName": "Hermetic Decans",
        "description": "Hermetic decan catalog, position, chart, and star surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "manazil",
        "x-displayName": "Manazil",
        "description": "Arabic lunar mansion catalog, position, bulk, and tradition lookup surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "muhurta",
        "x-displayName": "Muhurta",
        "description": "Vedic Muhurta direct and chart-backed classification and score surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "sidereal",
        "x-displayName": "Sidereal Utilities",
        "description": "Ayanamsa, sidereal conversion, and Nakshatra utility surfaces.",
        "x-family": "classical-vedic",
    },
    {
        "name": "astrocartography",
        "x-displayName": "Astrocartography",
        "description": "Astrocartography lines, chart-backed lines, subplanetary, and rendering surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "local-space",
        "x-displayName": "Local Space",
        "description": "Observer-local horizon and chart-backed local-space position surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "geodetic",
        "x-displayName": "Geodetic",
        "description": "Geodetic zodiac, planet equivalents, chart positions, and profile surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "galactic",
        "x-displayName": "Galactic",
        "description": "Galactic coordinate conversion, position, chart, and profile surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "galactic-houses",
        "x-displayName": "Galactic Houses",
        "description": "Galactic house cusps, placement, and chart placement surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "gauquelin",
        "x-displayName": "Gauquelin",
        "description": "Gauquelin sector, multi-sector, and chart-backed sector surfaces.",
        "x-family": "spatial",
    },
    {
        "name": "visibility",
        "x-displayName": "Visibility",
        "description": "Observer visibility assessment and tonight surfaces.",
        "x-family": "phenomena",
    },
    {
        "name": "phenomena",
        "x-displayName": "Phenomena",
        "description": "Stations, void Moon, rise-set, eclipses, occultations, heliacal, and paran surfaces.",
        "x-family": "phenomena",
    },
    {
        "name": "generic-phenomena",
        "x-displayName": "Generic Phenomena",
        "description": "Generic planet, solar condition, proximity, elongation, and crossing surfaces.",
        "x-family": "phenomena",
    },
    {
        "name": "phase",
        "x-displayName": "Phase and Photometry",
        "description": "Illumination, synodic phase, elongation, phase angle, diameter, and magnitude surfaces.",
        "x-family": "phenomena",
    },
    {
        "name": "planetary-hours",
        "x-displayName": "Planetary Hours",
        "description": "Sunrise-based planetary hour schedule and current-hour surfaces.",
        "x-family": "phenomena",
    },
    {
        "name": "asteroids (fast small-body)",
        "x-displayName": "Asteroids",
        "description": "Fast asteroid position, bulk, subset, family, and chart-family surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "comets (fast small-body)",
        "x-displayName": "Comets",
        "description": "Fast comet position, bulk, and catalog surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "stars (fixed stars)",
        "x-displayName": "Fixed Stars",
        "description": "Fixed, variable, and multiple-star catalog, state, range, and pair surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "nodes",
        "x-displayName": "Nodes",
        "description": "Planetary and small-body orbital node surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "orbits",
        "x-displayName": "Orbits",
        "description": "Heliocentric osculating elements and distance-extrema surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "uranian",
        "x-displayName": "Uranian",
        "description": "Uranian/Hamburg School hypothetical-body catalog and position surfaces.",
        "x-family": "catalogs",
    },
    {
        "name": "batch",
        "x-displayName": "Batch",
        "description": "Batch chart, transit, return, event, and progression surfaces.",
        "x-family": "website",
    },
    {
        "name": "website-chart-wheel",
        "x-displayName": "Website Chart Wheel",
        "description": "Website chart-wheel presets, validation, and drawing packet surfaces.",
        "x-family": "website",
    },
    {
        "name": "website-locations",
        "x-displayName": "Website Locations",
        "description": "Website location lookup and timezone validation surfaces.",
        "x-family": "website",
    },
    {
        "name": "website-pipeline",
        "x-displayName": "Website Pipeline",
        "description": "Website-oriented reduction pipeline surfaces for position and chart packets.",
        "x-family": "website",
    },
)

TAG_FAMILIES: dict[str, str] = {
    definition["name"]: definition["x-family"] for definition in _TAG_DEFINITIONS
}

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        **definition,
        "x-familyLabel": FAMILY_LABELS[definition["x-family"]],
    }
    for definition in _TAG_DEFINITIONS
]

OPENAPI_TAG_GROUPS: list[dict[str, Any]] = [
    {
        "name": FAMILY_LABELS[family],
        "tags": [
            definition["name"]
            for definition in _TAG_DEFINITIONS
            if definition["x-family"] == family
        ],
    }
    for family in OPENAPI_FAMILY_ORDER
    if any(definition["x-family"] == family for definition in _TAG_DEFINITIONS)
]


def family_for_tags(tags: Iterable[str] | None) -> tuple[str, str]:
    """Return the discoverability family for the first known route tag."""

    for tag in tags or ():
        family = TAG_FAMILIES.get(tag)
        if family is not None:
            return family, FAMILY_LABELS[family]
    return "other", FAMILY_LABELS["other"]


def install_openapi_discovery(app: FastAPI) -> None:
    """Install ordered tag metadata and ReDoc tag groups on the OpenAPI schema."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=OPENAPI_TAGS,
            servers=app.servers,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )
        schema["x-tagGroups"] = OPENAPI_TAG_GROUPS
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
