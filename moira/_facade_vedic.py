"""
Internal Vedic-method mixin for the public Moira facade.

These wrappers preserve the public ``Moira`` convenience surface while
delegating Panchanga, Pancha Pakshi, Shadbala, Jaimini, Ashtakavarga, and
Varga computation to their owning modules.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from datetime import date
from fractions import Fraction
from typing import Any
from .spk_reader import MissingEphemerisKernelError

_shadbala = importlib.import_module("moira.shadbala")
_varga = importlib.import_module("moira.varga")
_panchanga = importlib.import_module("moira.panchanga")
_daily_panchanga = importlib.import_module("moira.daily_panchanga")
_lunar_month = importlib.import_module("moira.lunar_month")
_gochara_dated = importlib.import_module("moira.gochara_dated")
_avasthas = importlib.import_module("moira.avasthas")
_sayanadi_dated = importlib.import_module("moira.sayanadi_dated")
_named_muhurta = importlib.import_module("moira.named_muhurta")
_special_muhurta = importlib.import_module("moira.special_muhurta")
_panchanga_shuddhi = importlib.import_module("moira.panchanga_shuddhi")
_muhurta_search = importlib.import_module("moira.muhurta_search")
_pancha_pakshi = importlib.import_module("moira.pancha_pakshi")


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class VedicFacadeMixin:
    """RITE: The Vedic Witness - the layer that routes the public Moira
    surface to Vedic computational techniques without owning their doctrine.

THEOREM: Mixin that provides Vedic astrological convenience wrappers for the
         public ``moira.facade.Moira`` class, delegating each computation to
         the authoritative owning module.

RITE OF PURPOSE:
    VedicFacadeMixin gives Python callers direct, coherent access to the
    Vedic families already admitted through engine/root and REST surfaces:
    Panchanga, Pancha Pakshi, Shadbala, Jaimini, Ashtakavarga, and Varga. It
    does not create new doctrine or route-shaped envelopes.

LAW OF OPERATION:
    Responsibilities:
        - Delegate Vedic computations to facade-module callables.
        - Provide chart-backed helpers only where the chart and houses already
          carry the required source truth.
    Non-responsibilities:
        - Does not implement Vedic calculations itself.
        - Does not derive location truth or create charts.
        - Does not return REST transport envelopes.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
    Structural invariants:
        - All methods delegate to owning module/root callables.

Canon: Moira Sovereign Facade Architecture; moira.panchanga,
       moira.pancha_pakshi, moira.shadbala, moira.jaimini,
       moira.ashtakavarga, moira.varga.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_vedic.VedicFacadeMixin",
    "risk": "medium",
    "api": {
        "frozen": [
            "panchanga", "panchanga_profile", "daily_panchanga", "lunar_month_at",
            "pancha_pakshi_profiles", "pancha_pakshi_profile_info",
            "pancha_pakshi_uromarisi_constitution_status",
            "pancha_pakshi_astronomical_paksha",
            "pancha_pakshi_nakshatra_bird_mapping",
            "pancha_pakshi_natal_moon_identity",
            "pancha_pakshi_first_eat_bird_mapping",
            "pancha_pakshi_padu_bird_mapping",
            "pancha_pakshi_sookshma_temporal_selection",
            "pancha_pakshi_schedule_sookshma_temporal_selection",
            "pancha_pakshi_civil_time_sookshma_selection",
            "pancha_pakshi_identity_from_initial_vowel",
            "pancha_pakshi_directed_relationship", "pancha_pakshi_schedule",
            "pancha_pakshi_local_solar_context",
            "pancha_pakshi_fixed_clock_materialization",
            "pancha_pakshi_fixed_clock_current_cell",
            "pancha_pakshi_solar_proportional_materialization",
            "pancha_pakshi_solar_proportional_current_cell",
            "shadbala",
            "shadbala_for_chart", "shadbala_profile", "shadbala_condition",
            "shadbala_network", "bhava_bala", "bhava_bala_for_chart",
            "jaimini_karakas",
            "jaimini_karakas_for_chart", "jaimini_profile",
            "jaimini_pair", "ashtakavarga", "ashtakavarga_for_chart",
            "ashtakavarga_profile", "ashtakavarga_sign_profile",
            "ashtakavarga_transit_strength", "varga", "varga_named",
            "varga_for_chart", "shodashvarga", "shodashvarga_for_chart", "d60_sign",
            "ayanamsa", "tropical_to_sidereal", "sidereal_to_tropical",
            "list_ayanamsa_systems"
        ],
        "internal": []
    },
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    _SHODASHVARGA_SELECTORS: tuple[str, ...] = (
        "hora",
        "chaturthamsha",
        "shashthamsha",
        "saptamsa",
        "ashtamsha",
        "navamsa",
        "dashamansa",
        "dwadashamsa",
        "shodashamsha",
        "vimshamsha",
        "chaturvimshamsha",
        "saptavimshamsha",
        "trimshamsa",
        "khavedamsha",
        "akshavedamsha",
        "shashtiamsha",
    )

    def _sidereal_longitudes_from_chart(
        self,
        chart,
        bodies: tuple[str, ...] | list[str],
        *,
        ayanamsa_system: str,
        _jd_ut1: float | None = None,
    ) -> dict[str, float]:
        facade = _facade_module()
        jd_ut1 = (
            facade.utc_to_ut1(chart.jd_ut)
            if _jd_ut1 is None
            else _jd_ut1
        )
        longitudes = chart.longitudes(include_nodes=True)
        result: dict[str, float] = {}
        for body in bodies:
            if body not in longitudes:
                raise KeyError(f"{body} not found in chart")
            result[body] = facade.tropical_to_sidereal(
                longitudes[body],
                jd_ut1,
                system=ayanamsa_system,
            )
        return result

    def ayanamsa(self, jd: float, system=None, mode: str = "true") -> float:
        """Compute ayanamsa for a UT Julian Day using the owning sidereal engine."""
        facade = _facade_module()
        selected_system = facade.Ayanamsa.LAHIRI if system is None else system
        return facade.ayanamsa(jd, selected_system, mode)

    def tropical_to_sidereal(
        self,
        tropical_longitude: float,
        jd: float,
        system=None,
        mode: str = "true",
    ) -> float:
        """Convert tropical longitude to sidereal longitude."""
        facade = _facade_module()
        selected_system = facade.Ayanamsa.LAHIRI if system is None else system
        return facade.tropical_to_sidereal(
            tropical_longitude,
            jd,
            system=selected_system,
            mode=mode,
        )

    def sidereal_to_tropical(
        self,
        sidereal_longitude: float,
        jd: float,
        system=None,
        mode: str = "true",
    ) -> float:
        """Convert sidereal longitude to tropical longitude."""
        facade = _facade_module()
        selected_system = facade.Ayanamsa.LAHIRI if system is None else system
        return facade.sidereal_to_tropical(
            sidereal_longitude,
            jd,
            system=selected_system,
            mode=mode,
        )

    def list_ayanamsa_systems(self) -> dict[str, float]:
        """Return the named ayanamsa registry exposed by the sidereal engine."""
        return _facade_module().list_ayanamsa_systems()

    def marriage_election_catalogue(self):
        """Discover source-selected marriage rules and admission evidence."""
        from .muhurta_marriage import marriage_election_catalogue
        return marriage_election_catalogue()

    def assess_marriage_election(self, evidence, **kwargs):
        """Pure marriage assessment; supplied evidence remains caller-owned."""
        from .muhurta_marriage import assess_marriage_election
        return assess_marriage_election(evidence, **kwargs)

    def marriage_election_for_datetime(self, dt: datetime, latitude: float, longitude: float, **kwargs):
        """Resolve marriage evidence using this facade's serving reader."""
        from .muhurta_marriage_dated import marriage_election_for_datetime
        return marriage_election_for_datetime(dt, latitude, longitude, reader=self._reader, **kwargs)

    def marriage_election_windows(self, start: datetime, end: datetime, latitude: float, longitude: float, **kwargs):
        """Resolve bounded marriage intervals using this facade's serving reader."""
        from ._muhurta_marriage_windows import marriage_election_windows
        return marriage_election_windows(start, end, latitude, longitude, reader=self._reader, **kwargs)

    def muhurta_lagna_catalogue(self):
        """Discover source-specific Lagna, Navamsa and strength policies."""
        from .muhurta_lagna import muhurta_lagna_catalogue
        return muhurta_lagna_catalogue()

    def evaluate_muhurta_lagna_strength(self, sidereal_longitudes, **kwargs):
        """Compose inspectable Lagna rules from supplied sidereal truth."""
        from .muhurta_lagna import evaluate_muhurta_lagna_strength
        return evaluate_muhurta_lagna_strength(sidereal_longitudes, **kwargs)

    def muhurta_lagna_for_datetime(self, dt: datetime, latitude: float, longitude: float, **kwargs):
        """Derive one Lagna snapshot using this engine's bound reader."""
        from .muhurta_lagna_dated import muhurta_lagna_for_datetime
        return muhurta_lagna_for_datetime(dt, latitude, longitude, reader=self._reader, **kwargs)

    def muhurta_dosha_catalogue(self):
        """Discover finite dosha profiles and explicitly scoped cancellation rules."""
        from .muhurta_dosha import muhurta_dosha_catalogue
        return muhurta_dosha_catalogue()

    def detect_muhurta_doshas(self, sun_sidereal_longitude, moon_sidereal_longitude, **kwargs):
        """Preserve independent dosha detection and source-specific Parihara evidence."""
        from .muhurta_dosha import detect_muhurta_doshas
        return detect_muhurta_doshas(sun_sidereal_longitude, moon_sidereal_longitude, **kwargs)

    def muhurta_doshas_for_date(self, local_date: date, latitude: float, longitude: float,
            *, timezone: str, necessary_activity=None, policy=None):
        """Compose sunrise-day dosha cells with this engine's existing reader."""
        from .muhurta_dosha import muhurta_doshas_for_date
        return muhurta_doshas_for_date(local_date, latitude, longitude, timezone=timezone,
            necessary_activity=necessary_activity, policy=policy, reader=self._reader)

    def panchanga_shuddhi_catalogue(self):
        """Discover admitted source profiles and historical Karana activities."""
        return _panchanga_shuddhi.panchanga_shuddhi_catalogue()

    def panchanga_shuddhi_from_longitudes(self, sun_sidereal_longitude, moon_sidereal_longitude, **kwargs):
        """Independent source findings from caller-owned inputs, without score migration."""
        return _panchanga_shuddhi.panchanga_shuddhi_from_longitudes(
            sun_sidereal_longitude, moon_sidereal_longitude, **kwargs)

    def panchanga_shuddhi_for_date(self, local_date: date, latitude: float, longitude: float,
            *, timezone: str, natal_nakshatra_index=None,
            policy: _panchanga_shuddhi.PanchangaShuddhiPolicy | None = None):
        """Sunrise-owned source assessment cells using this engine's reader."""
        return _panchanga_shuddhi.panchanga_shuddhi_for_date(local_date, latitude, longitude,
            timezone=timezone, natal_nakshatra_index=natal_nakshatra_index, policy=policy, reader=self._reader)

    def special_muhurta_from_solar_times(self, *, weekday: int, sunrise_jd_ut1=None,
            sunset_jd_ut1=None, half_set_jd_ut1=None, upper_limb_sunset_jd_ut1=None,
            policy: _special_muhurta.SpecialMuhurtaPolicy | None = None):
        """Source-selected Vijaya/Godhuli from caller-owned solar anchors."""
        return _special_muhurta.special_muhurta_from_solar_times(weekday=weekday,
            sunrise_jd_ut1=sunrise_jd_ut1, sunset_jd_ut1=sunset_jd_ut1,
            half_set_jd_ut1=half_set_jd_ut1, upper_limb_sunset_jd_ut1=upper_limb_sunset_jd_ut1, policy=policy)

    def muhurta_yogas_from_longitudes(self, sun_sidereal_longitude: float,
            moon_sidereal_longitude: float, *, weekday: int,
            policy: _special_muhurta.SpecialMuhurtaPolicy | None = None):
        """Selected Muhurta yoga presence, with no reader or ayanamsa conversion."""
        return _special_muhurta.muhurta_yogas_from_longitudes(sun_sidereal_longitude,
            moon_sidereal_longitude, weekday=weekday, policy=policy)

    def special_muhurta_for_date(self, local_date: date, latitude: float, longitude: float,
            *, timezone: str, policy: _special_muhurta.SpecialMuhurtaPolicy | None = None):
        """Seven-name source-selected product using this facade's reader."""
        return _special_muhurta.special_muhurta_for_date(local_date, latitude, longitude,
            timezone=timezone, policy=policy, reader=self._reader)

    def named_muhurta_from_solar_times(
        self, sunrise_jd_ut1: float, sunset_jd_ut1: float | None = None,
        previous_sunset_jd_ut1: float | None = None, *, weekday: int,
        policy: _named_muhurta.NamedMuhurtaPolicy | None = None,
    ) -> _named_muhurta.NamedMuhurtaResult:
        """Named intervals from supplied UT1 solar anchors, Monday=0 weekday."""
        return _named_muhurta.named_muhurta_from_solar_times(
            sunrise_jd_ut1, sunset_jd_ut1, previous_sunset_jd_ut1, weekday=weekday, policy=policy,
        )

    def named_muhurta_for_date(
        self, local_date: date, latitude: float, longitude: float, *, timezone: str,
        policy: _named_muhurta.NamedMuhurtaPolicy | None = None,
    ) -> _named_muhurta.NamedMuhurtaDay:
        """Named intervals for a sunrise date, using this facade's reader."""
        return _named_muhurta.named_muhurta_for_date(
            local_date, latitude, longitude, timezone=timezone, policy=policy, reader=self._reader,
        )

    def sayanadi_avastha(self, planet, sidereal_longitudes, lagna_sidereal_lon,
                         birth_ghati=None, first_syllable_value=None, *, context=None):
        """Source-owned standalone Sayanadi with canonical arithmetic trace."""
        return _avasthas.sayanadi_avastha(planet, sidereal_longitudes, lagna_sidereal_lon,
                                         birth_ghati, first_syllable_value, context=context)

    def evaluate_avasthas(self, sidereal_longitudes, lagna_sidereal_lon, policy=None,
                          node_longitudes=None, sayanadi_context=None):
        """Four classical families, with optional complete Sayanadi context."""
        return _avasthas.evaluate_avasthas(sidereal_longitudes, lagna_sidereal_lon,
                                          policy, node_longitudes, sayanadi_context)

    def avasthas_for_datetime(self, birth, latitude, longitude, *, name,
                              timezone_name=None, policy=None, avastha_policy=None):
        """Birth avasthas and previous-sunrise ghati using this reader."""
        return _sayanadi_dated.avasthas_for_datetime(
            birth, latitude, longitude, name=name, timezone_name=timezone_name,
            policy=policy, avastha_policy=avastha_policy, reader=self._reader,
        )

    def panchanga(self, chart, ayanamsa_system: str | None = None, policy=None):
        """Compute Panchanga truth from a chart's Sun and Moon positions."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        sun = chart.planets.get("Sun")
        moon = chart.planets.get("Moon")
        if sun is None or moon is None:
            raise ValueError("Sun and Moon must be present in chart for Panchanga")
        return _panchanga._panchanga_from_utc(
            sun.longitude,
            moon.longitude,
            chart.jd_ut,
            ayanamsa_system=system,
            policy=policy,
        )

    def panchanga_profile(self, result):
        """Build the Panchanga profile for an existing Panchanga result."""
        return _facade_module().panchanga_profile(result)

    def lunar_month_at(self, jd_ut1: float, *, policy=None):
        """Source-declared lunation context with this engine's reader."""
        return _lunar_month.lunar_month_at(jd_ut1, policy=policy, reader=self._reader)

    def find_muhurta_windows(self, start_jd_ut1: float, end_jd_ut1: float, *,
                             janma_moon_sidereal_lon=None, policy=None):
        """Complete bounded sampled Muhurta search using this engine's reader."""
        _muhurta_search._search_arguments(start_jd_ut1, end_jd_ut1,
                                           janma_moon_sidereal_lon, policy)
        return _muhurta_search.find_muhurta_windows(
            start_jd_ut1, end_jd_ut1, janma_moon_sidereal_lon=janma_moon_sidereal_lon,
            policy=policy, reader=self._muhurta_reader(),
        )

    def muhurta_score_for_chart(self, chart, *, janma_moon_sidereal_lon=None,
                                ayanamsa_system="Lahiri", policy=None):
        """Score supplied tropical chart inputs with this reader for live anchors."""
        return _muhurta_search.muhurta_score_for_chart(
            chart, janma_moon_sidereal_lon=janma_moon_sidereal_lon,
            ayanamsa_system=ayanamsa_system, policy=policy, reader=self._muhurta_reader(),
        )

    def _muhurta_reader(self):
        try:
            return self._reader
        except MissingEphemerisKernelError as exc:
            raise _muhurta_search.MuhurtaResourceError(
                "this Moira instance has no Muhurta planetary reader",
            ) from exc

    def gochara_at(self, natal_jd_ut1: float, transit_jd_ut1: float, *,
                   birth_location=None, policy=None):
        """Complete date-derived Gochar with this engine's reader at both epochs."""
        return _gochara_dated.gochara_at(
            natal_jd_ut1, transit_jd_ut1, birth_location=birth_location,
            policy=policy, reader=self._reader,
        )

    def gochara_for_datetimes(self, natal_dt: datetime, transit_dt: datetime, *,
                             birth_location=None, policy=None):
        """Gochar from two aware civil instants, converted once to UT1."""
        return _gochara_dated.gochara_for_datetimes(
            natal_dt, transit_dt, birth_location=birth_location,
            policy=policy, reader=self._reader,
        )

    def daily_panchanga(self, local_date: date, latitude: float, longitude: float,
                        *, timezone: str, policy=None):
        """Compute a sunrise-owned daily Panchanga with this facade's reader."""
        return _daily_panchanga.daily_panchanga(
            local_date, latitude, longitude, timezone=timezone,
            policy=policy, reader=self._reader,
        )

    def pancha_pakshi_profiles(
        self,
    ) -> tuple[_pancha_pakshi.PanchaPakshiProfileDescriptor, ...]:
        """List named Pancha Pakshi profiles without selecting a default."""
        return _pancha_pakshi.available_pancha_pakshi_profiles()

    def pancha_pakshi_uromarisi_constitution_status(
        self,
    ) -> _pancha_pakshi.PanchaPakshiUromarisiConstitutionStatus:
        """Return public governance metadata without private research data."""

        return _pancha_pakshi.pancha_pakshi_uromarisi_constitution_status()

    def pancha_pakshi_profile_info(
        self,
        profile_id: str,
    ) -> _pancha_pakshi.PanchaPakshiProfileInfo:
        """Describe one explicitly named Pancha Pakshi profile."""
        return _pancha_pakshi.pancha_pakshi_profile_info(profile_id)

    def pancha_pakshi_astronomical_paksha(
        self,
        profile_id: str,
        dt: datetime,
    ) -> _pancha_pakshi.PanchaPakshiAstronomicalPakshaInference:
        """Infer the source-mapped Paksha from geocentric lunar phase."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_astronomical_paksha_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            reader=self._reader,
        )

    def pancha_pakshi_natal_moon_identity(
        self,
        profile_id: str,
        dt: datetime,
    ) -> _pancha_pakshi.PanchaPakshiNatalMoonIdentity:
        """Apply the named source table through the fixed natal-Moon policy."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_natal_moon_identity_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            reader=self._reader,
        )

    def pancha_pakshi_nakshatra_bird_mapping(
        self,
        profile_id: str,
        *,
        profile_paksha: _pancha_pakshi.PanchaPakshiPaksha,
        nakshatra_index: int,
    ) -> _pancha_pakshi.PanchaPakshiNakshatraBirdMapping:
        """Return one source-table cell without applying natal-Moon policy."""

        return _pancha_pakshi.pancha_pakshi_nakshatra_bird_mapping(
            profile_id,
            profile_paksha=profile_paksha,
            nakshatra_index=nakshatra_index,
        )

    def pancha_pakshi_padu_bird_mapping(
        self,
        profile_id: str,
        *,
        profile_paksha: _pancha_pakshi.PanchaPakshiPaksha,
        weekday: _pancha_pakshi.PanchaPakshiWeekday,
    ) -> _pancha_pakshi.PanchaPakshiPaduBirdMapping:
        """Return one source-attested Paksha-and-weekday Padu bird."""

        return _pancha_pakshi.pancha_pakshi_padu_bird_mapping(
            profile_id,
            profile_paksha=profile_paksha,
            weekday=weekday,
        )

    def pancha_pakshi_sookshma_temporal_selection(
        self,
        profile_id: str,
        *,
        policy_id: _pancha_pakshi.PanchaPakshiSookshmaSelectorPolicyId,
        parent_activity: _pancha_pakshi.PanchaPakshiActivity,
        elapsed_nazhigai: Fraction,
    ) -> _pancha_pakshi.PanchaPakshiSookshmaSelection:
        """Select one exact Sookshma interval under a caller-named policy."""

        return _pancha_pakshi.pancha_pakshi_sookshma_temporal_selection(
            profile_id,
            policy_id=policy_id,
            parent_activity=parent_activity,
            elapsed_nazhigai=elapsed_nazhigai,
        )

    def pancha_pakshi_schedule_sookshma_temporal_selection(
        self,
        schedule_profile_id: str,
        selector_profile_id: str,
        *,
        profile_paksha: _pancha_pakshi.PanchaPakshiPaksha,
        half: _pancha_pakshi.PanchaPakshiHalf,
        weekday: _pancha_pakshi.PanchaPakshiWeekday,
        samam_index: int,
        subject_bird: _pancha_pakshi.PanchaPakshiBird,
        selector_policy_id: (
            _pancha_pakshi.PanchaPakshiSookshmaSelectorPolicyId
        ),
        elapsed_nazhigai: Fraction,
    ) -> _pancha_pakshi.PanchaPakshiScheduleSookshmaSelection:
        """Compose one named schedule samam with an explicit selector."""

        return (
            _pancha_pakshi
            .pancha_pakshi_schedule_sookshma_temporal_selection(
                schedule_profile_id,
                selector_profile_id,
                profile_paksha=profile_paksha,
                half=half,
                weekday=weekday,
                samam_index=samam_index,
                subject_bird=subject_bird,
                selector_policy_id=selector_policy_id,
                elapsed_nazhigai=elapsed_nazhigai,
            )
        )

    def pancha_pakshi_civil_time_sookshma_selection(
        self,
        schedule_profile_id: str,
        selector_profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        profile_paksha: _pancha_pakshi.PanchaPakshiPaksha,
        subject_bird: _pancha_pakshi.PanchaPakshiBird,
        timing_policy_id: _pancha_pakshi.PanchaPakshiSookshmaTimingPolicyId,
        selector_policy_id: (
            _pancha_pakshi.PanchaPakshiSookshmaSelectorPolicyId
        ),
    ) -> _pancha_pakshi.PanchaPakshiCivilTimeSookshmaSelection:
        """Route one aware instant through explicit timing and selector policy."""

        facade = _facade_module()
        return (
            _pancha_pakshi
            ._pancha_pakshi_civil_time_sookshma_selection_from_utc(
                schedule_profile_id,
                selector_profile_id,
                facade.jd_from_datetime(dt),
                latitude,
                longitude,
                profile_paksha=profile_paksha,
                subject_bird=subject_bird,
                timing_policy_id=timing_policy_id,
                selector_policy_id=selector_policy_id,
                reader=self._reader,
            )
        )

    def pancha_pakshi_first_eat_bird_mapping(
        self,
        profile_id: str,
        *,
        profile_paksha: _pancha_pakshi.PanchaPakshiPaksha,
        half: _pancha_pakshi.PanchaPakshiHalf,
        weekday: _pancha_pakshi.PanchaPakshiWeekday,
    ) -> _pancha_pakshi.PanchaPakshiFirstEatBirdMapping:
        """Return one source generator's weekday first-samam EAT seed."""

        return _pancha_pakshi.pancha_pakshi_first_eat_bird_mapping(
            profile_id,
            profile_paksha=profile_paksha,
            half=half,
            weekday=weekday,
        )

    def pancha_pakshi_identity_from_initial_vowel(
        self,
        profile_id: str,
        initial_vowel: str,
    ) -> _pancha_pakshi.PanchaPakshiInitialVowelIdentity:
        """Resolve a source-scoped aksara identity for a named profile."""
        return _pancha_pakshi.pancha_pakshi_identity_from_initial_vowel(
            profile_id,
            initial_vowel,
        )

    def pancha_pakshi_directed_relationship(
        self,
        profile_id: str,
        subject: _pancha_pakshi.PanchaPakshiBird,
        target: _pancha_pakshi.PanchaPakshiBird,
    ) -> _pancha_pakshi.PanchaPakshiDirectedRelationship:
        """Resolve one stored directed relationship without reciprocity inference."""
        return _pancha_pakshi.pancha_pakshi_directed_relationship(
            profile_id,
            subject,
            target,
        )

    def pancha_pakshi_schedule(
        self,
        profile_id: str,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
        half: _pancha_pakshi.PanchaPakshiHalf,
        weekday: _pancha_pakshi.PanchaPakshiWeekday,
    ) -> _pancha_pakshi.PanchaPakshiSchedule:
        """Generate one exact nominal schedule from a named source profile."""
        return _pancha_pakshi.pancha_pakshi_schedule(
            profile_id,
            paksha=paksha,
            half=half,
            weekday=weekday,
        )

    def pancha_pakshi_local_solar_context(
        self,
        profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
    ) -> _pancha_pakshi.PanchaPakshiLocalSolarContext:
        """Route an explicit Paksha through the enclosing local solar day."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_local_solar_context_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            paksha=paksha,
            reader=self._reader,
        )

    def pancha_pakshi_fixed_clock_materialization(
        self,
        profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
    ) -> _pancha_pakshi.PanchaPakshiFixedClockMaterialization:
        """Materialize fixed offsets from the governing solar-half start."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_fixed_clock_materialization_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            paksha=paksha,
            reader=self._reader,
        )

    def pancha_pakshi_fixed_clock_current_cell(
        self,
        profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
    ) -> _pancha_pakshi.PanchaPakshiFixedClockCurrentCellSelection:
        """Select the current fixed-clock cell after solar-half routing."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_fixed_clock_current_cell_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            paksha=paksha,
            reader=self._reader,
        )

    def pancha_pakshi_solar_proportional_materialization(
        self,
        profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
    ) -> _pancha_pakshi.PanchaPakshiSolarProportionalMaterialization:
        """Map nominal offsets proportionally over the governing solar half."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_solar_proportional_materialization_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            paksha=paksha,
            reader=self._reader,
        )

    def pancha_pakshi_solar_proportional_current_cell(
        self,
        profile_id: str,
        dt: datetime,
        latitude: float,
        longitude: float,
        *,
        paksha: _pancha_pakshi.PanchaPakshiPaksha,
    ) -> _pancha_pakshi.PanchaPakshiSolarProportionalCurrentCellSelection:
        """Select the current cell from the proportional solar-half partition."""

        facade = _facade_module()
        return _pancha_pakshi._pancha_pakshi_solar_proportional_current_cell_from_utc(
            profile_id,
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            paksha=paksha,
            reader=self._reader,
        )

    def shadbala(
        self,
        sidereal_longitudes: dict[str, float],
        planet_speeds: dict[str, float],
        houses,
        jd: float,
        tithi_number: int,
        vara_lord: str,
        is_day: bool,
        ayanamsa_system: str = "Lahiri",
        hora_lord: str | None = None,
        planet_latitudes: dict[str, float] | None = None,
        *, context=None, policy=None,
    ):
        """Compute Shadbala from caller-supplied sidereal chart truth."""
        return _facade_module().shadbala(
            sidereal_longitudes,
            planet_speeds,
            houses,
            jd,
            tithi_number,
            vara_lord,
            is_day,
            ayanamsa_system=ayanamsa_system,
            hora_lord=hora_lord,
            planet_latitudes=planet_latitudes,
            context=context, policy=policy,
        )

    def shadbala_context(self, jd: float, latitude: float, longitude: float, *,
                         ayanamsa_system: str = 'Lahiri', hora_lord: str | None = None,
                         jd_utc: float | None = None):
        """Derive immutable Shadbala evidence through this engine's reader."""
        return _shadbala.derive_shadbala_context(jd, latitude, longitude,
            ayanamsa_system=ayanamsa_system, hora_lord=hora_lord,
            jd_utc=jd_utc, reader=self._reader)

    def shadbala_for_chart(
        self,
        chart,
        houses,
        *,
        ayanamsa_system: str | None = None,
        is_day: bool | None = None,
        hora_lord: str | None = None,
        planet_latitudes: dict[str, float] | None = None,
        context=None, policy=None,
        observer_latitude: float | None = None,
        observer_longitude: float | None = None,
    ):
        """Compute Shadbala using an existing chart, houses, and Panchanga truth."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
        if context is None:
            if observer_latitude is None or observer_longitude is None:
                raise _shadbala.ShadbalaContextError('chart Shadbala requires observer coordinates or explicit context')
            context = self.shadbala_context(jd_ut1, observer_latitude, observer_longitude,
                ayanamsa_system=system, hora_lord=hora_lord, jd_utc=chart.jd_ut)
        seven = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
        sidereal_longitudes = self._sidereal_longitudes_from_chart(
            chart,
            seven,
            ayanamsa_system=system,
            _jd_ut1=jd_ut1,
        )
        planet_speeds = {
            planet: chart.planets[planet].speed
            for planet in seven
        }
        if planet_latitudes is None:
            planet_latitudes = {
                planet: chart.planets[planet].latitude
                for planet in seven
            }
        panchanga_result = self.panchanga(chart, ayanamsa_system=system)
        day_chart = (
            context.is_day
            if is_day is None
            else is_day
        )
        return facade.shadbala(
            sidereal_longitudes,
            planet_speeds,
            houses,
            jd_ut1,
            panchanga_result.tithi.number,
            panchanga_result.vara_lord,
            day_chart,
            ayanamsa_system=system,
            hora_lord=hora_lord,
            planet_latitudes=planet_latitudes,
            context=context, policy=policy,
        )

    def shadbala_profile(self, result):
        """Build the aggregate Shadbala chart profile."""
        return _facade_module().shadbala_chart_profile(result)

    def shadbala_condition(self, planet_result):
        """Build one planet's Shadbala condition profile."""
        return _facade_module().shadbala_condition_profile(planet_result)

    def shadbala_network(self, result, wars=()):
        """Build the Shadbala network profile."""
        return _shadbala.shadbala_network_profile(result, wars)

    def bhava_bala(
        self,
        shadbala_result,
        sidereal_longitudes: dict[str, float],
        houses,
    ):
        """Compute Bhava Bala (house strength, Raman Part II) from an
        existing Shadbala result and the chart truth that produced it."""
        return _facade_module().bhava_bala(
            shadbala_result,
            sidereal_longitudes,
            houses,
        )

    def bhava_bala_for_chart(
        self,
        chart,
        houses,
        *,
        ayanamsa_system: str | None = None,
        is_day: bool | None = None,
        hora_lord: str | None = None,
        planet_latitudes: dict[str, float] | None = None,
        context=None, policy=None,
        observer_latitude: float | None = None,
        observer_longitude: float | None = None,
    ):
        """Compute Bhava Bala using an existing chart and houses, deriving
        the prerequisite Shadbala internally via ``shadbala_for_chart``."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        seven = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
        graha_result = self.shadbala_for_chart(
            chart,
            houses,
            ayanamsa_system=system,
            is_day=is_day,
            hora_lord=hora_lord,
            planet_latitudes=planet_latitudes,
            context=context, policy=policy,
            observer_latitude=observer_latitude, observer_longitude=observer_longitude,
        )
        sidereal_longitudes = self._sidereal_longitudes_from_chart(
            chart,
            seven,
            ayanamsa_system=system,
        )
        return facade.bhava_bala(graha_result, sidereal_longitudes, houses)

    def jaimini_karakas(
        self,
        sidereal_longitudes: dict[str, float],
        scheme: int = 7,
        policy=None,
    ):
        """Compute Jaimini Chara Karakas from caller-supplied sidereal longitudes."""
        return _facade_module().jaimini_karakas(
            sidereal_longitudes,
            scheme=scheme,
            policy=policy,
        )

    def jaimini_karakas_for_chart(
        self,
        chart,
        *,
        ayanamsa_system: str | None = None,
        scheme: int = 7,
        policy=None,
    ):
        """Compute Jaimini Chara Karakas from an existing chart."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        bodies = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        if scheme == 8 or (policy is not None and getattr(policy, "scheme", scheme) == 8):
            bodies.append("Rahu")
        return facade.jaimini_karakas(
            self._sidereal_longitudes_from_chart(
                chart,
                bodies,
                ayanamsa_system=system,
            ),
            scheme=scheme,
            policy=policy,
        )

    def jaimini_profile(self, result):
        """Build a Jaimini chart profile from a karaka result."""
        return _facade_module().jaimini_chart_profile(result)

    def jaimini_pair(self, result, role_a: str, role_b: str):
        """Build a relation profile for two Jaimini karaka roles."""
        return _facade_module().karaka_pair(result, role_a, role_b)

    def ashtakavarga(
        self,
        sidereal_longitudes: dict[str, float],
        ayanamsa_system: str | None = None,
        policy=None,
    ):
        """Compute Ashtakavarga from caller-supplied sidereal longitudes."""
        return _facade_module().ashtakavarga(
            sidereal_longitudes,
            ayanamsa_system=ayanamsa_system,
            policy=policy,
        )

    def ashtakavarga_for_chart(
        self,
        chart,
        houses,
        *,
        ayanamsa_system: str | None = None,
        policy=None,
    ):
        """Compute Ashtakavarga from an existing chart and Lagna-bearing houses."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
        longitudes = self._sidereal_longitudes_from_chart(
            chart,
            ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"),
            ayanamsa_system=system,
            _jd_ut1=jd_ut1,
        )
        longitudes["Lagna"] = facade.tropical_to_sidereal(
            houses.asc,
            jd_ut1,
            system=system,
        )
        return facade.ashtakavarga(
            longitudes,
            ayanamsa_system=system,
            policy=policy,
        )

    def ashtakavarga_profile(self, result, policy=None):
        """Build an aggregate Ashtakavarga chart profile."""
        return _facade_module().ashtakavarga_chart_profile(result, policy)

    def ashtakavarga_sign_profile(self, bhinna, sign_idx: int, policy=None):
        """Build one sign's Ashtakavarga strength profile."""
        return _facade_module().sign_strength_profile(bhinna, sign_idx, policy)

    def ashtakavarga_transit_strength(self, planet: str, transit_sign_index: int, bhinna):
        """Return the Ashtakavarga rekha count for a planet transiting a sign."""
        return _facade_module().transit_strength(planet, transit_sign_index, bhinna)

    def _varga_function(self, varga: str, *, d60_method=_varga.D60Method.HARMONIC):
        _varga._require_d60_full_point(d60_method)
        if varga not in self._SHODASHVARGA_SELECTORS:
            raise ValueError(f"unknown varga selector: {varga!r}")
        if d60_method is not _varga.D60Method.HARMONIC:
            if varga != "shashtiamsha":
                raise ValueError("nondefault d60_method applies only to shashtiamsha")
            return lambda longitude: _varga.shashtiamsha(longitude, d60_method=d60_method)
        return getattr(_varga, varga)

    def varga(self, sidereal_longitude: float, divisor: int, name: str = ""):
        """Compute a generic Varga division from a sidereal longitude."""
        return _facade_module().calculate_varga(sidereal_longitude, divisor, name)

    def varga_named(self, sidereal_longitude: float, varga: str, *, d60_method=_varga.D60Method.HARMONIC):
        """Compute one named Varga from a sidereal longitude."""
        return self._varga_function(varga, d60_method=d60_method)(sidereal_longitude)

    def d60_sign(self, sidereal_longitude: float, *, method=_varga.D60Method.HARMONIC):
        """Return an explicitly selected sign-only D60 result."""
        return _varga.d60_sign(sidereal_longitude, method=method)

    def varga_for_chart(
        self,
        chart,
        body: str,
        varga: str,
        *,
        ayanamsa_system: str | None = None,
        d60_method=_varga.D60Method.HARMONIC,
    ):
        """Compute one named Varga for one body in an existing chart."""
        function = self._varga_function(varga, d60_method=d60_method)
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        sidereal = self._sidereal_longitudes_from_chart(
            chart,
            (body,),
            ayanamsa_system=system,
        )[body]
        return function(sidereal)

    def shodashvarga(self, sidereal_longitude: float, *, d60_method=_varga.D60Method.HARMONIC):
        """Compute Moira's admitted Shodashvarga set for one sidereal longitude."""
        _varga._require_d60_full_point(d60_method)
        if d60_method is not _varga.D60Method.HARMONIC:
            # Source profiles own strict circular normalization. Give every
            # division the same canonical input, including the left wrap limit.
            sidereal_longitude = _varga.d60_sign(sidereal_longitude, method=d60_method).longitude
        return {
            selector: self._varga_function(
                selector, d60_method=d60_method if selector == "shashtiamsha" else _varga.D60Method.HARMONIC,
            )(sidereal_longitude)
            for selector in self._SHODASHVARGA_SELECTORS
        }

    def shodashvarga_for_chart(
        self,
        chart,
        body: str,
        *,
        ayanamsa_system: str | None = None,
        d60_method=_varga.D60Method.HARMONIC,
    ):
        """Compute Moira's admitted Shodashvarga set for one chart body."""
        _varga._require_d60_full_point(d60_method)
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        sidereal = self._sidereal_longitudes_from_chart(
            chart,
            (body,),
            ayanamsa_system=system,
        )[body]
        return self.shodashvarga(sidereal, d60_method=d60_method)
