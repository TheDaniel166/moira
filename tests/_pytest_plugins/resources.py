"""Typed planetary and supplemental small-body test-resource policy."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import stat

import pytest

from ._common import _is_name_surrogate_reparse
from ._state import (
    _RESOURCE_ITEM_RECEIPT_KEY,
    _RESOURCE_ITEM_REQUIREMENT_KEY,
    _RESOURCE_RECEIPTS_KEY,
    _RESOURCE_RESOLVER_KEY,
    _SMALL_BODY_RESOURCE_RECEIPTS_KEY,
    _XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY,
    _XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY,
)


def _resource_policy_module():
    """Import the tests-only resource policy only for selected consumers."""

    return importlib.import_module("support.resource_policy")


def _small_body_resource_policy_module():
    """Import supplemental admission policy only for its explicit fixture."""

    return importlib.import_module("support.small_body_resource_policy")


def _planetary_resource_resolver(config):
    resolver = config.stash.get(_RESOURCE_RESOLVER_KEY, None)
    if resolver is not None:
        return resolver
    policy = _resource_policy_module()
    try:
        candidate = policy.discover_planetary_kernel_candidate()
    except Exception as exc:
        resolver = policy.PlanetaryResourceResolver(
            None,
            discovery_failure=(
                type(exc).__name__,
                f"planetary-kernel discovery failed: {exc}",
            ),
        )
    else:
        resolver = policy.PlanetaryResourceResolver(candidate)
    config.stash[_RESOURCE_RESOLVER_KEY] = resolver
    return resolver


def _planetary_requirement_for_item(item):
    cached = item.stash.get(_RESOURCE_ITEM_REQUIREMENT_KEY, None)
    if cached is not None:
        return cached

    markers = tuple(item.iter_markers(name="requires_ephemeris"))
    if not markers:
        return None

    policy = _resource_policy_module()
    requirements = []
    for marker in markers:
        if marker.args:
            raise pytest.UsageError(
                f"{item.nodeid}: requires_ephemeris accepts keyword "
                "capability fields only"
            )
        try:
            requirement = policy.PlanetaryKernelRequirement.from_mapping(
                marker.kwargs
            )
        except policy.ResourceContractError as exc:
            raise pytest.UsageError(
                f"{item.nodeid}: invalid requires_ephemeris contract: {exc}"
            ) from exc
        requirements.append(requirement)

    if len(markers) != 1:
        rendered = ", ".join(
            requirement.render()
            for requirement in requirements
        )
        raise pytest.UsageError(
            f"{item.nodeid}: duplicate or conflicting "
            "requires_ephemeris contracts: "
            + rendered
        )

    requirement = requirements[0]
    item.stash[_RESOURCE_ITEM_REQUIREMENT_KEY] = requirement
    return requirement


def _record_planetary_resource_receipt(config, nodeid: str, receipt) -> None:
    receipts = config.stash.get(_RESOURCE_RECEIPTS_KEY, None)
    if receipts is None:
        receipts = {}
        config.stash[_RESOURCE_RECEIPTS_KEY] = receipts
    receipts[nodeid] = receipt


def _record_planetary_live_failure(
    config,
    *,
    nodeid: str,
    stage: str,
    admitted_receipt,
    exc: Exception,
):
    """Record post-probe acquisition/teardown failure before propagating it."""

    policy = _resource_policy_module()
    failure = policy.PlanetaryKernelReceipt(
        name="planetary-kernel-live",
        disposition=policy.ResourceDisposition.FAILURE,
        requirement=admitted_receipt.requirement,
        candidate=admitted_receipt.candidate,
        capability=admitted_receipt.capability,
        reason=f"{stage} failed after capability admission: {exc}",
        failure_type=type(exc).__name__,
    )
    _record_planetary_resource_receipt(
        config,
        f"{nodeid}::{stage}",
        failure,
    )
    return failure


def _planetary_receipt_for_item(item):
    cached = item.stash.get(_RESOURCE_ITEM_RECEIPT_KEY, None)
    if cached is not None:
        return cached

    requirement = _planetary_requirement_for_item(item)
    if requirement is None:
        raise pytest.UsageError(
            f"{item.nodeid}: planetary resource requested without a "
            "requires_ephemeris contract"
        )
    receipt = _planetary_resource_resolver(item.config).resolve(requirement)
    item.stash[_RESOURCE_ITEM_RECEIPT_KEY] = receipt
    _record_planetary_resource_receipt(
        item.config,
        item.nodeid,
        receipt,
    )
    return receipt


def _enforce_planetary_resource_receipt(receipt) -> None:
    policy = _resource_policy_module()
    if receipt.disposition is policy.ResourceDisposition.RUN:
        return
    if receipt.disposition is policy.ResourceDisposition.SKIP:
        pytest.skip(receipt.render())
    pytest.fail(receipt.render(), pytrace=False)


def _record_small_body_resource_receipt(
    config,
    nodeid: str,
    receipt,
) -> None:
    receipts = config.stash.get(_SMALL_BODY_RESOURCE_RECEIPTS_KEY, None)
    if receipts is None:
        receipts = {}
        config.stash[_SMALL_BODY_RESOURCE_RECEIPTS_KEY] = receipts
    receipts[nodeid] = receipt


def _enforce_small_body_resource_receipt(receipt) -> None:
    policy = _small_body_resource_policy_module()
    if (
        receipt.disposition
        is policy.SmallBodyResourceDisposition.RUN
    ):
        return
    if (
        receipt.disposition
        is policy.SmallBodyResourceDisposition.SKIP
    ):
        pytest.skip(receipt.render())
    pytest.fail(receipt.render(), pytrace=False)


_EPHEMERIS_FIXTURES = {
    "configured_global_reader",
    "eclipse_calculator",
    "moira_engine",
    "natal_chart",
    "natal_houses",
    "planetary_kernel_path",
    "planetary_kernel_receipt",
    "planetary_reader",
    "reader",
    "small_body_reader_context",
    "small_body_reader_pool",
}


@pytest.hookimpl
def pytest_runtest_setup(item):
    """Enforce resource policy after skip admission and before fixtures.

    Pytest's skipping plugin is a ``tryfirst`` implementation, so it owns the
    single evaluation of dynamic skip/xfail conditions.  This ordinary
    conftest hook then runs before pytest's earlier-registered fixture-setup
    implementation.  Do not pre-evaluate marks here: stateful string
    conditions must retain pytest's exactly-once setup semantics.
    """

    requirement = _planetary_requirement_for_item(item)
    if requirement is None:
        return
    receipt = _planetary_receipt_for_item(item)
    _enforce_planetary_resource_receipt(receipt)


def _session_planetary_receipt(request, *, nodeid: str):
    policy = _resource_policy_module()
    receipt = _planetary_resource_resolver(request.config).resolve(
        policy.PlanetaryKernelRequirement()
    )
    _record_planetary_resource_receipt(
        request.config,
        nodeid,
        receipt,
    )
    _enforce_planetary_resource_receipt(receipt)
    return receipt


_XDIST_PLANETARY_RESOURCE_REPORT_KEY = (
    "moira_planetary_resource_report_v1"
)


_XDIST_SMALL_BODY_RESOURCE_REPORT_KEY = (
    "moira_small_body_resource_report_v1"
)


def _planetary_resource_summary(details):
    disposition_counts = {
        "run": 0,
        "skip": 0,
        "failure": 0,
    }
    identities: set[str] = set()
    for detail in details.values():
        disposition = detail["disposition"]
        disposition_counts[disposition] += 1
        identity = detail["identity"]
        if identity is not None:
            identities.add(identity)
    return {
        "receipts": len(details),
        **disposition_counts,
        "identities": sorted(identities),
    }


def _serialize_planetary_requirement(requirement) -> dict[str, object]:
    return {
        "product": requirement.product,
        "content_identity": requirement.content_identity,
        "interval": (
            None
            if requirement.interval is None
            else list(requirement.interval)
        ),
        "bodies": sorted(requirement.bodies),
        "target_center_pairs": [
            {
                "target_naif_id": route.target_naif_id,
                "center_naif_id": route.center_naif_id,
            }
            for route in sorted(requirement.target_center_pairs)
        ],
        "frame": requirement.frame,
        "segment_types": sorted(requirement.segment_types),
        "native_capability": requirement.native_capability,
    }


def _serialize_planetary_candidate(candidate) -> dict[str, object] | None:
    if candidate is None:
        return None
    fingerprint = candidate.fingerprint
    return {
        "path": str(candidate.path),
        "explicit": candidate.explicit,
        "source": candidate.source,
        "fingerprint": (
            None
            if fingerprint is None
            else {
                "resolved_path": str(fingerprint.resolved_path),
                "size": fingerprint.size,
                "mtime_ns": fingerprint.mtime_ns,
                "device_id": fingerprint.device_id,
                "file_id": fingerprint.file_id,
            }
        ),
    }


def _planetary_fingerprint_metadata(
    metadata: os.stat_result,
) -> tuple[int, int, int | None, int | None]:
    raw_file_id = getattr(metadata, "st_ino", None)
    raw_device_id = getattr(metadata, "st_dev", None)
    if (
        type(raw_file_id) is int
        and raw_file_id > 0
        and type(raw_device_id) is int
        and raw_device_id >= 0
    ):
        file_id = raw_file_id
        device_id = raw_device_id
    else:
        file_id = None
        device_id = None
    return (
        metadata.st_size,
        metadata.st_mtime_ns,
        device_id,
        file_id,
    )


def _planetary_content_sha256(
    fingerprint: dict[str, object],
) -> str:
    path = Path(str(fingerprint["resolved_path"]))
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.lstat()
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(
            f"cannot content-bind planetary resource {path}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise RuntimeError(
            "planetary resource content binding requires a real regular "
            f"file: {resolved}"
        )
    expected_path = Path(str(fingerprint["resolved_path"]))
    if os.path.normcase(str(resolved)) != os.path.normcase(
        str(expected_path)
    ):
        raise RuntimeError(
            "planetary resource resolved path changed before content binding: "
            f"{expected_path} -> {resolved}"
        )
    expected_metadata = (
        fingerprint["size"],
        fingerprint["mtime_ns"],
        fingerprint["device_id"],
        fingerprint["file_id"],
    )
    if _planetary_fingerprint_metadata(metadata) != expected_metadata:
        raise RuntimeError(
            "planetary resource fingerprint changed before content binding: "
            f"{resolved}"
        )

    digest = hashlib.sha256()
    try:
        with resolved.open("rb") as source:
            opened_metadata = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or _is_name_surrogate_reparse(opened_metadata)
                or _planetary_fingerprint_metadata(opened_metadata)
                != expected_metadata
            ):
                raise RuntimeError(
                    "planetary resource changed during secure content open: "
                    f"{resolved}"
                )
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
            final_metadata = os.fstat(source.fileno())
    except RuntimeError:
        raise
    except OSError as exc:
        raise RuntimeError(
            f"cannot hash planetary resource {resolved}: {exc}"
        ) from exc
    if (
        _planetary_fingerprint_metadata(final_metadata)
        != expected_metadata
        or _planetary_fingerprint_metadata(resolved.lstat())
        != expected_metadata
    ):
        raise RuntimeError(
            "planetary resource fingerprint changed during content binding: "
            f"{resolved}"
        )
    return digest.hexdigest()


def _bind_planetary_content_digests(
    report: dict[str, object],
) -> dict[str, object]:
    details = report["details"]
    assert isinstance(details, dict)
    digests: dict[tuple[object, ...], str] = {}
    for detail in details.values():
        assert isinstance(detail, dict)
        candidate = detail["candidate"]
        if candidate is None:
            continue
        assert isinstance(candidate, dict)
        fingerprint = candidate["fingerprint"]
        if fingerprint is None:
            continue
        assert isinstance(fingerprint, dict)
        key = (
            fingerprint["resolved_path"],
            fingerprint["size"],
            fingerprint["mtime_ns"],
            fingerprint["device_id"],
            fingerprint["file_id"],
        )
        digest = digests.get(key)
        if digest is None:
            digest = _planetary_content_sha256(fingerprint)
            digests[key] = digest
        fingerprint["content_sha256"] = digest
    return report


def _serialize_planetary_capability(capability) -> dict[str, object] | None:
    if capability is None:
        return None
    return {
        "product": capability.product,
        "content_identity": capability.content_identity,
        "summary_label": capability.summary_label,
        "planetary_ephemeris": capability.planetary_ephemeris,
        "lunar_ephemeris": capability.lunar_ephemeris,
        "segments": [
            {
                "target_naif_id": segment.route.target_naif_id,
                "center_naif_id": segment.route.center_naif_id,
                "frame": segment.frame,
                "segment_type": segment.segment_type,
                "start_jd": segment.start_jd,
                "end_jd": segment.end_jd,
            }
            for segment in capability.segments
        ],
        "bodies": sorted(capability.bodies),
        "target_center_pairs": [
            {
                "target_naif_id": route.target_naif_id,
                "center_naif_id": route.center_naif_id,
            }
            for route in sorted(capability.target_center_pairs)
        ],
        "frames": sorted(capability.frames),
        "segment_types": sorted(capability.segment_types),
        "native_capability": capability.native_capability,
    }


def _serialize_planetary_resource_report(config):
    receipts = config.stash.get(_RESOURCE_RECEIPTS_KEY, {})
    details = {}
    for nodeid, receipt in sorted(receipts.items()):
        identity = (
            receipt.capability.content_identity
            if receipt.capability is not None
            else None
        )
        details[nodeid] = {
            "disposition": receipt.disposition.value,
            "identity": identity,
            "requirement": _serialize_planetary_requirement(
                receipt.requirement
            ),
            "candidate": _serialize_planetary_candidate(
                receipt.candidate
            ),
            "capability": _serialize_planetary_capability(
                receipt.capability
            ),
            "reason": receipt.reason,
            "failure_type": receipt.failure_type,
            "rendered": receipt.render(),
        }

    resolver = config.stash.get(_RESOURCE_RESOLVER_KEY, None)
    probe_count = (
        getattr(resolver, "probe_count", 0)
        if resolver is not None
        else 0
    )
    return {
        "version": 1,
        "summary": _planetary_resource_summary(details),
        "details": details,
        "probe_count": probe_count,
    }


def _empty_planetary_resource_report():
    details = {}
    return {
        "version": 1,
        "summary": _planetary_resource_summary(details),
        "details": details,
        "probe_count": 0,
    }


def _normalize_planetary_routes(
    value: object,
    *,
    source: str,
) -> list[dict[str, int]]:
    if not isinstance(value, list):
        raise pytest.UsageError(
            f"{source} returned invalid planetary-resource routes"
        )
    routes: list[dict[str, int]] = []
    for route in value:
        if (
            not isinstance(route, dict)
            or set(route) != {"target_naif_id", "center_naif_id"}
            or type(route["target_naif_id"]) is not int
            or type(route["center_naif_id"]) is not int
        ):
            raise pytest.UsageError(
                f"{source} returned an invalid planetary-resource route"
            )
        routes.append(
            {
                "target_naif_id": route["target_naif_id"],
                "center_naif_id": route["center_naif_id"],
            }
        )
    if routes != sorted(
        routes,
        key=lambda route: (
            route["target_naif_id"],
            route["center_naif_id"],
        ),
    ) or len(
        {
            (route["target_naif_id"], route["center_naif_id"])
            for route in routes
        }
    ) != len(routes):
        raise pytest.UsageError(
            f"{source} returned noncanonical planetary-resource routes"
        )
    return routes


def _normalize_planetary_integer_set(
    value: object,
    *,
    source: str,
    positive: bool = False,
) -> list[int]:
    if (
        not isinstance(value, list)
        or any(
            type(item) is not int or (positive and item <= 0)
            for item in value
        )
        or value != sorted(set(value))
    ):
        raise pytest.UsageError(
            f"{source} returned a noncanonical planetary integer set"
        )
    return list(value)


def _normalize_planetary_requirement(
    value: object,
    *,
    source: str,
) -> dict[str, object]:
    fields = {
        "product",
        "content_identity",
        "interval",
        "bodies",
        "target_center_pairs",
        "frame",
        "segment_types",
        "native_capability",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise pytest.UsageError(
            f"{source} returned an invalid planetary-resource requirement"
        )
    for field in ("product", "content_identity"):
        if value[field] is not None and (
            type(value[field]) is not str or not value[field]
        ):
            raise pytest.UsageError(
                f"{source} returned invalid planetary requirement text"
            )
    interval = value["interval"]
    if interval is not None and (
        not isinstance(interval, list)
        or len(interval) != 2
        or any(
            type(bound) not in {int, float}
            or not math.isfinite(float(bound))
            for bound in interval
        )
        or float(interval[0]) > float(interval[1])
    ):
        raise pytest.UsageError(
            f"{source} returned an invalid planetary requirement interval"
        )
    if value["frame"] is not None and type(value["frame"]) is not int:
        raise pytest.UsageError(
            f"{source} returned an invalid planetary requirement frame"
        )
    if (
        value["native_capability"] is not None
        and type(value["native_capability"]) is not bool
    ):
        raise pytest.UsageError(
            f"{source} returned invalid planetary native requirement"
        )
    return {
        "product": value["product"],
        "content_identity": value["content_identity"],
        "interval": None if interval is None else list(interval),
        "bodies": _normalize_planetary_integer_set(
            value["bodies"],
            source=source,
        ),
        "target_center_pairs": _normalize_planetary_routes(
            value["target_center_pairs"],
            source=source,
        ),
        "frame": value["frame"],
        "segment_types": _normalize_planetary_integer_set(
            value["segment_types"],
            source=source,
            positive=True,
        ),
        "native_capability": value["native_capability"],
    }


def _normalize_planetary_candidate(
    value: object,
    *,
    source: str,
) -> dict[str, object] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "explicit", "source", "fingerprint"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["source"]) is not str
        or not value["source"]
        or type(value["explicit"]) is not bool
    ):
        raise pytest.UsageError(
            f"{source} returned an invalid planetary-resource candidate"
        )
    fingerprint = value["fingerprint"]
    normalized_fingerprint = None
    if fingerprint is not None:
        fields = {
            "resolved_path",
            "size",
            "mtime_ns",
            "device_id",
            "file_id",
        }
        if (
            not isinstance(fingerprint, dict)
            or set(fingerprint) != fields
            or type(fingerprint["resolved_path"]) is not str
            or not fingerprint["resolved_path"]
            or type(fingerprint["size"]) is not int
            or fingerprint["size"] < 0
            or type(fingerprint["mtime_ns"]) is not int
            or any(
                value is not None
                and (type(value) is not int or value < 0)
                for value in (
                    fingerprint["device_id"],
                    fingerprint["file_id"],
                )
            )
            or (
                (fingerprint["device_id"] is None)
                != (fingerprint["file_id"] is None)
            )
        ):
            raise pytest.UsageError(
                f"{source} returned an invalid planetary fingerprint"
            )
        normalized_fingerprint = dict(fingerprint)
    return {
        "path": value["path"],
        "explicit": value["explicit"],
        "source": value["source"],
        "fingerprint": normalized_fingerprint,
    }


def _normalize_planetary_capability(
    value: object,
    *,
    source: str,
) -> dict[str, object] | None:
    if value is None:
        return None
    fields = {
        "product",
        "content_identity",
        "summary_label",
        "planetary_ephemeris",
        "lunar_ephemeris",
        "segments",
        "bodies",
        "target_center_pairs",
        "frames",
        "segment_types",
        "native_capability",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or any(
            type(value[field]) is not str or not value[field]
            for field in ("product", "content_identity", "summary_label")
        )
        or any(
            value[field] is not None
            and (type(value[field]) is not str or not value[field])
            for field in ("planetary_ephemeris", "lunar_ephemeris")
        )
        or type(value["native_capability"]) is not bool
        or not isinstance(value["segments"], list)
    ):
        raise pytest.UsageError(
            f"{source} returned an invalid planetary-resource capability"
        )
    segments: list[dict[str, object]] = []
    for segment in value["segments"]:
        if (
            not isinstance(segment, dict)
            or set(segment)
            != {
                "target_naif_id",
                "center_naif_id",
                "frame",
                "segment_type",
                "start_jd",
                "end_jd",
            }
            or any(
                type(segment[field]) is not int
                for field in (
                    "target_naif_id",
                    "center_naif_id",
                    "frame",
                    "segment_type",
                )
            )
            or segment["segment_type"] <= 0
            or any(
                type(segment[field]) not in {int, float}
                or not math.isfinite(float(segment[field]))
                for field in ("start_jd", "end_jd")
            )
            or float(segment["start_jd"]) > float(segment["end_jd"])
        ):
            raise pytest.UsageError(
                f"{source} returned an invalid planetary segment"
            )
        segments.append(dict(segment))
    bodies = _normalize_planetary_integer_set(
        value["bodies"],
        source=source,
    )
    routes = _normalize_planetary_routes(
        value["target_center_pairs"],
        source=source,
    )
    frames = _normalize_planetary_integer_set(
        value["frames"],
        source=source,
    )
    segment_types = _normalize_planetary_integer_set(
        value["segment_types"],
        source=source,
        positive=True,
    )
    derived_bodies = sorted(
        {int(segment["target_naif_id"]) for segment in segments}
    )
    derived_routes = sorted(
        {
            (
                int(segment["target_naif_id"]),
                int(segment["center_naif_id"]),
            )
            for segment in segments
        }
    )
    derived_frames = sorted(
        {int(segment["frame"]) for segment in segments}
    )
    derived_segment_types = sorted(
        {int(segment["segment_type"]) for segment in segments}
    )
    if (
        not segments
        or value["content_identity"]
        != (value["planetary_ephemeris"] or value["summary_label"])
        or bodies != derived_bodies
        or [
            (route["target_naif_id"], route["center_naif_id"])
            for route in routes
        ]
        != derived_routes
        or frames != derived_frames
        or segment_types != derived_segment_types
    ):
        raise pytest.UsageError(
            f"{source} returned contradictory planetary capability evidence"
        )
    return {
        "product": value["product"],
        "content_identity": value["content_identity"],
        "summary_label": value["summary_label"],
        "planetary_ephemeris": value["planetary_ephemeris"],
        "lunar_ephemeris": value["lunar_ephemeris"],
        "segments": segments,
        "bodies": bodies,
        "target_center_pairs": routes,
        "frames": frames,
        "segment_types": segment_types,
        "native_capability": value["native_capability"],
    }


def _merge_planetary_resource_report(target, incoming, *, source: str):
    if (
        not isinstance(incoming, dict)
        or incoming.get("version") != 1
        or not isinstance(incoming.get("details"), dict)
        or not isinstance(incoming.get("summary"), dict)
        or type(incoming.get("probe_count")) is not int
        or incoming["probe_count"] < 0
    ):
        raise pytest.UsageError(
            f"{source} returned an invalid planetary-resource report"
        )

    incoming_details = incoming["details"]
    normalized_details = {}
    for nodeid, detail in incoming_details.items():
        if (
            type(nodeid) is not str
            or not isinstance(detail, dict)
            or set(detail)
            != {
                "disposition",
                "identity",
                "requirement",
                "candidate",
                "capability",
                "reason",
                "failure_type",
                "rendered",
            }
            or detail.get("disposition")
            not in {"run", "skip", "failure"}
            or (
                detail.get("identity") is not None
                and (
                    type(detail.get("identity")) is not str
                    or not detail.get("identity")
                )
            )
            or not isinstance(detail.get("requirement"), dict)
            or (
                detail.get("candidate") is not None
                and not isinstance(detail.get("candidate"), dict)
            )
            or (
                detail.get("capability") is not None
                and not isinstance(detail.get("capability"), dict)
            )
            or type(detail.get("reason")) is not str
            or not detail.get("reason")
            or (
                detail.get("failure_type") is not None
                and (
                    type(detail.get("failure_type")) is not str
                    or not detail.get("failure_type")
                )
            )
            or type(detail.get("rendered")) is not str
            or not detail.get("rendered")
        ):
            raise pytest.UsageError(
                f"{source} returned an invalid planetary-resource detail"
            )
        try:
            normalized = json.loads(
                json.dumps(
                    detail,
                    allow_nan=False,
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
        except (TypeError, ValueError) as exc:
            raise pytest.UsageError(
                f"{source} returned non-JSON planetary-resource evidence"
            ) from exc
        if (
            normalized["disposition"] == "run"
            and (
                normalized["candidate"] is None
                or normalized["capability"] is None
                or normalized["identity"] is None
            )
        ):
            raise pytest.UsageError(
                f"{source} returned capability-free planetary run evidence"
            )
        normalized["requirement"] = _normalize_planetary_requirement(
            normalized["requirement"],
            source=source,
        )
        normalized["candidate"] = _normalize_planetary_candidate(
            normalized["candidate"],
            source=source,
        )
        normalized["capability"] = _normalize_planetary_capability(
            normalized["capability"],
            source=source,
        )
        if normalized["disposition"] == "run" and (
            normalized["failure_type"] is not None
            or normalized["candidate"]["fingerprint"] is None
        ):
            raise pytest.UsageError(
                f"{source} returned contradictory planetary run evidence"
            )
        if (
            normalized["capability"] is not None
            and normalized["identity"]
            != normalized["capability"]["content_identity"]
        ):
            raise pytest.UsageError(
                f"{source} returned contradictory planetary identity evidence"
            )
        if (
            normalized["disposition"] == "skip"
            and normalized["failure_type"] is not None
        ) or (
            normalized["disposition"] == "failure"
            and normalized["failure_type"] is None
        ):
            raise pytest.UsageError(
                f"{source} returned contradictory planetary disposition evidence"
            )
        normalized_details[nodeid] = normalized

    if incoming["summary"] != _planetary_resource_summary(
        normalized_details
    ):
        raise pytest.UsageError(
            f"{source} returned a contradictory planetary-resource summary"
        )

    target_details = target["details"]
    for nodeid, detail in normalized_details.items():
        existing = target_details.get(nodeid)
        if existing is None or existing == detail:
            target_details[nodeid] = detail
            continue

        qualified_nodeid = f"{nodeid} [{source}]"
        suffix = 2
        while qualified_nodeid in target_details:
            qualified_nodeid = f"{nodeid} [{source}#{suffix}]"
            suffix += 1
        target_details[qualified_nodeid] = detail

    target["probe_count"] += incoming["probe_count"]
    target["summary"] = _planetary_resource_summary(target_details)
    return target


def _combined_planetary_resource_report(config):
    combined = _empty_planetary_resource_report()
    worker_report = config.stash.get(
        _XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY,
        None,
    )
    if worker_report is not None:
        _merge_planetary_resource_report(
            combined,
            worker_report,
            source="xdist workers",
        )
    _merge_planetary_resource_report(
        combined,
        _serialize_planetary_resource_report(config),
        source="controller",
    )
    return combined


def _serialize_small_body_resource_report(config):
    receipts = config.stash.get(_SMALL_BODY_RESOURCE_RECEIPTS_KEY, {})
    if not receipts:
        return _empty_small_body_resource_report()
    policy = _small_body_resource_policy_module()
    return policy.small_body_report_from_receipts(receipts)


def _empty_small_body_resource_report():
    return {
        "version": 1,
        "summary": {
            "receipts": 0,
            "run": 0,
            "skip": 0,
            "failure": 0,
            "terminal": 0,
            "identities": [],
            "manifests": 0,
            "shards": 0,
            "bodies": 0,
        },
        "details": {},
    }


def _merge_small_body_resource_report(target, incoming, *, source: str):
    policy = _small_body_resource_policy_module()
    try:
        return policy.merge_small_body_report(
            target,
            incoming,
            source=source,
        )
    except policy.SmallBodyResourceContractError as exc:
        raise pytest.UsageError(str(exc)) from exc


def _combined_small_body_resource_report(config):
    combined = _empty_small_body_resource_report()
    worker_report = config.stash.get(
        _XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY,
        None,
    )
    if worker_report is not None:
        _merge_small_body_resource_report(
            combined,
            worker_report,
            source="xdist workers",
        )
    controller_report = _serialize_small_body_resource_report(config)
    if controller_report["summary"]["receipts"]:
        _merge_small_body_resource_report(
            combined,
            controller_report,
            source="controller",
        )
    return combined

def prepare_item(item) -> None:
    """Freeze resource contracts during collection without touching kernels."""

    if (
        not item.get_closest_marker("requires_ephemeris")
        and _EPHEMERIS_FIXTURES & set(item.fixturenames)
    ):
        item.add_marker(
            pytest.mark.requires_ephemeris(content_identity="DE441")
        )
    _planetary_requirement_for_item(item)


def write_terminal_summary(terminalreporter, config) -> None:
    """Render controller-validated resource receipts."""

    resource_report = _combined_planetary_resource_report(config)
    resource_summary = resource_report["summary"]
    if resource_summary["receipts"]:
        identities = resource_summary["identities"]
        terminalreporter.write_line(
            "  Planetary resource: "
            f"receipts={resource_summary['receipts']}, "
            f"run={resource_summary['run']}, "
            f"skip={resource_summary['skip']}, "
            f"failure={resource_summary['failure']}, "
            f"content_probes={resource_report['probe_count']}, "
            "identities="
            + (
                ",".join(identities)
                if identities
                else "<none>"
            )
        )
        exceptional = [
            (nodeid, detail)
            for nodeid, detail in sorted(resource_report["details"].items())
            if detail["disposition"] != "run"
        ]
        for nodeid, detail in exceptional[:5]:
            terminalreporter.write_line(
                f"    {nodeid}: {detail['rendered']}"
            )

    small_body_report = _combined_small_body_resource_report(config)
    small_body_summary = small_body_report["summary"]
    if small_body_summary["receipts"]:
        identities = small_body_summary["identities"]
        terminalreporter.write_line(
            "  Supplemental small-body resource: "
            f"receipts={small_body_summary['receipts']}, "
            f"run={small_body_summary['run']}, "
            f"skip={small_body_summary['skip']}, "
            f"failure={small_body_summary['failure']}, "
            f"terminal={small_body_summary['terminal']}, "
            f"manifests={small_body_summary['manifests']}, "
            f"shards={small_body_summary['shards']}, "
            f"bodies={small_body_summary['bodies']}, "
            "identities="
            + (
                ",".join(identities)
                if identities
                else "<none>"
            )
        )
        exceptional = [
            (nodeid, detail)
            for nodeid, detail in sorted(
                small_body_report["details"].items()
            )
            if (
                detail["disposition"] != "run"
                or not detail["terminal"]
            )
        ]
        for nodeid, detail in exceptional[:5]:
            terminalreporter.write_line(
                f"    {nodeid}: {detail['rendered']}"
            )
