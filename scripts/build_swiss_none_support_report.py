from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "moira" / "docs" / "SWISS_EPHEMERIS_SYMBOL_TABLE.md"
OUTPUT = ROOT / "moira" / "docs" / "SWISS_EPHEMERIS_NONE_SUPPORT_REPORT.md"


def parse_none_rows() -> list[dict[str, str]]:
    text = SOURCE.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if line.startswith("| `") and "| `none` |" in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            rows.append(
                {
                    "symbol": parts[0].strip("`"),
                    "kind": parts[1],
                    "status": parts[2],
                    "truth_basis": parts[3].strip("`"),
                    "equivalent": parts[4],
                    "notes": parts[5],
                }
            )
    return rows


def decide(symbol: str, kind: str, status: str, notes: str) -> tuple[str, str, str, str]:
    if symbol in {
        "APP_TO_TRUE", "TRUE_TO_APP", "ECL2HOR", "EQU2HOR", "HOR2ECL", "HOR2EQU",
        "ASTNAMFILE", "EPHE_PATH", "FICTFILE", "STARFILE", "STARFILE_OLD",
        "FNAME_DE200", "FNAME_DE403", "FNAME_DE404", "FNAME_DE405", "FNAME_DE406",
        "FNAME_DFT", "FNAME_DFT2", "SE_FNAME_DE431",
        "AUNIT_TO_KM", "AUNIT_TO_LIGHTYEAR", "AUNIT_TO_PARSEC",
        "DE_NUMBER", "DELTAT_AUTOMATIC", "FICT_MAX", "MAX_STNAME", "NALL_NAT_POINTS",
        "NFICT_ELEM", "NPLANETS", "NSE_MODELS", "NSIDM_PREDEF", "TJD_INVALID",
        "NODBIT_FOPOINT", "NODBIT_MEAN", "NODBIT_OSCU", "NODBIT_OSCU_BAR",
        "SIDBIT_ECL_DATE", "SIDBIT_ECL_T0", "SIDBIT_NO_PREC_OFFSET", "SIDBIT_PREC_ORIG",
        "SIDBIT_SSY_PLANE", "SIDBIT_USER_UT", "SIDBITS",
        "FLG_DEFAULTEPH", "FLG_ICRS", "FLG_J2000", "FLG_JPLEPH", "FLG_JPLHOR",
        "FLG_JPLHOR_APPROX", "FLG_MOSEPH", "FLG_ORBEL_AA", "FLG_SPEED3",
        "FLG_SWIEPH", "FLG_TEST_PLMOON", "FLG_TROPICAL",
        "BIT_FORCE_SLOW_METHOD", "SIMULATE_VICTORVB",
        "close", "csnorm", "difcs2n", "difcsn", "get_library_path",
    }:
        return (
            "do_not_support",
            "Swiss internal/backend/file/control surface",
            "These are Swiss implementation details or C-library affordances, not stable domain concepts Moira should mirror.",
            "No Moira surface. Keep them out of the public API.",
        )

    if symbol in {
        "HARRINGTON", "NEPTUNE_ADAMS", "NEPTUNE_LEVERRIER", "NIBIRU",
        "PLUTO_LOWELL", "PLUTO_PICKERING", "VULCAN", "WALDEMATH", "WHITE_MOON",
    }:
        return (
            "do_not_support",
            "Hypothetical / obsolete body constant",
            "These are not part of Moira's supported physical body model.",
            "No Moira surface. If ever desired, add them only in a clearly separate hypothetical-bodies module.",
        )

    if symbol in {"BIT_DISC_BOTTOM", "BIT_DISC_CENTER", "BIT_FIXED_DISC_SIZE", "BIT_HINDU_RISING", "BIT_NO_REFRACTION"}:
        return (
            "support",
            "Rise/set doctrine selector",
            "These are real event-definition choices that matter for migration and reproducibility.",
            "Add a typed `RiseSetPolicy` / `RiseSetOptions` surface with fields like `disc_reference`, `fixed_disc_size`, `hindu_rising`, and `refraction`.",
        )

    if symbol in {"FLG_ASTROMETRIC", "FLG_BARYCTR", "FLG_NOABERR", "FLG_NOGDEFL", "FLG_NONUT", "FLG_TRUEPOS", "FLG_XYZ"}:
        return (
            "support",
            "Position-computation switch",
            "These correspond to meaningful output/control choices users genuinely need when migrating precision astronomy code.",
            "Expose them through typed kwargs/policies on `planet_at(...)` and facade wrappers: `center='barycentric'`, `frame='cartesian'`, `apparent=False`, `aberration=False`, `grav_deflection=False`, `nutation=False`.",
        )

    if symbol == "FLG_DPSIDEPS_1980":
        return (
            "defer",
            "Nutation-model selector",
            "A model-basis control is reasonable, but Swiss's flag is too narrow to mirror blindly.",
            "If added, expose a typed `NutationPolicy` or `nutation_model=` option rather than a Swiss compatibility flag.",
        )

    if symbol in {
        "ACRONYCHAL_RISING", "ACRONYCHAL_SETTING", "COSMICAL_SETTING",
        "EVENING_FIRST", "EVENING_LAST", "MORNING_FIRST", "MORNING_LAST",
        "HELFLAG_AV", "HELFLAG_AVKIND", "HELFLAG_AVKIND_MIN7", "HELFLAG_AVKIND_MIN9",
        "HELFLAG_AVKIND_PTO", "HELFLAG_AVKIND_VR", "HELFLAG_HIGH_PRECISION",
        "HELFLAG_LONG_SEARCH", "HELFLAG_NO_DETAILS", "HELFLAG_OPTICAL_PARAMS",
        "HELFLAG_SEARCH_1_PERIOD", "HELFLAG_VISLIM_DARK", "HELFLAG_VISLIM_NOMOON",
        "HELFLAG_VISLIM_PHOTOPIC", "HELIACAL_AVKIND", "HELIACAL_AVKIND_MIN7",
        "HELIACAL_AVKIND_MIN9", "HELIACAL_AVKIND_PTO", "HELIACAL_AVKIND_VR",
        "HELIACAL_HIGH_PRECISION", "HELIACAL_LONG_SEARCH", "HELIACAL_NO_DETAILS",
        "HELIACAL_OPTICAL_PARAMS", "HELIACAL_SEARCH_1_PERIOD", "HELIACAL_VISLIM_DARK",
        "HELIACAL_VISLIM_NOMOON", "HELIACAL_VISLIM_PHOTOPIC", "PHOTOPIC_FLAG",
        "SCOTOPIC_FLAG", "MIXEDOPIC_FLAG", "heliacal_pheno_ut", "vis_limit_mag",
    }:
        return (
            "defer",
            "Generalized heliacal / visibility surface",
            "This is a valid domain, but Moira should not accrete Swiss-style bitfields before the heliacal subsystem is unified and validated.",
            "Introduce typed surfaces such as `HeliacalEventKind`, `HeliacalPolicy`, and `VisibilityModel`, then map selected behaviors onto those.",
        )

    if symbol in {"COMET_OFFSET", "FLG_CENTER_BODY", "INTP_APOG", "INTP_PERG", "PLMOON_OFFSET"}:
        return (
            "do_not_support",
            "Swiss numeric selector / offset idiom",
            "The underlying capability may be valuable, but the Swiss numeric-offset selector pattern is not a good Moira API.",
            "Expose named body-specific or typed helper APIs instead of numeric offsets or interpolation bits.",
        )

    if symbol == "SIDM_USER":
        return (
            "support",
            "User-defined ayanamsa",
            "Custom sidereal frames are a legitimate specialist requirement and fit Moira's typed-configuration model.",
            "Add `UserDefinedAyanamsa(epoch_jd, offset_degrees)` and accept it anywhere `Ayanamsa.*` is accepted.",
        )

    if symbol.startswith("SIDM_"):
        return (
            "defer",
            "Additional ayanamsa constant",
            "Some of these may be worth supporting, but they should be added only when the doctrine/reference basis is explicit.",
            "Audit each candidate individually, then add it as a named `Ayanamsa.*` constant rather than for blanket Swiss parity.",
        )

    if symbol.startswith("MOD_") or symbol.startswith("MODEL_") or symbol.startswith("TIDAL_") or symbol in {"get_tid_acc", "set_tid_acc"}:
        return (
            "defer",
            "Model-basis / tidal-acceleration control",
            "These are scientifically meaningful, but Swiss's sprawling constant matrix is not the right Moira surface.",
            "If needed, add compact typed controls such as `DeltaTPolicy`, `PrecessionPolicy`, `NutationPolicy`, or `TidalAccelerationPolicy`.",
        )

    if symbol in {"azalt_rev", "cotrans_sp", "refrac", "refrac_extended", "time_equ"}:
        return (
            "support",
            "Low-level astronomy helper",
            "These are standard computational helpers with clear mathematical meaning and low API ambiguity.",
            "Expose direct low-level functions in the relevant modules: reverse horizontal transform, speed-aware coordinate transform, atmospheric refraction helpers, and equation-of-time helper.",
        )

    if symbol in {"calc_pctr", "house_pos", "houses_armc", "helio_cross", "helio_cross_ut", "mooncross_node", "mooncross_node_ut"}:
        return (
            "support",
            "Low-level specialist helper",
            "These are real computational surfaces that fit Moira's engine style and improve migration quality for advanced users.",
            "Add typed helpers such as `planet_relative_to(...)`, `body_house_position(...)`, `houses_from_armc(...)`, `next_heliocentric_transit(...)`, and `next_moon_node_crossing(...)`.",
        )

    if symbol in {"houses_armc_ex2", "houses_ex2"}:
        return (
            "defer",
            "House speed surface",
            "Useful for specialist work, but cusp/angle speed doctrine should be designed intentionally rather than copied from Swiss tuples.",
            "Add a `HouseDynamics` or speed-bearing house vessel only after locking the speed semantics and validation story.",
        )

    if symbol in {"get_orbital_elements", "orbit_max_min_true_distance"}:
        return (
            "defer",
            "Orbital-elements subsystem",
            "These are valuable but imply a separate public orbital-elements module with its own doctrine and tests.",
            "Add a dedicated `moira.orbits` layer with typed orbital elements and distance-extremes vessels.",
        )

    if symbol in {"lun_occult_where", "sol_eclipse_where"}:
        return (
            "defer",
            "Path/where geometry helper",
            "This is a real domain need, but the geometry/path surface should be designed as a first-class subsystem, not copied from Swiss call shapes.",
            "Introduce typed path/circumstance vessels such as `SolarEclipsePath` and `LunarOccultationPath`.",
        )

    if symbol in {"get_current_file_data", "lat_to_lmt", "lmt_to_lat"}:
        return (
            "do_not_support",
            "Legacy Swiss utility surface",
            "These are low-value utilities that do not fit Moira's core astronomy engine priorities.",
            "No Moira surface. Use Python/time utilities externally if needed.",
        )

    if symbol == "set_delta_t_userdef":
        return (
            "support",
            "Explicit Delta-T override",
            "This is a legitimate specialist control for historical/experimental work and aligns with Moira's model-basis transparency.",
            "Add a typed `delta_t_override` or `DeltaTPolicy(custom_seconds=...)` on time-sensitive search/position APIs.",
        )

    return (
        "defer",
        "Unclassified specialist gap",
        "The symbol names a real Swiss surface, but it should not be adopted without an intentional Moira-shaped design.",
        "Add only after a dedicated typed API and validation story are defined.",
    )


def build_rows() -> list[dict[str, str]]:
    rows = []
    for row in parse_none_rows():
        decision, what, why, how = decide(row["symbol"], row["kind"], row["status"], row["notes"])
        row["what"] = what
        row["decision"] = decision
        row["why"] = why
        row["how"] = how
        rows.append(row)
    return rows


def write_report(rows: list[dict[str, str]]) -> None:
    decision_counts: dict[str, int] = {"support": 0, "defer": 0, "do_not_support": 0}
    for row in rows:
        decision_counts[row["decision"]] += 1

    lines = [
        "# Swiss None-Surface Support Report",
        "",
        "This report expands the `none` truth-basis rows from",
        "`SWISS_EPHEMERIS_SYMBOL_TABLE.md` into explicit product decisions.",
        "",
        "Decision meanings:",
        "- `support`: Moira should expose this capability publicly.",
        "- `defer`: valid domain area, but should only be added after a typed Moira-shaped design pass.",
        "- `do_not_support`: Swiss-specific/internal/low-value surface that Moira should not mirror.",
        "",
        f"Total `none` rows: {len(rows)}",
        f"- `support`: {decision_counts['support']}",
        f"- `defer`: {decision_counts['defer']}",
        f"- `do_not_support`: {decision_counts['do_not_support']}",
        "",
        "Recommended support order:",
        "1. Position-computation switches and output modes (`FLG_ASTROMETRIC`, `FLG_TRUEPOS`, `FLG_NOABERR`, `FLG_NOGDEFL`, `FLG_NONUT`, `FLG_BARYCTR`, `FLG_XYZ`, `set_delta_t_userdef`).",
        "2. Rise/set doctrine selectors (`BIT_DISC_*`, `BIT_HINDU_RISING`, `BIT_NO_REFRACTION`).",
        "3. Low-level astronomy helpers (`azalt_rev`, `cotrans_sp`, `refrac`, `refrac_extended`, `time_equ`).",
        "4. Specialist search/helpers (`calc_pctr`, `house_pos`, `houses_armc`, `helio_cross*`, `mooncross_node*`).",
        "5. Deferred design families: generalized heliacal options, model-basis controls, additional ayanamsas, and path/where geometry.",
        "",
        "Interpretation:",
        "- `support` means the capability is worth adding, but usually not as a Swiss-shaped flag or tuple surface.",
        "- `defer` means the domain is real, but Moira should design a typed subsystem first.",
        "- `do_not_support` means the symbol is Swiss-internal, low-value, or contrary to Moira's API design.",
        "",
        "| Symbol | Kind | Current status | What it is | Decision | Why | How if supported |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['symbol']}` | {row['kind']} | {row['status']} | {row['what']} | "
            f"`{row['decision']}` | {row['why']} | {row['how']} |"
        )
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_report(build_rows())
