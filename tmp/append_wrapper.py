#!/usr/bin/env python3
"""Append the module-level next_solar_eclipse_at_location wrapper to eclipse.py."""

wrapper = (
    "\n\n"
    "# ---------------------------------------------------------------------------\n"
    "# Module-level convenience wrapper -- sol_eclipse_when_loc equivalent\n"
    "# ---------------------------------------------------------------------------\n"
    "\n"
    "def next_solar_eclipse_at_location(\n"
    "    jd_start: float,\n"
    "    latitude: float,\n"
    "    longitude: float,\n"
    "    *,\n"
    "    elevation_m: float = 0.0,\n"
    '    kind: str = "any",\n'
    "    max_lunations: int = 360,\n"
    "    reader=None,\n"
    ") -> SolarEclipseLocalCircumstances:\n"
    '    """Return local sky circumstances for the next solar eclipse visible at *latitude*, *longitude*.\n'
    "\n"
    "    Module-level convenience wrapper around\n"
    "    EclipseCalculator.next_solar_eclipse_at_location.\n"
    "    Equivalent to Swiss Ephemeris swe_sol_eclipse_when_loc.\n"
    "\n"
    "    Parameters\n"
    "    ----------\n"
    "    jd_start : float\n"
    "        Julian Day (UT) to start searching from.\n"
    "    latitude : float\n"
    "        Observer geodetic latitude in degrees (positive north).\n"
    "    longitude : float\n"
    "        Observer geodetic longitude in degrees (positive east).\n"
    "    elevation_m : float\n"
    "        Observer elevation above the geoid in metres.\n"
    "    kind : str\n"
    "        Eclipse type filter: 'any', 'total', 'annular', 'partial', 'central', or 'hybrid'.\n"
    "    max_lunations : int\n"
    "        Maximum lunations to scan before raising RuntimeError.\n"
    "    reader : SpkReader | None\n"
    "        Optional pre-constructed kernel reader.\n"
    "\n"
    "    Returns\n"
    "    -------\n"
    "    SolarEclipseLocalCircumstances\n"
    '    """\n'
    "    from .spk_reader import get_reader as _get_reader\n"
    "\n"
    "    calc = EclipseCalculator(reader=reader or _get_reader())\n"
    "    return calc.next_solar_eclipse_at_location(\n"
    "        jd_start,\n"
    "        latitude,\n"
    "        longitude,\n"
    "        elevation_m=elevation_m,\n"
    "        kind=kind,\n"
    "        max_lunations=max_lunations,\n"
    "    )\n"
)

with open("moira/eclipse.py", "a", encoding="utf-8") as f:
    f.write(wrapper)

print("appended successfully")
