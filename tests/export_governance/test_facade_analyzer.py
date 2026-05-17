from __future__ import annotations

from pathlib import Path

import pytest

from moira._export_governance.facade import FacadeAnalyzer


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "moira"
_SURFACE_FILES = [
    "__init__.py",
    "essentials.py",
    "classical.py",
    "predictive.py",
]


@pytest.fixture(scope="module")
def analyzer() -> FacadeAnalyzer:
    return FacadeAnalyzer(_PACKAGE_ROOT)


@pytest.mark.parametrize("relative_path", _SURFACE_FILES)
def test_surface_analysis_has_no_missing_or_stale_exports(
    analyzer: FacadeAnalyzer,
    relative_path: str,
) -> None:
    report = analyzer.analyze_facade(_PACKAGE_ROOT / relative_path)

    assert not report.missing_exports, (
        f"{relative_path} is missing re-exports: {sorted(report.missing_exports)}"
    )
    assert not report.stale_exports, (
        f"{relative_path} has stale exports: {sorted(report.stale_exports)}"
    )


def test_classical_star_imports_are_tracked_through_essentials(
    analyzer: FacadeAnalyzer,
) -> None:
    report = analyzer.analyze_facade(_PACKAGE_ROOT / "classical.py")

    expected = {"Moira", "Chart", "Body", "HouseSystem"}
    missing = expected - set(report.imported_symbols)
    assert not missing, f"classical.py lost expected forwarded imports: {sorted(missing)}"
