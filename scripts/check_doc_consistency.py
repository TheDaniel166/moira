"""
Release-facing doc consistency checks for primary Moira contract pages.

This script enforces a narrow set of hardening rules:

1. Known stale phrases from the production-readiness roadmap must not appear
   in primary public docs.
2. Core behavioral contract statements must remain present in the mirrored API
   references so drift is caught early.

The scope is intentionally small. This is a release guard, not a general
documentation linter.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
with (REPO_ROOT / "pyproject.toml").open("rb") as _project_stream:
    PROJECT_VERSION = tomllib.load(_project_stream)["project"]["version"]
PROJECT_VERSION_PATTERN = re.escape(PROJECT_VERSION)
ASTEROID_MANIFEST = json.loads(
    (REPO_ROOT / "moira/kernels/asteroids/manifest.json").read_text(
        encoding="utf-8"
    )
)
COMET_MANIFEST = json.loads(
    (REPO_ROOT / "moira/kernels/comets/manifest.json").read_text(
        encoding="utf-8"
    )
)
ASTEROID_IDENTITY = json.loads(
    (REPO_ROOT / "moira/data/asteroid_catalog_naif.metadata.json").read_text(
        encoding="utf-8"
    )
)
COMET_IDENTITY = json.loads(
    (REPO_ROOT / "moira/data/comet_catalog_naif.metadata.json").read_text(
        encoding="utf-8"
    )
)
ASTEROID_COUNT = f"{ASTEROID_MANIFEST['body_count']:,}"
ASTEROID_SHARDS = f"{ASTEROID_MANIFEST['shard_count']:,}"
ASTEROID_VERSION_PATTERN = re.escape(ASTEROID_MANIFEST["catalog_version"])
ASTEROID_MANIFEST_SHA_PATTERN = re.escape(
    ASTEROID_IDENTITY["source"]["release_manifest_sha256"]
)
COMET_COUNT = f"{COMET_MANIFEST['body_count']:,}"
COMET_SHARDS = f"{COMET_MANIFEST['shard_count']:,}"
COMET_VERSION_PATTERN = re.escape(COMET_MANIFEST["catalog_version"])
COMET_MANIFEST_SHA_PATTERN = re.escape(
    COMET_IDENTITY["source"]["release_manifest_sha256"]
)

PRIMARY_DOCS = (
    Path("README.md"),
    Path("PROVENANCE.md"),
    Path("llms.txt"),
    Path("llms-full.txt"),
    Path("wiki/01_doctrines/BEYOND_SWISS_EPHEMERIS.md"),
    Path("wiki/02_services/SERVICE_LAYER_GUIDE.md"),
    Path("wiki/02_standards/API_REFERENCE.md"),
    Path("wiki/02_standards/PLANETARY_REDUCTION_PIPELINE.md"),
    Path("wiki/03_validation/VALIDATION_ASTRONOMY.md"),
    Path("wiki/03_validation/VALIDATION_ASTROLOGY.md"),
    Path("wiki/03_validation/VALIDATION_EXPERIMENTAL.md"),
    Path("wiki/03_validation/RELEASE_VALIDATION_5_1_TO_5_2.md"),
    Path("wiki/06_roadmap/MOIRA_ROADMAP.md"),
    Path("website_docs/publication_sources.json"),
    Path("moira.wiki/API_REFERENCE.md"),
)


@dataclass(frozen=True)
class ForbiddenPattern:
    label: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class RequiredPattern:
    label: str
    pattern: re.Pattern[str]


FORBIDDEN_PATTERNS = (
    ForbiddenPattern(
        label="stale implicit UTC claim",
        pattern=re.compile(r"treated as UTC", re.IGNORECASE),
    ),
    ForbiddenPattern(
        label="stale AssertionError contract",
        pattern=re.compile(r"AssertionError"),
    ),
    ForbiddenPattern(
        label="removed decan_at reader parameter",
        pattern=re.compile(r"decan_at\([^\n)]*reader\s*="),
    ),
    ForbiddenPattern(
        label="superseded 2015 asteroid-family body count",
        pattern=re.compile(r"143[,\s]?711"),
    ),
    ForbiddenPattern(
        label="superseded asteroid-family count",
        pattern=re.compile(r"\b119\s+(?:recognized\s+)?(?:asteroid\s+)?famil(?:y|ies)\b", re.IGNORECASE),
    ),
    ForbiddenPattern(
        label="superseded current lot-definition count",
        pattern=re.compile(r"\b499\s+(?:Arabic\s+Parts|lots?)\b", re.IGNORECASE),
    ),
    ForbiddenPattern(
        label="superseded current ayanamsha count",
        pattern=re.compile(r"\b40\+\s+ayanamsha", re.IGNORECASE),
    ),
    ForbiddenPattern(
        label="superseded nutation table counts",
        pattern=re.compile(r"\b1?365\s+lunisolar\s*\+\s*687\s+planetary", re.IGNORECASE),
    ),
)


REQUIRED_PATTERNS: dict[Path, tuple[RequiredPattern, ...]] = {
    Path("README.md"): (
        RequiredPattern(
            label="current lot-definition count",
            pattern=re.compile(r"\b512 lot definitions\b"),
        ),
        RequiredPattern(
            label="current ayanamsha count",
            pattern=re.compile(r"\b12 admitted ayanamsha systems\b"),
        ),
        RequiredPattern(
            label="current nutation table counts",
            pattern=re.compile(r"1358 luni-solar \+ 1056 planetary terms"),
        ),
        RequiredPattern(
            label="current asteroid release identity",
            pattern=re.compile(
                rf"{re.escape(ASTEROID_COUNT)} selected asteroids[\s\S]*?"
                rf"{ASTEROID_VERSION_PATTERN}"
            ),
        ),
        RequiredPattern(
            label="current comet release identity",
            pattern=re.compile(
                rf"{re.escape(COMET_COUNT)} comets[\s\S]*?"
                rf"{COMET_VERSION_PATTERN}"
            ),
        ),
    ),
    Path("PROVENANCE.md"): (
        RequiredPattern(
            label="current asteroid manifest receipt",
            pattern=re.compile(
                rf"{ASTEROID_VERSION_PATTERN}[\s\S]*?"
                rf"{ASTEROID_MANIFEST['body_count']:,} canonical names[\s\S]*?"
                rf"{ASTEROID_MANIFEST_SHA_PATTERN}"
            ),
        ),
        RequiredPattern(
            label="current comet manifest receipt",
            pattern=re.compile(
                rf"{COMET_VERSION_PATTERN}[\s\S]*?"
                rf"{COMET_COUNT} comets in {COMET_SHARDS} shards[\s\S]*?"
                rf"{COMET_MANIFEST_SHA_PATTERN}"
            ),
        ),
    ),
    Path("llms.txt"): (
        RequiredPattern(
            label="current release version",
            pattern=re.compile(rf"current: {PROJECT_VERSION_PATTERN}"),
        ),
        RequiredPattern(
            label="current asteroid catalog summary",
            pattern=re.compile(
                rf"{re.escape(ASTEROID_COUNT)} asteroids[\s\S]*?"
                rf"{ASTEROID_VERSION_PATTERN}"
            ),
        ),
    ),
    Path("llms-full.txt"): (
        RequiredPattern(
            label="current lot-definition count",
            pattern=re.compile(r"\b512 lots\b"),
        ),
        RequiredPattern(
            label="current asteroid catalog summary",
            pattern=re.compile(
                rf"{re.escape(ASTEROID_COUNT)} asteroids as "
                rf"{re.escape(ASTEROID_SHARDS)} Type-13 shards[\s\S]*?"
                rf"{ASTEROID_VERSION_PATTERN}"
            ),
        ),
        RequiredPattern(
            label="current comet catalog summary",
            pattern=re.compile(
                rf"{re.escape(COMET_COUNT)} numbered periodic comets[\s\S]*?"
                rf"{re.escape(COMET_SHARDS)} Type-13 shards[\s\S]*?"
                rf"{COMET_VERSION_PATTERN}"
            ),
        ),
    ),
    Path("wiki/02_standards/API_REFERENCE.md"): (
        RequiredPattern(
            label="current engine baseline",
            pattern=re.compile(
                rf"\*\*Engine baseline:\*\* {PROJECT_VERSION_PATTERN}"
            ),
        ),
        RequiredPattern(
            label="naive datetime rejection contract",
            pattern=re.compile(
                r"jd_from_datetime.*timezone-aware datetime.*naïve datetimes raise `ValueError`"
            ),
        ),
        RequiredPattern(
            label="house classification unknown-code failure contract",
            pattern=re.compile(
                r"classify_house_system\(system\).*raises `ValueError` on unknown codes"
            ),
        ),
        RequiredPattern(
            label="house vessel effective system field",
            pattern=re.compile(
                r"`effective_system` \| `str` \| Effective system code after policy resolution"
            ),
        ),
        RequiredPattern(
            label="house vessel fallback flag field",
            pattern=re.compile(
                r"`fallback` \| `bool` \| Whether fallback policy altered the requested system"
            ),
        ),
        RequiredPattern(
            label="house vessel fallback reason field",
            pattern=re.compile(
                r"`fallback_reason` \| `str \\\| None` \| Human-readable fallback reason, if any"
            ),
        ),
        RequiredPattern(
            label="unknown system fallback enum name",
            pattern=re.compile(r"FALLBACK_TO_PLACIDUS"),
        ),
    ),
    Path("wiki/02_standards/PLANETARY_REDUCTION_PIPELINE.md"): (
        RequiredPattern(
            label="planetary reduction implementation entry point",
            pattern=re.compile(r"`planet_at\(\.\.\.\)`"),
        ),
        RequiredPattern(
            label="planetary reduction REST inspection route",
            pattern=re.compile(r"`POST /v1/pipeline/positions/planet`"),
        ),
        RequiredPattern(
            label="metadata-only small-body boundary",
            pattern=re.compile(r"metadata-only manifest does not make a body\s+position-capable"),
        ),
    ),
    Path("wiki/03_validation/VALIDATION_ASTRONOMY.md"): (
        RequiredPattern(
            label="recent release evidence ledger",
            pattern=re.compile(r"RELEASE_VALIDATION_5_1_TO_5_2\.md"),
        ),
    ),
    Path("wiki/03_validation/VALIDATION_ASTROLOGY.md"): (
        RequiredPattern(
            label="recent release evidence ledger",
            pattern=re.compile(r"RELEASE_VALIDATION_5_1_TO_5_2\.md"),
        ),
    ),
    Path("wiki/03_validation/VALIDATION_EXPERIMENTAL.md"): (
        RequiredPattern(
            label="recent release evidence ledger",
            pattern=re.compile(r"RELEASE_VALIDATION_5_1_TO_5_2\.md"),
        ),
    ),
    Path("wiki/06_roadmap/MOIRA_ROADMAP.md"): (
        RequiredPattern(
            label="living roadmap disclaimer",
            pattern=re.compile(r"Living engineering roadmap"),
        ),
    ),
    Path("website_docs/publication_sources.json"): (
        RequiredPattern(
            label="correct planetary reduction source mapping",
            pattern=re.compile(
                r'"id": "planetary-reduction"[\s\S]*?'
                r'"source": "wiki/02_standards/PLANETARY_REDUCTION_PIPELINE\.md"'
            ),
        ),
        RequiredPattern(
            label="private research excluded from public allowlist",
            pattern=re.compile(r'"release_history_floor": "5\.0\.0"'),
        ),
    ),
    Path("moira.wiki/API_REFERENCE.md"): (
        RequiredPattern(
            label="current engine baseline",
            pattern=re.compile(
                rf"\*\*Engine baseline:\*\* {PROJECT_VERSION_PATTERN}"
            ),
        ),
        RequiredPattern(
            label="naive datetime rejection contract",
            pattern=re.compile(
                r"jd_from_datetime.*timezone-aware datetime.*naïve datetimes raise `ValueError`"
            ),
        ),
        RequiredPattern(
            label="house classification unknown-code failure contract",
            pattern=re.compile(
                r"classify_house_system\(system\).*raises `ValueError` on unknown codes"
            ),
        ),
        RequiredPattern(
            label="house vessel effective system field",
            pattern=re.compile(
                r"`effective_system` \| `str` \| Effective system code after policy resolution"
            ),
        ),
        RequiredPattern(
            label="house vessel fallback flag field",
            pattern=re.compile(
                r"`fallback` \| `bool` \| Whether fallback policy altered the requested system"
            ),
        ),
        RequiredPattern(
            label="house vessel fallback reason field",
            pattern=re.compile(
                r"`fallback_reason` \| `str \\\| None` \| Human-readable fallback reason, if any"
            ),
        ),
        RequiredPattern(
            label="unknown system fallback enum name",
            pattern=re.compile(r"FALLBACK_TO_PLACIDUS"),
        ),
    ),
}


def _iter_forbidden_hits(path: Path, text: str) -> list[str]:
    hits: list[str] = []
    for rule in FORBIDDEN_PATTERNS:
        for match in rule.pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            hits.append(f"{path}:{line}: forbidden {rule.label}: {match.group(0)!r}")
    return hits


def _iter_missing_requirements(path: Path, text: str) -> list[str]:
    failures: list[str] = []
    for rule in REQUIRED_PATTERNS.get(path, ()):
        if not rule.pattern.search(text):
            failures.append(f"{path}: missing required contract: {rule.label}")
    return failures


def main() -> int:
    failures: list[str] = []

    for relative_path in PRIMARY_DOCS:
        absolute_path = REPO_ROOT / relative_path
        text = absolute_path.read_text(encoding="utf-8", errors="replace")
        failures.extend(_iter_forbidden_hits(relative_path, text))
        failures.extend(_iter_missing_requirements(relative_path, text))

    if failures:
        print("Doc consistency check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("Doc consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
