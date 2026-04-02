from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = REPO_ROOT / "wiki"
GIT_WIKI_ROOT = REPO_ROOT / "moira.wiki"
DEFAULT_REPO_URL = "https://github.com/TheDaniel166/moira"
DEFAULT_REPO_REF = "main"

LINK_RE = re.compile(r"(?P<prefix>!?\[[^\]]*\]\()(?P<target>[^)\s]+)(?P<suffix>(?:\s+\"[^\"]*\")?\))")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize the flat moira.wiki Git wiki mirror from the canonical wiki/ tree."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify moira.wiki is in sync without writing files.",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="Do not remove markdown files in moira.wiki that are not generated from wiki/.",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="Repository web URL used when rewriting links to non-wiki files.",
    )
    parser.add_argument(
        "--repo-ref",
        default=DEFAULT_REPO_REF,
        help="Repository ref used in generated GitHub blob links for non-wiki files.",
    )
    return parser.parse_args()


def _canonical_files() -> list[Path]:
    files = sorted(WIKI_ROOT.rglob("*.md"))
    basenames: dict[str, Path] = {}
    duplicates: list[str] = []
    for path in files:
        if path.name in basenames:
            duplicates.append(path.name)
        else:
            basenames[path.name] = path
    if duplicates:
        joined = ", ".join(sorted(set(duplicates)))
        raise RuntimeError(f"Duplicate markdown basenames under wiki/: {joined}")
    return files


def _split_anchor(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    return path_part, f"#{anchor}"


def _path_from_local_target(source_path: Path, target_path: str) -> Path | None:
    normalized = target_path.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized):
        return Path(normalized)
    if normalized.startswith("/"):
        return Path(normalized)
    if normalized.startswith("wiki/") or normalized.startswith("moira/") or normalized.startswith("tests/"):
        return REPO_ROOT / normalized
    return (source_path.parent / normalized).resolve()


def _rewrite_target(
    source_path: Path,
    target: str,
    basename_map: dict[Path, str],
    repo_url: str,
    repo_ref: str,
) -> str:
    target_path, anchor = _split_anchor(target)
    if not target_path:
        return target

    lowered = target_path.lower()
    if (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or target_path.startswith("#")
    ):
        return target

    local_path = _path_from_local_target(source_path, target_path)
    if local_path is None:
        return target

    try:
        resolved = local_path.resolve()
    except OSError:
        return target

    try:
        wiki_rel = resolved.relative_to(WIKI_ROOT.resolve())
    except ValueError:
        wiki_rel = None

    if wiki_rel is not None and resolved in basename_map:
        return f"{basename_map[resolved]}{anchor}"

    try:
        repo_rel = resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        repo_rel = None

    if repo_rel is not None:
        repo_rel_posix = repo_rel.as_posix()
        return f"{repo_url.rstrip('/')}/blob/{repo_ref}/{repo_rel_posix}{anchor}"

    return target


def _rewrite_links(
    text: str,
    source_path: Path,
    basename_map: dict[Path, str],
    repo_url: str,
    repo_ref: str,
) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        rewritten = _rewrite_target(source_path, target, basename_map, repo_url, repo_ref)
        return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

    return LINK_RE.sub(replace, text)


def _render_page(
    source_path: Path,
    basename_map: dict[Path, str],
    repo_url: str,
    repo_ref: str,
) -> str:
    source_rel = source_path.relative_to(REPO_ROOT).as_posix()
    header = (
        f"<!-- Generated from {source_rel} by scripts/sync_git_wiki.py. Do not edit directly. -->\n\n"
    )
    body = source_path.read_text(encoding="utf-8")
    body = _rewrite_links(body, source_path, basename_map, repo_url, repo_ref)
    return header + body


def _write_outputs(
    rendered: dict[str, str],
    prune: bool,
) -> tuple[list[str], list[str], list[str]]:
    written: list[str] = []
    unchanged: list[str] = []
    removed: list[str] = []

    GIT_WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    expected = set(rendered)

    if prune:
        for path in sorted(GIT_WIKI_ROOT.glob("*.md")):
            if path.name not in expected:
                path.unlink()
                removed.append(path.name)

    for name, content in rendered.items():
        output_path = GIT_WIKI_ROOT / name
        existing = output_path.read_text(encoding="utf-8") if output_path.exists() else None
        if existing == content:
            unchanged.append(name)
            continue
        output_path.write_text(content, encoding="utf-8")
        written.append(name)

    return written, unchanged, removed


def _check_outputs(rendered: dict[str, str], prune: bool) -> int:
    expected = set(rendered)
    extras: list[str] = []
    mismatches: list[str] = []
    missing: list[str] = []

    if prune:
        for path in sorted(GIT_WIKI_ROOT.glob("*.md")):
            if path.name not in expected:
                extras.append(path.name)

    for name, content in rendered.items():
        output_path = GIT_WIKI_ROOT / name
        if not output_path.exists():
            missing.append(name)
            continue
        existing = output_path.read_text(encoding="utf-8")
        if existing != content:
            mismatches.append(name)

    if not extras and not mismatches and not missing:
        print("moira.wiki is in sync with wiki/")
        return 0

    if missing:
        print("Missing generated pages:")
        for name in missing:
            print(f"  {name}")
    if mismatches:
        print("Out-of-date generated pages:")
        for name in mismatches:
            print(f"  {name}")
    if extras:
        print("Unexpected markdown files in moira.wiki:")
        for name in extras:
            print(f"  {name}")
    return 1


def main() -> int:
    args = _parse_args()
    files = _canonical_files()
    basename_map = {path.resolve(): path.name for path in files}
    rendered = {
        path.name: _render_page(path, basename_map, args.repo_url, args.repo_ref)
        for path in files
    }

    if args.check:
        return _check_outputs(rendered, prune=not args.no_prune)

    written, unchanged, removed = _write_outputs(rendered, prune=not args.no_prune)
    print(
        "Synchronized moira.wiki from wiki/: "
        f"{len(written)} written, {len(unchanged)} unchanged, {len(removed)} removed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())