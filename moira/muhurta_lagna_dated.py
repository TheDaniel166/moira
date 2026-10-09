"""Reader-bound instantaneous Muhurta Lagna and optional canonical Shadbala."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from math import nextafter
from .muhurta_lagna import MuhurtaLagnaPolicy, MuhurtaLagnaAssessment, evaluate_muhurta_lagna_strength, _SEVEN
from .gochara_dated import GocharaDatePolicy, GocharaEpoch, GocharaResourceError, _epoch
from .muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
from .spk_reader import KernelReader, get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from ._ephemeris_time import _EphemerisTimeBasisError
from .julian import jd_from_datetime, utc_to_ut1
from .nodes import true_node
from .sayanadi_dated import _lagna
from .houses import calculate_houses
from .panchanga_shuddhi import _number


def _opposite_node(rahu):
    """Keep the exact opposite sign even when float addition rounds upward."""
    sign = (int(rahu // 30) + 6) % 12
    opposite = rahu + 180 if rahu < 180 else rahu - 180
    return min(opposite, nextafter((sign + 1) * 30., sign * 30.))


@dataclass(frozen=True, slots=True)
class MuhurtaLagnaSnapshot:
    """Epoch, serving-resource identity and finite Lagna components at one instant."""
    dt: datetime
    latitude: float
    longitude: float
    epoch: GocharaEpoch
    assessment: MuhurtaLagnaAssessment
    reader_binding: str
    shadbala_basis: str
    hora_lord: str | None
    node_mode: str = field(init=False, default='true_geometric_of_date')
    longitude_frame: str = field(init=False, default='apparent_geocentric_true_ecliptic_of_date')
    interval_semantics: str = field(init=False, default='instant_only_no_duration_guarantee')


def muhurta_lagna_for_datetime(dt: datetime, latitude: float, longitude: float, *,
        policy: MuhurtaLagnaPolicy | None = None, include_shadbala: bool = False,
        hora_lord: str | None = None, natal_moon_sidereal_longitude: float | None = None,
        natal_lagna_sidereal_longitude: float | None = None,
        reader: KernelReader | None = None) -> MuhurtaLagnaSnapshot:
    """Compute one geocentric snapshot with explicit true nodes and sidereal frame.

    Optional Shadbala reuses its owner, Porphyry house geometry, JD weekday,
    geometric day/night and caller-selected hora lord (omitted when absent).
    Missing/polar Lagna is disclosed; resource/coverage failures never fall back.
    """
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('dt must be a timezone-aware civil datetime')
    rt = dt.astimezone(timezone.utc).astimezone(dt.tzinfo)
    if rt.replace(tzinfo=None) != dt.replace(tzinfo=None) or rt.fold != dt.fold:
        raise ValueError('dt is a nonexistent or inconsistent local civil instant')
    lat, lon = _number('latitude', latitude), _number('longitude', longitude)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('latitude/longitude outside geographic range')
    if type(include_shadbala) is not bool:
        raise TypeError('include_shadbala must be boolean')
    if hora_lord is not None and (type(hora_lord) is not str or hora_lord not in _SEVEN or not include_shadbala):
        raise ValueError('hora_lord requires include_shadbala and a classical planet')
    active = MuhurtaLagnaPolicy() if policy is None else policy
    # Validate optional direct inputs before accessing any resource.
    evaluate_muhurta_lagna_strength({}, jd_ut1=0, policy=active,
        natal_moon_sidereal_longitude=natal_moon_sidereal_longitude,
        natal_lagna_sidereal_longitude=natal_lagna_sidereal_longitude)
    try:
        bound = get_reader() if reader is None else reader
        with use_reader_override(bound):
            jd = utc_to_ut1(jd_from_datetime(dt))
            epoch = _epoch(jd, bound, GocharaDatePolicy(ayanamsa_system=active.ayanamsa_system))
            positions = {p.planet: p.position.sidereal_longitude for p in epoch.positions}
            rahu = (true_node(jd, reader=bound, jd_tt=epoch.jd_tt).longitude - epoch.ayanamsa_degrees) % 360
            ketu = _opposite_node(rahu)
            positions.update(Rahu=rahu, Ketu=ketu)
            lagna = tropical_lagna = None
            if abs(lat) < 90:
                try:
                    # Reuse the singularity guard, then use the canonical house
                    # owner's angle for both the Lagna and Shadbala composition.
                    _lagna(epoch, lat, lon)
                    houses = calculate_houses(jd, lat, lon, 'O')
                    tropical_lagna = houses.asc
                    lagna = (tropical_lagna - epoch.ayanamsa_degrees) % 360
                except ValueError as exc:
                    if 'unique Lagna' not in str(exc):
                        raise
            strength = None
            basis = 'not_requested'
            if include_shadbala and lagna is None:
                basis = 'unavailable_lagna_geometry'
            elif include_shadbala:
                from .planets import planet_at
                from .shadbala import shadbala
                from .dignities import is_day_chart
                from .panchanga import _panchanga_from_resolved_longitudes
                from .sidereal import _nakshatra_position_from_sidereal
                if houses.effective_system != 'O':
                    raise ValueError('Shadbala house geometry must remain Porphyry')
                planets = {p: planet_at(p, jd, reader=bound, jd_tt=epoch.jd_tt) for p in _SEVEN}
                limbs = _panchanga_from_resolved_longitudes(
                    epoch.tropical_longitudes[0], epoch.tropical_longitudes[1], positions['Sun'], positions['Moon'],
                    jd, active.ayanamsa_system, _nakshatra_position_from_sidereal(positions['Moon']))
                strength = shadbala({p: positions[p] for p in _SEVEN}, {p: planets[p].speed for p in _SEVEN},
                    houses, jd, limbs.tithi.number, limbs.vara_lord,
                    is_day_chart(epoch.tropical_longitudes[0], tropical_lagna),
                    ayanamsa_system=active.ayanamsa_system, hora_lord=hora_lord,
                    planet_latitudes={p: planets[p].latitude for p in _SEVEN})
                basis = 'canonical_shadbala_porphyry_jd_weekday_geometric_day_caller_hora'
            assessment = evaluate_muhurta_lagna_strength(positions, jd_ut1=jd,
                lagna_sidereal_longitude=lagna, policy=active, shadbala_result=strength,
                natal_moon_sidereal_longitude=natal_moon_sidereal_longitude,
                natal_lagna_sidereal_longitude=natal_lagna_sidereal_longitude)
            assessment = replace(assessment, input_basis='serving_reader_derived_sidereal_same_epoch')
            return MuhurtaLagnaSnapshot(dt, lat, lon, epoch, assessment,
                'discovered_reader' if reader is None else 'caller_owned_reader', basis, hora_lord)
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError('Muhurta Lagna instant is outside serving kernel coverage') from exc
    except (MissingKernelError, _EphemerisTimeBasisError, GocharaResourceError) as exc:
        raise MuhurtaResourceError('Muhurta Lagna requires the serving planetary, clock and anchor resources') from exc


__all__ = ['MuhurtaLagnaSnapshot', 'muhurta_lagna_for_datetime']
