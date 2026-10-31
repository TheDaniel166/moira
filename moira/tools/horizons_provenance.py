"""
moira.tools.horizons_provenance — JPL Horizons system-release provenance
=========================================================================
A Horizons query response names the API (``API VERSION: 1.2``) and, per object,
a ``Revised`` date, but not the Horizons *system release* that produced it
(for example ``4.98e``).  The release is published only in the manual's
Introduction (``Version 4.98e (August 25, 2026)``), so it must be read from
there at generation time and recorded next to the artifact it describes.

This module keeps three honest classes of evidence apart:

- ``recorded``    the artifact carries a ``horizons_system_release`` block read
                  when it was generated;
- ``inferred``    the artifact predates no recorded release, but every
                  retrieval date is on or after the release date of a release
                  that is still current, so no later release can have served it;
- ``unrecorded``  the artifact was retrieved before that release, or records no
                  retrieval date; the release then in service is not known.

Nothing here edits an existing artifact.  Small-body manifests and oracle
receipts are byte-bound by SHA-256, so existing artifacts are classified in a
sidecar (``tests/fixtures/horizons_system_provenance.json``) instead.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

MANUAL_URL = "https://ssd.jpl.nasa.gov/horizons/manual.html"
_RELEASE_PATTERN = re.compile(
    r"Version\s+(\d+\.\d+[a-z]?)\s+\(([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})\)"
)
_RETRIEVAL_KEYS = frozenset(
    {"retrieved_utc", "retrieved_utc_date", "fetched_at_utc", "released_utc"}
)
EVIDENCE_NOT_IN_RESPONSE = (
    "Read from the Horizons manual's Introduction when the artifact was "
    "generated; the query response itself carries no system release."
)


class HorizonsProvenanceError(RuntimeError):
    """Raised when the system release cannot be established or classified."""


@dataclass(frozen=True, slots=True)
class HorizonsSystemRelease:
    """One Horizons system release as published, with when and how it was read."""

    version: str
    release_date: str
    source_url: str
    observed_utc: str
    evidence: str


def parse_system_release(manual_text: str) -> tuple[str, str]:
    """Return ``(version, release_date_iso)`` from the manual's Introduction.

    The first ``Version X.YYz (Month D, YYYY)`` statement is the current
    release.  An absent or unparseable statement raises rather than guessing.

    Raises:
        HorizonsProvenanceError: if no release statement is present.

    Side effects:
        None.
    """

    match = _RELEASE_PATTERN.search(manual_text)
    if match is None:
        raise HorizonsProvenanceError(
            "the Horizons manual does not state a 'Version X.YYz (Month D, YYYY)' release"
        )
    version, month, day, year = match.groups()
    try:
        released = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
    except ValueError as exc:
        raise HorizonsProvenanceError(f"unparseable release date: {match.group(0)!r}") from exc
    return version, released.date().isoformat()


def fetch_system_release(
    *,
    fetch: Callable[[str], str] | None = None,
    now: datetime | None = None,
) -> HorizonsSystemRelease:
    """Read the current Horizons system release from the manual.

    ``fetch`` maps a URL to its text and defaults to one HTTPS GET with a
    30-second timeout; tests inject it.  Any failure raises: a provenance
    record is never produced from a guess.

    Raises:
        HorizonsProvenanceError: if the page cannot be read or parsed.

    Side effects:
        One network request when ``fetch`` is not supplied.
    """

    def default_fetch(url: str) -> str:
        with urllib.request.urlopen(url, timeout=30) as handle:  # noqa: S310 - fixed HTTPS URL
            return handle.read().decode("utf-8", errors="replace")

    reader = fetch or default_fetch
    try:
        text = reader(MANUAL_URL)
    except Exception as exc:  # noqa: BLE001 - reported with its cause
        raise HorizonsProvenanceError(f"cannot read {MANUAL_URL}: {exc}") from exc
    version, release_date = parse_system_release(text)
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return HorizonsSystemRelease(
        version=version,
        release_date=release_date,
        source_url=MANUAL_URL,
        observed_utc=observed.isoformat().replace("+00:00", "Z"),
        evidence=EVIDENCE_NOT_IN_RESPONSE,
    )


def release_block(release: HorizonsSystemRelease) -> dict[str, str]:
    """JSON-ready ``horizons_system_release`` block for a new artifact.

    Side effects:
        None.
    """

    return asdict(release)


def manifest_release_block(release: HorizonsSystemRelease) -> dict[str, str]:
    """Release block for a catalog manifest, scoped to the moment it was written.

    A catalog is assembled over several runs (a refresh re-queries only stale
    bodies and keeps older shards), so a manifest cannot claim that every shard
    came from the release observed when it was written.

    Side effects:
        None.
    """

    return {
        **asdict(release),
        "scope": (
            "observed when the manifest was written; shards may have been retrieved "
            "earlier, possibly under an earlier release"
        ),
    }


def collect_retrieval_dates(payload: Any) -> list[str]:
    """Every retrieval date (``YYYY-MM-DD``) recorded anywhere in a payload.

    Side effects:
        None.
    """

    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _RETRIEVAL_KEYS and isinstance(value, str) and len(value) >= 10:
                    found.append(value[:10])
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return sorted(found)


def classify_artifact(
    payload: Any, release: HorizonsSystemRelease
) -> tuple[str, str | None, str]:
    """Classify one artifact as ``(evidence_class, version, basis)``.

    ``release`` is the release observed as current.  See the module docstring
    for the three classes; ``partial`` marks retrievals that straddle the
    release date, which no single version describes.

    Side effects:
        None.
    """

    recorded = payload.get("horizons_system_release") if isinstance(payload, dict) else None
    if isinstance(recorded, dict) and recorded.get("version"):
        return "recorded", str(recorded["version"]), "block read when the artifact was generated"
    dates = collect_retrieval_dates(payload)
    if not dates:
        return "unrecorded", None, "the artifact records no retrieval date"
    first, last = dates[0], dates[-1]
    if first >= release.release_date:
        return (
            "inferred",
            release.version,
            f"all retrievals ({first}..{last}) are on or after the {release.release_date} "
            f"release of {release.version}, which was still current on {release.observed_utc[:10]}",
        )
    if last < release.release_date:
        return (
            "unrecorded",
            None,
            f"retrieved {first}..{last}, before {release.version} ({release.release_date}); "
            "the release then in service is not recorded",
        )
    return (
        "partial",
        None,
        f"retrievals {first}..{last} straddle the {release.release_date} release of {release.version}",
    )


def sidecar_entries(
    items: Iterable[tuple[str, Any]], release: HorizonsSystemRelease
) -> list[dict[str, Any]]:
    """Classify ``(path, payload)`` pairs into sorted sidecar rows.

    Side effects:
        None.
    """

    rows = []
    for path, payload in items:
        evidence_class, version, basis = classify_artifact(payload, release)
        dates = sorted(set(collect_retrieval_dates(payload)))
        rows.append(
            {
                "path": path,
                "evidence_class": evidence_class,
                "system_release": version,
                "retrieval_dates": dates[:1] + dates[-1:] if len(dates) > 1 else dates,
                "basis": basis,
            }
        )
    return sorted(rows, key=lambda row: row["path"])
