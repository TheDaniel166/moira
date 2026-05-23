import sys
import os
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.julian import julian_day, ut_to_tt, delta_t_from_jd
from moira.asteroids import asteroid_at
from moira.spk_reader import use_reader_override
from moira.coordinates import ecliptic_to_equatorial
from moira.obliquity import true_obliquity
from moira.houses import calculate_houses

def placidus_3d_house(ra: float, dec: float, ramc: float, lat: float, obliquity: float) -> float:
    # Convert degrees to radians
    ra_rad = math.radians(ra)
    dec_rad = math.radians(dec)
    ramc_rad = math.radians(ramc)
    lat_rad = math.radians(lat)
    
    # Hour angle (LHA) of the body
    # LHA = RAMC - RA
    lha = (ramc - ra + 180.0) % 360.0 - 180.0
    lha_rad = math.radians(lha)
    
    # Calculate semi-diurnal arc (SD)
    # cos(SD) = -tan(lat) * tan(dec)
    val = -math.tan(lat_rad) * math.tan(dec_rad)
    if val >= 1.0:
        # Circumpolar (never rises)
        return 0.0
    elif val <= -1.0:
        # Circumpolar (never sets)
        return 0.0
    
    sd_rad = math.acos(val)
    sd = math.degrees(sd_rad)
    sn = 180.0 - sd  # semi-nocturnal arc
    
    # Determine if body is above or below horizon in Placidus space
    # In Placidus, diurnal/nocturnal is determined by the diurnal/nocturnal arcs
    # Let's compute the diurnal/nocturnal position
    # The diurnal hemisphere is LHA in [-SD, SD]
    is_diurnal = abs(lha) <= sd
    
    if is_diurnal:
        # Above horizon
        # Upper meridian (MC) is LHA = 0
        # Eastern side (houses 10, 11, 12): LHA > 0 (body is rising towards MC)
        # Western side (houses 7, 8, 9): LHA < 0 (body is setting away from MC)
        # Fraction of semi-arc from MC
        frac = abs(lha) / sd
        
        if lha >= 0:
            # Eastern diurnal (MC -> ASC)
            # MC = 10.0 (frac = 0)
            # ASC = 13.0 / 1.0 (frac = 1)
            # House position is: 10 + 3 * frac
            return 10.0 + 3.0 * frac
        else:
            # Western diurnal (MC -> DSC)
            # MC = 10.0 (frac = 0)
            # DSC = 7.0 (frac = 1)
            # House position is: 10 - 3 * frac
            # Wait, house range is [7.0, 10.0]
            return 10.0 - 3.0 * frac
    else:
        # Below horizon
        # Lower meridian (IC) is LHA = 180 or -180
        # Eastern side (houses 1, 2, 3): LHA is negative (going from IC to ASC)
        # Wait! Let's check LHA signs:
        # LHA = RAMC - RA
        # LHA = 0 is MC
        # LHA = 180 is IC
        # Eastern nocturnal (IC -> ASC)
        # Western nocturnal (IC -> DSC)
        # Let's compute distance from IC
        # IC is LHA = 180 or -180
        dist_ic = 180.0 - abs(lha)
        frac = dist_ic / sn
        
        if lha >= 0:
            # Western nocturnal (DSC -> IC)
            # DSC = 7.0 (frac = 0)
            # IC = 4.0 (frac = 1)
            # House position is: 7 - 3 * frac
            return 7.0 - 3.0 * frac
        else:
            # Eastern nocturnal (ASC -> IC)
            # ASC = 1.0 (or 13.0) (frac = 0)
            # IC = 4.0 (frac = 1)
            # House position is: 1.0 + 3.0 * frac
            # Wait! If frac goes from 0 (ASC) to 1 (IC), then house position is 1.0 + 3.0 * frac
            # Since houses are 1, 2, 3:
            # ASC is cusp 1 (1.0)
            # IC is cusp 4 (4.0)
            return 1.0 + 3.0 * frac

def main():
    jd_ut = julian_day(1987, 8, 3, 13.0 + 52.0 / 60.0)
    lat = -12.033333
    lon = -77.016667
    
    try:
        engine = moira.Moira()
        # Compute houses to get RAMC and obliquity
        h_cusps = calculate_houses(jd_ut, lat, lon, "P")
        ramc = h_cusps.armc
        obliquity = true_obliquity(ut_to_tt(jd_ut))
        
        print(f"RAMC: {ramc:.6f}°")
        print(f"Obliquity: {obliquity:.6f}°")
        print(f"Ascendant (Moira): {h_cusps.asc:.6f}°")
        print(f"MC (Moira): {h_cusps.mc:.6f}°")
        
        # Swiss Ephemeris reference data from the image:
        swiss_data = {
            "Ceres":       {"ra": 260.8470411, "dec": -27.40204287, "house": 3.91559979},
            "Pallas":      {"ra": 233.8274962, "dec": 19.2887369,  "house": 3.065329687},
            "Juno":        {"ra": 333.0950213, "dec": -1.38022627,  "house": 6.337459304},
            "Vesta":       {"ra": 95.32602581, "dec": 21.25396924, "house": 10.42673257},
            "Astraea":     {"ra": 177.2705037, "dec": 4.844167984,  "house": 1.168234198},
            "Hebe":        {"ra": 290.3651591, "dec": -13.06990453, "house": 4.934953841},
            "Iris":        {"ra": 291.9973976, "dec": -15.92435715, "house": 4.998582535},
            "Flora":       {"ra": 326.2090307, "dec": -18.77346117, "house": 6.201941698},
            "Metis":       {"ra": 145.6603304, "dec": 17.78075056,  "house": 12.17680018},
            "Hygiea":      {"ra": 124.7031927, "dec": 18.76268834, "house": 11.45033903},
            "Parthenope":  {"ra": 143.9829878, "dec": 15.50504818,  "house": 12.10538916},
            "Victoria":    {"ra": 122.7278883, "dec": 14.38136144,  "house": 11.36510144},
            "Egeria":      {"ra": 77.39083352, "dec": 26.96245217,  "house": 9.791951985}
        }
        
        print("\nPlacidus 3D House Position Verification:")
        print("-" * 80)
        print(f"{'Body':12s} | {'Swiss Value':15s} | {'Moira (3D Placidus)':20s} | {'Difference':15s}")
        print("-" * 80)
        
        with use_reader_override(engine._reader):
            for name, swiss in swiss_data.items():
                pos = asteroid_at(name, jd_ut)
                # Compute RA/Dec using Moira positions to ensure consistency
                m_ra, m_dec = ecliptic_to_equatorial(pos.longitude, pos.latitude, obliquity)
                m_ra = m_ra % 360.0
                
                # Option 1: Compute 3D Placidus using Swiss RA/Dec values from the image
                h_3d_swiss = placidus_3d_house(swiss["ra"], swiss["dec"], ramc, lat, obliquity)
                # Option 2: Compute 3D Placidus using Moira's computed RA/Dec
                h_3d_moira = placidus_3d_house(m_ra, m_dec, ramc, lat, obliquity)
                
                diff = h_3d_moira - swiss["house"]
                print(f"{name:<12s} | {swiss['house']:15.8f} | {h_3d_moira:20.8f} | {diff:+.8f}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
