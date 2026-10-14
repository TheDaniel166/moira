"""Generate and validate the Light Box conformance manifest baseline.

LB-WP1 defines the evidence contract without admitting evidence.  Every
calculation surface discovered by LB-WP0 receives an explicit unresolved row;
later work packages may replace those dispositions only with reviewed,
release-bound evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
SCHEMA_PATH = REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_SCHEMA.json"
ADMISSIONS_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_ADMISSIONS.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json"
)
MARKDOWN_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_MANIFEST.generated.md"
)
INVENTORY_GENERATOR_PATH = (
    REPO_ROOT / "scripts" / "generate_lightbox_calculation_inventory.py"
)
GENERATOR_PATH = "scripts/generate_lightbox_conformance_manifest.py"
SCHEMA_VERSION = "moira.lightbox-conformance-manifest/v1"

CONFORMANCE_STATUSES = (
    "conformant",
    "partial",
    "not_applicable",
    "unresolved",
)
RESIDUAL_DISPOSITIONS = (
    "numeric",
    "invariant",
    "doctrine_source",
    "regression_parity",
    "not_applicable",
    "unresolved",
)
SEMANTIC_FIELDS = (
    "inputs",
    "units",
    "reference_frame",
    "origin",
    "timescale",
    "corrections",
    "policies_defaults",
    "fallbacks",
    "refusal_behavior",
)
EVIDENCE_DISCLOSURES = (
    "authority_comparator",
    "corpus",
    "metric",
    "tolerance_or_invariant",
    "observed_result",
    "exclusions",
)

ADMISSION_CONTRACTS: Mapping[str, Mapping[str, Any]] = {
    "reduction_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The response embeds a typed reduction vessel with explicit pipeline or stage truth beside the final result.",
        "stage_label": "Typed reduction response",
        "operation": "Normalize the request, execute the governed calculation, and serialize the returned reduction truth with the result.",
        "semantic_values": {
            "inputs": ["Typed request schema is exposed by OpenAPI."],
            "units": [
                "Named response fields carry their domain units; this admission does not generalize unnamed fields."
            ],
            "reference_frame": [
                "The reduction vessel exposes the applied frame where the calculation defines one."
            ],
            "origin": [
                "The reduction vessel exposes the applied center or observer context where applicable."
            ],
            "timescale": [
                "The reduction vessel exposes normalized time and UT/TT values where applicable."
            ],
            "corrections": [
                "Applied correction flags or stage sequence are returned by the reduction vessel."
            ],
            "policies_defaults": [
                "Typed request defaults are visible in OpenAPI; runtime selections are carried by the reduction result where defined."
            ],
            "fallbacks": [
                "Only fallbacks explicitly carried by the response are admitted."
            ],
            "refusal_behavior": [
                "Typed request validation and documented transport errors bound invalid requests."
            ],
        },
        "public_modes": [
            "embedded_result",
            "paired_reduction_endpoint",
            "generated_documentation",
        ],
    },
    "source_truth_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The public Python result pairs the legacy calculation value with a typed vessel that exposes the governing source, scale, frame, center, correction, or singularity facts applicable to that calculation.",
        "stage_label": "Additive public-Python truth vessel",
        "operation": "Validate the public inputs, execute the existing calculation path, and return its result beside explicitly named reduction truth without changing the legacy API.",
        "semantic_values": {
            "inputs": [
                "The public Python signature and typed truth vessel define the admitted inputs and result fields."
            ],
            "units": [
                "Each numeric truth field carries a unit-bearing name or a documented result-vessel unit; no unnamed unit is inferred."
            ],
            "reference_frame": [
                "Frame identity is explicit where the calculation transforms coordinates; time-only calculations do not acquire an invented spatial frame."
            ],
            "origin": [
                "Center, observer, or civil-time origin is explicit where applicable to the calculation."
            ],
            "timescale": [
                "Input, intermediate, and output time scales are named where the calculation depends on an epoch."
            ],
            "corrections": [
                "Applied models, corrections, and deliberately omitted corrections are carried where applicable."
            ],
            "policies_defaults": [
                "Compatibility defaults remain on the legacy surface; the additive truth surface names its effective mode and policy."
            ],
            "fallbacks": [
                "Only source branches, conventions, or unavailable states explicitly present in the truth vessel are admitted."
            ],
            "refusal_behavior": [
                "Invalid finite-domain, scale-label, singular-geometry, center, or resource inputs follow the owning public function's explicit error contract."
            ],
        },
        "public_modes": [
            "embedded_result",
            "source_only",
            "generated_documentation",
        ],
    },
    "policy_reduction_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The response embeds a typed reduction vessel with governing policy, applied choices, and computation-path truth.",
        "stage_label": "Policy-aware reduction response",
        "operation": "Resolve the typed policy, execute the calculation, and return requested/applied policy with reduction truth.",
        "semantic_values": {
            "inputs": ["Typed request schema is exposed by OpenAPI."],
            "units": [
                "Named response fields carry their domain units; no unnamed unit is inferred."
            ],
            "reference_frame": [
                "Frame semantics remain limited to the response and linked standard."
            ],
            "origin": [
                "Origin or observer semantics remain limited to the response and linked standard."
            ],
            "timescale": [
                "Time normalization is returned where this calculation is time-dependent."
            ],
            "corrections": [
                "Only corrections present in the reduction vessel are admitted."
            ],
            "policies_defaults": [
                "Requested and applied policy are explicit in the typed reduction contract."
            ],
            "fallbacks": [
                "Fallback state and reason are explicit where the governed policy permits fallback."
            ],
            "refusal_behavior": [
                "Typed validation or an explicit unsupported-policy error bounds refusal behavior."
            ],
        },
        "public_modes": [
            "embedded_result",
            "paired_reduction_endpoint",
            "generated_documentation",
        ],
    },
    "embedded_frame_receipt": {
        "inspectability_mode": "embedded_result",
        "summary": "The result embeds request, time, frame, bounds, validation, provenance, correction-model, and stage-sequence vessels.",
        "stage_label": "Frame-specific position receipt",
        "operation": "Normalize time and bodies, compute in the named center/frame, validate invariants, and return provenance plus stage sequence.",
        "semantic_values": {
            "inputs": [
                "Timezone-aware datetime and a bounded unique body list are typed and validated."
            ],
            "units": [
                "Angles are degrees; distances are kilometres and AU; time deltas are seconds or days where named."
            ],
            "reference_frame": ["true_of_date_ecliptic"],
            "origin": [
                "The response names Sun, Solar System barycenter, Earth, or requested planet center."
            ],
            "timescale": [
                "Requested UTC datetime, normalized UTC, JD UT, JD TT, and delta-T are returned."
            ],
            "corrections": [
                "Correction model and light-time/apparent/geometric flags are returned."
            ],
            "policies_defaults": [
                "Maximum body count and normalized request echo are returned."
            ],
            "fallbacks": ["No unreported frame fallback is admitted by this contract."],
            "refusal_behavior": [
                "Invalid datetime/body lists and non-finite output values are rejected by typed validators."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "embedded_orbital_receipt": {
        "inspectability_mode": "embedded_result",
        "summary": "The orbital result embeds time conversion, gravity, frame construction, state-source identity, thresholds, and a stage sequence.",
        "stage_label": "Orbital-elements evidence envelope",
        "operation": "Validate body and epoch, bind UT1/TT/TDB, construct the governed state/frame, reduce osculating elements, and return provenance.",
        "semantic_values": {
            "inputs": [
                "A finite UT1 Julian date and admitted body identifier are typed and validated."
            ],
            "units": [
                "Distances use AU or kilometres, angles use degrees, rates name their time denominator, and gravity uses km^3/s^2."
            ],
            "reference_frame": [
                "The response names center, fixed J2000 ecliptic orientation, frame construction routine, and models."
            ],
            "origin": [
                "The response names center-relative state-vector provenance and kernel route legs."
            ],
            "timescale": [
                "UT1 input, TT/TDB evaluation, delta-T, TT-TDB conversion policy, version, and source hash are returned."
            ],
            "corrections": [
                "Apparent and light-time corrections are explicitly marked not applied for osculating elements."
            ],
            "policies_defaults": [
                "Gravity rule, component constants, singularity thresholds, and admitted interval are returned."
            ],
            "fallbacks": [
                "Unavailable/singular element cases are governed by explicit threshold policy rather than an inferred value."
            ],
            "refusal_behavior": [
                "Non-finite epochs, empty bodies, unsupported bodies, and unavailable kernel routes are explicit errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "doctrine_profile": {
        "inspectability_mode": "embedded_result",
        "summary": "The typed profile carries source/doctrine composition and limitation state, while linked standards own the fuller derivation.",
        "stage_label": "Doctrine-bound profile assembly",
        "operation": "Validate inputs, apply the named doctrine/profile policy, and return structured components, omissions, and provenance where defined.",
        "semantic_values": {
            "inputs": ["Typed request schema is exposed by OpenAPI."],
            "units": [
                "Units are admitted only where named by the response or linked standard."
            ],
            "reference_frame": [
                "Astronomical frame claims remain limited to nested calculation vessels."
            ],
            "origin": [
                "Source tradition and calculation origin are separated where the result contract exposes them."
            ],
            "timescale": [
                "Time semantics remain limited to the typed request and linked standard."
            ],
            "corrections": [
                "No correction is inferred beyond nested calculation truth."
            ],
            "policies_defaults": [
                "The governing doctrine/profile policy is explicit in source and linked standards."
            ],
            "fallbacks": [
                "Omissions or unavailable states are preserved rather than silently synthesized."
            ],
            "refusal_behavior": [
                "Typed validation and explicit unavailable states bound refusal behavior."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "motion_witness": {
        "inspectability_mode": "embedded_result",
        "summary": "The response is itself a signed motion witness that exposes the directional basis for the classification.",
        "stage_label": "Signed aspect-motion witness",
        "operation": "Evaluate signed longitudinal separation over the governed time step and return the witness used by the applying/separating classification.",
        "semantic_values": {
            "inputs": ["Typed aspect-motion request is exposed by OpenAPI."],
            "units": [
                "Angular quantities and the witness time step use the units named by the response."
            ],
            "reference_frame": [
                "Reference-frame scope is limited to the linked signed-motion standard and calculation inputs."
            ],
            "origin": [
                "Both participating longitudes and their signed relation form the witness origin."
            ],
            "timescale": [
                "The witness carries the comparison-time basis defined by the route contract."
            ],
            "corrections": [
                "No correction is inferred beyond the input longitudes and returned witness."
            ],
            "policies_defaults": [
                "Applying/separating policy is governed by the signed-motion validation document."
            ],
            "fallbacks": [
                "Unavailable motion evidence is not silently classified by this admission."
            ],
            "refusal_behavior": [
                "Typed request validation bounds invalid aspect-motion inputs."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "position_aspect_analysis": {
        "inspectability_mode": "embedded_result",
        "summary": "The response preserves normalized caller-supplied longitudes, aspect policy, node exclusions, counts, and the explicit absence of motion inference.",
        "stage_label": "Position-only aspect analysis",
        "operation": "Validate and normalize supplied longitudes, apply the named aspect policy, and return events beside the exact computation truth used.",
        "semantic_values": {
            "inputs": [
                "A bounded typed map of named ecliptic longitudes and explicit aspect-policy controls is exposed by OpenAPI."
            ],
            "units": [
                "Longitudes, separations, aspect angles, orbs, and allowed orbs are degrees."
            ],
            "reference_frame": [
                "The response identifies caller-supplied ecliptic longitudes without inventing an epoch-specific frame."
            ],
            "origin": [
                "The caller-supplied positions are the sole positional origin; no ephemeris lookup is implied."
            ],
            "timescale": [
                "No epoch or time evolution is evaluated; motion semantics are returned as not computed without speeds."
            ],
            "corrections": [
                "No positional correction is inferred beyond longitude normalization and the returned node exclusion list."
            ],
            "policies_defaults": [
                "Tier, orb factor, node inclusion, normalized positions, and aspect count are returned in computation truth."
            ],
            "fallbacks": [
                "The route has no ephemeris or frame fallback; excluded nodes are named explicitly."
            ],
            "refusal_behavior": [
                "Typed validation rejects insufficient, non-finite, coercive, or unowned inputs before engine execution."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "chart_wheel_packet_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The drawing packet preserves immutable chart coordinates beside deterministic label geometry and explicit chart, house, orientation, aspect, and placement policy truth.",
        "stage_label": "Chart-wheel drawing-packet truth",
        "operation": "Build the governed chart and optional house frame, derive drawing primitives without replacing calculated positions, and return the applied policies and label-placement result beside the packet.",
        "semantic_values": {
            "inputs": [
                "A typed chart, optional house request, and bounded chart-wheel configuration are exposed by OpenAPI."
            ],
            "units": [
                "Calculated longitudes, drawing angles, cusps, aspect geometry, and label displacement use degrees where named."
            ],
            "reference_frame": [
                "The packet names the requested and effective wheel orientation and its anchor source; it does not reinterpret the calculated chart frame."
            ],
            "origin": [
                "Point geometry retains each calculated longitude while label geometry is returned separately as a display-only displacement."
            ],
            "timescale": [
                "The typed chart request supplies the calculation epoch; label placement does not advance or alter it."
            ],
            "corrections": [
                "No astronomical correction is inferred from display placement; the packet states that point positions are preserved."
            ],
            "policies_defaults": [
                "Node override, requested and effective house policy, orientation, aspect selection, and requested and achieved label separation are explicit."
            ],
            "fallbacks": [
                "House-system fallback and impossible-density separation reduction are disclosed; neither silently changes calculated point coordinates."
            ],
            "refusal_behavior": [
                "Typed validation rejects invalid configuration, unavailable house-dependent orientation, unknown-time house requests, and invalid house coordinates."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "solar_condition_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The instant and event-search routes expose one shared classical solar-proximity threshold policy and preserve the engine-reported crossing boundary in each event.",
        "stage_label": "Solar-condition boundary truth",
        "operation": "Classify a body's instantaneous angular separation from the Sun or search a bounded interval for ingress and egress across the selected classical threshold.",
        "semantic_values": {
            "inputs": [
                "A typed body and Julian date, or a typed body, bounded Julian-date interval, and admitted solar condition are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates use days; angular separations and signed and absolute event thresholds use degrees."
            ],
            "reference_frame": [
                "The routes use the engine-returned ecliptic longitudes for the body and Sun under the bound planetary reader; the transport does not invent an additional frame claim."
            ],
            "origin": [
                "Solar angular separation is measured from the Sun; event signs retain ingress or egress direction while the absolute boundary is also returned."
            ],
            "timescale": [
                "The requested Julian dates are interpreted by the existing engine entrypoints and are not silently replaced by another epoch."
            ],
            "corrections": [
                "No additional transport correction is applied; the response preserves the engine's solar-condition truth or crossing event."
            ],
            "policies_defaults": [
                "Cazimi, combustion, and under-sunbeams thresholds come from one immutable doctrine-owned map and are repeated in response provenance."
            ],
            "fallbacks": [
                "No threshold fallback is admitted; the routes report the bound reader owner and return the effective shared threshold policy."
            ],
            "refusal_behavior": [
                "Typed validation rejects non-finite dates, unsupported event bodies or conditions, reversed windows, and searches longer than the admitted span."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "station_motion_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "For major-planet requests, the station routes expose the signed longitude-speed state, bounded search policy, crossing bracket, solver tolerance, frame/correction policy, clock, and serving ephemeris identity without replacing legacy results.",
        "stage_label": "Station-motion search and state truth",
        "operation": "Sample the declared apparent geocentric true-ecliptic longitude-speed product on a UT1 search lattice, bracket strict sign changes, refine each zero by bisection, and return the applied reduction and search truth beside legacy results.",
        "semantic_values": {
            "inputs": [
                "Typed body, Julian-date state or search bounds, optional scan step, and next-search horizon are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates and solver tolerances use days; longitude uses degrees; signed longitude speed uses degrees per day."
            ],
            "reference_frame": [
                "The response names ICRF barycentric source vectors and the apparent geocentric true ecliptic and equinox of date result frame."
            ],
            "origin": [
                "The observer center is Earth's geocenter; topocentric displacement is explicitly false."
            ],
            "timescale": [
                "Search epochs are UT1, each reduction reports bound UT1, TT, and TDB values, and the centered longitude-rate sample is identified as TT."
            ],
            "corrections": [
                "Light time, annual aberration, gravitational deflection, precession, and nutation flags are returned; topocentric correction is explicitly excluded."
            ],
            "policies_defaults": [
                "For major planets, the zero-speed threshold, strict sign-change rule, requested and effective scan step, coarse bracket, bisection method, tolerance, iteration cap, exact rate sample, and serving DE/LE identity are explicit."
            ],
            "fallbacks": [
                "Sun and Moon return an explicit non-retrograding-body reason; an empty bounded planetary search returns a distinct no-station-in-window reason. A null next-station body remains null and carries its reason in documented headers. Small-body requests name their family and the limitation that supplemental body-kernel identity and exact rate sampling are not exposed."
            ],
            "refusal_behavior": [
                "Typed service validation rejects unsupported bodies, non-finite dates, reversed ranges, non-positive steps, and non-positive next-search horizons."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "void_of_course_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The void-of-course routes expose their exact-perfection doctrine, sign-bounded search, numerical witness, frame/correction policy, clock, and serving ephemeris identity without replacing legacy results.",
        "stage_label": "Void-of-course sign-window truth",
        "operation": "Find the Moon's tropical sign boundaries, scan the selected traditional or modern body set for exact directional Ptolemaic aspect perfections, select the last perfection or explicit no-aspect sign-entry fallback, and return the governing truth beside the legacy window or state.",
        "semantic_values": {
            "inputs": [
                "Typed Julian-date window, state, next, or range bounds plus the explicit modern-mode boolean are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates and solver tolerances use days; duration uses hours; aspect targets, longitudes, and exactness residuals use degrees."
            ],
            "reference_frame": [
                "The response names ICRF barycentric source vectors and apparent geocentric true ecliptic and equinox of date longitudes in the tropical zodiac."
            ],
            "origin": [
                "The observer center is Earth's geocenter; topocentric displacement is explicitly false."
            ],
            "timescale": [
                "Request and event Julian dates are UT1, and the request receipt exposes the bound TT and TDB epochs."
            ],
            "corrections": [
                "Light time, annual aberration, gravitational deflection, precession, and nutation are explicit; topocentric correction is excluded."
            ],
            "policies_defaults": [
                "Traditional mode is the default six-body policy; modern mode adds Uranus, Neptune, and Pluto. The eight directional Ptolemaic targets, exact-perfection rather than orb-entry rule, sign-ingress boundary, scan cadence, and bisection tolerance are returned."
            ],
            "fallbacks": [
                "When a sign contains no exact admitted aspect, the returned reason identifies the sign-entry fallback. Next search uses the existing fixed horizon, and range membership and deduplication rules are explicit; no doctrine mode is inferred."
            ],
            "refusal_behavior": [
                "Typed service validation rejects non-finite dates and reversed ranges; truth-bearing engine entrypoints also reject non-positive or non-finite next-search horizons."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "relationship_overlay_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "Each directional overlay embeds labels, node policy, point count, target house-system identity, effective system, and fallback state.",
        "stage_label": "Directional house-overlay truth",
        "operation": "Build the source chart and target house frame, assign each admitted point to a house, and return the house-frame truth with placements.",
        "semantic_values": {
            "inputs": [
                "Two typed relationship parties, direction, labels, and node policy are exposed by OpenAPI."
            ],
            "units": [
                "Placement and cusp longitudes are degrees; house assignments are numbered one through twelve."
            ],
            "reference_frame": [
                "The target house frame is identified by requested and effective house systems."
            ],
            "origin": [
                "Source-chart points are placed into the explicitly labeled target party's houses."
            ],
            "timescale": [
                "Each party's typed birth epoch governs its chart or house frame; no shared epoch is inferred."
            ],
            "corrections": [
                "No correction is inferred beyond the chart and house computations represented by the response."
            ],
            "policies_defaults": [
                "Direction, labels, node inclusion, point count, and target house systems are explicit."
            ],
            "fallbacks": [
                "Target-house fallback is returned as an explicit boolean with the effective system."
            ],
            "refusal_behavior": [
                "Unknown target birth time and invalid direction states are explicit transport errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "relationship_chart_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The derived relationship chart carries its construction method, epoch or midpoint truth, house-frame policy, and a nested position-only aspect analysis.",
        "stage_label": "Derived relationship-chart truth",
        "operation": "Construct the selected composite or Davison chart, preserve method-specific computation truth, and analyze the derived longitudes under explicit aspect policy.",
        "semantic_values": {
            "inputs": [
                "Two typed relationship parties plus method, house, node, tier, and orb policy are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates use days; coordinates and chart/aspect angles use degrees."
            ],
            "reference_frame": [
                "House-frame inclusion and source/effective house-system identity are returned where defined."
            ],
            "origin": [
                "The response distinguishes composite reference-place construction from the selected Davison midpoint construction."
            ],
            "timescale": [
                "Composite mean Julian day or Davison raw and used Julian days are returned by the method-specific truth vessel."
            ],
            "corrections": [
                "Davison correction application and corrected target MC are explicit; no unreported correction is admitted."
            ],
            "policies_defaults": [
                "Construction method, house policy, aspect tier, orb factor, and node inclusion are carried by the response."
            ],
            "fallbacks": [
                "House-system fallback remains limited to the nested house and construction truth actually returned."
            ],
            "refusal_behavior": [
                "Unsupported methods, conflicting house policy, missing birth time, and invalid aspect policy are explicit errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "relationship_transit_search_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The transit search embeds immutable derived-chart identity, construction truth, target-set identity, search policy, event source, counts, and interpretation scope.",
        "stage_label": "Relationship transit-search receipt",
        "operation": "Construct and identify the static relationship chart, materialize bounded targets, execute canonical transit searches, and return search truth beside events.",
        "semantic_values": {
            "inputs": [
                "Typed relationship-chart construction, moving bodies, targets, interval, direction, motion, and solver policy are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates and step/tolerance values use days; longitudes and aspect geometry use degrees."
            ],
            "reference_frame": [
                "The target identity names the relationship-chart reference frame and static geometry hash."
            ],
            "origin": [
                "Targets are bound to one identified composite or Davison chart and its returned construction truth."
            ],
            "timescale": [
                "The target epoch, search interval, direction, and search-motion policy are returned explicitly."
            ],
            "corrections": [
                "No moving-target or orb-window correction is inferred; target motion and orb-window policy are named."
            ],
            "policies_defaults": [
                "Tier, aspect names, step policy, solver tolerance, call count, event source, and interpretation scope are returned."
            ],
            "fallbacks": [
                "Automatic per-body stepping is named as policy; no silent chart or target fallback is admitted."
            ],
            "refusal_behavior": [
                "Server search budgets, unavailable requested nodes, invalid intervals, and unbounded inputs fail before solver execution."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "relationship_aspect_search_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The cross-chart search returns its effective labels, aspect policy, node-variant policy, motion limit, ordering, and event count beside the events.",
        "stage_label": "Cross-chart aspect-search truth",
        "operation": "Build two independent charts, apply the effective inter-chart aspect policy, and return the bounded search truth beside aspects or enriched contacts.",
        "semantic_values": {
            "inputs": [
                "Two typed relationship parties, labels, tier, orb factor, and node policy are exposed by OpenAPI."
            ],
            "units": [
                "Chart and aspect longitudes, separations, angles, and orbs are degrees."
            ],
            "reference_frame": [
                "The response identifies independent chart longitudes without inventing a shared relationship-chart frame."
            ],
            "origin": [
                "Source and target parties remain directionally labeled in computation truth; enriched contacts retain the labels per event."
            ],
            "timescale": [
                "Each chart retains its own birth epoch; no shared motion epoch is inferred."
            ],
            "corrections": [
                "No cross-chart motion correction is inferred; applying and separating remain unclassified without a shared time basis."
            ],
            "policies_defaults": [
                "Effective tier, orb factor, node inclusion, node-variant policy, custom-orb status, ordering, and event count are returned."
            ],
            "fallbacks": [
                "No hidden aspect-policy or chart fallback is admitted by this contract."
            ],
            "refusal_behavior": [
                "Typed request validation and engine policy validation bound invalid parties, labels, tiers, orb factors, and node inputs."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "pattern_search_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The pattern search returns chart-position and motion sources, node and orb policy, selection mode, requested names, dominance policy, ordering, and count beside structured pattern evidence.",
        "stage_label": "Aspect-pattern search truth",
        "operation": "Build one chart context, select the requested registered detectors, detect and optionally dominance-filter patterns, evaluate coherence, and return search truth beside results.",
        "semantic_values": {
            "inputs": [
                "A typed chart plus node, orb, pattern-selection, and dominance controls are exposed by OpenAPI."
            ],
            "units": [
                "Pattern longitudes, aspect angles, orb ledgers, and coherence reference orbs use degrees where named."
            ],
            "reference_frame": [
                "Positions and rates come from one chart context; no relationship-chart frame is inferred."
            ],
            "origin": [
                "The response names chart longitudes and chart longitude rates as the detection and coherence inputs."
            ],
            "timescale": [
                "The chart epoch supplies the position and instantaneous rate context; no event search is performed."
            ],
            "corrections": [
                "No pattern correction is inferred beyond the returned detector, contribution, and coherence vessels."
            ],
            "policies_defaults": [
                "Node inclusion, orb factor, all-versus-explicit selection, requested names, dominance filtering, ordering, and result count are returned."
            ],
            "fallbacks": [
                "An empty result remains inspectable through the search truth; no substitute pattern is synthesized."
            ],
            "refusal_behavior": [
                "Typed request and engine registry validation reject invalid chart, policy, or pattern-name inputs."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "midpoint_search_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The midpoint routes return their position source, shorter-arc geometry, planet-set and node policy, dial/focus/score semantics, ordering, and event count beside results.",
        "stage_label": "Midpoint and dial-search truth",
        "operation": "Build chart longitudes, filter the named planet set, compute shorter-arc midpoints, and apply any requested dial, focus, orb, and count-ranking policy.",
        "semantic_values": {
            "inputs": [
                "A typed chart, named planet set, node policy, and applicable orb and dial controls are exposed by OpenAPI."
            ],
            "units": [
                "Ecliptic longitudes, midpoint positions, dials, and orbs are degrees; weighting scores are counts."
            ],
            "reference_frame": [
                "The response identifies chart longitudes as the positional source and the selected dial projection where applicable."
            ],
            "origin": [
                "Each midpoint retains its contributing pair; pictures retain focus and generating pair; weights retain their picture ledger."
            ],
            "timescale": [
                "The chart epoch supplies the positions; midpoint and dial operations do not advance time."
            ],
            "corrections": [
                "No correction is inferred beyond shorter-arc midpoint geometry and the named dial projection."
            ],
            "policies_defaults": [
                "Planet set, node inclusion, orb, dial, focus exclusion, score meaning, ordering, and result count are returned where applicable."
            ],
            "fallbacks": [
                "Unsupported planet sets or dials are errors; an empty picture result is returned without a synthesized fallback."
            ],
            "refusal_behavior": [
                "Typed request validation and midpoint engine validation bound nested node policy, planet-set, orb, and dial inputs."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "sidereal_utility_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The sidereal and Nakshatra utility routes return their effective ayanamsa reduction path, UT1/TT epochs, delta-T, polynomial or live-star-anchor components, fallback state, and equal-mansion partition truth beside the result.",
        "stage_label": "Sidereal and Nakshatra utility computation truth",
        "operation": "Validate finite UT1 Julian date and longitude inputs, resolve the named ayanamsa on TT, apply mechanical longitude conversion or 27-Nakshatra segmentation, and return computation truth and provenance beside the result.",
        "semantic_values": {
            "inputs": [
                "A finite UT1 Julian date, named built-in ayanamsa system, true/mean mode, and finite longitude or bounded named longitude map are exposed by OpenAPI."
            ],
            "units": [
                "Julian dates use days, delta-T uses seconds, and ayanamsa, precession, drift, nutation, longitudes, and Nakshatra spans use degrees."
            ],
            "reference_frame": [
                "The response distinguishes tropical ecliptic of date from the selected sidereal zodiac frame and names the anchor star where applicable."
            ],
            "origin": [
                "Ayanamsa offsets are anchored to J2000 polynomial reference values or live star positions; no observer-local topocentric or house origin is implied."
            ],
            "timescale": [
                "Input epochs are caller-supplied UT1 Julian dates; computation truth discloses the resolved TT Julian date and delta-T seconds."
            ],
            "corrections": [
                "IAU 2006 general precession, secular drift, IAU 2000A nutation in longitude, or live star-anchor evaluation are disclosed by computation truth."
            ],
            "policies_defaults": [
                "System identity, requested/effective mode, effective reduction path, and equal 27-Nakshatra / 4-pada partition constants are returned explicitly."
            ],
            "fallbacks": [
                "Star-anchor lookup fallback to the polynomial path and exact-boundary Nakshatra/pada clamping are disclosed explicitly when they occur."
            ],
            "refusal_behavior": [
                "Typed request validation and engine guards reject unknown systems, invalid modes, non-finite JDs or longitudes, and empty or oversized bulk maps."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "chart_shape_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The chart-shape route returns normalized ten-body longitudes, circular ordering, adjacent gap receipts, ordered Jones detector attempts, and the selected detector rule beside the classified shape.",
        "stage_label": "Jones chart-shape classification truth",
        "operation": "Build or validate the ten canonical planetary longitudes, normalize circular ordering and gap separations, evaluate the ordered Jones detectors, and return the classified shape beside its computation truth.",
        "semantic_values": {
            "inputs": [
                "Either a typed chart request or an explicit ten-planet longitude map (Sun through Pluto) is exposed by OpenAPI."
            ],
            "units": [
                "Longitudes, occupied arc, largest gap, gap spans, and functioning aspect orbs use degrees."
            ],
            "reference_frame": [
                "Computation truth names either apparent geocentric tropical ecliptic of date (for chart-derived inputs) or caller-supplied longitudes."
            ],
            "origin": [
                "Input source is explicitly labeled as chart_request or caller_supplied_positions; only the ten canonical Jones bodies are admitted."
            ],
            "timescale": [
                "When chart-derived, the chart request supplies the epoch; when position-derived, no epoch is inferred."
            ],
            "corrections": [
                "Input longitudes are normalized modulo 360 degrees; no hidden positional or node/angle addition is applied."
            ],
            "policies_defaults": [
                "Required ten-body set, body-dependent major aspect orbs, group-separation thresholds, ordered detector attempts, and selected detector are explicit."
            ],
            "fallbacks": [
                "Ordered detector precedence and the final Splash fallback are explicitly recorded in detector_attempts and selected_detector."
            ],
            "refusal_behavior": [
                "Typed validation and engine guards reject missing, extra, or non-finite planetary longitudes before detector evaluation."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "planetary_hours_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The planetary-hours routes return the enclosing sunrise-to-next-sunrise local solar window, 24 Chaldean daytime/nighttime hour bounds, optional hour-at lookup, and explicit provenance naming the vessel, sequence basis, solar-event source, and stage sequence.",
        "stage_label": "Sunrise-anchored Chaldean planetary-hours resolution",
        "operation": "Validate geographic coordinates and UT1 JD, resolve the enclosing sunrise-to-next-sunrise local solar day, partition daytime and nighttime into 12 Chaldean hours each, optionally select the containing hour, and emit provenance.",
        "semantic_values": {
            "inputs": [
                "Typed request schema exposes jd, latitude, longitude, include_iso_utc, and (for hour-at) include_schedule in OpenAPI."
            ],
            "units": [
                "Geographic coordinates use degrees; Julian Days and day/night durations use days."
            ],
            "reference_frame": [
                "Sunrise and sunset boundaries are evaluated in the observer's topocentric horizontal frame via moira._solar."
            ],
            "origin": [
                "Topocentric observer at caller-supplied geographic latitude and longitude."
            ],
            "timescale": [
                "Input and hour-boundary JDs use UT1, with optional UTC ISO-8601 calendar serialization."
            ],
            "corrections": [
                "Standard solar-limb and atmospheric-refraction horizon altitude (-0.8333 degrees) is applied during sunrise/sunset refinement."
            ],
            "policies_defaults": [
                "Provenance names Chaldean_order, weekday_rulership, sunrise_to_next_sunrise windowing, moira.planetary_hours.PlanetaryHour (distinct from moira.cycles.PlanetaryHour), and utc_output_only."
            ],
            "fallbacks": [
                "No silent polar fallback is admitted; hour-at returns null with contains_requested_jd=false only if a window does not contain the requested JD."
            ],
            "refusal_behavior": [
                "Typed request validation and solar-window guards reject non-finite JDs, out-of-range coordinates, or polar days/nights lacking sunrise/sunset crossings."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "visibility_assessment_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The visibility assessment route returns the target and solar geometry, criterion family, effective limiting magnitude, and optional physical atmospheric-extinction, directional twilight-brightness, and Crumey point-source threshold breakdowns.",
        "stage_label": "Empirical and physical visibility assessment",
        "operation": "Validate target body, epoch, observer coordinates, and visibility policy; evaluate apparent target/solar altitudes, elongation, magnitude, and selected visibility criterion; and return the full assessment breakdown.",
        "semantic_values": {
            "inputs": [
                "Typed request schema exposes body, jd_ut, lat, lon, and optional VisibilityPolicyRequest fields in OpenAPI."
            ],
            "units": [
                "Altitudes, elongations, and coordinates use degrees; magnitudes and extinction use V-band magnitudes; sky brightness uses nanolamberts."
            ],
            "reference_frame": [
                "Topocentric horizontal altitude/azimuth and apparent geocentric/topocentric solar elongation at the observer."
            ],
            "origin": [
                "Topocentric observer at caller-supplied geographic latitude, longitude, and policy elevation."
            ],
            "timescale": [
                "Evaluation epoch is Julian Day in Universal Time (jd_ut)."
            ],
            "corrections": [
                "True and apparent altitudes, optional Kasten-Young or Schaefer atmospheric extinction, directional twilight brightness, and lunar crescent details are exposed explicitly."
            ],
            "policies_defaults": [
                "Criterion family, extinction model, twilight model, field factor, and whether target extinction is applied separately are carried in the response."
            ],
            "fallbacks": [
                "No silent criterion substitution is performed; physical component validity flags and lunar crescent classification are reported explicitly."
            ],
            "refusal_behavior": [
                "Typed validation and engine guards reject unsupported target bodies, invalid coordinates, and out-of-domain policy parameters."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "astrocartography_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The astrocartography routes return MC/IC/ASC/DSC horizon and meridian loci, subplanetary Zenith/Nadir points, or dynamic/fixed-star series alongside explicit subject provenance or computation_truth.",
        "stage_label": "Locational astrocartography projection and provenance",
        "operation": "Resolve direct RA/Dec, chart-derived planetary/minor-body/lot/point coordinates, fixed-star registry positions, or multi-epoch transit snapshots; project MC/IC/ASC/DSC curves and Zenith/Nadir points; and emit subject provenance or computation_truth.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose direct RA/Dec maps with gmst_deg, chart datetime/body/subject specifications, fixed-star names with jd_ut/jd_tt, or dynamic transit epochs and observer coordinates."
            ],
            "units": [
                "Right ascension, declination, GMST, geographic latitude/longitude, and lat_step use degrees."
            ],
            "reference_frame": [
                "Equatorial RA/Dec of date projected onto geographic latitude/longitude via Greenwich sidereal rotation and horizon altitude geometry."
            ],
            "origin": [
                "Provenance and computation_truth distinguish direct_none, chart_request topocentric observer, and geocentric ecliptic-to-equatorial subject origins."
            ],
            "timescale": [
                "Chart and dynamic routes bind UTC/UT1 and TT epochs explicitly; direct RA/Dec routes bind caller-supplied gmst_deg and optional jd_ut."
            ],
            "corrections": [
                "Horizon refraction inclusion, topocentric vs geocentric subject reduction, and ordered stage sequences are recorded in provenance or computation_truth."
            ],
            "policies_defaults": [
                "Subject classes, NAIF IDs, canonical names, position sources, lat_step cadence, and geometry-only interpretation rules are explicit."
            ],
            "fallbacks": [
                "No silent small-body family disambiguation or comet topocentric fallback is permitted."
            ],
            "refusal_behavior": [
                "Typed validation rejects ambiguous unqualified small bodies, unsupported chart bodies, partial observer overrides, duplicate subject labels, and out-of-range steps."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "locational_projection_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The chart-backed Gauquelin, geodetic, and local-space routes project chart bodies into diurnal sectors, geographic equivalents/angles, or local horizon azimuth/altitude while embedding typed provenance.",
        "stage_label": "Chart-backed locational projection and provenance",
        "operation": "Normalize chart datetime and observer coordinates, resolve apparent celestial positions and obliquity/sidereal time, project into Gauquelin 36-sector diurnal arcs, geodetic MC/ASC/equivalents, or local-space azimuth/altitude, and attach provenance.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose timezone-aware datetime, observer coordinates, body lists, and technique-specific horizon or zodiac parameters in OpenAPI."
            ],
            "units": [
                "Right ascension, declination, longitudes, azimuth, altitude, obliquity, and degree-in-sector use degrees; Gauquelin sectors use integer indices 1..36."
            ],
            "reference_frame": [
                "Provenance names chart_apparent_topocentric_ra_dec_lst, chart_tropical_longitudes / chart_epoch_obliquity, or chart_apparent_topocentric_ra_dec."
            ],
            "origin": [
                "Topocentric observer or geocentric chart reduction as declared in provenance.observer and coordinate_source."
            ],
            "timescale": [
                "Timezone-aware UTC datetime normalized to UT1/TT chart epochs."
            ],
            "corrections": [
                "Apparent topocentric RA/Dec, true obliquity of date, sidereal rotation, and horizon altitude policies are recorded in provenance.stage_sequence."
            ],
            "policies_defaults": [
                "Requested/returned bodies, coordinate_source, zodiac/ayanamsa policy, and Gauquelin plus-zone / horizon status classifications are explicit."
            ],
            "fallbacks": [
                "Circumpolar and never-rises bodies in Gauquelin sectors preserve explicit horizon_status with null sector fields rather than fabricated sectors."
            ],
            "refusal_behavior": [
                "Typed validation rejects naive datetimes, non-finite or polar-invalid latitudes, unsupported bodies, and incomplete observer coordinates."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "paran_search_and_packet_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The natal paran search and website paran packet routes return co-rising/culminating/setting paran events, crossing source methods, altitude policies, strength models, optional four-circle crossing inventories, and packet provenance/warnings.",
        "stage_label": "Horizon/meridian paran search and packet composition",
        "operation": "Resolve diurnal rise/set/culmination/anti-culmination crossings for requested planets and fixed stars on the local day, pair co-temporal crossings within orb under the active policy preset, and emit crossing inventories, angular contacts, heliacal events, and provenance.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose bodies, natal_jd, lat, lon, orb_minutes, policy_preset, and inventory/packet inclusion flags in OpenAPI."
            ],
            "units": [
                "Geographic coordinates and horizon altitude policies use degrees; crossing times use JD UT1; orbs and contact deltas use minutes."
            ],
            "reference_frame": [
                "Topocentric horizon (Rising/Setting) and local meridian (Culminating/AntiCulminating) for the observer latitude and longitude."
            ],
            "origin": [
                "Topocentric observer at caller-supplied latitude and longitude."
            ],
            "timescale": [
                "Crossing and event timestamps are reported in JD UT1 alongside UTC ISO-8601 timestamps."
            ],
            "corrections": [
                "Each ParanCrossingResponse records source_method (find_phenomena or get_transit) and altitude_policy (-0.5667 degrees for horizon crossings, null for meridian transits)."
            ],
            "policies_defaults": [
                "Effective policy preset, event/axis/body family labels, linear orb strength model, and star-canon tiers are returned explicitly."
            ],
            "fallbacks": [
                "Circumpolar or non-crossing bodies report explicit ParanCrossingStatus (always_above_horizon, always_below_horizon) and absence_reason in crossing_inventory; missing planetary kernels in the website packet emit explicit warnings."
            ],
            "refusal_behavior": [
                "Typed validation rejects unknown policy presets, unknown star-canon tiers, invalid coordinates, and extra fields."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "eclipse_circumstances_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The solar and lunar eclipse search and local-circumstances routes return the eclipse instant, 17-field geometric/Saros/Metonic data vessel, and topocentric contact or overlap circumstances with declared source_model and canon_method.",
        "stage_label": "Solar and lunar eclipse search and topocentric circumstances",
        "operation": "Locate the next matching solar or lunar syzygy eclipse and, for local routes, evaluate topocentric solar/lunar altitude, azimuth, overlap, or penumbral/umbral contact circumstances under native or nasa_compat mode.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose jd_start, kind, and (for local routes) latitude, longitude, elevation_m, max_lunations, or mode in OpenAPI."
            ],
            "units": [
                "Longitudes, latitudes, node distances, 3D separations, altitudes, and azimuths use degrees; elevation uses meters; epochs use JD UT."
            ],
            "reference_frame": [
                "Geocentric ecliptic longitudes/latitudes for syzygy classification and topocentric horizontal azimuth/altitude for local circumstances."
            ],
            "origin": [
                "Geocenter for global syzygy classification; observer latitude, longitude, and elevation for local circumstances."
            ],
            "timescale": [
                "Eclipse and contact instants are returned as jd_ut with paired datetime_utc strings."
            ],
            "corrections": [
                "Lunar local circumstances explicitly record mode (native or nasa_compat), source_model, and canon_method; solar local circumstances record topocentric_separation_deg and topocentric_overlap."
            ],
            "policies_defaults": [
                "Eclipse type filter (any, total, partial, annular, penumbral), Saros/Metonic cycle indices, and contact visibility flags are explicit."
            ],
            "fallbacks": [
                "Contacts absent for partial or penumbral lunar eclipses (such as u1..u4) are returned as null rather than fabricated."
            ],
            "refusal_behavior": [
                "Typed validation and engine guards reject unknown eclipse kinds, invalid modes, non-finite JDs, and out-of-range coordinates."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "heliacal_and_twilight_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The planetary heliacal and twilight routes return topocentric horizon/twilight crossing instants and heliacal visibility geometry (elongation, planet/Sun altitudes, apparent magnitude) for the observer.",
        "stage_label": "Topocentric twilight and planetary heliacal event resolution",
        "operation": "Evaluate local solar depression crossings (-0.8333, -6, -12, -18 degrees) for twilight or scan forward for the next applicable planetary heliacal phenomenon (heliacal/acronychal/cosmical rising or setting, evening first, morning last).",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose jd_day or jd_start, lat, lon, and (for heliacal) body, kind, and search_days in OpenAPI."
            ],
            "units": [
                "Coordinates, elongations, and altitudes use degrees; apparent magnitude uses V-band magnitude; epochs use JD UT."
            ],
            "reference_frame": [
                "Topocentric horizontal frame and apparent solar elongation at the observer."
            ],
            "origin": [
                "Topocentric observer at caller-supplied geographic latitude and longitude."
            ],
            "timescale": [
                "Event instants are reported as jd_ut with paired datetime_utc strings."
            ],
            "corrections": [
                "Standard solar horizon (-0.8333 deg) and civil/nautical/astronomical twilight depression thresholds (-6, -12, -18 deg) or heliacal arcus visionis / visibility thresholds are applied."
            ],
            "policies_defaults": [
                "Standard Ptolemy/Schoch heliacal event kinds and twilight depression tiers are exposed as named fields."
            ],
            "fallbacks": [
                "Inapplicable heliacal event kinds (such as evening_first for outer planets) or absent twilight crossings return null without fabricating an instant."
            ],
            "refusal_behavior": [
                "Typed validation rejects unknown heliacal kinds, unsupported bodies, non-finite JDs, and out-of-range geographic coordinates."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "transit_and_return_search_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The transit, ingress, natal-aspect, lunar-phase, and solar/lunar/planet/relocated return routes return exact crossing or phase instants alongside embedded computation_truth, classification, relation, condition_profile, or dual-chart relocation receipts.",
        "stage_label": "Predictive transit, ingress, phase, and return search truth",
        "operation": "Resolve moving and target bodies or phase angles on the apparent geocentric ecliptic lattice, bracket and bisect exact crossings under explicit step/tolerance/direction policies, and return event vessels with computation_truth or relocated-return chart receipts.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose moving bodies, targets or natal longitudes, aspect specs, search windows or return years, direction/motion filters, step/tolerance overrides, and relocation coordinates in OpenAPI."
            ],
            "units": [
                "Longitudes, phase angles, aspect angles, orbs, and geographic coordinates use degrees; epochs, scan steps, and solver tolerances use days (JD UT)."
            ],
            "reference_frame": [
                "Apparent geocentric true ecliptic of date for longitude crossings, sign ingresses, lunar phases, and returns; topocentric house frames for relocated return charts."
            ],
            "origin": [
                "Geocenter for transit, ingress, phase, and return timing; source and relocated geographic coordinates for relocated return chart contexts."
            ],
            "timescale": [
                "Event and return instants are reported in JD UT alongside UTC ISO-8601 timestamps; relocated returns also bind JD TT."
            ],
            "corrections": [
                "Target resolution truth, crossing bracket and bisection tolerance, retrograde-hit and orb-window boundary flags, or same-epoch/same-celestial-snapshot relocation truth are returned explicitly."
            ],
            "policies_defaults": [
                "Requested and effective step_days, solver_tolerance_days, direction filter, search_motion, return search policy, and house-system fallback flags are carried by the response."
            ],
            "fallbacks": [
                "Unentered or unexited aspect orb windows remain null on jd_entering/jd_leaving; house-system polar fallbacks in relocated returns are disclosed per chart without altering return timing."
            ],
            "refusal_behavior": [
                "Typed validation rejects reversed windows, non-finite JDs, unknown movers/targets, invalid return selectors, and out-of-range steps or tolerances."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "progression_and_arc_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The secondary progression, solar/time-key/planetary arc, and daily house-frame progression routes return progressed positions or cusps with embedded doctrine/rate/application classifications, relation, and condition_profile, paired with dedicated /reduction endpoints exposing ProgressionComputationTruth.",
        "stage_label": "Progressed chart, directed arc, and house-frame derivation",
        "operation": "Map natal and target epochs through the selected progression time key, directed arc rate, or daily house-frame rotation, evaluate progressed positions or cusps, and expose full stage and formula receipts on the paired /reduction endpoint.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose timezone-aware natal_dt and target_dt, method/technique selectors, bodies, converse flags, observer coordinates, and house policy in OpenAPI."
            ],
            "units": [
                "Longitudes, latitudes, right ascensions, declinations, cusps, and solar/directed arcs use degrees; speeds use degrees per day; epochs use JD UT."
            ],
            "reference_frame": [
                "The response names coordinate_system (ecliptic_longitude, equatorial_ra, declination, or house_cusps) and pairs with /reduction for full frame provenance."
            ],
            "origin": [
                "Geocentric planetary reduction for secondary/arc progressions; topocentric observer latitude and longitude for progressed house frames."
            ],
            "timescale": [
                "Natal and progressed JD UT and target UTC datetime are returned in the response and expanded with elapsed years and key constants on /reduction."
            ],
            "corrections": [
                "Direct vs converse motion, rate_mode, application_mode, and house-system fallback state are explicit."
            ],
            "policies_defaults": [
                "Doctrine family, coordinate system, rate mode, application mode, relation, and condition_profile are embedded on every response."
            ],
            "fallbacks": [
                "House-frame polar fallback is reported explicitly on house-frame responses and /reduction vessels; no silent technique substitution is permitted."
            ],
            "refusal_behavior": [
                "Typed validation rejects naive datetimes, unsupported bodies, missing arc_body on planetary_arc, and invalid observer coordinates."
            ],
        },
        "public_modes": [
            "embedded_result",
            "paired_reduction_endpoint",
            "generated_documentation",
        ],
    },
    "primary_directions_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The primary-directions speculum and network/reduction routes expose the complete equatorial/mundane speculum (lon, lat, ra, dec, ha, dsa, nsa, upper, f) or directed network graph paired with PrimaryDirectionsArcsReductionTruth.",
        "stage_label": "Primary-directions speculum and network reduction truth",
        "operation": "Compute equatorial and mundane speculum coordinates (RA, declination, hour angle, diurnal/nocturnal semi-arcs, meridian hemisphere, ascensional/mundane factor) or reduce the primary-direction network alongside UT1/TT/delta-T, observer, house_context, resolved_policy, and stage_sequence.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose timezone-aware chart datetime, observer latitude/longitude, house system, bodies, node inclusion, max_arc, and primary-directions policy/preset in OpenAPI."
            ],
            "units": [
                "Longitudes, latitudes, right ascensions, declinations, hour angles, semi-arcs, and directed arcs use degrees; delta_t_seconds uses seconds; epochs use JD UT and JD TT."
            ],
            "reference_frame": [
                "Equatorial and mundane diurnal/nocturnal semi-arc geometry on the celestial sphere for the observer latitude."
            ],
            "origin": [
                "Observer geographic latitude and longitude (with explicit PositionObserverContextResponse on reduction routes)."
            ],
            "timescale": [
                "Reduction routes report requested_datetime, normalized_datetime_utc, jd_ut, jd_tt, and delta_t_seconds."
            ],
            "corrections": [
                "Latitude doctrine (zodiacal vs cum_latitudine), converse doctrine, house-system fallback, and target-extension contexts are explicit in resolved_policy."
            ],
            "policies_defaults": [
                "Method (placidus/regiomontanus), space (mundane/zodiacal), key, key_source, perfection_kind, admitted relation/significator/promissor classes, and policy_source are returned."
            ],
            "fallbacks": [
                "House-system fallback is reported in house_context; speculum and network routes do not mask evaluation failures."
            ],
            "refusal_behavior": [
                "Typed validation rejects naive datetimes, polar/invalid observer latitudes, non-positive max_arc, unknown presets or keys, and self-directions."
            ],
        },
        "public_modes": [
            "embedded_result",
            "paired_reduction_endpoint",
            "generated_documentation",
        ],
    },
    "timelord_and_profection_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The annual/schedule profection and Firdaria, Decennials, and Zodiacal Releasing sequence routes return complete period sequences alongside embedded activation_truth, chronology receipts, DecennialSequenceAssemblyTruth, or ZRFortuneAngularityTruth.",
        "stage_label": "Hellenistic and medieval time-lord and profection sequence truth",
        "operation": "Evaluate Whole Sign annual/monthly profections with civil-anniversary chronology and activation truth, or construct Firdaria, Decennials, or Zodiacal Releasing period sequences with embedded sect, year/month basis, sequence assembly, or Fortune-angularity truth.",
        "semantic_values": {
            "inputs": [
                "Typed request schemas expose natal ascendant or timezone-aware natal/query datetimes, sect or lot longitudes, variant/level selectors, and civil_timezone/leap_day/ambiguous_time policies in OpenAPI."
            ],
            "units": [
                "Longitudes and activation orbs use degrees; period durations use years, months, and days under the declared year basis; interval bounds use JD UT and ISO dates."
            ],
            "reference_frame": [
                "Tropical Whole Sign houses and ecliptic longitudes for profections, Decennials, and Zodiacal Releasing; sect-governed Chaldean/planetary sequences for Firdaria."
            ],
            "origin": [
                "Natal chart epoch and natal Ascendant, sect light, or Lot of Spirit/Fortune anchor."
            ],
            "timescale": [
                "Profection schedules bind IANA civil_timezone with tzdata version and UTC/JD interval bounds; Decennials and Firdaria report sequence_origin_jd, time_basis, and calendar_projection_basis."
            ],
            "corrections": [
                "Loosing-of-the-bond transitions, Fortune-relative angularity and peak classification, Decennial forward-arc ordering from sect light, and leap-day/DST fold policies are explicit."
            ],
            "policies_defaults": [
                "Firdaria nocturnal variant (al-Qabisi vs Bonatti), Decennial 360-day year / 30-day month basis, ZR 360-day Egyptian year basis, and profection interval/boundary semantics are carried in the response."
            ],
            "fallbacks": [
                "Absent natal positions in profections return activation_truth.status='not_evaluable' with reason='natal_positions_not_supplied'; absent Fortune longitude in ZR returns fortune_angularity_truth.status='not_evaluable'."
            ],
            "refusal_behavior": [
                "Typed validation rejects naive datetimes, pre-birth query dates, unsupported Decennial deep levels (3-4), invalid variants or lot names, and unconfigured Feb-29 or DST fold policies when triggered."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "batch_assembly_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The batch chart, chart-reduction, event, return, and progression routes preserve deterministic request ordering, item-level failure isolation (BatchFailureResponse), and per-item embedded computation_truth or paired /reduction receipts.",
        "stage_label": "Bounded batch calculation and item-level failure isolation",
        "operation": "Validate the bounded batch request list, execute each chart, transit/ingress/station/lunar-phase/aspect event, return, or progression item with per-item exception isolation, and return ordered success payloads (with embedded truth or reduction vessels) and typed failure receipts.",
        "semantic_values": {
            "inputs": [
                "Bounded request arrays (with explicit maximum item counts) of typed chart, event, return, or progression request items are exposed by OpenAPI."
            ],
            "units": [
                "Each item payload preserves the exact domain units (degrees, AU/km, JD UT/TT days, seconds) of its underlying single-item contract."
            ],
            "reference_frame": [
                "Each succeeded item carries the reference frame and coordinate system of its underlying chart, transit/ingress, return, or progression vessel."
            ],
            "origin": [
                "Geocentric or topocentric observer context is preserved per item and exposed in /v1/batch/charts/reduction and /v1/batch/progressions/reduction."
            ],
            "timescale": [
                "Each item resolves and reports its own UTC/UT1/TT epochs; batch chart construction resolves UTC, TT, and UT1 once per item for all consumers."
            ],
            "corrections": [
                "Per-item reduction vessels (/v1/batch/charts/reduction, /v1/batch/progressions/reduction) and embedded transit/ingress/return computation_truth preserve all applied corrections and stage sequences."
            ],
            "policies_defaults": [
                "Item index, kind/technique, total_count, succeeded_count, failed_count, and per-item policy/truth vessels are returned."
            ],
            "fallbacks": [
                "Per-item failures are isolated into structured BatchFailureResponse(error_type, message, error_module) with ok=False rather than aborting sibling items."
            ],
            "refusal_behavior": [
                "Envelope-level validation rejects empty or over-limit batch arrays, unknown discriminators, and malformed request schemas with 422 before item execution."
            ],
        },
        "public_modes": [
            "embedded_result",
            "paired_reduction_endpoint",
            "generated_documentation",
        ],
    },
    "classical_dignities_and_condition_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The classical dignities, receptions, and condition-profile surfaces embed EssentialDignityTruth, AccidentalDignityTruth, SectTruth, SolarConditionTruth, MutualReceptionTruth, and derived condition/network graph receipts.",
        "stage_label": "Classical dignity, reception, and condition-network evaluation",
        "operation": "Validate chart or planet/house inputs and DignityComputationPolicy, evaluate atomic essential components, accidental conditions, sect/hayz/horizon truth, solar proximity/phase truth, and formal receptions, and project deterministic per-planet, chart-wide, and network condition profiles.",
        "semantic_values": {
            "inputs": [
                "Planet/house position lists or timezone-aware chart request parameters, optional DignityHorizonFrame, node/fixed-star longitudes, and typed DignityComputationPolicy are validated."
            ],
            "units": [
                "Longitudes, separations, and orbs are degrees; essential and accidental weights and scores are signed integers."
            ],
            "reference_frame": [
                "Tropical ecliptic sign/degree placement paired with optional exact Ascendant/Midheaven horizon geometry (DignityHorizonFrame / HorizonTruth)."
            ],
            "origin": [
                "Geocentric ecliptic longitudes and topocentric house/horizon frame from the chart or caller-supplied positions."
            ],
            "timescale": [
                "Chart-backed REST routes resolve the timezone-aware UTC datetime through the Moira engine; direct position functions operate on instantaneous longitudes and speeds."
            ],
            "corrections": [
                "Sect/Hayz horizon method (exact horizon vs house-cusp fallback), Mercury sect model, solar proximity band classification, and besieging dependency completeness are explicitly carried in the truth vessels."
            ],
            "policies_defaults": [
                "EssentialDignityTruth and SectTruth echo scoring_mode (william_lilly_1647 default), bounds_doctrine, triplicity_doctrine, and HalbHayzDoctrine alongside per-component weights and status."
            ],
            "fallbacks": [
                "Missing Sun, incomplete besieging bodies, or exact boundary ties fail closed as typed TruthEvaluationStatus (NOT_EVALUABLE / SUPPRESSED_BY_POLICY) with an explicit reason string rather than fabricating a condition or score."
            ],
            "refusal_behavior": [
                "Duplicate planet entries, non-finite coordinates, incoherent scoring/doctrine combinations (such as Lilly 1647 with modern co-rulers), and outer-planet condition queries without modern_co_rulers are rejected."
            ],
        },
        "public_modes": [
            "embedded_result",
            "source_only",
            "generated_documentation",
        ],
    },
    "classical_lots_evaluation_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The classical lots chart route returns LotsResultResponse with evaluated ArabicPartResponse items (carrying ArabicPartComputationTruth, ArabicPartClassification, LotDependencyCompletenessTruth, and LotAstrologicalConditionTruth) beside explicit LotNotEvaluableResponse records.",
        "stage_label": "Classical lots formula projection and dependency completeness evaluation",
        "operation": "Derive chart positions and house cusps through Moira, resolve LotsComputationPolicy (including unresolved-reference mode and derived/external reference switches), evaluate each catalog lot with ArabicPartComputationTruth and dependency completeness, and segregate missing-reference lots into LotNotEvaluableResponse.",
        "semantic_values": {
            "inputs": [
                "Timezone-aware datetime, finite observer coordinates, house_system, optional external reference longitudes (syzygy, prenatal_new_moon, prenatal_full_moon, lord_of_hour), and LotsComputationPolicy are validated."
            ],
            "units": [
                "Ecliptic longitudes and sign degrees are degrees in [0, 360) and [0, 30); DMS tuples carry integer degrees/minutes and float seconds."
            ],
            "reference_frame": [
                "Tropical ecliptic longitudes projected from the Ascendant, house cusps, planetary rulers, or inter-lot references under explicit LotArcPolicy."
            ],
            "origin": [
                "Observer-specific Ascendant and house cusps combined with geocentric planetary positions."
            ],
            "timescale": [
                "Chart epoch is normalized from the timezone-aware datetime through the Moira chart service."
            ],
            "corrections": [
                "Diurnal/nocturnal formula reversal (reversed_at_night and reversed_for_chart), effective add/sub reference keys, and projector reference truth are recorded on ArabicPartComputationTruth."
            ],
            "policies_defaults": [
                "LotsComputationPolicy defaults to unresolved_reference_mode='skip' with derived Fortune/Spirit/Eros and external syzygy/prenatal/lord_of_hour references enabled when supplied."
            ],
            "fallbacks": [
                "Lots whose required external or derived references are absent are never fabricated; under 'skip' mode they are recorded in not_evaluable with missing_references and status='not_evaluable'."
            ],
            "refusal_behavior": [
                "Naive datetimes, non-finite observer or optional reference longitudes, invalid policy values, or missing references under strict failure mode raise validation errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "ordinary_antiscia_contacts_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The ordinary antiscia contacts route embeds AntisciaContactResponse items with shadow longitude, orb, and optional speed-based applying/separating motion state beside AntisciaProvenanceResponse.",
        "stage_label": "Solstitial reflection and ordinary antiscia contact search",
        "operation": "Validate bounded caller-supplied longitudes, optional speeds, and orb, reflect each longitude across the Cancer-Capricorn (antiscion) and Aries-Libra (contra-antiscion) axes, match contacts within orb in deterministic order, and attach AntisciaProvenanceResponse.",
        "semantic_values": {
            "inputs": [
                "Bounded non-empty position map (up to 64 bodies), finite orb in [0, 30] degrees, and optional finite speed map are validated."
            ],
            "units": [
                "Longitudes, reflected shadows, and orbs are degrees; optional speeds are degrees per day."
            ],
            "reference_frame": [
                "Tropical ecliptic longitudes reflected across the 0 Cancer / 0 Capricorn solstitial axis ((180 - lon) mod 360) and 0 Aries / 0 Libra equinoctial axis ((360 - lon) mod 360)."
            ],
            "origin": [
                "Caller-supplied ecliptic longitude map; ephemeris is explicitly marked 'not_used' in AntisciaProvenanceResponse."
            ],
            "timescale": [
                "Instantaneous caller-supplied positions; chart_motion is 'not_computed' when speeds are omitted or 'applying_separating_from_caller_speeds' when speeds are supplied."
            ],
            "corrections": [
                "AntisciaProvenanceResponse explicitly declares primary_direction_boundary='not_primary_direction_antiscia' and records the exact reflection formulas and stage_sequence."
            ],
            "policies_defaults": [
                "Default orb is 1.0 degree, maximum positions is 64, maximum orb is 30.0 degrees, and result_ordering is 'orb_asc_then_input_pair_order'."
            ],
            "fallbacks": [
                "When speeds are omitted for a pair, motion_state and applying remain None rather than guessing motion direction."
            ],
            "refusal_behavior": [
                "Empty or over-limit position maps, blank or duplicate trimmed body names, non-finite longitudes/speeds, and out-of-range orbs are rejected with 422 validation errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
    "manazil_lunar_mansion_vessel": {
        "inspectability_mode": "embedded_result",
        "summary": "The Arabic lunar mansion (Manazil) position route returns MansionPositionEnvelopeResponse pairing MansionPositionResponse (1..28 index, degrees_in, computation_longitude, and tradition attribution) with MansionProvenanceResponse.",
        "stage_label": "Equal-28 Arabic lunar mansion division and tradition attribution",
        "operation": "Validate finite longitude, tropical/sidereal mode (requiring jd_ut when sidereal), and MansionTraditionName, normalize or convert longitude to the computation frame, divide 360 degrees into 28 equal mansions, attach tradition nature/signification, and emit MansionProvenanceResponse with stage_sequence.",
        "semantic_values": {
            "inputs": [
                "Finite ecliptic longitude, MansionComputationMode (tropical or sidereal), optional jd_ut, ayanamsa_system, ayanamsa_mode, and MansionTraditionName are validated."
            ],
            "units": [
                "Requested, normalized, computation, and in-mansion longitudes are degrees; mansion span is 360/28 degrees; jd_ut is Julian Day UT."
            ],
            "reference_frame": [
                "Explicitly reported in MansionProvenanceResponse.mode ('tropical' or 'sidereal' with named ayanamsa_system and ayanamsa_mode)."
            ],
            "origin": [
                "0 degrees Aries (tropical or sidereal according to mode) divided into 28 equal 12d51m25.7s segments."
            ],
            "timescale": [
                "Sidereal mode requires a finite jd_ut epoch for ayanamsa reduction and echoes jd_ut in MansionProvenanceResponse; tropical mode is epoch-independent."
            ],
            "corrections": [
                "Sidereal mode applies the requested ayanamsa_system and ayanamsa_mode before equal-28 mansion indexing and records the stage in stage_sequence."
            ],
            "policies_defaults": [
                "Default mode is 'tropical', default tradition is 'agrippa', default sidereal ayanamsa is 'Lahiri' ('true'), and default authority is 'al_biruni_book_of_instruction'."
            ],
            "fallbacks": [
                "No silent fallback between tropical and sidereal modes is permitted; sidereal mode without jd_ut is refused."
            ],
            "refusal_behavior": [
                "Non-finite longitudes or jd_ut, unknown traditions or modes, blank ayanamsa strings, and sidereal requests missing jd_ut are rejected with 422 validation errors."
            ],
        },
        "public_modes": ["embedded_result", "generated_documentation"],
    },
}


class LightBoxConformanceError(RuntimeError):
    """Raised when inventory, schema, or manifest truth is inconsistent."""


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LightBoxConformanceError(f"cannot load JSON: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise LightBoxConformanceError(
            f"JSON root must be an object: {_relative(path)}"
        )
    return value


def _load_inventory_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_calculation_inventory",
        INVENTORY_GENERATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise LightBoxConformanceError("cannot load LB-WP0 inventory generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_current_inventory() -> dict[str, Any]:
    """Load the committed inventory and prove it matches current source truth."""
    committed = _load_json(INVENTORY_PATH)
    generator = _load_inventory_generator()
    current = generator.build_inventory()
    if committed != current:
        raise LightBoxConformanceError(
            "LB-WP0 calculation inventory is stale; regenerate it before LB-WP1"
        )
    return committed


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise LightBoxConformanceError(f"unsupported JSON Schema type: {expected}")


def _resolve_schema_ref(root: Mapping[str, Any], reference: str) -> Mapping[str, Any]:
    if not reference.startswith("#/"):
        raise LightBoxConformanceError(
            f"only local schema refs are supported: {reference}"
        )
    value: Any = root
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or part not in value:
            raise LightBoxConformanceError(f"unresolvable schema ref: {reference}")
        value = value[part]
    if not isinstance(value, dict):
        raise LightBoxConformanceError(f"schema ref is not an object: {reference}")
    return value


def validate_json_schema_instance(
    instance: Any,
    schema: Mapping[str, Any],
) -> list[str]:
    """Validate the strict JSON Schema subset used by the WP1 contract."""
    errors: list[str] = []

    def walk(value: Any, rule: Mapping[str, Any], path: str) -> None:
        if "$ref" in rule:
            walk(value, _resolve_schema_ref(schema, str(rule["$ref"])), path)
            return

        if "const" in rule and value != rule["const"]:
            errors.append(f"{path}: expected constant {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{path}: value {value!r} is outside the admitted enum")

        expected = rule.get("type")
        if expected is not None:
            expected_types = [expected] if isinstance(expected, str) else list(expected)
            if not any(_json_type_matches(value, item) for item in expected_types):
                errors.append(
                    f"{path}: expected type {expected_types}, got {type(value).__name__}"
                )
                return

        if isinstance(value, dict):
            required = rule.get("required", [])
            for name in required:
                if name not in value:
                    errors.append(f"{path}: missing required field {name!r}")
            properties = rule.get("properties", {})
            if rule.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        errors.append(f"{path}: unexpected field {name!r}")
            for name, child_rule in properties.items():
                if name in value:
                    walk(value[name], child_rule, f"{path}.{name}")

        if isinstance(value, list):
            minimum = rule.get("minItems")
            if isinstance(minimum, int) and len(value) < minimum:
                errors.append(f"{path}: requires at least {minimum} item(s)")
            if rule.get("uniqueItems"):
                serialized = [
                    json.dumps(item, sort_keys=True, ensure_ascii=False)
                    for item in value
                ]
                if len(serialized) != len(set(serialized)):
                    errors.append(f"{path}: items must be unique")
            item_rule = rule.get("items")
            if isinstance(item_rule, dict):
                for index, item in enumerate(value):
                    walk(item, item_rule, f"{path}[{index}]")

        if isinstance(value, str):
            minimum = rule.get("minLength")
            if isinstance(minimum, int) and len(value) < minimum:
                errors.append(f"{path}: string is shorter than {minimum}")
            pattern = rule.get("pattern")
            if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
                errors.append(f"{path}: string does not match {pattern!r}")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = rule.get("minimum")
            if isinstance(minimum, (int, float)) and value < minimum:
                errors.append(f"{path}: value is less than {minimum}")

    walk(instance, schema, "$")
    return errors


def _reference(
    kind: str,
    target: str,
    label: str,
    version_identity: str | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "target": target,
        "label": label,
        "version_identity": version_identity,
    }


def _unresolved_disclosure(field_label: str) -> dict[str, Any]:
    return {
        "disposition": "unresolved",
        "values": [],
        "references": [],
        "notes": f"{field_label} has not yet been assessed under the WP1 contract.",
    }


def _unresolved_entry(
    row: Mapping[str, Any],
    *,
    engine_version: str,
    inventory_fingerprint: str,
) -> dict[str, Any]:
    surface_id = str(row["surface_id"])
    canonical_id = str(row["canonical_id"])
    source_path = str(row["source_path"])
    source_line = int(row["source_line"])
    source_reference = _reference(
        "source",
        f"{source_path}#L{source_line}",
        "WP0 ownership pointer; presence is not conformance evidence.",
        engine_version,
    )
    return {
        "surface_id": surface_id,
        "canonical_surface_id": canonical_id,
        "entry_role": "alias" if row["alias_of"] is not None else "canonical",
        "surface_kind": str(row["surface_kind"]),
        "ownership": {
            "source_path": source_path,
            "source_line": source_line,
        },
        "conformance_status": "unresolved",
        "stage_derivation": {
            "disposition": "unresolved",
            "inspectability_mode": "unresolved",
            "derivation_summary": (
                "Stage and derivation inspectability have not yet been reviewed under "
                "the WP1 contract."
            ),
            "stages": [],
            "references": [source_reference],
        },
        "semantics": {
            name: _unresolved_disclosure(name.replace("_", " ").capitalize())
            for name in SEMANTIC_FIELDS
        },
        "evidence": {
            "disposition": "unresolved",
            "classes": ["unresolved"],
            **{
                name: _unresolved_disclosure(name.replace("_", " ").capitalize())
                for name in EVIDENCE_DISCLOSURES
            },
            "receipts": [],
            "notes": "No evidence class or release-bound receipt is admitted in WP1.",
        },
        "residual": {
            "disposition": "unresolved",
            "metric": None,
            "unit": None,
            "observed_result": None,
            "tolerance_or_invariant": None,
            "rationale": (
                "WP1 does not assume that this surface requires a numeric residual; "
                "the reviewed disposition remains unresolved."
            ),
            "receipt_references": [],
        },
        "release_identity": {
            "engine_version": engine_version,
            "inventory_fingerprint_sha256": inventory_fingerprint,
            "source_revision": None,
            "verification_status": "unresolved",
            "last_verified_on": None,
            "receipt_references": [],
        },
        "public_exposure": {
            "disposition": "unresolved",
            "modes": ["unresolved"],
            "references": [],
            "notes": (
                "Embedded, paired-endpoint, generated-documentation, or source-only "
                "exposure has not yet been reviewed."
            ),
        },
        "notes": [
            "Unresolved is visible and is not a pass, partial pass, or failure.",
        ],
    }


def _inventory_references(
    row: Mapping[str, Any],
    *,
    engine_version: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source = _reference(
        "source",
        f"{row['source_path']}#L{row['source_line']}",
        "Owning public transport source for this structural admission.",
        engine_version,
    )
    documents = [
        _reference(
            "documentation",
            str(path),
            "Inventory-linked documentation reviewed as a semantic lead; scope is limited to its text.",
            engine_version,
        )
        for path in row.get("documentation_paths", [])
    ]
    tests = [
        _reference(
            "test",
            str(path),
            "Inventory-linked test source reviewed as an evidence lead; it is not an exact release receipt.",
            engine_version,
        )
        for path in row.get("test_paths", [])
    ]
    return documents, tests, source


def _admitted_entry(
    row: Mapping[str, Any],
    admission: Mapping[str, Any],
    *,
    engine_version: str,
    inventory_fingerprint: str,
) -> dict[str, Any]:
    entry = _unresolved_entry(
        row,
        engine_version=engine_version,
        inventory_fingerprint=inventory_fingerprint,
    )
    contract_kind = str(admission["contract_kind"])
    template = ADMISSION_CONTRACTS[contract_kind]
    documents, tests, source = _inventory_references(
        row,
        engine_version=engine_version,
    )
    semantic_references = [source, *documents]
    evidence_classes = [str(value) for value in admission["evidence_classes"]]
    entry["conformance_status"] = "partial"
    entry["stage_derivation"] = {
        "disposition": "documented",
        "inspectability_mode": template["inspectability_mode"],
        "derivation_summary": template["summary"],
        "stages": [
            {
                "stage_id": contract_kind.replace("_", "-"),
                "label": template["stage_label"],
                "operation": template["operation"],
                "inputs": [str(row.get("request_schema", "typed request"))],
                "outputs": [str(row.get("response_schema", "typed response"))],
                "corrections": [
                    "Only corrections explicitly carried by the response or linked standard are admitted."
                ],
                "references": semantic_references,
            }
        ],
        "references": semantic_references,
    }
    entry["semantics"] = {
        name: {
            "disposition": "partial",
            "values": list(template["semantic_values"][name]),
            "references": semantic_references,
            "notes": (
                "Structurally reviewed for this admitted exemplar. A partial disposition "
                "does not generalize beyond the named route, response fields, and references."
            ),
        }
        for name in SEMANTIC_FIELDS
    }
    entry["evidence"] = {
        "disposition": "partial",
        "classes": evidence_classes,
        "authority_comparator": _unresolved_disclosure("Authority comparator"),
        "corpus": _unresolved_disclosure("Release-bound corpus"),
        "metric": _unresolved_disclosure("Release-bound metric"),
        "tolerance_or_invariant": {
            "disposition": "partial",
            "values": [
                "Typed response invariants and doctrine/source constraints are exercised by the linked test sources."
            ],
            "references": [*tests, *documents],
            "notes": "These are candidate evidence sources, not a replayed exact-release receipt.",
        },
        "observed_result": _unresolved_disclosure("Release-bound observed result"),
        "exclusions": {
            "disposition": "documented",
            "values": [
                "No external-authority accuracy result, universal family coverage, or current-release numerical residual is claimed by this structural admission."
            ],
            "references": [source],
            "notes": "The admission is deliberately narrower than full Light Box conformance.",
        },
        "receipts": [],
        "notes": (
            "Existing test and documentation sources support structural review, but no "
            "replayed exact-release receipt has yet been admitted."
        ),
    }
    entry["residual"] = {
        "disposition": "unresolved",
        "metric": None,
        "unit": None,
        "observed_result": None,
        "tolerance_or_invariant": None,
        "rationale": (
            "A structural exemplar does not establish the appropriate residual class or "
            "an observed exact-release result. No numeric residual is invented."
        ),
        "receipt_references": [],
    }
    entry["release_identity"] = {
        "engine_version": engine_version,
        "inventory_fingerprint_sha256": inventory_fingerprint,
        "source_revision": None,
        "verification_status": "not_verified",
        "last_verified_on": None,
        "receipt_references": [],
    }
    entry["public_exposure"] = {
        "disposition": "partial",
        "modes": list(template["public_modes"]),
        "references": semantic_references,
        "notes": (
            "The named source and response vessel establish current-source exposure. "
            "Exact released-artifact identity remains unverified."
        ),
    }
    entry["notes"] = [
        f"Stage 2 structural exemplar admitted through {contract_kind!r}.",
        "Partial is not conformant; residual, authority/corpus, and exact release identity remain unresolved.",
    ]
    return entry


def load_admissions(inventory: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    payload = _load_json(ADMISSIONS_PATH)
    if payload.get("schema_version") != "moira.lightbox-conformance-admissions/v1":
        raise LightBoxConformanceError("unsupported Light Box admissions schema")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise LightBoxConformanceError("Light Box admissions entries must be an array")
    inventory_rows = {
        str(row["surface_id"]): row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    result: dict[str, Mapping[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise LightBoxConformanceError(f"admission {index} must be an object")
        surface_id = str(entry.get("surface_id", ""))
        if surface_id in result:
            raise LightBoxConformanceError(f"duplicate admission: {surface_id}")
        row = inventory_rows.get(surface_id)
        if row is None:
            raise LightBoxConformanceError(
                f"admission is outside current inventory: {surface_id}"
            )
        if row["alias_of"] is not None:
            raise LightBoxConformanceError(
                f"admission must name a canonical surface: {surface_id}"
            )
        contract_kind = str(entry.get("contract_kind", ""))
        if contract_kind not in ADMISSION_CONTRACTS:
            raise LightBoxConformanceError(
                f"unsupported admission contract {contract_kind!r}: {surface_id}"
            )
        classes = entry.get("evidence_classes")
        if not isinstance(classes, list) or not classes or "unresolved" in classes:
            raise LightBoxConformanceError(
                f"admission needs bounded evidence classes: {surface_id}"
            )
        if not row.get("documentation_paths") or not row.get("test_paths"):
            raise LightBoxConformanceError(
                f"structural exemplar lacks inventory documentation/test leads: {surface_id}"
            )
        result[surface_id] = entry
    return result


def _complete_counter(
    values: Sequence[str], vocabulary: Sequence[str]
) -> dict[str, int]:
    counts = Counter(values)
    return {name: counts.get(name, 0) for name in vocabulary}


def _summary(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    canonical = [row for row in entries if row["entry_role"] == "canonical"]
    return {
        "entries_total": len(entries),
        "canonical_entries": len(canonical),
        "alias_entries": len(entries) - len(canonical),
        "canonical_by_status": _complete_counter(
            [str(row["conformance_status"]) for row in canonical],
            CONFORMANCE_STATUSES,
        ),
        "all_entries_by_status": _complete_counter(
            [str(row["conformance_status"]) for row in entries],
            CONFORMANCE_STATUSES,
        ),
        "canonical_by_residual_disposition": _complete_counter(
            [str(row["residual"]["disposition"]) for row in canonical],
            RESIDUAL_DISPOSITIONS,
        ),
    }


def build_manifest(inventory: Mapping[str, Any]) -> dict[str, Any]:
    engine_version = str(inventory["engine_version"])
    fingerprint = str(inventory["surface_fingerprint_sha256"])
    admitted_rows = [
        row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    ]
    admissions = load_admissions(inventory)
    entries = []
    for row in admitted_rows:
        admission = admissions.get(str(row["surface_id"]))
        if admission is None:
            entry = _unresolved_entry(
                row,
                engine_version=engine_version,
                inventory_fingerprint=fingerprint,
            )
        else:
            entry = _admitted_entry(
                row,
                admission,
                engine_version=engine_version,
                inventory_fingerprint=fingerprint,
            )
        entries.append(entry)
    entries.sort(key=lambda row: row["surface_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "inventory_schema_version": str(inventory["schema_version"]),
        "classification_version": str(inventory["classification_version"]),
        "engine_version": engine_version,
        "inventory_fingerprint_sha256": fingerprint,
        "generated_by": GENERATOR_PATH,
        "inventory_path": _relative(INVENTORY_PATH),
        "scope_rule": (
            "Every LB-WP0 in-scope surface appears exactly once. Alias rows remain "
            "visible but only canonical rows contribute to conformance totals."
        ),
        "limitations": [
            "The schema baseline admits no calculation as conformant; bounded structural exemplars may be partial only.",
            "A source pointer establishes ownership only, not stage transparency, numerical validation, or documentation sufficiency.",
            "Unresolved is an explicit visible state and must never be aggregated as conformant, partial, or not applicable.",
            "A partial structural admission is not an exact-release verification and cannot supply a missing residual, authority, or corpus result.",
        ],
        "summary": _summary(entries),
        "entries": entries,
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_manifest_semantics(
    manifest: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> list[str]:
    """Apply cross-field and inventory invariants beyond structural schema."""
    errors: list[str] = []
    inventory_rows = {
        str(row["surface_id"]): row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        return ["$.entries: must be an array before semantic validation"]

    entry_ids = [str(row.get("surface_id")) for row in entries if isinstance(row, dict)]
    if len(entry_ids) != len(set(entry_ids)):
        errors.append("$.entries: duplicate surface IDs")
    missing = sorted(set(inventory_rows) - set(entry_ids))
    unexpected = sorted(set(entry_ids) - set(inventory_rows))
    if missing:
        errors.append(f"$.entries: missing in-scope inventory IDs: {missing[:5]}")
    if unexpected:
        errors.append(
            f"$.entries: contains non-admitted inventory IDs: {unexpected[:5]}"
        )

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        path = f"$.entries[{index}]"
        surface_id = str(entry.get("surface_id"))
        source = inventory_rows.get(surface_id)
        if source is None:
            continue
        expected_role = "alias" if source["alias_of"] is not None else "canonical"
        comparisons = {
            "canonical_surface_id": source["canonical_id"],
            "entry_role": expected_role,
            "surface_kind": source["surface_kind"],
        }
        for field, expected in comparisons.items():
            if entry.get(field) != expected:
                errors.append(f"{path}.{field}: does not match LB-WP0 inventory")
        ownership = entry.get("ownership", {})
        if isinstance(ownership, dict) and (
            ownership.get("source_path") != source["source_path"]
            or ownership.get("source_line") != source["source_line"]
        ):
            errors.append(f"{path}.ownership: does not match LB-WP0 inventory")

        release = entry.get("release_identity", {})
        if isinstance(release, dict):
            if release.get("engine_version") != manifest.get("engine_version"):
                errors.append(f"{path}.release_identity.engine_version: manifest drift")
            if release.get("inventory_fingerprint_sha256") != manifest.get(
                "inventory_fingerprint_sha256"
            ):
                errors.append(
                    f"{path}.release_identity.inventory_fingerprint_sha256: manifest drift"
                )
            if release.get("verification_status") == "verified":
                if not _nonempty(release.get("source_revision")):
                    errors.append(
                        f"{path}.release_identity: verified row needs revision"
                    )
                if not _nonempty(release.get("last_verified_on")):
                    errors.append(f"{path}.release_identity: verified row needs date")
                if not release.get("receipt_references"):
                    errors.append(
                        f"{path}.release_identity: verified row needs receipt"
                    )

        residual = entry.get("residual", {})
        if isinstance(residual, dict):
            disposition = residual.get("disposition")
            resolved = {"numeric", "invariant", "doctrine_source", "regression_parity"}
            if disposition in resolved:
                required = ("metric", "observed_result", "tolerance_or_invariant")
                if any(not _nonempty(residual.get(field)) for field in required):
                    errors.append(
                        f"{path}.residual: resolved disposition lacks measurement"
                    )
                if disposition == "numeric" and not _nonempty(residual.get("unit")):
                    errors.append(f"{path}.residual: numeric disposition needs unit")
                if not residual.get("receipt_references"):
                    errors.append(
                        f"{path}.residual: resolved disposition needs receipt"
                    )

        evidence = entry.get("evidence", {})
        if isinstance(evidence, dict):
            disposition = evidence.get("disposition")
            classes = evidence.get("classes")
            if disposition == "unresolved" and classes != ["unresolved"]:
                errors.append(
                    f"{path}.evidence: unresolved must be explicit and exclusive"
                )
            if disposition == "not_applicable" and classes != ["not_applicable"]:
                errors.append(
                    f"{path}.evidence: not_applicable must be explicit and exclusive"
                )
            if disposition == "verified" and not evidence.get("receipts"):
                errors.append(f"{path}.evidence: verified evidence needs a receipt")

        exposure = entry.get("public_exposure", {})
        if isinstance(exposure, dict):
            disposition = exposure.get("disposition")
            modes = exposure.get("modes")
            if disposition == "unresolved" and modes != ["unresolved"]:
                errors.append(f"{path}.public_exposure: unresolved must be explicit")
            if disposition == "not_applicable" and modes != ["not_applicable"]:
                errors.append(
                    f"{path}.public_exposure: not_applicable must be explicit"
                )

        status = entry.get("conformance_status")
        if status == "conformant":
            unresolved_markers = (
                entry.get("stage_derivation", {}).get("disposition") == "unresolved",
                entry.get("evidence", {}).get("disposition") == "unresolved",
                entry.get("residual", {}).get("disposition") == "unresolved",
                entry.get("release_identity", {}).get("verification_status")
                != "verified",
                entry.get("public_exposure", {}).get("disposition") == "unresolved",
            )
            if any(unresolved_markers):
                errors.append(f"{path}: conformant row contains unresolved evidence")

    expected_summary = _summary(entries)
    if manifest.get("summary") != expected_summary:
        errors.append("$.summary: does not match entry-derived counts")
    if manifest.get("engine_version") != inventory.get("engine_version"):
        errors.append("$.engine_version: does not match LB-WP0 inventory")
    if manifest.get("inventory_fingerprint_sha256") != inventory.get(
        "surface_fingerprint_sha256"
    ):
        errors.append("$.inventory_fingerprint_sha256: does not match LB-WP0 inventory")
    return errors


def validate_manifest(
    manifest: Mapping[str, Any],
    inventory: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> list[str]:
    return validate_json_schema_instance(
        manifest, schema
    ) + validate_manifest_semantics(
        manifest,
        inventory,
    )


def render_json(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(manifest: Mapping[str, Any]) -> str:
    summary = manifest["summary"]
    status = summary["canonical_by_status"]
    residual = summary["canonical_by_residual_disposition"]
    lines = [
        "# Light Box Conformance Manifest",
        "",
        f"> Generated by `{GENERATOR_PATH}`. Do not edit by hand.",
        "",
        f"- Schema: `{manifest['schema_version']}`",
        f"- Engine version: `{manifest['engine_version']}`",
        f"- Inventory fingerprint: `{manifest['inventory_fingerprint_sha256']}`",
        f"- Canonical schema: `{_relative(SCHEMA_PATH)}`",
        "",
        "## Boundary",
        "",
        "This LB-WP1 artifact defines the evidence fields required for every admitted calculation. It does **not** certify a calculation. Every row begins `unresolved`; later work must admit evidence row by row. A source pointer proves ownership only.",
        "",
        "Aliases remain visible but do not inflate the canonical denominator. Numeric residuals are required only when `numeric` is the reviewed disposition; categorical techniques can use invariant, doctrine/source, regression/parity, or not-applicable dispositions with explicit rationale and receipts.",
        "",
        "## Current status",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| All entries | {summary['entries_total']} |",
        f"| Canonical entries | {summary['canonical_entries']} |",
        f"| Alias entries | {summary['alias_entries']} |",
        f"| Canonical conformant | {status['conformant']} |",
        f"| Canonical partial | {status['partial']} |",
        f"| Canonical not applicable | {status['not_applicable']} |",
        f"| Canonical unresolved | {status['unresolved']} |",
        "",
        "### Residual dispositions (canonical entries)",
        "",
        "| Disposition | Count |",
        "|---|---:|",
    ]
    for name in RESIDUAL_DISPOSITIONS:
        lines.append(f"| `{name}` | {residual[name]} |")

    lines.extend(
        [
            "",
            "## Required per-surface contract",
            "",
            "Each entry must record:",
            "",
            "- stage/derivation disposition, inspectability mode, ordered stages, and references;",
            "- inputs, units, reference frame, origin, timescale, corrections, policies/defaults, fallbacks, and refusal behavior;",
            "- evidence class, authority/comparator, corpus, metric, tolerance/invariant, observed result, exclusions, and receipts;",
            "- residual disposition and any applicable measurement, unit, tolerance/invariant, rationale, and receipt;",
            "- engine/inventory identity, source revision, verification status/date, and release receipts; and",
            "- public exposure through embedded results, paired reduction endpoints, generated documentation, source-only access, or an explicit unresolved/N/A disposition.",
            "",
            "The schema rejects missing required fields and unknown fields. Cross-field validation additionally prevents a `conformant` row from retaining unresolved core evidence and requires release identity plus receipts for verified rows.",
            "",
            "## Entries",
            "",
            "| Surface ID | Role | Kind | Status | Inspectability | Residual | Exposure | Release | Owner |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for entry in manifest["entries"]:
        owner = entry["ownership"]
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{_escape(entry['surface_id'])}`",
                    f"`{entry['entry_role']}`",
                    f"`{entry['surface_kind']}`",
                    f"`{entry['conformance_status']}`",
                    f"`{entry['stage_derivation']['inspectability_mode']}`",
                    f"`{entry['residual']['disposition']}`",
                    f"`{','.join(entry['public_exposure']['modes'])}`",
                    f"`{entry['release_identity']['verification_status']}`",
                    f"`{owner['source_path']}:{owner['source_line']}`",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Next Light Box layer",
            "",
            "LB-WP2 must admit the strongest existing exemplars against this exact contract. Until a row receives reviewed, release-bound evidence, `unresolved` remains the truthful status.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _check_file(path: Path, expected: str) -> bool:
    return path.is_file() and path.read_text(encoding="utf-8") == expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the generated conformance artifacts are stale",
    )
    args = parser.parse_args()

    try:
        inventory = load_current_inventory()
        schema = _load_json(SCHEMA_PATH)
        manifest = build_manifest(inventory)
        errors = validate_manifest(manifest, inventory, schema)
        if errors:
            raise LightBoxConformanceError(
                "manifest validation failed:\n- " + "\n- ".join(errors[:25])
            )
        json_text = render_json(manifest)
        markdown_text = render_markdown(manifest)
        if args.check:
            stale = [
                _relative(path)
                for path, expected in (
                    (MANIFEST_PATH, json_text),
                    (MARKDOWN_PATH, markdown_text),
                )
                if not _check_file(path, expected)
            ]
            if stale:
                raise LightBoxConformanceError(
                    "Light Box conformance manifest is stale: " + ", ".join(stale)
                )
            print("Light Box conformance schema and manifest are current.")
            return 0

        _write_atomic(MANIFEST_PATH, json_text)
        _write_atomic(MARKDOWN_PATH, markdown_text)
        print(f"Generated {_relative(MANIFEST_PATH)}.")
        print(f"Generated {_relative(MARKDOWN_PATH)}.")
        return 0
    except LightBoxConformanceError as exc:
        print(f"Light Box conformance generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
