import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.julian import julian_day
from moira.asteroids import asteroid_at
from moira.spk_reader import use_reader_override, KernelPool

def main():
    jd_ut = julian_day(1987, 8, 3, 13.0 + 52.0 / 60.0)
    
    try:
        engine = moira.Moira()
        reader = engine._reader
        
        # Readers we want to test:
        # Reader 1: sb441_type13_shard_001.bsp
        # Reader 17: sb441-n373s.bsp
        # Reader 18: asteroids.bsp
        
        de441 = reader._readers[0]
        shard1 = reader._readers[1]
        sb441 = reader._readers[17]
        asteroids = reader._readers[18]
        
        pools = {
            "Shard 1 (Type 13)": KernelPool([de441, shard1]),
            "sb441-n373s.bsp (Type 2)": KernelPool([de441, sb441]),
            "asteroids.bsp (Type 13)": KernelPool([de441, asteroids])
        }
        
        print("Flora positions under different kernels at 1987-08-03 13:52:00 UT:")
        print("-" * 100)
        
        for name, pool in pools.items():
            try:
                with use_reader_override(pool):
                    pos = asteroid_at("Flora", jd_ut)
                    print(f"{name:<25s} | Lon: {pos.longitude:12.6f}° | Lat: {pos.latitude:+10.6f}° | Speed: {pos.speed:+10.6f}")
            except Exception as e:
                print(f"{name:<25s} | Error: {e}")
                
        # Also print the Swiss Ephemeris value for comparison
        print(f"{'Swiss Ephemeris (Image)':<25s} | Lon: 322.16832920° | Lat: -4.92014136° | Speed: -0.23794519")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
