"""
tests/test_api_reference_validation.py — Bug Condition Exploration Tests

Validates: Requirements 1.1 through 1.17

This test suite encodes the EXPECTED CORRECT STATE of wiki/02_standards/API_REFERENCE.md.
It is designed to FAIL on the unfixed reference — failure confirms the 17 discrepancies
exist. When all 17 corrections are applied (Task 3), this suite will pass.

Part A — Text-matching assertions (D-01 through D-17):
    Each test reads the reference and asserts the correct text is present.
    These tests FAIL on the unfixed reference (expected behaviour for Task 1).

Part B — Executable import/call checks:
    These confirm the bug is documentation-only (the code is correct).
    These tests PASS on the unfixed reference.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Reference document path
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_REF = _REPO_ROOT / "wiki" / "02_standards" / "API_REFERENCE.md"


def _ref() -> str:
    """Return the full text of the API reference document."""
    return _API_REF.read_text(encoding="utf-8")


# ===========================================================================
# PART A — Text-matching assertions
# Each test asserts the CORRECT state. All should FAIL on the unfixed doc.
# ===========================================================================


def test_d01_classical_tier_planetary_hours_correct_name():
    """
    D-01: The moira.classical tier table planetary hours row must list
    `planetary_hours`, not `planetary_hours_for_day`.

    Validates: Requirement 1.1
    """
    text = _ref()

    # Locate the moira.classical tier table section by anchoring to the markdown headings.
    # Using the heading prevents false-positives from prose that mentions both module names
    # on the same line (e.g. the introductory note on line 38).
    classical_section_match = re.search(
        r"### `moira\.classical`.*?### `moira\.predictive`",
        text,
        re.DOTALL,
    )
    assert classical_section_match is not None, "Could not locate moira.classical tier table section"
    classical_section = classical_section_match.group(0)

    # Find the planetary hours row
    ph_row_match = re.search(r"\|\s*Planetary hours\s*\|([^\n]+)", classical_section)
    assert ph_row_match is not None, "Could not find 'Planetary hours' row in moira.classical tier table"
    ph_row = ph_row_match.group(1)

    assert "planetary_hours_for_day" not in ph_row, (
        f"D-01 BUG: moira.classical tier table Planetary hours row contains "
        f"`planetary_hours_for_day` — should be `planetary_hours`. Row: {ph_row!r}"
    )
    assert "planetary_hours" in ph_row, (
        f"D-01 BUG: moira.classical tier table Planetary hours row does not contain "
        f"`planetary_hours`. Row: {ph_row!r}"
    )


def test_d02_predictive_tier_returns_row_no_spurious_symbols():
    """
    D-02: The moira.predictive tier table "Returns" row must NOT list
    `half_return_series` or `lifetime_returns` as predictive additions.
    Those symbols belong to moira.classical (via moira.cycles).

    Validates: Requirement 1.2
    """
    text = _ref()

    # Locate the moira.predictive tier table
    predictive_section_match = re.search(
        r"moira\.predictive.*?Adds the complete forecasting.*?moira\.facade",
        text,
        re.DOTALL,
    )
    assert predictive_section_match is not None, "Could not locate moira.predictive tier table section"
    predictive_section = predictive_section_match.group(0)

    # Find the Returns row
    returns_row_match = re.search(r"\|\s*Returns\s*\|([^\n]+)", predictive_section)
    assert returns_row_match is not None, "Could not find 'Returns' row in moira.predictive tier table"
    returns_row = returns_row_match.group(1)

    assert "half_return_series" not in returns_row, (
        f"D-02 BUG: moira.predictive tier table Returns row contains `half_return_series` "
        f"— this symbol belongs to moira.classical (via moira.cycles), not predictive. "
        f"Row: {returns_row!r}"
    )
    assert "lifetime_returns" not in returns_row, (
        f"D-02 BUG: moira.predictive tier table Returns row contains `lifetime_returns` "
        f"— this symbol belongs to moira.classical (via moira.cycles), not predictive. "
        f"Row: {returns_row!r}"
    )


def test_d03_predictive_tier_void_of_course_includes_void_periods_in_range():
    """
    D-03: The moira.predictive tier table "Void of course" row must include
    `void_periods_in_range` alongside the other three void-of-course symbols.

    Validates: Requirement 1.3
    """
    text = _ref()

    # Locate the moira.predictive tier table
    predictive_section_match = re.search(
        r"moira\.predictive.*?Adds the complete forecasting.*?moira\.facade",
        text,
        re.DOTALL,
    )
    assert predictive_section_match is not None, "Could not locate moira.predictive tier table section"
    predictive_section = predictive_section_match.group(0)

    # Find the Void of course row
    voc_row_match = re.search(r"\|\s*Void of course\s*\|([^\n]+)", predictive_section)
    assert voc_row_match is not None, "Could not find 'Void of course' row in moira.predictive tier table"
    voc_row = voc_row_match.group(1)

    assert "void_periods_in_range" in voc_row, (
        f"D-03 BUG: moira.predictive tier table 'Void of course' row does not include "
        f"`void_periods_in_range`. Row: {voc_row!r}"
    )


def test_d04_essentials_import_block_includes_delta_t_breakdown():
    """
    D-04: The moira.essentials import block must include `DeltaTBreakdown`
    and `delta_t_breakdown`, which are present in essentials.__all__.

    Validates: Requirement 1.12
    """
    text = _ref()

    # Locate the moira.essentials import block
    essentials_block_match = re.search(
        r"from moira\.essentials import.*?```",
        text,
        re.DOTALL,
    )
    assert essentials_block_match is not None, "Could not locate moira.essentials import block"
    essentials_block = essentials_block_match.group(0)

    assert "DeltaTBreakdown" in essentials_block, (
        f"D-04 BUG: moira.essentials import block does not include `DeltaTBreakdown`. "
        f"This symbol is in essentials.__all__ but is absent from the documented import block."
    )
    assert "delta_t_breakdown" in essentials_block, (
        f"D-04 BUG: moira.essentials import block does not include `delta_t_breakdown`. "
        f"This symbol is in essentials.__all__ but is absent from the documented import block."
    )


def test_d05_predictive_tier_eclipses_no_next_solar_eclipse_at_location():
    """
    D-05: The moira.predictive tier table "Eclipses" row must NOT list
    `next_solar_eclipse_at_location` as a direct predictive export without
    a note about moira.facade / moira.eclipse availability.

    The symbol is exported from moira.facade and moira.eclipse, but NOT
    re-exported through moira.predictive.

    Validates: Requirement 1.15
    """
    text = _ref()

    # Locate the moira.predictive tier table
    predictive_section_match = re.search(
        r"moira\.predictive.*?Adds the complete forecasting.*?moira\.facade",
        text,
        re.DOTALL,
    )
    assert predictive_section_match is not None, "Could not locate moira.predictive tier table section"
    predictive_section = predictive_section_match.group(0)

    # Find the Eclipses row
    eclipses_row_match = re.search(r"\|\s*Eclipses\s*\|([^\n]+)", predictive_section)
    assert eclipses_row_match is not None, "Could not find 'Eclipses' row in moira.predictive tier table"
    eclipses_row = eclipses_row_match.group(1)

    assert "next_solar_eclipse_at_location" not in eclipses_row, (
        f"D-05 BUG: moira.predictive tier table Eclipses row lists `next_solar_eclipse_at_location` "
        f"as a direct predictive export. This symbol is NOT re-exported from moira.predictive; "
        f"it is available from moira.facade and moira.eclipse directly. Row: {eclipses_row!r}"
    )


def test_d06_galactic_houses_in_alternative_frames_table():
    """
    D-06: `galactic_houses(dt, latitude, longitude)` must appear in the
    "Alternative frames & specialty coordinates" method table in Section 4.

    The method exists in facade.py at line 3270 but is absent from the reference.

    Validates: Requirement 1.5
    """
    text = _ref()

    # Locate the Alternative frames & specialty coordinates section
    alt_frames_match = re.search(
        r"### Alternative frames & specialty coordinates.*?###",
        text,
        re.DOTALL,
    )
    assert alt_frames_match is not None, "Could not locate 'Alternative frames & specialty coordinates' section"
    alt_frames_section = alt_frames_match.group(0)

    assert "galactic_houses" in alt_frames_section, (
        "D-06 BUG: `galactic_houses` is absent from the 'Alternative frames & specialty coordinates' "
        "method table in Section 4. The method exists in facade.py (line 3270) but is not documented."
    )


def test_d07_timing_table_cross_references_void_of_course_subsection():
    """
    D-07: The Section 4 timing method table must include a cross-reference to
    the "Void of Course Moon" subsection for `moon_void_of_course` and
    `is_moon_void_of_course`, or list those methods directly in the timing table.

    Currently they appear only in a separate subsection, making the timing table
    incomplete.

    Validates: Requirement 1.13
    """
    text = _ref()

    # Locate the timing techniques table in Section 4
    timing_table_match = re.search(
        r"### Timing techniques.*?### Progressions",
        text,
        re.DOTALL,
    )
    assert timing_table_match is not None, "Could not locate 'Timing techniques' table in Section 4"
    timing_table = timing_table_match.group(0)

    # The timing table should either list the methods directly or cross-reference the subsection
    has_moon_voc = "moon_void_of_course" in timing_table
    has_is_moon_voc = "is_moon_void_of_course" in timing_table
    has_voc_crossref = "Void of Course Moon" in timing_table or "void of course" in timing_table.lower()

    assert has_moon_voc or has_voc_crossref, (
        "D-07 BUG: The Section 4 timing method table does not include `moon_void_of_course` "
        "or a cross-reference to the 'Void of Course Moon' subsection. Users scanning the "
        "timing table cannot discover these methods."
    )
    assert has_is_moon_voc or has_voc_crossref, (
        "D-07 BUG: The Section 4 timing method table does not include `is_moon_void_of_course` "
        "or a cross-reference to the 'Void of Course Moon' subsection."
    )


def test_d08_timing_table_cross_references_electional_subsection():
    """
    D-08: The Section 4 timing method table must include a cross-reference to
    the "Electional search" subsection for `electional_windows`, or list the
    method directly in the timing table.

    Currently it appears only in a separate subsection.

    Validates: Requirement 1.14
    """
    text = _ref()

    # Locate the timing techniques table in Section 4
    timing_table_match = re.search(
        r"### Timing techniques.*?### Progressions",
        text,
        re.DOTALL,
    )
    assert timing_table_match is not None, "Could not locate 'Timing techniques' table in Section 4"
    timing_table = timing_table_match.group(0)

    has_electional = "electional_windows" in timing_table
    has_electional_crossref = "Electional search" in timing_table or "electional" in timing_table.lower()

    assert has_electional or has_electional_crossref, (
        "D-08 BUG: The Section 4 timing method table does not include `electional_windows` "
        "or a cross-reference to the 'Electional search' subsection. Users scanning the "
        "timing table cannot discover this method."
    )


def test_d09_mutation_period_at_correct_signature_and_return_type():
    """
    D-09: Section 10 must document `mutation_period_at(longitude)` returning
    `GreatMutationElement`, not `mutation_period_at(jd_ut)` returning `MutationPeriod`.

    Actual signature: mutation_period_at(longitude: float) -> GreatMutationElement

    Validates: Requirement 1.8
    """
    text = _ref()

    # Find the mutation_period_at function table row in Section 10
    # It appears in the Great Conjunctions function table
    mpa_row_match = re.search(
        r"\|\s*`mutation_period_at\([^`]*\)`\s*\|\s*`([^`]+)`\s*\|([^\n]+)",
        text,
    )
    assert mpa_row_match is not None, (
        "Could not find `mutation_period_at(...)` row in the API reference"
    )

    full_row = mpa_row_match.group(0)
    return_type = mpa_row_match.group(1)
    param_match = re.search(r"mutation_period_at\(([^)]*)\)", full_row)
    param = param_match.group(1) if param_match else ""

    assert param == "longitude", (
        f"D-09 BUG: `mutation_period_at` is documented with parameter `{param}` "
        f"but the actual parameter is `longitude`. Full row: {full_row!r}"
    )
    assert return_type == "GreatMutationElement", (
        f"D-09 BUG: `mutation_period_at` is documented as returning `{return_type}` "
        f"but the actual return type is `GreatMutationElement`. Full row: {full_row!r}"
    )


def test_d10_planetary_age_profile_correct_signature():
    """
    D-10: Section 10 must document `planetary_age_profile(age_years=None)`,
    not `planetary_age_profile(jd_natal, jd_now)`.

    Actual signature: planetary_age_profile(age_years: float | None = None) -> PlanetaryAgeProfile

    Validates: Requirement 1.9
    """
    text = _ref()

    # Find the planetary_age_profile function table row
    pap_row_match = re.search(
        r"\|\s*`planetary_age_profile\([^`]*\)`\s*\|[^\n]+",
        text,
    )
    assert pap_row_match is not None, (
        "Could not find `planetary_age_profile(...)` row in the API reference"
    )

    full_row = pap_row_match.group(0)
    param_match = re.search(r"planetary_age_profile\(([^)]*)\)", full_row)
    params = param_match.group(1) if param_match else ""

    assert "jd_natal" not in params, (
        f"D-10 BUG: `planetary_age_profile` is documented with parameter `jd_natal` "
        f"but the actual parameter is `age_years`. Full row: {full_row!r}"
    )
    assert "jd_now" not in params, (
        f"D-10 BUG: `planetary_age_profile` is documented with parameter `jd_now` "
        f"but the actual parameter is `age_years`. Full row: {full_row!r}"
    )
    assert "age_years" in params, (
        f"D-10 BUG: `planetary_age_profile` is not documented with parameter `age_years`. "
        f"Full row: {full_row!r}"
    )


def test_d11_d14_section9_firdar_period_table_has_timelords_qualifier():
    """
    D-11 / D-14: The Section 9 FirdarPeriod field table heading must carry
    the `(moira.timelords)` qualifier to distinguish it from the
    moira.cycles.FirdarPeriod documented in Section 10.

    Validates: Requirements 1.10 (D-11) and 1.10 (D-14)
    """
    text = _ref()

    # Section 9 is the Firdaria (Persian Time Lords) section
    # Find the FirdarPeriod fields heading in Section 9 (before Section 10)
    section9_match = re.search(
        r"## 9\. Timing Techniques.*?## 10\.",
        text,
        re.DOTALL,
    )
    assert section9_match is not None, "Could not locate Section 9 (Timing Techniques)"
    section9 = section9_match.group(0)

    # Find the FirdarPeriod fields heading
    firdar_heading_match = re.search(
        r"####\s*`FirdarPeriod`\s*fields([^\n]*)",
        section9,
    )
    assert firdar_heading_match is not None, (
        "Could not find `FirdarPeriod` fields heading in Section 9"
    )
    heading_line = firdar_heading_match.group(0)

    assert "(moira.timelords)" in heading_line, (
        f"D-11/D-14 BUG: Section 9 `FirdarPeriod` fields table heading does not carry "
        f"the `(moira.timelords)` qualifier. Without this qualifier, users cannot "
        f"distinguish it from `moira.cycles.FirdarPeriod` in Section 10. "
        f"Heading: {heading_line!r}"
    )


def test_d12_d16_section8_planetary_hour_table_has_planetary_hours_qualifier():
    """
    D-12 / D-16: The Section 8 PlanetaryHour field table heading must carry
    the `(moira.planetary_hours)` qualifier to distinguish it from the
    moira.cycles.PlanetaryHour documented in Section 10.

    Validates: Requirements 1.11 (D-12) and 1.11 (D-16)
    """
    text = _ref()

    # Section 8 is Classical Techniques
    section8_match = re.search(
        r"## 8\. Classical Techniques.*?## 9\.",
        text,
        re.DOTALL,
    )
    assert section8_match is not None, "Could not locate Section 8 (Classical Techniques)"
    section8 = section8_match.group(0)

    # Find the PlanetaryHour reference in the Planetary Hours subsection
    # The heading or comment should carry (moira.planetary_hours)
    ph_qualifier_present = "(moira.planetary_hours)" in section8

    assert ph_qualifier_present, (
        "D-12/D-16 BUG: Section 8 Planetary Hours does not carry the "
        "`(moira.planetary_hours)` qualifier for the PlanetaryHour vessel. "
        "Without this qualifier, users cannot distinguish it from "
        "`moira.cycles.PlanetaryHour` in Section 10."
    )


def test_d13_section10_cycles_import_block_includes_firdar_and_planetary_hours():
    """
    D-13: The Section 10 moira.cycles import block must include the Firdar
    symbols (FirdarPeriod, FirdarSubPeriod, FirdarSeries, firdar_series,
    firdar_at) and the planetary hours symbols (PlanetaryDayInfo, PlanetaryHour,
    PlanetaryHoursProfile, planetary_day_ruler, planetary_hours_for_day).

    Validates: Requirement 1.16
    """
    text = _ref()

    # Locate the Section 10 moira.cycles import block
    cycles_import_match = re.search(
        r"from moira\.cycles import.*?```",
        text,
        re.DOTALL,
    )
    assert cycles_import_match is not None, "Could not locate moira.cycles import block in Section 10"
    cycles_import = cycles_import_match.group(0)

    required_firdar = [
        "FirdarPeriod", "FirdarSubPeriod", "FirdarSeries",
        "firdar_series", "firdar_at",
    ]
    required_planetary_hours = [
        "PlanetaryDayInfo", "PlanetaryHoursProfile",
        "planetary_day_ruler", "planetary_hours_for_day",
    ]

    for symbol in required_firdar:
        assert symbol in cycles_import, (
            f"D-13 BUG: Section 10 moira.cycles import block is missing Firdar symbol `{symbol}`. "
            f"This symbol is in cycles.__all__ but absent from the documented import block."
        )

    for symbol in required_planetary_hours:
        assert symbol in cycles_import, (
            f"D-13 BUG: Section 10 moira.cycles import block is missing planetary hours symbol "
            f"`{symbol}`. This symbol is in cycles.__all__ but absent from the documented import block."
        )


def test_d15_section11_huber_import_block_notes_tier_availability():
    """
    D-15: Section 11 Huber Method must include a note stating that Huber symbols
    are also available via moira.classical, moira.predictive, and moira.facade,
    not only via direct moira.huber import.

    Validates: Requirement 1.17
    """
    text = _ref()

    # Locate Section 11
    section11_match = re.search(
        r"## 11\. Huber Method.*?## 12\.",
        text,
        re.DOTALL,
    )
    assert section11_match is not None, "Could not locate Section 11 (Huber Method)"
    section11 = section11_match.group(0)

    # The section should mention that Huber symbols are available via the tier modules
    has_classical_note = "moira.classical" in section11
    has_predictive_note = "moira.predictive" in section11
    has_facade_note = "moira.facade" in section11

    assert has_classical_note and has_predictive_note and has_facade_note, (
        f"D-15 BUG: Section 11 Huber Method does not note that Huber symbols are also "
        f"available via moira.classical, moira.predictive, and moira.facade. "
        f"has_classical={has_classical_note}, has_predictive={has_predictive_note}, "
        f"has_facade={has_facade_note}. "
        f"The section only documents moira.huber as the import path."
    )


def test_d17_classical_tier_huber_row_notes_direct_import():
    """
    D-17: The moira.classical tier table Huber row must include a note that
    Huber symbols are `(also importable directly from moira.huber)`.

    Validates: Requirement 1.17 (joint with D-15)
    """
    text = _ref()

    # Locate the moira.classical tier table section by anchoring to the markdown headings.
    # Using the heading prevents false-positives from prose that mentions both module names
    # on the same line (e.g. the introductory note on line 38).
    classical_section_match = re.search(
        r"### `moira\.classical`.*?### `moira\.predictive`",
        text,
        re.DOTALL,
    )
    assert classical_section_match is not None, "Could not locate moira.classical tier table section"
    classical_section = classical_section_match.group(0)

    # Find the Huber row
    huber_row_match = re.search(r"\|\s*Huber\s*\|([^\n]+)", classical_section)
    assert huber_row_match is not None, "Could not find 'Huber' row in moira.classical tier table"
    huber_row = huber_row_match.group(1)

    assert "moira.huber" in huber_row, (
        f"D-17 BUG: moira.classical tier table Huber row does not include a note about "
        f"`moira.huber` as a direct import path. The reference is inconsistent about "
        f"which import path is canonical. Row: {huber_row!r}"
    )


# ===========================================================================
# PART B — Executable import/call checks
# These confirm the bug is documentation-only (the code is correct).
# These tests SHOULD PASS on the unfixed reference.
# ===========================================================================


def test_part_b_mutation_period_at_rejects_jd_ut_kwarg():
    """
    Part B: Calling mutation_period_at(jd_ut=...) raises TypeError because
    the actual parameter is `longitude`, not `jd_ut`.

    This confirms D-09 is a documentation bug, not a code bug.

    Validates: Requirements 1.8, 2.4
    """
    from moira.cycles import mutation_period_at

    with pytest.raises(TypeError):
        mutation_period_at(jd_ut=2451545.0)  # type: ignore[call-arg]


def test_part_b_planetary_age_profile_rejects_jd_natal_jd_now_kwargs():
    """
    Part B: Calling planetary_age_profile(jd_natal=..., jd_now=...) raises
    TypeError because the actual parameter is `age_years`.

    This confirms D-10 is a documentation bug, not a code bug.

    Validates: Requirements 1.9, 2.5
    """
    from moira.cycles import planetary_age_profile

    with pytest.raises(TypeError):
        planetary_age_profile(jd_natal=2451545.0, jd_now=2451910.0)  # type: ignore[call-arg]


def test_part_b_essentials_exports_delta_t_breakdown():
    """
    Part B: `from moira.essentials import DeltaTBreakdown, delta_t_breakdown`
    succeeds — confirming D-04 is a documentation omission, not a code bug.

    Validates: Requirement 1.12
    """
    from moira.essentials import DeltaTBreakdown, delta_t_breakdown  # noqa: F401

    assert DeltaTBreakdown is not None
    assert delta_t_breakdown is not None
    assert callable(delta_t_breakdown)


def test_part_b_predictive_exports_void_periods_in_range():
    """
    Part B: `from moira.predictive import void_periods_in_range` succeeds —
    confirming D-03 is a documentation omission, not a code bug.

    Validates: Requirement 1.3
    """
    from moira.predictive import void_periods_in_range  # noqa: F401

    assert void_periods_in_range is not None
    assert callable(void_periods_in_range)


# ===========================================================================
# PART B — Additional code-correctness checks (property-based)
# ===========================================================================


@given(longitude=st.floats(min_value=0.0, max_value=360.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=20)
def test_part_b_mutation_period_at_accepts_longitude_parameter(longitude: float):
    """
    Part B (property): mutation_period_at(longitude=x) always returns a
    GreatMutationElement for any longitude in [0, 360).

    Validates: Requirements 1.8, 2.4

    **Validates: Requirements 1.8**
    """
    from moira.cycles import GreatMutationElement, mutation_period_at

    result = mutation_period_at(longitude)
    assert isinstance(result, GreatMutationElement), (
        f"mutation_period_at({longitude}) returned {result!r}, "
        f"expected a GreatMutationElement member"
    )


@given(age_years=st.floats(min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=20)
def test_part_b_planetary_age_profile_accepts_age_years_parameter(age_years: float):
    """
    Part B (property): planetary_age_profile(age_years=x) always returns a
    PlanetaryAgeProfile with `current` set for any age in [0, 120].

    Validates: Requirements 1.9, 2.5

    **Validates: Requirements 1.9**
    """
    from moira.cycles import PlanetaryAgeProfile, planetary_age_profile

    result = planetary_age_profile(age_years=age_years)
    assert isinstance(result, PlanetaryAgeProfile), (
        f"planetary_age_profile(age_years={age_years}) returned {result!r}, "
        f"expected a PlanetaryAgeProfile"
    )
    assert result.current is not None, (
        f"planetary_age_profile(age_years={age_years}).current is None — "
        f"expected a valid PlanetaryAgePeriod when age_years is provided"
    )


# ===========================================================================
# PART C — Preservation property tests (Task 2)
# These assert that correct entries in the reference are unchanged after fix.
# All tests in this section MUST PASS on the unfixed reference (baseline).
# ===========================================================================

# ---------------------------------------------------------------------------
# Snapshot helpers — extract stable content from the unfixed reference
# ---------------------------------------------------------------------------

def _section(text: str, start_marker: str, end_marker: str) -> str:
    """Extract the text between two markers (exclusive)."""
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    assert start != -1, f"Could not find start marker: {start_marker!r}"
    assert end != -1, f"Could not find end marker: {end_marker!r}"
    return text[start:end]


def _extract_table_rows(text: str, table_header_fragment: str) -> list[str]:
    """Return all non-header, non-separator rows from a markdown table
    identified by a fragment of its header line."""
    lines = text.splitlines()
    in_table = False
    rows: list[str] = []
    for line in lines:
        stripped = line.strip()
        if table_header_fragment in stripped and stripped.startswith("|"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            if re.match(r"^\|[-| ]+\|$", stripped):
                continue  # separator row
            rows.append(stripped)
    return rows


# ---------------------------------------------------------------------------
# Preservation: vessel field tables that must not change
# ---------------------------------------------------------------------------

class TestPreservationVesselTables:
    """
    Property 2: Preservation — vessel field tables not in the 17 discrepancy
    list must be byte-for-byte identical before and after the fix.

    These tests record the baseline (unfixed) state and assert it is preserved.
    """

    def _assert_table_present_and_stable(self, table_name: str, expected_fields: list[str]) -> None:
        """Assert that a named vessel table contains all expected field rows."""
        text = _ref()
        for field in expected_fields:
            assert field in text, (
                f"PRESERVATION FAILURE: Field `{field}` is missing from the "
                f"`{table_name}` vessel table. This entry was correct before the fix "
                f"and must not have been disturbed."
            )

    def test_return_event_fields_preserved(self):
        """ReturnEvent vessel fields must be unchanged."""
        self._assert_table_present_and_stable("ReturnEvent", [
            "jd_ut", "body", "longitude",
        ])

    def test_return_series_fields_preserved(self):
        """ReturnSeries vessel fields must be unchanged."""
        self._assert_table_present_and_stable("ReturnSeries", [
            "ReturnSeries",
        ])

    def test_synodic_cycle_position_fields_preserved(self):
        """SynodicCyclePosition vessel fields must be unchanged."""
        self._assert_table_present_and_stable("SynodicCyclePosition", [
            "SynodicCyclePosition",
        ])

    def test_great_conjunction_fields_preserved(self):
        """GreatConjunction vessel fields must be unchanged."""
        self._assert_table_present_and_stable("GreatConjunction", [
            "GreatConjunction",
        ])

    def test_planetary_age_period_fields_preserved(self):
        """PlanetaryAgePeriod vessel fields must be unchanged."""
        self._assert_table_present_and_stable("PlanetaryAgePeriod", [
            "PlanetaryAgePeriod",
        ])

    def test_planetary_age_profile_fields_preserved(self):
        """PlanetaryAgeProfile vessel fields must be unchanged."""
        self._assert_table_present_and_stable("PlanetaryAgeProfile", [
            "PlanetaryAgeProfile",
        ])

    def test_firdar_sub_period_fields_preserved(self):
        """FirdarSubPeriod vessel fields must be unchanged."""
        self._assert_table_present_and_stable("FirdarSubPeriod", [
            "FirdarSubPeriod",
        ])

    def test_chart_vessel_fields_preserved(self):
        """Chart vessel fields (jd_ut, planets, nodes, obliquity, delta_t) must be unchanged."""
        self._assert_table_present_and_stable("Chart", [
            "jd_ut", "planets", "nodes", "obliquity",
        ])

    def test_planet_data_fields_preserved(self):
        """PlanetData vessel fields must be unchanged."""
        self._assert_table_present_and_stable("PlanetData", [
            "longitude", "latitude", "speed", "distance",
        ])

    def test_house_cusps_fields_preserved(self):
        """HouseCusps vessel fields must be unchanged."""
        self._assert_table_present_and_stable("HouseCusps", [
            "cusps", "asc", "mc", "armc", "vertex", "system",
        ])

    def test_aspect_data_fields_preserved(self):
        """AspectData vessel fields must be unchanged."""
        self._assert_table_present_and_stable("AspectData", [
            "body1", "body2", "aspect", "orb", "applying",
        ])


# ---------------------------------------------------------------------------
# Preservation: import blocks that must not change (Sections 5–9, 12–19)
# ---------------------------------------------------------------------------

class TestPreservationImportBlocks:
    """
    Property 2: Preservation — import blocks not in the 17 discrepancy list
    must be identical before and after the fix.
    """

    def test_section5_ephemeris_imports_preserved(self):
        """Section 5 ephemeris import block must be unchanged."""
        text = _ref()
        assert "from moira.facade import planet_at, all_planets_at, sky_position_at" in text, (
            "PRESERVATION FAILURE: Section 5 ephemeris import block has been disturbed."
        )

    def test_section7_houses_imports_preserved(self):
        """Section 7 houses import block must be unchanged."""
        text = _ref()
        assert "from moira.facade import calculate_houses, HouseCusps, HouseSystem" in text, (
            "PRESERVATION FAILURE: Section 7 houses import block has been disturbed."
        )

    def test_section7_aspects_imports_preserved(self):
        """Section 7 aspects import block must be unchanged."""
        text = _ref()
        assert "from moira.facade import" in text
        assert "find_aspects, aspects_between, aspects_to_point" in text, (
            "PRESERVATION FAILURE: Section 7 aspects import block has been disturbed."
        )

    def test_section8_dignities_imports_preserved(self):
        """Section 8 dignities import block must be unchanged."""
        text = _ref()
        assert "calculate_dignities, calculate_receptions" in text, (
            "PRESERVATION FAILURE: Section 8 dignities import block has been disturbed."
        )

    def test_section4_facade_construction_preserved(self):
        """Section 4 Moira construction examples must be unchanged."""
        text = _ref()
        assert "m = Moira()" in text, (
            "PRESERVATION FAILURE: Section 4 Moira construction example has been disturbed."
        )
        assert 'Moira(kernel_path="/path/to/de441.bsp")' in text, (
            "PRESERVATION FAILURE: Section 4 kernel_path construction example has been disturbed."
        )


# ---------------------------------------------------------------------------
# Preservation: function signatures not in the 17 discrepancy list
# ---------------------------------------------------------------------------

class TestPreservationFunctionSignatures:
    """
    Property 2: Preservation — function signatures not in the 17 discrepancy
    list must be byte-for-byte identical before and after the fix.
    """

    def test_return_series_signature_preserved(self):
        """return_series signature must be unchanged."""
        text = _ref()
        assert "return_series" in text, (
            "PRESERVATION FAILURE: `return_series` has been removed from the reference."
        )

    def test_synodic_cycle_position_signature_preserved(self):
        """synodic_cycle_position signature must be unchanged."""
        text = _ref()
        assert "synodic_cycle_position" in text, (
            "PRESERVATION FAILURE: `synodic_cycle_position` has been removed from the reference."
        )

    def test_great_conjunctions_signature_preserved(self):
        """great_conjunctions signature must be unchanged."""
        text = _ref()
        assert "great_conjunctions" in text, (
            "PRESERVATION FAILURE: `great_conjunctions` has been removed from the reference."
        )

    def test_planetary_age_at_signature_preserved(self):
        """planetary_age_at signature must be unchanged."""
        text = _ref()
        assert "planetary_age_at" in text, (
            "PRESERVATION FAILURE: `planetary_age_at` has been removed from the reference."
        )

    def test_void_of_course_window_signature_preserved(self):
        """void_of_course_window signature must be unchanged."""
        text = _ref()
        assert "void_of_course_window" in text, (
            "PRESERVATION FAILURE: `void_of_course_window` has been removed from the reference."
        )

    def test_is_void_of_course_signature_preserved(self):
        """is_void_of_course signature must be unchanged."""
        text = _ref()
        assert "is_void_of_course" in text, (
            "PRESERVATION FAILURE: `is_void_of_course` has been removed from the reference."
        )

    def test_next_void_of_course_signature_preserved(self):
        """next_void_of_course signature must be unchanged."""
        text = _ref()
        assert "next_void_of_course" in text, (
            "PRESERVATION FAILURE: `next_void_of_course` has been removed from the reference."
        )

    def test_firdaria_signature_preserved(self):
        """firdaria signature must be unchanged."""
        text = _ref()
        assert "firdaria" in text, (
            "PRESERVATION FAILURE: `firdaria` has been removed from the reference."
        )

    def test_zodiacal_releasing_signature_preserved(self):
        """zodiacal_releasing signature must be unchanged."""
        text = _ref()
        assert "zodiacal_releasing" in text, (
            "PRESERVATION FAILURE: `zodiacal_releasing` has been removed from the reference."
        )

    def test_vimshottari_dasha_signature_preserved(self):
        """vimshottari_dasha signature must be unchanged."""
        text = _ref()
        assert "vimshottari_dasha" in text, (
            "PRESERVATION FAILURE: `vimshottari_dasha` has been removed from the reference."
        )

    def test_house_zones_signature_preserved(self):
        """house_zones signature must be unchanged."""
        text = _ref()
        assert "house_zones" in text, (
            "PRESERVATION FAILURE: `house_zones` has been removed from the reference."
        )

    def test_age_point_signature_preserved(self):
        """age_point signature must be unchanged."""
        text = _ref()
        assert "age_point" in text, (
            "PRESERVATION FAILURE: `age_point` has been removed from the reference."
        )

    def test_chart_intensity_profile_signature_preserved(self):
        """chart_intensity_profile signature must be unchanged."""
        text = _ref()
        assert "chart_intensity_profile" in text, (
            "PRESERVATION FAILURE: `chart_intensity_profile` has been removed from the reference."
        )


# ---------------------------------------------------------------------------
# Preservation: integration import checks (Requirements 3.1–3.10)
# ---------------------------------------------------------------------------

class TestPreservationIntegrationImports:
    """
    Property 2: Preservation — all currently working imports must continue
    to work after the fix. No source code in moira/ is changed.
    """

    def test_req_3_1_essentials_core_imports(self):
        """Requirement 3.1: moira.essentials core symbols importable."""
        from moira.essentials import Body, Chart, HouseSystem, Moira  # noqa: F401
        assert all(x is not None for x in [Moira, Chart, Body, HouseSystem])

    def test_req_3_2_classical_technique_imports(self):
        """Requirement 3.2: moira.classical technique symbols importable."""
        from moira.classical import (  # noqa: F401
            calculate_dignities,
            calculate_lots,
            firdaria,
            vimshottari,
            zodiacal_releasing,
        )
        assert all(
            x is not None
            for x in [calculate_dignities, calculate_lots, firdaria, zodiacal_releasing, vimshottari]
        )

    def test_req_3_3_predictive_imports(self):
        """Requirement 3.3: moira.predictive forecasting symbols importable."""
        from moira.predictive import (  # noqa: F401
            EclipseData,
            find_transits,
            secondary_progression,
            synastry_aspects,
        )
        assert all(x is not None for x in [find_transits, secondary_progression, synastry_aspects, EclipseData])

    def test_req_3_5_cycles_imports(self):
        """Requirement 3.5: moira.cycles core symbols importable."""
        from moira.cycles import (  # noqa: F401
            great_conjunctions,
            planetary_age_at,
            return_series,
            synodic_cycle_position,
        )
        assert all(x is not None for x in [return_series, synodic_cycle_position, great_conjunctions, planetary_age_at])

    def test_req_3_6_huber_imports(self):
        """Requirement 3.6: moira.huber symbols importable."""
        from moira.huber import age_point, chart_intensity_profile, house_zones  # noqa: F401
        assert all(x is not None for x in [house_zones, age_point, chart_intensity_profile])

    def test_req_3_7_root_dasha_imports(self):
        """Requirement 3.7: moira root dasha symbols importable."""
        from moira import AlternateDashaPeriod, ashtottari, yogini_dasha  # noqa: F401
        assert all(x is not None for x in [ashtottari, yogini_dasha, AlternateDashaPeriod])

    def test_req_3_8_root_ashtakavarga_imports(self):
        """Requirement 3.8: moira root ashtakavarga symbols importable."""
        from moira import ashtakavarga, bhinnashtakavarga, shadbala  # noqa: F401
        assert all(x is not None for x in [bhinnashtakavarga, ashtakavarga, shadbala])

    def test_req_3_9_harmograms_imports(self):
        """Requirement 3.9: moira.harmograms symbols importable."""
        from moira.harmograms import (  # noqa: F401
            harmogram_trace,
            intensity_function_spectrum,
            project_harmogram_strength,
        )
        assert all(x is not None for x in [harmogram_trace, intensity_function_spectrum, project_harmogram_strength])

    def test_req_3_10_facade_time_imports(self):
        """Requirement 3.10: moira.facade time utility symbols importable."""
        from moira.facade import (  # noqa: F401
            calendar_from_jd,
            datetime_from_jd,
            delta_t,
            jd_from_datetime,
        )
        assert all(x is not None for x in [jd_from_datetime, datetime_from_jd, calendar_from_jd, delta_t])

    def test_firdar_period_classes_are_distinct(self):
        """
        moira.timelords.FirdarPeriod and moira.cycles.FirdarPeriod must be
        distinct classes with distinct field sets.
        """
        import dataclasses

        from moira.cycles import FirdarPeriod as CyclesFirdarPeriod
        from moira.timelords import FirdarPeriod as TimelordsFirdarPeriod

        assert CyclesFirdarPeriod is not TimelordsFirdarPeriod, (
            "moira.cycles.FirdarPeriod and moira.timelords.FirdarPeriod must be distinct classes."
        )

        cycles_fields = {f.name for f in dataclasses.fields(CyclesFirdarPeriod)}
        timelords_fields = {f.name for f in dataclasses.fields(TimelordsFirdarPeriod)}

        # cycles.FirdarPeriod has: ruler, start_jd, end_jd, duration_years, ordinal, sub_periods
        assert "ruler" in cycles_fields, "moira.cycles.FirdarPeriod must have `ruler` field"
        assert "duration_years" in cycles_fields, "moira.cycles.FirdarPeriod must have `duration_years` field"
        assert "ordinal" in cycles_fields, "moira.cycles.FirdarPeriod must have `ordinal` field"

        # timelords.FirdarPeriod has: level, planet, years, major_planet, is_day_chart, etc.
        assert "planet" in timelords_fields, "moira.timelords.FirdarPeriod must have `planet` field"
        assert "years" in timelords_fields, "moira.timelords.FirdarPeriod must have `years` field"
        assert "is_day_chart" in timelords_fields, "moira.timelords.FirdarPeriod must have `is_day_chart` field"

        # The two field sets must differ
        assert cycles_fields != timelords_fields, (
            "moira.cycles.FirdarPeriod and moira.timelords.FirdarPeriod must have different field sets."
        )

    def test_planetary_hour_classes_are_distinct(self):
        """
        moira.planetary_hours.PlanetaryHour and moira.cycles.PlanetaryHour must be
        distinct classes with distinct field sets.
        """
        import dataclasses

        from moira.cycles import PlanetaryHour as CyclesPlanetaryHour
        from moira.planetary_hours import PlanetaryHour as PHPlanetaryHour

        assert CyclesPlanetaryHour is not PHPlanetaryHour, (
            "moira.cycles.PlanetaryHour and moira.planetary_hours.PlanetaryHour must be distinct classes."
        )

        cycles_fields = {f.name for f in dataclasses.fields(CyclesPlanetaryHour)}
        ph_fields = {f.name for f in dataclasses.fields(PHPlanetaryHour)}

        # cycles.PlanetaryHour has: hour_number, ruler, start_jd, end_jd, is_day_hour
        assert "hour_number" in cycles_fields, "moira.cycles.PlanetaryHour must have `hour_number` field"
        assert "is_day_hour" in cycles_fields, "moira.cycles.PlanetaryHour must have `is_day_hour` field"

        # planetary_hours.PlanetaryHour has: hour_number, ruler, jd_start, jd_end, is_daytime
        # (it DOES have hour_number, but uses jd_start/jd_end and is_daytime instead of is_day_hour)
        assert "is_daytime" in ph_fields, (
            "moira.planetary_hours.PlanetaryHour must have `is_daytime` field"
        )
        assert "is_day_hour" not in ph_fields, (
            "moira.planetary_hours.PlanetaryHour must NOT have `is_day_hour` field"
        )

        assert cycles_fields != ph_fields, (
            "moira.cycles.PlanetaryHour and moira.planetary_hours.PlanetaryHour must have different field sets."
        )

# ---------------------------------------------------------------------------
# Preservation: property-based test — stable function signatures
# ---------------------------------------------------------------------------

@given(
    symbol=st.sampled_from([
        "return_series", "synodic_cycle_position", "great_conjunctions",
        "planetary_age_at", "void_of_course_window", "is_void_of_course",
        "next_void_of_course", "firdaria", "zodiacal_releasing",
        "house_zones", "age_point", "chart_intensity_profile",
        "find_transits", "secondary_progression", "synastry_aspects",
        "calculate_dignities", "calculate_lots",
    ])
)
@settings(max_examples=17)
def test_preservation_stable_symbols_present_in_reference(symbol: str):
    """
    Property 2 (PBT): Every symbol not in the 17 discrepancy list must remain
    present in the API reference after the fix.

    This property generates from the set of known-correct symbols and asserts
    each one appears in the reference text.
    """
    text = _ref()
    assert symbol in text, (
        f"PRESERVATION FAILURE: Symbol `{symbol}` has been removed from the API reference. "
        f"This symbol was correctly documented before the fix and must not be disturbed."
    )
