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
from typing import Any

_shadbala = importlib.import_module("moira.shadbala")
_varga = importlib.import_module("moira.varga")
_panchanga = importlib.import_module("moira.panchanga")
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
            "panchanga", "panchanga_profile",
            "pancha_pakshi_profiles", "pancha_pakshi_profile_info",
            "pancha_pakshi_identity_from_initial_vowel",
            "pancha_pakshi_directed_relationship", "pancha_pakshi_schedule",
            "pancha_pakshi_local_solar_context",
            "pancha_pakshi_fixed_clock_materialization",
            "shadbala",
            "shadbala_for_chart", "shadbala_profile", "shadbala_condition",
            "shadbala_network", "bhava_bala", "bhava_bala_for_chart",
            "jaimini_karakas",
            "jaimini_karakas_for_chart", "jaimini_profile",
            "jaimini_pair", "ashtakavarga", "ashtakavarga_for_chart",
            "ashtakavarga_profile", "ashtakavarga_sign_profile",
            "ashtakavarga_transit_strength", "varga", "varga_named",
            "varga_for_chart", "shodashvarga", "shodashvarga_for_chart",
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

    def pancha_pakshi_profiles(
        self,
    ) -> tuple[_pancha_pakshi.PanchaPakshiProfileDescriptor, ...]:
        """List named Pancha Pakshi profiles without selecting a default."""
        return _pancha_pakshi.available_pancha_pakshi_profiles()

    def pancha_pakshi_profile_info(
        self,
        profile_id: str,
    ) -> _pancha_pakshi.PanchaPakshiProfileInfo:
        """Describe one explicitly named Pancha Pakshi profile."""
        return _pancha_pakshi.pancha_pakshi_profile_info(profile_id)

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
        )

    def shadbala_for_chart(
        self,
        chart,
        houses,
        *,
        ayanamsa_system: str | None = None,
        is_day: bool | None = None,
        hora_lord: str | None = None,
        planet_latitudes: dict[str, float] | None = None,
    ):
        """Compute Shadbala using an existing chart, houses, and Panchanga truth."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
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
            facade.is_day_chart(chart.planets["Sun"].longitude, houses.asc)
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

    def _varga_function(self, varga: str):
        if varga not in self._SHODASHVARGA_SELECTORS:
            raise ValueError(f"unknown varga selector: {varga!r}")
        return getattr(_varga, varga)

    def varga(self, sidereal_longitude: float, divisor: int, name: str = ""):
        """Compute a generic Varga division from a sidereal longitude."""
        return _facade_module().calculate_varga(sidereal_longitude, divisor, name)

    def varga_named(self, sidereal_longitude: float, varga: str):
        """Compute one named Varga from a sidereal longitude."""
        return self._varga_function(varga)(sidereal_longitude)

    def varga_for_chart(
        self,
        chart,
        body: str,
        varga: str,
        *,
        ayanamsa_system: str | None = None,
    ):
        """Compute one named Varga for one body in an existing chart."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        sidereal = self._sidereal_longitudes_from_chart(
            chart,
            (body,),
            ayanamsa_system=system,
        )[body]
        return self._varga_function(varga)(sidereal)

    def shodashvarga(self, sidereal_longitude: float):
        """Compute Moira's admitted Shodashvarga set for one sidereal longitude."""
        return {
            selector: self._varga_function(selector)(sidereal_longitude)
            for selector in self._SHODASHVARGA_SELECTORS
        }

    def shodashvarga_for_chart(
        self,
        chart,
        body: str,
        *,
        ayanamsa_system: str | None = None,
    ):
        """Compute Moira's admitted Shodashvarga set for one chart body."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        sidereal = self._sidereal_longitudes_from_chart(
            chart,
            (body,),
            ayanamsa_system=system,
        )[body]
        return self.shodashvarga(sidereal)
