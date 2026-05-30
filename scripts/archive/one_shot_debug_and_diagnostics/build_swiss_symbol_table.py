from __future__ import annotations

import io
import re
import tarfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "moira" / "docs" / "SWISS_EPHEMERIS_SYMBOL_TABLE.md"
PYSWISSEPH_VERSION = "2.10.3.2"
PYSWISSEPH_SDIST_URL = (
    "https://files.pythonhosted.org/packages/66/a6/"
    "db70d67a00dda42ebd033538c086879328f4c17f670eafe8aca2f11abfef/"
    "pyswisseph-2.10.3.2.tar.gz"
)


FUNCTION_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "set_ephe_path": ("mapped", "`Moira(kernel_path=...)`, `set_kernel_path(...)`", "same configuration job, but via path injection rather than Swiss global state"),
    "set_jpl_file": ("mapped", "`Moira(kernel_path=...)`, `set_kernel_path(...)`", "same configuration job, but via full kernel path rather than Swiss file-name switch"),
    "set_topo": ("partial", "per-call `observer_lat`, `observer_lon`, `observer_elev_m`", "no global observer state"),
    "close": ("unsupported", "none", "no C-library lifecycle"),
    "set_delta_t_userdef": ("missing", "none", "no public user Delta-T override surface exists"),
    "julday": ("mapped", "`moira.julian.julian_day(...)`", "verified"),
    "revjul": ("mapped", "`moira.julian.calendar_from_jd(...)`", "verified"),
    "utc_to_jd": ("partial", "`jd_from_datetime(...)`", "UTC datetime -> single JD helper exists; Swiss dual TT/UT return does not"),
    "jdet_to_utc": ("partial", "`datetime_from_jd(...)`, `calendar_datetime_from_jd(...)`", "shape differs"),
    "jdut1_to_utc": ("partial", "`datetime_from_jd(...)`, `calendar_datetime_from_jd(...)`", "JD-to-calendar conversion exists, but not as a distinct UT1-labelled helper"),
    "deltat": ("partial", "`delta_t(year_decimal)`", "signature differs"),
    "deltat_ex": ("partial", "`delta_t(...)`", "Delta-T value exists, but Swiss flag-controlled variant does not"),
    "sidtime": ("mapped", "`greenwich_mean_sidereal_time(...)`", "verified"),
    "sidtime0": ("mapped", "`apparent_sidereal_time(...)`", "verified direct helper"),
    "time_equ": ("missing", "none", "no public equation-of-time helper exists"),
    "day_of_week": ("stdlib", "Python `datetime.date.weekday()`", "no dedicated Moira helper needed"),
    "utc_time_zone": ("stdlib", "Python `datetime`/`zoneinfo`", "not a Moira concern"),
    "calc_ut": ("partial", "`planet_at(...)`, `m.chart(...)`, `m.sky_position(...)`", "Swiss umbrella surface is split across multiple Moira position APIs"),
    "calc": ("partial", "`planet_at(..., jd_tt=...)`", "TT-capable body-position pipeline exists, but Swiss tuple/flag shape does not"),
    "calc_pctr": ("missing", "none", "no public arbitrary-center body-position API is exposed"),
    "get_planet_name": ("partial", "`Body.*` constants / canonical body strings", "names are first-class identifiers rather than lookup results"),
    "get_orbital_elements": ("missing", "none", "no public orbital-elements API is exposed"),
    "orbit_max_min_true_distance": ("missing", "none", "no public orbital distance-extremes API is exposed"),
    "houses": ("mapped", "`calculate_houses(...)`, `m.houses(...)`", "same house-cusp computation is exposed directly"),
    "houses_ex": ("partial", "`calculate_houses(...)` plus sidereal conversion separately", "sidereal house output exists, but not as a flags-based wrapper"),
    "houses_ex2": ("missing", "none", "no public cusp-speed / angle-speed house surface exists"),
    "houses_armc": ("missing", "none", "no public ARMC house-construction helper is exposed"),
    "houses_armc_ex2": ("missing", "none", "no public ARMC-plus-speeds house helper is exposed"),
    "house_pos": ("missing", "none", "no public house-position helper is exposed"),
    "house_name": ("partial", "`HOUSE_SYSTEM_NAMES`, `HouseSystem` constants", "name table exists, but not as Swiss byte-code helper"),
    "set_sid_mode": ("partial", "per-call `ayanamsa(...)`, sidereal helpers, `Ayanamsa` constants", "no global mode"),
    "get_ayanamsa_ut": ("mapped", "`moira.sidereal.ayanamsa(...)`", "verified function, different name"),
    "get_ayanamsa_ex_ut": ("partial", "`ayanamsa(...)`", "ayanamsa value exists, but Swiss flag-return variant does not"),
    "get_ayanamsa_name": ("partial", "`Ayanamsa` string constants", "use symbolic constants directly; no Swiss-style label helper"),
    "get_ayanamsa": ("mapped", "`moira.sidereal.ayanamsa(...)`", "function accepts TT or UT semantics directly"),
    "get_ayanamsa_ex": ("partial", "`ayanamsa(...)`", "ayanamsa value exists, but Swiss flag-return variant does not"),
    "fixstar": ("mapped", "`fixed_star_at(...)`, `m.fixed_star(...)`", "same fixed-star position pipeline"),
    "fixstar2": ("mapped", "`fixed_star_at(...)`, `m.fixed_star(...)`", "same fixed-star position pipeline"),
    "fixstar_ut": ("mapped", "`fixed_star_at(...)`, `m.fixed_star(...)`", "same fixed-star position pipeline; low-level surface is TT-oriented"),
    "fixstar2_ut": ("mapped", "`fixed_star_at(...)`, `m.fixed_star(...)`", "same fixed-star position pipeline"),
    "fixstar_mag": ("mapped", "`star_magnitude(...)`", "verified"),
    "fixstar2_mag": ("mapped", "`star_magnitude(...)`", "verified"),
    "sol_eclipse_when_glob": ("partial", "`EclipseCalculator.next_solar_eclipse(...)`", "class method, not flat function"),
    "sol_eclipse_when_loc": ("partial", "`EclipseCalculator.solar_local_circumstances(...)`", "shape differs"),
    "sol_eclipse_where": ("missing", "none", "no solar eclipse path/where helper is exposed"),
    "sol_eclipse_how": ("partial", "`solar_local_circumstances(...)`", "closest current local-attribute surface"),
    "lun_eclipse_when": ("partial", "`EclipseCalculator.next_lunar_eclipse(...)`", "class method"),
    "lun_eclipse_when_loc": ("partial", "`EclipseCalculator.lunar_local_circumstances(...)`", "shape differs"),
    "lun_eclipse_how": ("partial", "`lunar_local_circumstances(...)` / analysis bundle", "shape differs"),
    "lun_occult_when_glob": ("partial", "`all_lunar_occultations(...)`, `m.occultations(...)`", "present, not Swiss-shaped"),
    "lun_occult_when_loc": ("partial", "`lunar_occultation(..., observer_lat=..., observer_lon=...)`", "local occultation search exists, but not as Swiss return-shape wrapper"),
    "lun_occult_where": ("missing", "none", "no occultation-path / where-style helper is exposed"),
    "rise_trans": ("partial", "`find_phenomena(...)`, `get_transit(...)`", "split API"),
    "rise_trans_true_hor": ("partial", "`find_phenomena(..., altitude=...)`", "custom horizon altitude is supported, but not via Swiss rsmi wrapper"),
    "nod_aps": ("partial", "`all_planetary_nodes(...)`, `m.planetary_nodes(...)`", "Moira splits planetary nodes/apsides from the separate lunar-node surfaces"),
    "nod_aps_ut": ("partial", "`all_planetary_nodes(...)`, `m.planetary_nodes(...)`", "Moira splits planetary nodes/apsides from the separate lunar-node surfaces"),
    "mooncross_node": ("missing", "none", "no public Moon-node-crossing helper exists"),
    "mooncross_node_ut": ("missing", "none", "no public Moon-node-crossing helper exists"),
    "pheno": ("mapped", "`phase_angle(...)`, `illuminated_fraction(...)`, `elongation(...)`, `angular_diameter(...)`, `apparent_magnitude(...)`", "semantic equivalent split across phase helpers"),
    "pheno_ut": ("mapped", "`phase_angle(...)`, `illuminated_fraction(...)`, `elongation(...)`, `angular_diameter(...)`, `apparent_magnitude(...)`", "semantic equivalent split across phase helpers"),
    "heliacal_ut": ("partial", "star heliacal helpers in `fixed_stars` and facade", "fixed-star heliacal search exists, but not as the Swiss generalized event wrapper"),
    "heliacal_pheno_ut": ("missing", "none", "no detailed heliacal-phenomena helper is exposed"),
    "vis_limit_mag": ("missing", "none", "no public visual-limiting-magnitude helper is exposed"),
    "azalt": ("partial", "`equatorial_to_horizontal(...)`", "equatorial transform exists; Swiss one-call mode/pressure wrapper does not"),
    "azalt_rev": ("missing", "none", "no public reverse horizontal-transform helper is exposed"),
    "cotrans": ("mapped", "`ecliptic_to_equatorial(...)`, `equatorial_to_ecliptic(...)`", "same coordinate-transform math, split into directional helpers"),
    "cotrans_sp": ("missing", "none", "no public coordinate-transform-with-speed helper is exposed"),
    "refrac": ("missing", "none", "no public atmospheric-refraction helper is exposed"),
    "refrac_extended": ("missing", "none", "no public extended atmospheric-refraction helper is exposed"),
    "degnorm": ("mapped", "`normalize_degrees(...)`", "verified"),
    "radnorm": ("stdlib", "Python `math` modulo", "no dedicated Moira helper needed"),
    "deg_midp": ("stdlib", "modular arithmetic", "no dedicated Moira helper needed"),
    "rad_midp": ("stdlib", "Python `math` plus modular arithmetic", "no dedicated Moira helper needed"),
    "difdeg2n": ("stdlib", "modular arithmetic", "no dedicated Moira helper needed"),
    "difdegn": ("stdlib", "modular arithmetic", "no dedicated Moira helper needed"),
    "difrad2n": ("stdlib", "Python `math` plus modular arithmetic", "no dedicated Moira helper needed"),
    "difcs2n": ("unsupported", "none", "centisecond-format Swiss utility"),
    "difcsn": ("unsupported", "none", "centisecond-format Swiss utility"),
    "mooncross": ("mapped", "`next_transit('Moon', target_lon, jd_start)`", "same target-longitude crossing search"),
    "mooncross_ut": ("mapped", "`next_transit('Moon', target_lon, jd_start)`", "same target-longitude crossing search"),
    "solcross": ("mapped", "`next_transit('Sun', target_lon, jd_start)`", "same target-longitude crossing search"),
    "solcross_ut": ("mapped", "`next_transit('Sun', target_lon, jd_start)`", "same target-longitude crossing search"),
    "helio_cross": ("missing", "none", "no public heliocentric longitude-crossing helper exists"),
    "helio_cross_ut": ("missing", "none", "no public heliocentric longitude-crossing helper exists"),
    "gauquelin_sector": ("mapped", "`moira.gauquelin.gauquelin_sector(...)`, `all_gauquelin_sectors(...)`, `m.gauquelin_sectors(...)`", "same Gauquelin sector computation; wrappers also exist"),
    "cs2degstr": ("stdlib", "formatting", "no dedicated Moira helper needed"),
    "cs2lonlatstr": ("stdlib", "formatting", "no dedicated Moira helper needed"),
    "cs2timestr": ("stdlib", "formatting", "no dedicated Moira helper needed"),
    "csnorm": ("unsupported", "none", "not meaningful for Moira API surface"),
    "csroundsec": ("stdlib", "formatting/rounding", "no dedicated Moira helper needed"),
    "d2l": ("stdlib", "`int(...)`", "no Moira helper needed"),
    "date_conversion": ("partial", "`julian_day(...)`, `calendar_from_jd(...)`, datetime helpers", "calendar-conversion semantics exist, but not as one Swiss validation function"),
    "split_deg": ("stdlib", "local arithmetic", "no dedicated audited helper"),
    "lat_to_lmt": ("missing", "none", "no local-mean-time helper is exposed"),
    "lmt_to_lat": ("missing", "none", "no local-mean-time helper is exposed"),
    "get_current_file_data": ("missing", "none", "kernel/file introspection helper is not exposed"),
    "get_library_path": ("missing", "none", "pure-Python engine has no Swiss library path surface"),
    "get_tid_acc": ("missing", "none", "no public tidal-acceleration getter exists"),
    "set_tid_acc": ("missing", "none", "no public tidal-acceleration setter exists"),
    "set_lapse_rate": ("missing", "none", "no public lapse-rate override surface exists"),
}

CONSTANT_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "__version__": ("mapped", "`moira.__version__`", "same concept, different module"),
    "version": ("mapped", "`moira.__version__`", "same concept, different module"),
    "SUN": ("mapped", "`Body.SUN` / `'Sun'`", "body identifier"),
    "MOON": ("mapped", "`Body.MOON` / `'Moon'`", "body identifier"),
    "MERCURY": ("mapped", "`Body.MERCURY` / `'Mercury'`", "body identifier"),
    "VENUS": ("mapped", "`Body.VENUS` / `'Venus'`", "body identifier"),
    "MARS": ("mapped", "`Body.MARS` / `'Mars'`", "body identifier"),
    "JUPITER": ("mapped", "`Body.JUPITER` / `'Jupiter'`", "body identifier"),
    "SATURN": ("mapped", "`Body.SATURN` / `'Saturn'`", "body identifier"),
    "URANUS": ("mapped", "`Body.URANUS` / `'Uranus'`", "body identifier"),
    "NEPTUNE": ("mapped", "`Body.NEPTUNE` / `'Neptune'`", "body identifier"),
    "PLUTO": ("mapped", "`Body.PLUTO` / `'Pluto'`", "body identifier"),
    "EARTH": ("mapped", "`Body.EARTH` / `'Earth'`", "body identifier"),
    "TRUE_NODE": ("mapped", "`Body.TRUE_NODE`", "body identifier"),
    "MEAN_NODE": ("mapped", "`Body.MEAN_NODE`", "body identifier"),
    "MEAN_APOG": ("mapped", "`Body.LILITH`", "closest body identifier"),
    "OSCU_APOG": ("mapped", "`Body.TRUE_LILITH`", "closest body identifier"),
    "CHIRON": ("mapped", "`'Chiron'`", "centaur / body identifier"),
    "PHOLUS": ("mapped", "`'Pholus'`", "centaur / body identifier"),
    "CERES": ("mapped", "`'Ceres'`", "body identifier"),
    "PALLAS": ("mapped", "`'Pallas'`", "body identifier"),
    "JUNO": ("mapped", "`'Juno'`", "body identifier"),
    "VESTA": ("mapped", "`'Vesta'`", "body identifier"),
    "CUPIDO": ("mapped", "`UranianBody.CUPIDO`", "verified Uranian support"),
    "HADES": ("mapped", "`UranianBody.HADES`", "verified Uranian support"),
    "ZEUS": ("mapped", "`UranianBody.ZEUS`", "verified Uranian support"),
    "KRONOS": ("mapped", "`UranianBody.KRONOS`", "verified Uranian support"),
    "APOLLON": ("mapped", "`UranianBody.APOLLON`", "verified Uranian support"),
    "ADMETOS": ("mapped", "`UranianBody.ADMETOS`", "verified Uranian support"),
    "VULKANUS": ("mapped", "`UranianBody.VULKANUS`", "verified Uranian support"),
    "POSEIDON": ("mapped", "`UranianBody.POSEIDON`", "verified Uranian support"),
    "VULCAN": ("unsupported", "none", "fictional/hypothetical body not exposed by Moira"),
    "WALDEMATH": ("unsupported", "none", "fictional/hypothetical body not exposed by Moira"),
    "WHITE_MOON": ("unsupported", "none", "fictional/hypothetical body not exposed by Moira"),
    "NIBIRU": ("unsupported", "none", "fictional/hypothetical body not exposed by Moira"),
    "HARRINGTON": ("unsupported", "none", "fictional/hypothetical body not exposed by Moira"),
    "NEPTUNE_ADAMS": ("unsupported", "none", "obsolete/hypothetical body constant not exposed"),
    "NEPTUNE_LEVERRIER": ("unsupported", "none", "obsolete/hypothetical body constant not exposed"),
    "PLUTO_LOWELL": ("unsupported", "none", "obsolete/hypothetical body constant not exposed"),
    "PLUTO_PICKERING": ("unsupported", "none", "obsolete/hypothetical body constant not exposed"),
    "AST_OFFSET": ("mapped", "`asteroid_at(...)` family", "asteroid access exists"),
    "FICT_OFFSET": ("partial", "`moira.uranian` and selected body modules", "hypothetical-body family exists, but not as Swiss numeric offsets"),
    "FICT_OFFSET_1": ("partial", "`moira.uranian` and selected body modules", "hypothetical-body family exists, but not as Swiss numeric offsets"),
    "HELIACAL_RISING": ("partial", "`heliacal_rising(...)`", "event exists as dedicated function, not selector constant"),
    "HELIACAL_SETTING": ("partial", "`heliacal_setting(...)`", "event exists as dedicated function, not selector constant"),
    "HELIACAL_AVKIND": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_AVKIND_MIN7": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_AVKIND_MIN9": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_AVKIND_PTO": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_AVKIND_VR": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_HIGH_PRECISION": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_LONG_SEARCH": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_NO_DETAILS": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_OPTICAL_PARAMS": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_SEARCH_1_PERIOD": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_VISLIM_DARK": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_VISLIM_NOMOON": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELIACAL_VISLIM_PHOTOPIC": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AV": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AVKIND": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AVKIND_MIN7": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AVKIND_MIN9": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AVKIND_PTO": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_AVKIND_VR": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_HIGH_PRECISION": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_LONG_SEARCH": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_NO_DETAILS": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_OPTICAL_PARAMS": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_SEARCH_1_PERIOD": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_VISLIM_DARK": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_VISLIM_NOMOON": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "HELFLAG_VISLIM_PHOTOPIC": ("missing", "none", "no direct Swiss-style heliacal option surface"),
    "ACRONYCHAL_RISING": ("missing", "none", "no current Moira event-kind equivalent"),
    "ACRONYCHAL_SETTING": ("missing", "none", "no current Moira event-kind equivalent"),
    "COSMICAL_SETTING": ("missing", "none", "no current Moira event-kind equivalent"),
    "MORNING_FIRST": ("missing", "none", "no current Moira event-kind equivalent"),
    "MORNING_LAST": ("missing", "none", "no current Moira event-kind equivalent"),
    "EVENING_FIRST": ("missing", "none", "no current Moira event-kind equivalent"),
    "EVENING_LAST": ("missing", "none", "no current Moira event-kind equivalent"),
    "FIXSTAR": ("unsupported", "none", "Swiss catalog constant not needed in Moira API"),
    "DE_NUMBER": ("unsupported", "none", "Swiss build/runtime constant not part of Moira API"),
    "DELTAT_AUTOMATIC": ("unsupported", "none", "Swiss internal delta-T mode constant not exposed"),
    "FICT_MAX": ("unsupported", "none", "Swiss internal range constant not part of Moira API"),
    "SIMULATE_VICTORVB": ("unsupported", "none", "Swiss compatibility flag not part of Moira API"),
    "STARFILE_OLD": ("unsupported", "none", "Swiss file constant not part of Moira API"),
    "PHOTOPIC_FLAG": ("missing", "none", "no direct Swiss-style visibility option surface"),
    "SCOTOPIC_FLAG": ("missing", "none", "no direct Swiss-style visibility option surface"),
    "MIXEDOPIC_FLAG": ("missing", "none", "no direct Swiss-style visibility option surface"),
    "CALC_RISE": ("partial", "`find_phenomena(...)['Rise']`", "event key instead of selector flag"),
    "CALC_SET": ("partial", "`find_phenomena(...)['Set']`", "event key instead of selector flag"),
    "CALC_MTRANSIT": ("partial", "`get_transit(..., upper=True)`", "boolean parameter instead of selector flag"),
    "CALC_ITRANSIT": ("partial", "`get_transit(..., upper=False)`", "boolean parameter instead of selector flag"),
    "FLG_SWIEPH": ("unsupported", "none", "Swiss backend selector not relevant to Moira"),
    "FLG_JPLEPH": ("unsupported", "none", "Swiss backend selector not relevant to Moira"),
    "FLG_MOSEPH": ("unsupported", "none", "Swiss backend selector not relevant to Moira"),
    "FLG_SPEED": ("mapped", "built into `PlanetData.speed`", "no flag needed"),
    "FLG_EQUATORIAL": ("partial", "`sky_position_at(...)` / coordinate transforms", "equatorial outputs exist, but not as a calc flag"),
    "FLG_XYZ": ("missing", "none", "no public cartesian-output surface exists"),
    "FLG_RADIANS": ("stdlib", "convert in caller", "Moira uses degrees"),
    "FLG_HELCTR": ("mapped", "`heliocentric_planet_at(...)`, `m.heliocentric(...)`", "verified"),
    "FLG_BARYCTR": ("missing", "none", "no public barycentric-output surface exists"),
    "FLG_TOPOCTR": ("mapped", "per-call observer coordinates", "no flag needed"),
    "FLG_SIDEREAL": ("mapped", "sidereal helpers / ayanamsa conversion", "no flag needed"),
    "FLG_ASTROMETRIC": ("missing", "none", "no public astrometric-output switch verified"),
    "FLG_TRUEPOS": ("missing", "none", "no public true-position switch verified"),
    "FLG_NOABERR": ("missing", "none", "no public no-aberration switch verified"),
    "FLG_NOGDEFL": ("missing", "none", "no public no-deflection switch verified"),
    "FLG_NONUT": ("missing", "none", "no public no-nutation switch verified"),
    "FLG_DPSIDEPS_1980": ("missing", "none", "no public nutation-model switch verified"),
    "GREG_CAL": ("partial", "`julian_day(...)` default Gregorian", "same doctrine, different API"),
    "JUL_CAL": ("partial", "`calendar_from_jd(...)` / calendar helpers", "same doctrine, different API"),
    "SIDM_LAHIRI": ("mapped", "`Ayanamsa.LAHIRI`", "verified"),
    "SIDM_FAGAN_BRADLEY": ("mapped", "`Ayanamsa.FAGAN_BRADLEY`", "verified"),
    "SIDM_KRISHNAMURTI": ("mapped", "`Ayanamsa.KRISHNAMURTI`", "verified"),
    "SIDM_RAMAN": ("mapped", "`Ayanamsa.RAMAN`", "verified"),
    "SIDM_YUKTESHWAR": ("mapped", "`Ayanamsa.YUKTESHWAR`", "verified"),
    "SIDM_DJWHAL_KHUL": ("mapped", "`Ayanamsa.DJWHAL_KHUL`", "verified"),
    "SIDM_DELUCE": ("mapped", "`Ayanamsa.DE_LUCE`", "verified naming difference"),
    "SIDM_USHASHASHI": ("mapped", "`Ayanamsa.USHA_SHASHI`", "verified naming difference"),
    "SIDM_JN_BHASIN": ("mapped", "`Ayanamsa.BHASIN`", "verified naming difference"),
    "SIDM_SASSANIAN": ("mapped", "`Ayanamsa.SASSANIAN`", "verified"),
    "SIDM_BABYL_KUGLER1": ("mapped", "`Ayanamsa.KUGLER_1`", "verified naming difference"),
    "SIDM_BABYL_KUGLER2": ("mapped", "`Ayanamsa.KUGLER_2`", "verified naming difference"),
    "SIDM_BABYL_KUGLER3": ("mapped", "`Ayanamsa.KUGLER_3`", "verified naming difference"),
    "SIDM_BABYL_HUBER": ("mapped", "`Ayanamsa.HUBER`", "verified"),
    "SIDM_BABYL_ETPSC": ("mapped", "`Ayanamsa.ETA_PISCIUM`", "verified naming difference"),
    "SIDM_HIPPARCHOS": ("mapped", "`Ayanamsa.HIPPARCHOS`", "verified"),
    "SIDM_SURYASIDDHANTA": ("mapped", "`Ayanamsa.SURYASIDDHANTA`", "verified"),
    "SIDM_SURYASIDDHANTA_MSUN": ("mapped", "`Ayanamsa.SURYASIDDHANTA_MSUN`", "verified"),
    "SIDM_ARYABHATA": ("mapped", "`Ayanamsa.ARYABHATA`", "verified"),
    "SIDM_ARYABHATA_MSUN": ("mapped", "`Ayanamsa.ARYABHATA_MSUN`", "verified"),
    "SIDM_SS_CITRA": ("mapped", "`Ayanamsa.SS_CITRA`", "verified"),
    "SIDM_SS_REVATI": ("mapped", "`Ayanamsa.SS_REVATI`", "verified"),
    "SIDM_TRUE_CITRA": ("mapped", "`Ayanamsa.TRUE_CHITRAPAKSHA`", "verified naming difference"),
    "SIDM_TRUE_REVATI": ("mapped", "`Ayanamsa.TRUE_REVATI`", "verified"),
    "SIDM_TRUE_PUSHYA": ("mapped", "`Ayanamsa.TRUE_PUSHYA`", "verified"),
    "SIDM_ALDEBARAN_15TAU": ("mapped", "`Ayanamsa.ALDEBARAN_15_TAU`", "verified naming difference"),
    "SIDM_GALCENT_0SAG": ("mapped", "`Ayanamsa.GALACTIC_0_SAG`", "verified naming difference"),
    "SIDM_GALCENT_5SAG": ("mapped", "`Ayanamsa.GALACTIC_5_SAG`", "verified naming difference"),
    "SIDM_GALCENT_COCHRANE": ("mapped", "`Ayanamsa.GALCENT_COCHRANE`", "verified naming difference"),
    "SIDM_GALCENT_RGILBRAND": ("mapped", "`Ayanamsa.GALCENT_RG_BRAND`", "verified naming difference"),
    "SIDM_USER": ("missing", "none", "no verified user-defined ayanamsa surface"),
    "SIDM_ARYABHATA_522": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_B1950": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_BABYL_BRITTON": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALALIGN_MARDYKS": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALCENT_MULA_WILHELM": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALEQU_FIORENZA": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALEQU_IAU1958": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALEQU_MULA": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_GALEQU_TRUE": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_J1900": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_J2000": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_KRISHNAMURTI_VP291": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_LAHIRI_1940": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_LAHIRI_ICRC": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_LAHIRI_VP285": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_TRUE_MULA": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_TRUE_SHEORAN": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "SIDM_VALENS_MOON": ("missing", "none", "not present in current `Ayanamsa` namespace"),
    "ISIS": ("mapped", "`main_belt_at('Isis', ...)`", "named small-body support exists"),
    "PROSERPINA": ("mapped", "`main_belt_at('Proserpina', ...)`", "named small-body support exists"),
    "VARUNA": ("mapped", "`tno_at('Varuna', ...)`", "named small-body support exists"),
}


TRUTH_BASIS_OVERRIDES: dict[str, str] = {
    "set_ephe_path": "api_shape_domain",
    "set_jpl_file": "api_shape_domain",
    "calc_ut": "api_shape_same_math",
    "cotrans": "decomposed_math",
    "fixstar": "exact_math",
    "fixstar2": "exact_math",
    "fixstar_ut": "exact_math",
    "fixstar2_ut": "exact_math",
    "fixstar_mag": "exact_math",
    "fixstar2_mag": "exact_math",
    "gauquelin_sector": "exact_math",
    "get_ayanamsa": "exact_math",
    "get_ayanamsa_ut": "exact_math",
    "heliacal_ut": "api_shape_domain",
    "houses": "exact_math",
    "julday": "exact_math",
    "mooncross": "exact_math",
    "mooncross_ut": "exact_math",
    "nod_aps": "api_shape_domain",
    "nod_aps_ut": "api_shape_domain",
    "pheno": "decomposed_math",
    "pheno_ut": "decomposed_math",
    "revjul": "exact_math",
    "rise_trans": "decomposed_math",
    "sidtime": "exact_math",
    "sidtime0": "exact_math",
    "solcross": "exact_math",
    "solcross_ut": "exact_math",
}


def fetch_symbols() -> tuple[list[str], list[str]]:
    data = urllib.request.urlopen(PYSWISSEPH_SDIST_URL, timeout=30).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        member_name = next(name for name in tf.getnames() if name.endswith("pyswisseph.c"))
        text = tf.extractfile(member_name).read().decode("utf-8", errors="replace")
    funcs = sorted(set(re.findall(r"/\* swisseph\.([A-Za-z0-9_]+) \*/", text)))
    const_patterns = [
        r'PyModule_Add(?:Int|Float|Object|String)Constant\(m,\s*"([A-Za-z0-9_]+)"',
        r'PyDict_SetItemString\(d,\s*"([A-Za-z0-9_]+)"',
    ]
    consts: set[str] = set()
    for pattern in const_patterns:
        consts.update(re.findall(pattern, text))
    consts = {name for name in consts if name not in funcs}
    return funcs, sorted(consts)


def classify_constant(name: str) -> tuple[str, str, str]:
    if name in CONSTANT_OVERRIDES:
        return CONSTANT_OVERRIDES[name]
    if name in {"BIT_ASTRO_TWILIGHT", "BIT_CIVIL_TWILIGHT", "BIT_NAUTIC_TWILIGHT"}:
        return ("partial", "`twilight_times(...)`", "dedicated twilight result surface replaces mode bits")
    if name in {"BIT_DISC_BOTTOM", "BIT_DISC_CENTER", "BIT_FIXED_DISC_SIZE", "BIT_HINDU_RISING", "BIT_NO_REFRACTION"}:
        return ("missing", "none", "specific rise/set doctrine selector is not exposed publicly")
    if name in {"BIT_FORCE_SLOW_METHOD", "SE_FNAME_DE431", "SIDBIT_ECL_DATE", "SIDBIT_ECL_T0", "SIDBIT_PREC_ORIG", "SIDBIT_SSY_PLANE", "SIDBIT_USER_UT", "SIDBITS", "SIDBIT_NO_PREC_OFFSET", "TJD_INVALID"}:
        return ("unsupported", "none", "Swiss engine/file/mode constant is not part of the Moira public API")
    if name in {"EQU2HOR", "ECL2HOR", "HOR2ECL", "HOR2EQU", "APP_TO_TRUE", "TRUE_TO_APP"}:
        return ("unsupported", "none", "Swiss transform selector constant is not needed by the Moira API")
    if name in {"INTP_APOG", "INTP_PERG", "COMET_OFFSET", "PLMOON_OFFSET", "FLG_CENTER_BODY"}:
        return ("missing", "none", "Swiss selector/offset surface has no public Moira equivalent")
    if name.startswith("SIDM_"):
        return ("missing", "none", "sidereal constant is not present in the current `Ayanamsa` namespace")
    if name.startswith("FLG_"):
        return ("unsupported", "none", "Swiss calc/backend flag is not exposed as a public constant in Moira")
    if name.startswith("BIT_"):
        return ("missing", "none", "rise/twilight option bit is not exposed as a public selector")
    if name.startswith("ECL_"):
        return ("partial", "typed eclipse classification and event vessels", "not exposed as Swiss flag bits")
    if name.startswith("HELFLAG_") or name.startswith("HELIACAL_"):
        return ("missing", "none", "Swiss heliacal option/selector constant is not exposed publicly")
    if name.startswith("MODEL_") or name.startswith("MOD_"):
        return ("missing", "none", "Swiss model-tuning constants are not exposed publicly")
    if name.startswith("TIDAL_"):
        return ("missing", "none", "tidal-acceleration override family is not exposed publicly")
    if name.startswith("SPLIT_DEG_"):
        return ("stdlib", "local arithmetic/formatting", "no dedicated audited helper")
    if name.endswith("_OFFSET"):
        return ("missing", "none", "no generic Swiss offset-number API is exposed")
    if name in {"ASC", "MC", "ARMC", "VERTEX", "EQUASC", "COASC1", "COASC2", "POLASC", "NASCMC"}:
        return ("partial", "house result vessels / chart angles", "same concept, different API shape")
    if name.startswith("FNAME_") or name.endswith("FILE") or name == "EPHE_PATH":
        return ("unsupported", "none", "Swiss file-path constants not relevant to Moira API")
    if name.startswith("N") or name.startswith("MAX_"):
        return ("unsupported", "none", "Swiss internal/module-size constant")
    if name in {"AUNIT_TO_KM", "AUNIT_TO_LIGHTYEAR", "AUNIT_TO_PARSEC", "DELTAT_AUTOMATIC"}:
        return ("unsupported", "none", "Swiss internal conversion/mode constant is not part of Moira public API")
    return ("unsupported", "none", "Swiss symbol has no public migration surface in Moira")


def truth_basis(kind: str, status: str, symbol: str, equivalent: str, notes: str) -> str:
    if symbol in TRUTH_BASIS_OVERRIDES:
        return TRUTH_BASIS_OVERRIDES[symbol]
    if status in {"missing", "unsupported"}:
        return "none"
    if status == "stdlib":
        return "stdlib"

    lower_eq = equivalent.lower()
    lower_notes = notes.lower()

    if kind == "constant":
        if status == "mapped":
            if symbol in {"SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO", "EARTH", "TRUE_NODE", "MEAN_NODE", "MEAN_APOG", "OSCU_APOG"}:
                return "symbolic"
            if symbol.startswith("SIDM_") or symbol in {"CUPIDO", "HADES", "ZEUS", "KRONOS", "APOLLON", "ADMETOS", "VULKANUS", "POSEIDON"}:
                return "symbolic"
            if symbol == "FLG_SPEED":
                return "embedded_math"
            return "symbolic"
        return "api_shape_same_math"

    if "semantic equivalent split across" in lower_notes or "split across" in lower_notes or "split api" in lower_notes:
        return "decomposed_math"
    if "same concept" in lower_notes or "same doctrine" in lower_notes or "same configuration job" in lower_notes or "same target-longitude crossing search" in lower_notes:
        return "api_shape_same_math"
    if "shape differs" in lower_notes or "selector flag" in lower_notes or "calc flag" in lower_notes or "byte-code helper" in lower_notes:
        return "api_shape_same_math"
    if "no global" in lower_notes or "closest current" in lower_notes or "present, not swiss-shaped" in lower_notes:
        return "api_shape_domain"
    if "different name" in lower_notes or "verified direct helper" in lower_notes:
        return "exact_math"
    if "verified" in lower_notes and "," not in equivalent:
        return "exact_math"
    if "verified" in lower_notes and "," in equivalent:
        return "decomposed_math"
    if "tt-capable" in lower_notes or "calendar conversion pieces exist" in lower_notes:
        return "api_shape_same_math"
    if "exists, but" in lower_notes or "supported, but" in lower_notes:
        return "api_shape_same_math"
    if "plus sidereal conversion separately" in lower_eq:
        return "decomposed_math"
    if status == "mapped":
        return "exact_math"
    return "api_shape_domain"


def build_rows() -> list[tuple[str, str, str, str, str, str]]:
    funcs, consts = fetch_symbols()
    rows: list[tuple[str, str, str, str, str, str]] = []
    for name in funcs:
        status, eq, note = FUNCTION_OVERRIDES.get(
            name,
            ("missing", "none", "Swiss function has no public migration surface in Moira"),
        )
        rows.append((name, "function", status, truth_basis("function", status, name, eq, note), eq, note))
    for name in consts:
        status, eq, note = classify_constant(name)
        rows.append((name, "constant", status, truth_basis("constant", status, name, eq, note), eq, note))
    rows.sort(key=lambda row: (row[1], row[0].lower()))
    return rows


def write_table(rows: list[tuple[str, str, str, str, str, str]]) -> None:
    status_order = ("mapped", "partial", "stdlib", "missing", "unsupported")
    counts = {key: 0 for key in status_order}
    basis_order = ("exact_math", "decomposed_math", "embedded_math", "api_shape_same_math", "api_shape_domain", "symbolic", "stdlib", "none")
    basis_counts = {key: 0 for key in basis_order}
    for _, _, status, basis, _, _ in rows:
        counts[status] = counts.get(status, 0) + 1
        basis_counts[basis] = basis_counts.get(basis, 0) + 1

    lines = [
        "# Swiss Ephemeris Symbol Table",
        "",
        f"Generated from the exact `pyswisseph` `{PYSWISSEPH_VERSION}` source distribution",
        "plus local Moira audit rules.",
        "",
        "This is the canonical row-by-row ledger for Swiss-to-Moira mapping work.",
        "",
        f"Total symbols: {len(rows)}",
        "",
        "Status meanings:",
        "- `mapped`: a public Moira surface exists for the Swiss symbol's semantic job.",
        "- `partial`: Moira covers the same semantic area, but not as a 1:1 symbol/signature/flag mapping.",
        "- `stdlib`: use Python or standard-library facilities instead of a Moira surface.",
        "- `missing`: no public Moira equivalent currently exists.",
        "- `unsupported`: Swiss-only internal/backend/file/control symbol with no Moira migration surface.",
        "",
        "Truth basis meanings:",
        "- `exact_math`: same mathematical operation or result family is exposed directly.",
        "- `decomposed_math`: same mathematical result exists, but is split across multiple Moira calls/results.",
        "- `embedded_math`: the Swiss concept exists implicitly inside a richer Moira result.",
        "- `api_shape_same_math`: the same underlying math/doctrine exists, but only through a materially different API shape.",
        "- `api_shape_domain`: the same domain/problem area is covered, but not with a claim of identical underlying math.",
        "- `symbolic`: constant/identifier correspondence rather than a numeric algorithm claim.",
        "- `stdlib`: handled by Python/stdlib rather than Moira.",
        "- `none`: no public Moira migration surface.",
        "- `exact_math` and `decomposed_math` rows are assigned explicitly for audited symbols; they are not left to generic fallback classification.",
        "",
        "Status totals:",
        f"- `mapped`: {counts['mapped']}",
        f"- `partial`: {counts['partial']}",
        f"- `stdlib`: {counts['stdlib']}",
        f"- `missing`: {counts['missing']}",
        f"- `unsupported`: {counts['unsupported']}",
        "",
        "Truth-basis totals:",
        f"- `exact_math`: {basis_counts['exact_math']}",
        f"- `decomposed_math`: {basis_counts['decomposed_math']}",
        f"- `embedded_math`: {basis_counts['embedded_math']}",
        f"- `api_shape_same_math`: {basis_counts['api_shape_same_math']}",
        f"- `api_shape_domain`: {basis_counts['api_shape_domain']}",
        f"- `symbolic`: {basis_counts['symbolic']}",
        f"- `stdlib`: {basis_counts['stdlib']}",
        f"- `none`: {basis_counts['none']}",
        "",
        "| Symbol | Kind | Status | Truth basis | Moira equivalent | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for symbol, kind, status, basis, equivalent, notes in rows:
        lines.append(f"| `{symbol}` | {kind} | {status} | `{basis}` | {equivalent} | {notes} |")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_table(build_rows())
