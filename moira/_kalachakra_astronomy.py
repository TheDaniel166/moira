"""Reader-bound Moon composition for Kalachakra; no server or alternate-dasha owner."""
from ._ephemeris_time import _bind_ephemeris_time, _EphemerisTimeBasisError
from .julian import utc_to_ut1
from .planets import planet_at
from .sidereal import _ayanamsa_at_tt, _STAR_ANCHORED
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from .stars import star_at
from ._kalachakra_types import (
    KalachakraEpoch, KalachakraAstronomy, KalachakraProvenance, KalachakraInvariantError,
    KalachakraCoverageError, KalachakraResourceError, astronomical_epoch, named_ayanamsa, angle,
)


def derive(epoch, ayanamsa_system, tropical, reader):
    """Bind one epoch, reduce one ayanamsa, and optionally derive a geocentric Moon."""
    jd = astronomical_epoch(epoch)
    named_ayanamsa(ayanamsa_system)
    if tropical is not None:
        tropical = angle(tropical,"moon_tropical_lon")
    derived = tropical is None
    jd_ut1 = utc_to_ut1(jd)
    try:
        reader = get_reader() if reader is None else reader
        with use_reader_override(reader):
            bound = _bind_ephemeris_time(jd_ut1,reader)
            identity = bound.identity
            if any(v is None for v in (identity.planetary_ephemeris,identity.lunar_ephemeris,
                                      identity.lunar_tidal_acceleration_arcsec_per_cy2)):
                raise KalachakraResourceError("declared planetary/lunar clock identity is required")
            anchor = None
            if ayanamsa_system in _STAR_ANCHORED:
                anchor,target = _STAR_ANCHORED[ayanamsa_system]
                try:
                    star = star_at(anchor,bound.epoch_tt,product="astrometric")
                except (KeyError,ValueError) as exc:
                    # These errors belong to the anchor lookup/catalogue contract.
                    raise KalachakraResourceError("required live anchor catalogue is unavailable or invalid") from exc
                offset = (star.longitude-target)%360
            else:
                offset = _ayanamsa_at_tt(bound.epoch_tt,ayanamsa_system,"true")
            if derived:
                tropical = planet_at("Moon",jd_ut1,reader=reader,jd_tt=bound.epoch_tt,
                    apparent=True,aberration=True,grav_deflection=True,nutation=True,
                    center="geocentric",frame="ecliptic").longitude
            receipt = KalachakraAstronomy(jd_ut1,bound.epoch_tt,bound.epoch_tdb,
                bound.delta_t_seconds,bound.delta_t_correction_seconds,bound.tdb_minus_tt_seconds,
                bound.raw_delta_t.source_product,identity.summary_label,
                identity.planetary_ephemeris,identity.lunar_ephemeris,
                identity.lunar_tidal_acceleration_arcsec_per_cy2,ayanamsa_system,offset,anchor)
    except OutOfRangeError as exc:
        raise KalachakraCoverageError("birth epoch is outside serving ephemeris coverage") from exc
    except (MissingKernelError,_EphemerisTimeBasisError,FileNotFoundError) as exc:
        raise KalachakraResourceError("required Kalachakra ephemeris, time identity or live anchor is unavailable") from exc
    except (ValueError,TypeError,AttributeError,LookupError) as exc:
        # Missing anchor keys were translated at their lookup above. Elsewhere,
        # KeyError and IndexError describe generated-state defects, not outages.
        raise KalachakraInvariantError("invalid generated Kalachakra astronomical context") from exc
    try:
        normalized = KalachakraEpoch(epoch.kind,epoch.value).value.isoformat() if epoch.kind == "datetime" else None
        return KalachakraProvenance("derived_moon" if derived else "supplied_tropical",
            (tropical-offset)%360,jd,normalized,tropical,receipt)
    except (ValueError,TypeError,AttributeError,KeyError) as exc:
        raise KalachakraInvariantError("invalid generated Kalachakra astronomical provenance") from exc
