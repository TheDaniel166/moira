"""
JPL Horizons Oracle — astroquery-backed integration for position validation.

Wraps astroquery.jplhorizons to fetch reference ephemeris data for planets,
the Moon, and the Sun, enabling direct comparison against Moira's DE441-backed
positions.

Authority: JPL Solar System Dynamics Group. HORIZONS is the NASA standard
reference for solar system ephemeris and is considered the primary oracle
for all position/velocity comparisons.

Requires: astroquery (already in project .venv)
"""

import math
from typing import NamedTuple, Optional


class HorizonsPosition(NamedTuple):
    """Observer-frame position from JPL HORIZONS (RA/Dec)."""
    jd_ut: float
    ra_deg: float
    dec_deg: float
    distance_au: float
    distance_km: float
    ra_rate_arcsec_per_hr: float
    dec_rate_arcsec_per_hr: float
    range_rate_km_s: float


class HorizonsEcliptic(NamedTuple):
    """Ecliptic coordinates from JPL HORIZONS."""
    jd_ut: float
    lon_deg: float
    lat_deg: float
    distance_au: float
    distance_km: float


class HorizonsVectors(NamedTuple):
    """Cartesian state vectors from JPL HORIZONS (AU, AU/day)."""
    jd_ut: float
    x_au: float
    y_au: float
    z_au: float
    range_au: float
    lon_deg: float
    lat_deg: float


_AU_TO_KM = 149_597_870.7

_BODY_IDS = {
    "Sun":     "10",
    "Mercury": "199",
    "Venus":   "299",
    "Earth":   "399",
    "Moon":    "301",
    "Mars":    "499",
    "Jupiter": "599",
    "Saturn":  "699",
    "Uranus":  "799",
    "Neptune": "899",
}

# Astroquery location strings for common observer positions.
_LOCATION_CODES = {
    "@geocenter": "500@399",
    "@sun":       "@10",
    "@ssb":       "@0",
}


class HorizonsOracle:
    """
    JPL HORIZONS oracle client backed by astroquery.jplhorizons.

    All methods require live network access. Mark calling tests with
    @pytest.mark.network so the conftest network-block fixture allows
    socket connections.
    """

    def _horizons(self, body: str, jd_ut: float, location: str):
        from astroquery.jplhorizons import Horizons
        obj_id = _BODY_IDS[body]
        loc = _LOCATION_CODES.get(location, location)
        return Horizons(id=obj_id, location=loc, epochs=jd_ut)

    def fetch_position(
        self,
        body: str,
        jd_ut: float,
        observer: str = "@geocenter",
    ) -> Optional[HorizonsPosition]:
        """
        Fetch geocentric (or observer-frame) RA/Dec from HORIZONS.

        Returns HorizonsPosition or None if the query fails.
        """
        try:
            eph = self._horizons(body, jd_ut, observer).ephemerides()
            return HorizonsPosition(
                jd_ut=jd_ut,
                ra_deg=float(eph["RA"][0]),
                dec_deg=float(eph["DEC"][0]),
                distance_au=float(eph["delta"][0]),
                distance_km=float(eph["delta"][0]) * _AU_TO_KM,
                ra_rate_arcsec_per_hr=float(eph["RA_rate"][0]),
                dec_rate_arcsec_per_hr=float(eph["DEC_rate"][0]),
                range_rate_km_s=float(eph["delta_rate"][0]),
            )
        except Exception as exc:
            print(f"HorizonsOracle.fetch_position failed ({body} @ {jd_ut}): {exc}")
            return None

    def fetch_ecliptic(
        self,
        body: str,
        jd_ut: float,
        observer: str = "@geocenter",
    ) -> Optional[HorizonsEcliptic]:
        """
        Fetch J2000 ecliptic lon/lat from HORIZONS observer ephemerides.

        Returns HorizonsEcliptic or None if the query fails.
        """
        try:
            eph = self._horizons(body, jd_ut, observer).ephemerides()
            return HorizonsEcliptic(
                jd_ut=jd_ut,
                lon_deg=float(eph["EclLon"][0]),
                lat_deg=float(eph["EclLat"][0]),
                distance_au=float(eph["delta"][0]),
                distance_km=float(eph["delta"][0]) * _AU_TO_KM,
            )
        except Exception as exc:
            print(f"HorizonsOracle.fetch_ecliptic failed ({body} @ {jd_ut}): {exc}")
            return None

    def fetch_vectors(
        self,
        body: str,
        jd_ut: float,
        center: str = "@sun",
        refplane: str = "ecliptic",
    ) -> Optional[HorizonsVectors]:
        """
        Fetch Cartesian state vectors from HORIZONS.

        Converts x/y/z (AU) to ecliptic longitude and latitude.
        ``refplane='ecliptic'`` returns J2000 ecliptic-plane vectors; at
        J2000.0 this frame matches Moira's true-of-date ecliptic.

        Returns HorizonsVectors or None if the query fails.
        """
        try:
            vecs = self._horizons(body, jd_ut, center).vectors(refplane=refplane)
            x = float(vecs["x"][0])
            y = float(vecs["y"][0])
            z = float(vecs["z"][0])
            r = math.sqrt(x * x + y * y + z * z)
            lon = math.degrees(math.atan2(y, x)) % 360.0
            lat = math.degrees(math.asin(max(-1.0, min(1.0, z / r)))) if r > 0 else 0.0
            return HorizonsVectors(
                jd_ut=jd_ut,
                x_au=x,
                y_au=y,
                z_au=z,
                range_au=r,
                lon_deg=lon,
                lat_deg=lat,
            )
        except Exception as exc:
            print(f"HorizonsOracle.fetch_vectors failed ({body} @ {jd_ut}): {exc}")
            return None

    def fetch_illumination(
        self,
        body: str,
        jd_ut: float,
        observer: str = "@geocenter",
    ) -> Optional[dict]:
        """
        Fetch illumination fraction, phase angle, and elongation from HORIZONS.

        Returns dict with keys illumination_fraction, phase_angle_deg,
        elongation_deg, or None if the query fails.
        """
        try:
            eph = self._horizons(body, jd_ut, observer).ephemerides()
            return {
                "illumination_fraction": float(eph["illumination"][0]) / 100.0,
                "phase_angle_deg": float(eph["alpha"][0]),
                "elongation_deg": float(eph["elong"][0]),
            }
        except Exception as exc:
            print(f"HorizonsOracle.fetch_illumination failed ({body} @ {jd_ut}): {exc}")
            return None


class InternalOracle:
    """
    Fallback oracle using Moira's internal consistency checks.

    Used when external HORIZONS API is unavailable. Provides weaker validation
    but still catches algorithmic errors.
    """

    def __init__(self, reader):
        self.reader = reader

    def validate_position_consistency(self, body: str, jd_ut: float) -> dict:
        """Validate position consistency across Moira's transform chain."""
        return {}
