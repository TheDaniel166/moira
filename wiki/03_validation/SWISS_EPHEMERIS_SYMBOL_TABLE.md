# Swiss Ephemeris Symbol Table

Generated from the exact `pyswisseph` `2.10.3.2` source distribution
plus local Moira audit rules.

This is the canonical row-by-row ledger for Swiss-to-Moira mapping work.

Total symbols: 432

Status meanings:
- `mapped`: a public Moira surface exists for the Swiss symbol's semantic job.
- `supported`: a public Moira surface exists and is intentionally admitted, but
  through a materially different typed API shape rather than a close symbol/form
  correspondence.
- `partial`: Moira covers the same semantic area, but not as a 1:1 symbol/signature/flag mapping.
- `stdlib`: use Python or standard-library facilities instead of a Moira surface.
- `missing`: no public Moira equivalent currently exists.
- `unsupported`: Swiss-only internal/backend/file/control symbol with no Moira migration surface.

Truth basis meanings:
- `exact_math`: same mathematical operation or result family is exposed directly.
- `decomposed_math`: same mathematical result exists, but is split across multiple Moira calls/results.
- `embedded_math`: the Swiss concept exists implicitly inside a richer Moira result.
- `api_shape_same_math`: the same underlying math/doctrine exists, but only through a materially different API shape.
- `api_shape_different`: the capability is intentionally supported, but through
  a typed Moira-shaped surface rather than a close Swiss-style symbol or flag.
- `api_shape_domain`: the same domain/problem area is covered, but not with a claim of identical underlying math.
- `symbolic`: constant/identifier correspondence rather than a numeric algorithm claim.
- `stdlib`: handled by Python/stdlib rather than Moira.
- `none`: no public Moira migration surface.
- `exact_math` and `decomposed_math` rows are assigned explicitly for audited symbols; they are not left to generic fallback classification.

Status totals:
- `mapped`: 101
- `supported`: 18
- `partial`: 87
- `stdlib`: 22
- `missing`: 133
- `unsupported`: 71

Truth-basis totals:
- `exact_math`: 20
- `decomposed_math`: 4
- `embedded_math`: 1
- `api_shape_same_math`: 74
- `api_shape_different`: 18
- `api_shape_domain`: 22
- `symbolic`: 67
- `stdlib`: 22
- `none`: 204

| Symbol | Kind | Status | Truth basis | Moira equivalent | Notes |
| --- | --- | --- | --- | --- | --- |
| `__version__` | constant | mapped | `symbolic` | `moira.__version__` | same concept, different module |
| `ACRONYCHAL_RISING` | constant | partial | `api_shape_domain` | `HeliacalEventKind.ACRONYCHAL_RISING` in `moira.heliacal` | design vessel exists; heliacal computation still deferred pending validation oracle |
| `ACRONYCHAL_SETTING` | constant | partial | `api_shape_domain` | `HeliacalEventKind.ACRONYCHAL_SETTING` in `moira.heliacal` | design vessel exists; heliacal computation still deferred pending validation oracle |
| `ADMETOS` | constant | mapped | `symbolic` | `UranianBody.ADMETOS` | verified Uranian support |
| `APOLLON` | constant | mapped | `symbolic` | `UranianBody.APOLLON` | verified Uranian support |
| `APP_TO_TRUE` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `ARMC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `ASC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `AST_OFFSET` | constant | mapped | `symbolic` | `asteroid_at(...)` family | asteroid access exists |
| `ASTNAMFILE` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `AUNIT_TO_KM` | constant | unsupported | `none` | none | Swiss internal conversion/mode constant is not part of Moira public API |
| `AUNIT_TO_LIGHTYEAR` | constant | unsupported | `none` | none | Swiss internal conversion/mode constant is not part of Moira public API |
| `AUNIT_TO_PARSEC` | constant | unsupported | `none` | none | Swiss internal conversion/mode constant is not part of Moira public API |
| `BIT_ASTRO_TWILIGHT` | constant | partial | `api_shape_same_math` | `twilight_times(...)` | dedicated twilight result surface replaces mode bits |
| `BIT_CIVIL_TWILIGHT` | constant | partial | `api_shape_same_math` | `twilight_times(...)` | dedicated twilight result surface replaces mode bits |
| `BIT_DISC_BOTTOM` | constant | supported | `api_shape_different` | `RiseSetPolicy(disc_reference='bottom')` | typed doctrine field replaces integer bit |
| `BIT_DISC_CENTER` | constant | supported | `api_shape_different` | `RiseSetPolicy(disc_reference='center')` | typed doctrine field replaces integer bit |
| `BIT_FIXED_DISC_SIZE` | constant | supported | `api_shape_different` | `RiseSetPolicy(fixed_disc_size=True)` | typed doctrine field replaces integer bit |
| `BIT_FORCE_SLOW_METHOD` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `BIT_HINDU_RISING` | constant | supported | `api_shape_different` | `RiseSetPolicy(hindu_rising=True)` | typed doctrine field replaces integer bit |
| `BIT_NAUTIC_TWILIGHT` | constant | partial | `api_shape_same_math` | `twilight_times(...)` | dedicated twilight result surface replaces mode bits |
| `BIT_NO_REFRACTION` | constant | supported | `api_shape_different` | `RiseSetPolicy(refraction=False)` | typed doctrine field replaces integer bit |
| `CALC_ITRANSIT` | constant | partial | `api_shape_same_math` | `get_transit(..., upper=False)` | boolean parameter instead of selector flag |
| `CALC_MTRANSIT` | constant | partial | `api_shape_same_math` | `get_transit(..., upper=True)` | boolean parameter instead of selector flag |
| `CALC_RISE` | constant | partial | `api_shape_same_math` | `find_phenomena(...)['Rise']` | event key instead of selector flag |
| `CALC_SET` | constant | partial | `api_shape_same_math` | `find_phenomena(...)['Set']` | event key instead of selector flag |
| `CERES` | constant | mapped | `symbolic` | `'Ceres'` | body identifier |
| `CHIRON` | constant | mapped | `symbolic` | `'Chiron'` | centaur / body identifier |
| `COASC1` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `COASC2` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `COMET_OFFSET` | constant | missing | `none` | none | Swiss selector/offset surface has no public Moira equivalent |
| `COSMICAL_SETTING` | constant | partial | `api_shape_domain` | `HeliacalEventKind.COSMIC_SETTING` in `moira.heliacal` | design vessel exists; heliacal computation still deferred pending validation oracle |
| `CUPIDO` | constant | mapped | `symbolic` | `UranianBody.CUPIDO` | verified Uranian support |
| `DE_NUMBER` | constant | unsupported | `none` | none | Swiss build/runtime constant not part of Moira API |
| `DELTAT_AUTOMATIC` | constant | unsupported | `none` | none | Swiss internal delta-T mode constant not exposed |
| `EARTH` | constant | mapped | `symbolic` | `Body.EARTH` / `'Earth'` | body identifier |
| `ECL2HOR` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `ECL_1ST_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_2ND_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_3RD_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_4TH_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_ALLTYPES_LUNAR` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_ALLTYPES_SOLAR` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_ANNULAR` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_ANNULAR_TOTAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_CENTRAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_HYBRID` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_MAX_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_NONCENTRAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_NUT` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_OCC_BEG_DAYLIGHT` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_OCC_END_DAYLIGHT` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_ONE_TRY` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PARTBEG_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PARTEND_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PARTIAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PENUMBBEG_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PENUMBEND_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_PENUMBRAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_TOTAL` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_TOTBEG_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_TOTEND_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `ECL_VISIBLE` | constant | partial | `api_shape_same_math` | typed eclipse classification and event vessels | not exposed as Swiss flag bits |
| `EPHE_PATH` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `EQU2HOR` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `EQUASC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `EVENING_FIRST` | constant | missing | `none` | none | no current Moira event-kind equivalent |
| `EVENING_LAST` | constant | missing | `none` | none | no current Moira event-kind equivalent |
| `FICT_MAX` | constant | unsupported | `none` | none | Swiss internal range constant not part of Moira API |
| `FICT_OFFSET` | constant | partial | `api_shape_same_math` | `moira.uranian` and selected body modules | hypothetical-body family exists, but not as Swiss numeric offsets |
| `FICT_OFFSET_1` | constant | partial | `api_shape_same_math` | `moira.uranian` and selected body modules | hypothetical-body family exists, but not as Swiss numeric offsets |
| `FICTFILE` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FIXSTAR` | constant | unsupported | `none` | none | Swiss catalog constant not needed in Moira API |
| `FLG_ASTROMETRIC` | constant | supported | `api_shape_different` | `planet_at(..., apparent=False)` | typed bool kwarg replaces integer flag |
| `FLG_BARYCTR` | constant | supported | `api_shape_different` | `planet_at(..., center='barycentric')` | typed string kwarg replaces integer flag |
| `FLG_CENTER_BODY` | constant | missing | `none` | none | Swiss selector/offset surface has no public Moira equivalent |
| `FLG_DEFAULTEPH` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_DPSIDEPS_1980` | constant | missing | `none` | none | no public nutation-model switch verified |
| `FLG_EQUATORIAL` | constant | partial | `api_shape_same_math` | `sky_position_at(...)` / coordinate transforms | equatorial outputs exist, but not as a calc flag |
| `FLG_HELCTR` | constant | mapped | `symbolic` | `heliocentric_planet_at(...)`, `m.heliocentric(...)` | verified |
| `FLG_ICRS` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_J2000` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_JPLEPH` | constant | unsupported | `none` | none | Swiss backend selector not relevant to Moira |
| `FLG_JPLHOR` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_JPLHOR_APPROX` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_MOSEPH` | constant | unsupported | `none` | none | Swiss backend selector not relevant to Moira |
| `FLG_NOABERR` | constant | supported | `api_shape_different` | `planet_at(..., aberration=False)` | typed bool kwarg replaces integer flag |
| `FLG_NOGDEFL` | constant | supported | `api_shape_different` | `planet_at(..., grav_deflection=False)` | typed bool kwarg replaces integer flag |
| `FLG_NONUT` | constant | supported | `api_shape_different` | `planet_at(..., nutation=False)` | typed bool kwarg replaces integer flag |
| `FLG_ORBEL_AA` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_RADIANS` | constant | stdlib | `stdlib` | convert in caller | Moira uses degrees |
| `FLG_SIDEREAL` | constant | mapped | `symbolic` | sidereal helpers / ayanamsa conversion | no flag needed |
| `FLG_SPEED` | constant | mapped | `embedded_math` | built into `PlanetData.speed` | no flag needed |
| `FLG_SPEED3` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_SWIEPH` | constant | unsupported | `none` | none | Swiss backend selector not relevant to Moira |
| `FLG_TEST_PLMOON` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_TOPOCTR` | constant | mapped | `symbolic` | per-call observer coordinates | no flag needed |
| `FLG_TROPICAL` | constant | unsupported | `none` | none | Swiss calc/backend flag is not exposed as a public constant in Moira |
| `FLG_TRUEPOS` | constant | supported | `api_shape_different` | `planet_at(..., apparent=False)` | same as FLG_ASTROMETRIC; typed bool kwarg replaces integer flag |
| `FLG_XYZ` | constant | supported | `api_shape_different` | `planet_at(..., frame='cartesian')` → `CartesianPosition` | typed string kwarg + result vessel replaces integer flag |
| `FNAME_DE200` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DE403` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DE404` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DE405` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DE406` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DFT` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `FNAME_DFT2` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `GREG_CAL` | constant | partial | `api_shape_same_math` | `julian_day(...)` default Gregorian | same doctrine, different API |
| `HADES` | constant | mapped | `symbolic` | `UranianBody.HADES` | verified Uranian support |
| `HARRINGTON` | constant | unsupported | `none` | none | fictional/hypothetical body not exposed by Moira |
| `HELFLAG_AV` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_AVKIND` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_AVKIND_MIN7` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_AVKIND_MIN9` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_AVKIND_PTO` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_AVKIND_VR` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_HIGH_PRECISION` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_LONG_SEARCH` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_NO_DETAILS` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_OPTICAL_PARAMS` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_SEARCH_1_PERIOD` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_VISLIM_DARK` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_VISLIM_NOMOON` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELFLAG_VISLIM_PHOTOPIC` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_AVKIND` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_AVKIND_MIN7` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_AVKIND_MIN9` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_AVKIND_PTO` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_AVKIND_VR` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_HIGH_PRECISION` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_LONG_SEARCH` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_NO_DETAILS` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_OPTICAL_PARAMS` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_RISING` | constant | partial | `api_shape_same_math` | `heliacal_rising(...)` | event exists as dedicated function, not selector constant |
| `HELIACAL_SEARCH_1_PERIOD` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_SETTING` | constant | partial | `api_shape_same_math` | `heliacal_setting(...)` | event exists as dedicated function, not selector constant |
| `HELIACAL_VISLIM_DARK` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_VISLIM_NOMOON` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HELIACAL_VISLIM_PHOTOPIC` | constant | missing | `none` | none | no direct Swiss-style heliacal option surface |
| `HOR2ECL` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `HOR2EQU` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `INTP_APOG` | constant | missing | `none` | none | Swiss selector/offset surface has no public Moira equivalent |
| `INTP_PERG` | constant | missing | `none` | none | Swiss selector/offset surface has no public Moira equivalent |
| `ISIS` | constant | mapped | `symbolic` | `main_belt_at('Isis', ...)` | named small-body support exists |
| `JUL_CAL` | constant | partial | `api_shape_same_math` | `calendar_from_jd(...)` / calendar helpers | same doctrine, different API |
| `JUNO` | constant | mapped | `symbolic` | `'Juno'` | body identifier |
| `JUPITER` | constant | mapped | `symbolic` | `Body.JUPITER` / `'Jupiter'` | body identifier |
| `KRONOS` | constant | mapped | `symbolic` | `UranianBody.KRONOS` | verified Uranian support |
| `MARS` | constant | mapped | `symbolic` | `Body.MARS` / `'Mars'` | body identifier |
| `MAX_STNAME` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `MC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `MEAN_APOG` | constant | mapped | `symbolic` | `Body.LILITH` | closest body identifier |
| `MEAN_NODE` | constant | mapped | `symbolic` | `Body.MEAN_NODE` | body identifier |
| `MERCURY` | constant | mapped | `symbolic` | `Body.MERCURY` / `'Mercury'` | body identifier |
| `MIXEDOPIC_FLAG` | constant | missing | `none` | none | no direct Swiss-style visibility option surface |
| `MOD_BIAS_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_BIAS_IAU2000` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_BIAS_IAU2006` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_BIAS_NONE` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_ESPENAK_MEEUS_2006` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_STEPHENSON_1997` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_STEPHENSON_ETC_2016` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_STEPHENSON_MORRISON_1984` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_DELTAT_STEPHENSON_MORRISON_2004` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHOR_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHOR_LONG_AGREEMENT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHORA_1` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHORA_2` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHORA_3` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_JPLHORA_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NBIAS` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NDELTAT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NJPLHOR` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NJPLHORA` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NNUT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NPREC` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_IAU_1980` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_IAU_2000A` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_IAU_2000B` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_IAU_CORR_1987` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_NUT_WOOLARD` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_BRETAGNON_2003` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_DEFAULT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_DEFAULT_SHORT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_IAU_1976` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_IAU_2000` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_IAU_2006` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_LASKAR_1986` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_NEWCOMB` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_OWEN_1990` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_SIMON_1994` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_VONDRAK_2011` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_WILL_EPS_LASK` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOD_PREC_WILLIAMS_1994` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_BIAS` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_DELTAT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_JPLHOR_MODE` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_JPLHORA_MODE` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_NUT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_PREC_LONGTERM` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_PREC_SHORTTERM` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MODEL_SIDT` | constant | missing | `none` | none | Swiss model-tuning constants are not exposed publicly |
| `MOON` | constant | mapped | `symbolic` | `Body.MOON` / `'Moon'` | body identifier |
| `MORNING_FIRST` | constant | missing | `none` | none | no current Moira event-kind equivalent |
| `MORNING_LAST` | constant | missing | `none` | none | no current Moira event-kind equivalent |
| `NALL_NAT_POINTS` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NASCMC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `NEPTUNE` | constant | mapped | `symbolic` | `Body.NEPTUNE` / `'Neptune'` | body identifier |
| `NEPTUNE_ADAMS` | constant | unsupported | `none` | none | obsolete/hypothetical body constant not exposed |
| `NEPTUNE_LEVERRIER` | constant | unsupported | `none` | none | obsolete/hypothetical body constant not exposed |
| `NFICT_ELEM` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NIBIRU` | constant | unsupported | `none` | none | fictional/hypothetical body not exposed by Moira |
| `NODBIT_FOPOINT` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NODBIT_MEAN` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NODBIT_OSCU` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NODBIT_OSCU_BAR` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NPLANETS` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NSE_MODELS` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `NSIDM_PREDEF` | constant | unsupported | `none` | none | Swiss internal/module-size constant |
| `OSCU_APOG` | constant | mapped | `symbolic` | `Body.TRUE_LILITH` | closest body identifier |
| `PALLAS` | constant | mapped | `symbolic` | `'Pallas'` | body identifier |
| `PHOLUS` | constant | mapped | `symbolic` | `'Pholus'` | centaur / body identifier |
| `PHOTOPIC_FLAG` | constant | missing | `none` | none | no direct Swiss-style visibility option surface |
| `PLMOON_OFFSET` | constant | missing | `none` | none | Swiss selector/offset surface has no public Moira equivalent |
| `PLUTO` | constant | mapped | `symbolic` | `Body.PLUTO` / `'Pluto'` | body identifier |
| `PLUTO_LOWELL` | constant | unsupported | `none` | none | obsolete/hypothetical body constant not exposed |
| `PLUTO_PICKERING` | constant | unsupported | `none` | none | obsolete/hypothetical body constant not exposed |
| `POLASC` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `POSEIDON` | constant | mapped | `symbolic` | `UranianBody.POSEIDON` | verified Uranian support |
| `PROSERPINA` | constant | mapped | `symbolic` | `main_belt_at('Proserpina', ...)` | named small-body support exists |
| `SATURN` | constant | mapped | `symbolic` | `Body.SATURN` / `'Saturn'` | body identifier |
| `SCOTOPIC_FLAG` | constant | missing | `none` | none | no direct Swiss-style visibility option surface |
| `SE_FNAME_DE431` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_ECL_DATE` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_ECL_T0` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_NO_PREC_OFFSET` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_PREC_ORIG` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_SSY_PLANE` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBIT_USER_UT` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDBITS` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `SIDM_ALDEBARAN_15TAU` | constant | mapped | `symbolic` | `Ayanamsa.ALDEBARAN_15_TAU` | verified naming difference |
| `SIDM_ARYABHATA` | constant | mapped | `symbolic` | `Ayanamsa.ARYABHATA` | verified |
| `SIDM_ARYABHATA_522` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_ARYABHATA_MSUN` | constant | mapped | `symbolic` | `Ayanamsa.ARYABHATA_MSUN` | verified |
| `SIDM_B1950` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_BABYL_BRITTON` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_BABYL_ETPSC` | constant | mapped | `symbolic` | `Ayanamsa.ETA_PISCIUM` | verified naming difference |
| `SIDM_BABYL_HUBER` | constant | mapped | `symbolic` | `Ayanamsa.HUBER` | verified |
| `SIDM_BABYL_KUGLER1` | constant | mapped | `symbolic` | `Ayanamsa.KUGLER_1` | verified naming difference |
| `SIDM_BABYL_KUGLER2` | constant | mapped | `symbolic` | `Ayanamsa.KUGLER_2` | verified naming difference |
| `SIDM_BABYL_KUGLER3` | constant | mapped | `symbolic` | `Ayanamsa.KUGLER_3` | verified naming difference |
| `SIDM_DELUCE` | constant | mapped | `symbolic` | `Ayanamsa.DE_LUCE` | verified naming difference |
| `SIDM_DJWHAL_KHUL` | constant | mapped | `symbolic` | `Ayanamsa.DJWHAL_KHUL` | verified |
| `SIDM_FAGAN_BRADLEY` | constant | mapped | `symbolic` | `Ayanamsa.FAGAN_BRADLEY` | verified |
| `SIDM_GALALIGN_MARDYKS` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_GALCENT_0SAG` | constant | mapped | `symbolic` | `Ayanamsa.GALACTIC_0_SAG` | verified naming difference |
| `SIDM_GALCENT_COCHRANE` | constant | mapped | `symbolic` | `Ayanamsa.GALCENT_COCHRANE` | verified naming difference |
| `SIDM_GALCENT_MULA_WILHELM` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_GALCENT_RGILBRAND` | constant | mapped | `symbolic` | `Ayanamsa.GALCENT_RG_BRAND` | verified naming difference |
| `SIDM_GALEQU_FIORENZA` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_GALEQU_IAU1958` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_GALEQU_MULA` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_GALEQU_TRUE` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_HIPPARCHOS` | constant | mapped | `symbolic` | `Ayanamsa.HIPPARCHOS` | verified |
| `SIDM_J1900` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_J2000` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_JN_BHASIN` | constant | mapped | `symbolic` | `Ayanamsa.BHASIN` | verified naming difference |
| `SIDM_KRISHNAMURTI` | constant | mapped | `symbolic` | `Ayanamsa.KRISHNAMURTI` | verified |
| `SIDM_KRISHNAMURTI_VP291` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_LAHIRI` | constant | mapped | `symbolic` | `Ayanamsa.LAHIRI` | verified |
| `SIDM_LAHIRI_1940` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_LAHIRI_ICRC` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_LAHIRI_VP285` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_RAMAN` | constant | mapped | `symbolic` | `Ayanamsa.RAMAN` | verified |
| `SIDM_SASSANIAN` | constant | mapped | `symbolic` | `Ayanamsa.SASSANIAN` | verified |
| `SIDM_SS_CITRA` | constant | mapped | `symbolic` | `Ayanamsa.SS_CITRA` | verified |
| `SIDM_SS_REVATI` | constant | mapped | `symbolic` | `Ayanamsa.SS_REVATI` | verified |
| `SIDM_SURYASIDDHANTA` | constant | mapped | `symbolic` | `Ayanamsa.SURYASIDDHANTA` | verified |
| `SIDM_SURYASIDDHANTA_MSUN` | constant | mapped | `symbolic` | `Ayanamsa.SURYASIDDHANTA_MSUN` | verified |
| `SIDM_TRUE_CITRA` | constant | mapped | `symbolic` | `Ayanamsa.TRUE_CHITRAPAKSHA` | verified naming difference |
| `SIDM_TRUE_MULA` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_TRUE_PUSHYA` | constant | mapped | `symbolic` | `Ayanamsa.TRUE_PUSHYA` | verified |
| `SIDM_TRUE_REVATI` | constant | mapped | `symbolic` | `Ayanamsa.TRUE_REVATI` | verified |
| `SIDM_TRUE_SHEORAN` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_USER` | constant | mapped | `api_shape_same_math` | `UserDefinedAyanamsa(reference_value_j2000, drift_per_century)` in `moira.sidereal` | fully functional; replaces Swiss global-mutation pattern with a typed frozen dataclass |
| `SIDM_USHASHASHI` | constant | mapped | `symbolic` | `Ayanamsa.USHA_SHASHI` | verified naming difference |
| `SIDM_VALENS_MOON` | constant | missing | `none` | none | not present in current `Ayanamsa` namespace |
| `SIDM_YUKTESHWAR` | constant | mapped | `symbolic` | `Ayanamsa.YUKTESHWAR` | verified |
| `SIMULATE_VICTORVB` | constant | unsupported | `none` | none | Swiss compatibility flag not part of Moira API |
| `SPLIT_DEG_KEEP_DEG` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_KEEP_SIGN` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_NAKSHATRA` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_ROUND_DEG` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_ROUND_MIN` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_ROUND_SEC` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `SPLIT_DEG_ZODIACAL` | constant | stdlib | `stdlib` | local arithmetic/formatting | no dedicated audited helper |
| `STARFILE` | constant | unsupported | `none` | none | Swiss file-path constants not relevant to Moira API |
| `STARFILE_OLD` | constant | unsupported | `none` | none | Swiss file constant not part of Moira API |
| `SUN` | constant | mapped | `symbolic` | `Body.SUN` / `'Sun'` | body identifier |
| `TIDAL_26` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_AUTOMATIC` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE200` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE403` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE404` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE405` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE406` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE421` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE422` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE430` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE431` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DE441` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_DEFAULT` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_JPLEPH` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_MOSEPH` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_STEPHENSON_2016` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TIDAL_SWIEPH` | constant | missing | `none` | none | tidal-acceleration override family is not exposed publicly |
| `TJD_INVALID` | constant | unsupported | `none` | none | Swiss engine/file/mode constant is not part of the Moira public API |
| `TRUE_NODE` | constant | mapped | `symbolic` | `Body.TRUE_NODE` | body identifier |
| `TRUE_TO_APP` | constant | unsupported | `none` | none | Swiss transform selector constant is not needed by the Moira API |
| `URANUS` | constant | mapped | `symbolic` | `Body.URANUS` / `'Uranus'` | body identifier |
| `VARUNA` | constant | mapped | `symbolic` | `tno_at('Varuna', ...)` | named small-body support exists |
| `VENUS` | constant | mapped | `symbolic` | `Body.VENUS` / `'Venus'` | body identifier |
| `version` | constant | mapped | `symbolic` | `moira.__version__` | same concept, different module |
| `VERTEX` | constant | partial | `api_shape_same_math` | house result vessels / chart angles | same concept, different API shape |
| `VESTA` | constant | mapped | `symbolic` | `'Vesta'` | body identifier |
| `VULCAN` | constant | unsupported | `none` | none | fictional/hypothetical body not exposed by Moira |
| `VULKANUS` | constant | mapped | `symbolic` | `UranianBody.VULKANUS` | verified Uranian support |
| `WALDEMATH` | constant | unsupported | `none` | none | fictional/hypothetical body not exposed by Moira |
| `WHITE_MOON` | constant | unsupported | `none` | none | fictional/hypothetical body not exposed by Moira |
| `ZEUS` | constant | mapped | `symbolic` | `UranianBody.ZEUS` | verified Uranian support |
| `azalt` | function | partial | `api_shape_domain` | `equatorial_to_horizontal(...)` | equatorial transform exists; Swiss one-call mode/pressure wrapper does not |
| `azalt_rev` | function | supported | `api_shape_different` | `horizontal_to_equatorial(az, alt, lst, lat)` | standalone typed helper replaces Swiss in/out array |
| `calc` | function | partial | `api_shape_same_math` | `planet_at(..., jd_tt=...)` | TT-capable body-position pipeline exists, but Swiss tuple/flag shape does not |
| `calc_pctr` | function | mapped | `api_shape_same_math` | `planet_relative_to(body, center_body, jd_ut, reader)` → `PlanetData` in `moira.planets` | typed typed helper; center body is a named `Body.*` constant, not a numeric offset |
| `calc_ut` | function | partial | `api_shape_same_math` | `planet_at(...)`, `m.chart(...)`, `m.sky_position(...)` | Swiss umbrella surface is split across multiple Moira position APIs |
| `close` | function | unsupported | `none` | none | no C-library lifecycle |
| `cotrans` | function | mapped | `decomposed_math` | `ecliptic_to_equatorial(...)`, `equatorial_to_ecliptic(...)` | same coordinate-transform math, split into directional helpers |
| `cotrans_sp` | function | supported | `api_shape_different` | `cotrans_sp(lon, lat, dist, dlon, dlat, ddist, obliquity)` | typed tuple-return helper replaces Swiss array in/out |
| `cs2degstr` | function | stdlib | `stdlib` | formatting | no dedicated Moira helper needed |
| `cs2lonlatstr` | function | stdlib | `stdlib` | formatting | no dedicated Moira helper needed |
| `cs2timestr` | function | stdlib | `stdlib` | formatting | no dedicated Moira helper needed |
| `csnorm` | function | unsupported | `none` | none | not meaningful for Moira API surface |
| `csroundsec` | function | stdlib | `stdlib` | formatting/rounding | no dedicated Moira helper needed |
| `d2l` | function | stdlib | `stdlib` | `int(...)` | no Moira helper needed |
| `date_conversion` | function | partial | `api_shape_domain` | `julian_day(...)`, `calendar_from_jd(...)`, datetime helpers | calendar-conversion semantics exist, but not as one Swiss validation function |
| `day_of_week` | function | stdlib | `stdlib` | Python `datetime.date.weekday()` | no dedicated Moira helper needed |
| `deg_midp` | function | stdlib | `stdlib` | modular arithmetic | no dedicated Moira helper needed |
| `degnorm` | function | mapped | `exact_math` | `normalize_degrees(...)` | verified |
| `deltat` | function | partial | `api_shape_domain` | `delta_t(year_decimal)` | signature differs |
| `deltat_ex` | function | partial | `api_shape_same_math` | `delta_t(...)` | Delta-T value exists, but Swiss flag-controlled variant does not |
| `difcs2n` | function | unsupported | `none` | none | centisecond-format Swiss utility |
| `difcsn` | function | unsupported | `none` | none | centisecond-format Swiss utility |
| `difdeg2n` | function | stdlib | `stdlib` | modular arithmetic | no dedicated Moira helper needed |
| `difdegn` | function | stdlib | `stdlib` | modular arithmetic | no dedicated Moira helper needed |
| `difrad2n` | function | stdlib | `stdlib` | Python `math` plus modular arithmetic | no dedicated Moira helper needed |
| `fixstar` | function | mapped | `exact_math` | `fixed_star_at(...)`, `m.fixed_star(...)` | same fixed-star position pipeline |
| `fixstar2` | function | mapped | `exact_math` | `fixed_star_at(...)`, `m.fixed_star(...)` | same fixed-star position pipeline |
| `fixstar2_mag` | function | mapped | `exact_math` | `star_magnitude(...)` | verified |
| `fixstar2_ut` | function | mapped | `exact_math` | `fixed_star_at(...)`, `m.fixed_star(...)` | same fixed-star position pipeline |
| `fixstar_mag` | function | mapped | `exact_math` | `star_magnitude(...)` | verified |
| `fixstar_ut` | function | mapped | `exact_math` | `fixed_star_at(...)`, `m.fixed_star(...)` | same fixed-star position pipeline; low-level surface is TT-oriented |
| `gauquelin_sector` | function | mapped | `exact_math` | `moira.gauquelin.gauquelin_sector(...)`, `all_gauquelin_sectors(...)`, `m.gauquelin_sectors(...)` | same Gauquelin sector computation; wrappers also exist |
| `get_ayanamsa` | function | mapped | `exact_math` | `moira.sidereal.ayanamsa(...)` | function accepts TT or UT semantics directly |
| `get_ayanamsa_ex` | function | partial | `api_shape_same_math` | `ayanamsa(...)` | ayanamsa value exists, but Swiss flag-return variant does not |
| `get_ayanamsa_ex_ut` | function | partial | `api_shape_same_math` | `ayanamsa(...)` | ayanamsa value exists, but Swiss flag-return variant does not |
| `get_ayanamsa_name` | function | partial | `api_shape_domain` | `Ayanamsa` string constants | use symbolic constants directly; no Swiss-style label helper |
| `get_ayanamsa_ut` | function | mapped | `exact_math` | `moira.sidereal.ayanamsa(...)` | verified function, different name |
| `get_current_file_data` | function | missing | `none` | none | kernel/file introspection helper is not exposed |
| `get_library_path` | function | missing | `none` | none | pure-Python engine has no Swiss library path surface |
| `get_orbital_elements` | function | partial | `api_shape_same_math` | `orbital_elements_at(body, jd_ut)` -> `KeplerianElements` in `moira.orbits` | implemented as a typed heliocentric osculating-element surface; validated against JPL HORIZONS |
| `get_planet_name` | function | partial | `api_shape_domain` | `Body.*` constants / canonical body strings | names are first-class identifiers rather than lookup results |
| `get_tid_acc` | function | missing | `none` | none | no public tidal-acceleration getter exists |
| `heliacal_pheno_ut` | function | missing | `none` | none | no detailed heliacal-phenomena helper is exposed |
| `heliacal_ut` | function | partial | `api_shape_domain` | star heliacal helpers in `fixed_stars` and facade | fixed-star heliacal search exists, but not as the Swiss generalized event wrapper |
| `helio_cross` | function | mapped | `api_shape_same_math` | `next_heliocentric_transit(body, target_lon, jd_start, reader)` → `float` in `moira.planets` | UT-native; adaptive scan + bisection; raises on `Body.SUN` |
| `helio_cross_ut` | function | mapped | `api_shape_same_math` | `next_heliocentric_transit(body, target_lon, jd_start, reader)` → `float` in `moira.planets` | same as `helio_cross`; Moira uses UT natively so no separate UT variant is needed |
| `house_name` | function | partial | `api_shape_same_math` | `HOUSE_SYSTEM_NAMES`, `HouseSystem` constants | name table exists, but not as Swiss byte-code helper |
| `house_pos` | function | mapped | `api_shape_same_math` | `body_house_position(longitude, house_cusps)` → `float` in `moira.houses` | returns fractional house number (e.g. 3.75 = 75% through house 3) |
| `houses` | function | mapped | `exact_math` | `calculate_houses(...)`, `m.houses(...)` | same house-cusp computation is exposed directly |
| `houses_armc` | function | mapped | `api_shape_same_math` | `houses_from_armc(armc, obliquity, lat, system, *, policy, sun_longitude)` → `HouseCusps` in `moira.houses` | full 18-system dispatch; typed policy replaces integer flags |
| `houses_armc_ex2` | function | mapped | `api_shape_same_math` | `house_dynamics_from_armc(armc, obliquity, lat, system, *, policy, sun_longitude, darmc_deg)` → `HouseDynamics` in `moira.houses` | ARMC-native house dynamics now exist directly; fixed-obliquity finite difference in ARMC space replaces the Swiss extended tuple surface |
| `houses_ex` | function | partial | `api_shape_same_math` | `calculate_houses(...)` plus sidereal conversion separately | sidereal house output exists, but not as a flags-based wrapper |
| `houses_ex2` | function | mapped | `api_shape_same_math` | `cusp_speeds_at(jd_ut, lat, lon, system, *, policy, dt)` → `HouseDynamics` in `moira.houses` | centred finite difference over ±dt; returns typed `CuspSpeed` + angle speeds; 23 unit tests passing |
| `jdet_to_utc` | function | partial | `api_shape_same_math` | `datetime_from_jd(...)`, `calendar_datetime_from_jd(...)` | shape differs |
| `jdut1_to_utc` | function | partial | `api_shape_same_math` | `datetime_from_jd(...)`, `calendar_datetime_from_jd(...)` | JD-to-calendar conversion exists, but not as a distinct UT1-labelled helper |
| `julday` | function | mapped | `exact_math` | `moira.julian.julian_day(...)` | verified |
| `lat_to_lmt` | function | missing | `none` | none | no local-mean-time helper is exposed |
| `lmt_to_lat` | function | missing | `none` | none | no local-mean-time helper is exposed |
| `lun_eclipse_how` | function | partial | `api_shape_same_math` | `lunar_local_circumstances(...)` / analysis bundle | shape differs |
| `lun_eclipse_when` | function | partial | `api_shape_domain` | `EclipseCalculator.next_lunar_eclipse(...)` | class method |
| `lun_eclipse_when_loc` | function | partial | `api_shape_same_math` | `EclipseCalculator.lunar_local_circumstances(...)` | shape differs |
| `lun_occult_when_glob` | function | partial | `api_shape_domain` | `all_lunar_occultations(...)`, `m.occultations(...)` | present, not Swiss-shaped |
| `lun_occult_when_loc` | function | partial | `api_shape_same_math` | `lunar_occultation(..., observer_lat=..., observer_lon=...)` | local occultation search exists, but not as Swiss return-shape wrapper |
| `lun_occult_where` | function | partial | `api_shape_domain` | `lunar_occultation_path_at(...)`, `lunar_star_occultation_path_at(...)` -> `OccultationPathGeometry` in `moira.occultations` | exact-JD path geometry is implemented; current external validation includes Swiss `where` maximum geography plus multiple external IOTA graze/limit text slices (El Nath, Spica N/S, epsilon Ari, Alcyone, Merope, Asellus Borealis, Regulus). Nominal site altitude is honoured where the source declares it, and a lunar-limb profile correction hook now exists for future topography-backed graze refinement. |
| `mooncross` | function | mapped | `exact_math` | `next_transit('Moon', target_lon, jd_start)` | same target-longitude crossing search |
| `mooncross_node` | function | mapped | `exact_math` | `next_moon_node_crossing(jd_start, reader, ascending=True)` → `float` in `moira.nodes` | 0.5-day scan + 52-iteration bisection on geocentric ecliptic latitude |
| `mooncross_node_ut` | function | mapped | `api_shape_same_math` | `next_moon_node_crossing(jd_start, reader, ascending=True)` → `float` in `moira.nodes` | same as `mooncross_node`; Moira is UT-native so no separate UT variant needed |
| `mooncross_ut` | function | mapped | `exact_math` | `next_transit('Moon', target_lon, jd_start)` | same target-longitude crossing search |
| `nod_aps` | function | partial | `api_shape_domain` | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | Moira splits planetary nodes/apsides from the separate lunar-node surfaces |
| `nod_aps_ut` | function | partial | `api_shape_domain` | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | Moira splits planetary nodes/apsides from the separate lunar-node surfaces |
| `orbit_max_min_true_distance` | function | partial | `api_shape_same_math` | `distance_extremes_at(body, jd_ut)` -> `DistanceExtremes` in `moira.orbits` | implemented as a typed perihelion/aphelion search surface; validated against JPL HORIZONS vector-derived heliocentric extrema |
| `pheno` | function | mapped | `decomposed_math` | `phase_angle(...)`, `illuminated_fraction(...)`, `elongation(...)`, `angular_diameter(...)`, `apparent_magnitude(...)` | semantic equivalent split across phase helpers |
| `pheno_ut` | function | mapped | `decomposed_math` | `phase_angle(...)`, `illuminated_fraction(...)`, `elongation(...)`, `angular_diameter(...)`, `apparent_magnitude(...)` | semantic equivalent split across phase helpers |
| `rad_midp` | function | stdlib | `stdlib` | Python `math` plus modular arithmetic | no dedicated Moira helper needed |
| `radnorm` | function | stdlib | `stdlib` | Python `math` modulo | no dedicated Moira helper needed |
| `refrac` | function | supported | `api_shape_different` | `atmospheric_refraction(altitude_deg, ...)` | typed kwargs replace Swiss int mode flag |
| `refrac_extended` | function | supported | `api_shape_different` | `atmospheric_refraction_extended(altitude_deg, ...)` | typed kwargs replace Swiss struct; returns (refraction, dip) tuple |
| `revjul` | function | mapped | `exact_math` | `moira.julian.calendar_from_jd(...)` | verified |
| `rise_trans` | function | partial | `decomposed_math` | `find_phenomena(...)`, `get_transit(...)` | split API |
| `rise_trans_true_hor` | function | partial | `api_shape_same_math` | `find_phenomena(..., altitude=...)` | custom horizon altitude is supported, but not via Swiss rsmi wrapper |
| `set_delta_t_userdef` | function | supported | `api_shape_different` | `DeltaTPolicy(model='fixed', fixed_delta_t=...)` passed to `ut_to_tt()` / `planet_at()` | typed immutable policy replaces Swiss global mutable state |
| `set_ephe_path` | function | mapped | `api_shape_domain` | `Moira(kernel_path=...)`, `set_kernel_path(...)` | same configuration job, but via path injection rather than Swiss global state |
| `set_jpl_file` | function | mapped | `api_shape_domain` | `Moira(kernel_path=...)`, `set_kernel_path(...)` | same configuration job, but via full kernel path rather than Swiss file-name switch |
| `set_lapse_rate` | function | missing | `none` | none | no public lapse-rate override surface exists |
| `set_sid_mode` | function | partial | `api_shape_domain` | per-call `ayanamsa(...)`, sidereal helpers, `Ayanamsa` constants | no global mode |
| `set_tid_acc` | function | missing | `none` | none | no public tidal-acceleration setter exists |
| `set_topo` | function | partial | `api_shape_domain` | per-call `observer_lat`, `observer_lon`, `observer_elev_m` | no global observer state |
| `sidtime` | function | mapped | `exact_math` | `greenwich_mean_sidereal_time(...)` | verified |
| `sidtime0` | function | mapped | `exact_math` | `apparent_sidereal_time(...)` | verified direct helper |
| `sol_eclipse_how` | function | partial | `api_shape_domain` | `solar_local_circumstances(...)` | closest current local-attribute surface |
| `sol_eclipse_when_glob` | function | partial | `api_shape_domain` | `EclipseCalculator.next_solar_eclipse(...)` | class method, not flat function |
| `sol_eclipse_when_loc` | function | partial | `api_shape_same_math` | `EclipseCalculator.solar_local_circumstances(...)` | shape differs |
| `sol_eclipse_where` | function | partial | `api_shape_domain` | `EclipseCalculator.solar_eclipse_path(...)` -> `SolarEclipsePath` in `moira.eclipse` | numerical greatest-geography and sampled central-track surface implemented; current external validation is Swiss `where` maximum geography |
| `solcross` | function | mapped | `exact_math` | `next_transit('Sun', target_lon, jd_start)` | same target-longitude crossing search |
| `solcross_ut` | function | mapped | `exact_math` | `next_transit('Sun', target_lon, jd_start)` | same target-longitude crossing search |
| `split_deg` | function | stdlib | `stdlib` | local arithmetic | no dedicated audited helper |
| `time_equ` | function | supported | `api_shape_different` | `equation_of_time(jd_tt)` | returns EoT in degrees; multiply by 4 for minutes of time |
| `utc_time_zone` | function | stdlib | `stdlib` | Python `datetime`/`zoneinfo` | not a Moira concern |
| `utc_to_jd` | function | partial | `api_shape_domain` | `jd_from_datetime(...)` | UTC datetime -> single JD helper exists; Swiss dual TT/UT return does not |
| `vis_limit_mag` | function | missing | `none` | none | no public visual-limiting-magnitude helper is exposed |

