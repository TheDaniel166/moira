"""Explicit synthetic geometry for structural strength tests, never an oracle.

These fixtures have no ephemeris provenance: flat declinations, chosen
30-Sha motional values, and stated day/night geometry. Real-date/source
acceptance lives in test_shadbala_source_repairs and the REST regression.
"""

from moira.shadbala_context import ShadbalaContext, SEVEN


def supplied_context(
    positions,
    jd=2451545.0,
    system="Lahiri",
    is_day=True,
    vara_lord="Sun",
    hora_lord=None,
    abda="Saturn",
    masa="Saturn",
):
    return ShadbalaContext(
        jd,
        system,
        tuple((p, positions[p] % 360) for p in SEVEN),
        tuple((p, 0.0) for p in SEVEN),
        tuple((p, 30.0) for p in SEVEN),
        0.5 if is_day else 0.0,
        jd - 0.25 if is_day else jd - 0.75,
        jd + 0.25 if is_day else jd - 0.25,
        jd + 0.75 if is_day else jd + 0.25,
        abda,
        masa,
        vara_lord,
        hora_lord,
    )
