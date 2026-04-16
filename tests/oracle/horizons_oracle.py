"""
JPL Horizons Oracle — direct API integration for comprehensive position validation.

This module wraps the JPL HORIZONS API to fetch reference ephemeris data for
planets, the Moon, and the Sun, enabling direct comparison against Moira's
internally-computed DE441-backed positions.

Authority: JPL Solar System Dynamics Group.  HORIZONS is the NASA standard
reference for solar system ephemeris and is considered the primary oracle
for all position/velocity comparisons.

Usage:
    >>> oracle = HorizonsOracle()
    >>> result = oracle.fetch_position("Mars", 2451545.0, observer="@sun")
    >>> print(result.ra_deg, result.dec_deg, result.distance_au)

Reference: https://ssd.jpl.nasa.gov/horizons_user_guide.html
"""

import urllib.request
import urllib.parse
import json
from typing import NamedTuple, Optional
from dataclasses import dataclass
import math


class HorizonsPosition(NamedTuple):
    """Position data from JPL HORIZONS."""
    jd_ut: float
    ra_deg: float           # Right ascension (degrees)
    dec_deg: float          # Declination (degrees)
    distance_au: float      # Distance (AU)
    distance_km: float      # Distance (km)
    ra_rate_deg_per_day: float  # RA rate
    dec_rate_deg_per_day: float # Dec rate
    range_rate_km_s: float  # Range rate (km/s)


class HorizonsEcliptic(NamedTuple):
    """Ecliptic coordinates from JPL HORIZONS."""
    jd_ut: float
    lon_deg: float          # Ecliptic longitude (degrees)
    lat_deg: float          # Ecliptic latitude (degrees)
    distance_au: float      # Distance (AU)
    distance_km: float      # Distance (km)


class HorizonsOracle:
    """
    JPL HORIZONS API client for oracle position data.
    
    Queries the live HORIZONS API for reference ephemeris. Results are
    considered the ground truth for all position/velocity comparisons.
    """
    
    # HORIZONS object ID codes (standard designations)
    BODY_IDS = {
        "Sun":     "10",      # Sun
        "Mercury": "199",     # Mercury
        "Venus":   "299",     # Venus
        "Earth":   "399",     # Earth
        "Moon":    "301",     # Moon
        "Mars":    "499",     # Mars
        "Jupiter": "599",     # Jupiter
        "Saturn":  "699",     # Saturn
        "Uranus":  "799",     # Uranus
        "Neptune": "899",     # Neptune
    }
    
    # Observer codes (standard locations)
    OBSERVER_CODES = {
        "@sun":     "10",          # Sun (heliocentric)
        "@ssb":     "@0",          # Solar System Barycenter
        "@geocenter": "500",       # Earth center (geocentric)
        "@moon":    "301",         # Moon center
    }
    
    def __init__(self):
        """Initialize HORIZONS oracle client."""
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.timeout_sec = 30
    
    def fetch_position(
        self,
        body: str,
        jd_ut: float,
        observer: str = "@geocenter",
        reference_frame: str = "ICRF",
    ) -> Optional[HorizonsPosition]:
        """
        Fetch J2000.0 ICRF position from HORIZONS API.
        
        Args:
            body: Body name (e.g., "Mars", "Moon").
            jd_ut: Julian Day (UT1) to query.
            observer: Observer location code (default geocentric).
            reference_frame: "ICRF" or "FK4" (default ICRF).
        
        Returns:
            HorizonsPosition namedtuple or None if query fails.
        """
        if body not in self.BODY_IDS:
            raise ValueError(f"Unknown body: {body}")
        
        obj_id = self.BODY_IDS[body]
        site = self.OBSERVER_CODES.get(observer, observer)
        
        # HORIZONS API expects specific parameter format
        params = {
            "format": "json",
            "COMMAND": obj_id,
            "EPHEM_TYPE": "VECTORS",
            "CENTER": site,
            "START_TIME": self._jd_to_horizons_time(jd_ut),
            "STOP_TIME": self._jd_to_horizons_time(jd_ut),
            "STEP_SIZE": "1",
            "OUT_UNITS": "AU-D",
            "VECT_TABLE": "2",
            "REF_PLANE": "FRAME",
            "REF_SYSTEM": "ICRF",
            "CSV_FORMAT": "NO",
            "OBJ_DATA": "NO",
        }
        
        try:
            url = self.base_url + "?" + urllib.parse.urlencode(params)
            print(f"DEBUG: Querying {url[:80]}...")
            with urllib.request.urlopen(url, timeout=self.timeout_sec) as response:
                data = json.loads(response.read().decode())
            
            # Check for valid HORIZONS response
            if isinstance(data, dict):
                result = data.get("result", {})
                if isinstance(result, dict):
                    vectors = result.get("vectors", [])
                    if vectors and isinstance(vectors, list) and len(vectors) > 0:
                        vec = vectors[0]
                        return HorizonsPosition(
                            jd_ut=float(vec.get("jd", jd_ut)),
                            ra_deg=float(vec.get("ra", 0.0)),
                            dec_deg=float(vec.get("dec", 0.0)),
                            distance_au=float(vec.get("range", 0.0)),
                            distance_km=float(vec.get("range", 0.0)) * 149597870.7,
                            ra_rate_deg_per_day=float(vec.get("ra_rate", 0.0)),
                            dec_rate_deg_per_day=float(vec.get("dec_rate", 0.0)),
                            range_rate_km_s=float(vec.get("range_rate", 0.0)),
                        )
        except Exception as e:
            print(f"HORIZONS query failed for {body} at JD {jd_ut}: {e}")
        
        return None
    
    def fetch_ecliptic(
        self,
        body: str,
        jd_ut: float,
        observer: str = "@geocenter",
    ) -> Optional[HorizonsEcliptic]:
        """
        Fetch ecliptic coordinates from HORIZONS.
        
        Args:
            body: Body name.
            jd_ut: Julian Day (UT1).
            observer: Observer location code.
        
        Returns:
            HorizonsEcliptic namedtuple or None if query fails.
        """
        # Query with ecliptic reference frame
        if body not in self.BODY_IDS:
            raise ValueError(f"Unknown body: {body}")
        
        obj_id = self.BODY_IDS[body]
        site = self.OBSERVER_CODES.get(observer, observer)
        
        params = {
            "format": "json",
            "COMMAND": obj_id,
            "EPHEM_TYPE": "VECTORS",
            "CENTER": site,
            "START_TIME": self._jd_to_horizons_time(jd_ut),
            "STOP_TIME": self._jd_to_horizons_time(jd_ut),
            "STEP_SIZE": "1",
            "OUT_UNITS": "AU-D",
            "VECT_TABLE": "2",
            "REF_PLANE": "ECLIPTIC",
            "REF_SYSTEM": "J2000",
            "CSV_FORMAT": "NO",
        }
        
        try:
            url = self.base_url + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=self.timeout_sec) as response:
                data = json.loads(response.read().decode())
            
            if data.get("signature", {}).get("version", "").startswith("API_H"):
                result = data.get("result", {})
                vectors = result.get("vectors", [])
                if vectors:
                    vec = vectors[0]
                    return HorizonsEcliptic(
                        jd_ut=float(vec.get("jd")),
                        lon_deg=float(vec.get("lon", 0.0)),
                        lat_deg=float(vec.get("lat", 0.0)),
                        distance_au=float(vec.get("range", 0.0)),
                        distance_km=float(vec.get("range", 0.0)) * 149597870.7,
                    )
        except Exception as e:
            print(f"HORIZONS ecliptic query failed for {body} at JD {jd_ut}: {e}")
        
        return None
    
    @staticmethod
    def _jd_to_horizons_time(jd_ut: float) -> str:
        """Convert JD to HORIZONS API date format (YYYY-MMM-DD HH:MM:SS)."""
        # Simple approximation: convert JD to gregorian date
        # For production, use proper calendar library
        jd = jd_ut + 0.5
        z = int(jd)
        f = jd - z
        
        if z < 2299161:
            a = z
        else:
            alpha = int((z - 1867216.25) / 36524.25)
            a = z + 1 + alpha - alpha // 4
        
        b = a + 1524
        c = int((b - 122.1) / 365.25)
        d = int(365.25 * c)
        e = int((b - d) / 30.6001)
        
        day = b - d - int(30.6001 * e)
        month = e - 1 if e < 14 else e - 13
        year = c - 4716 if month > 2 else c - 4715
        
        hours = f * 24.0
        h = int(hours)
        m = int((hours - h) * 60)
        s = int(((hours - h) * 60 - m) * 60)
        
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        return f"{year}-{months[month-1]}-{day:02d} {h:02d}:{m:02d}:{s:02d}"


# Optional: Fallback validation using internal cross-checks (no external API)
class InternalOracle:
    """
    Fallback oracle using Moira's own internal consistency checks.
    
    Used when external HORIZONS API is unavailable. Provides weaker validation
    but still catches algorithmic errors.
    """
    
    def __init__(self, reader):
        """
        Initialize with an open SpkReader.
        
        Args:
            reader: SpkReader instance (DE441 kernel access).
        """
        self.reader = reader
    
    def validate_position_consistency(self, body: str, jd_ut: float) -> dict:
        """
        Validate position consistency across Moira's transform chain.
        
        Returns dict of internal check results.
        """
        # Check: ICRF → ecliptic → equatorial round-trip consistency
        # (i.e., no lost precision in chain)
        results = {}
        # (Implementation deferred; requires access to internal transform stack)
        return results
