import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.spk_reader import use_reader_override

def main():
    try:
        engine = moira.Moira()
        reader = engine._reader
        
        # Check which kernel has Flora (NAIF ID 2000008)
        # Let's inspect the KernelPool readers
        print(f"Kernel Pool consists of {len(reader._readers)} readers:")
        for i, r in enumerate(reader._readers):
            # Check if this reader has a segment for (0, 2000008) or (10, 2000008) or similar
            # SmallBodyKernel or SpkReader
            has_seg = r.has_segment(0, 2000008) or r.has_segment(10, 2000008)
            path_str = getattr(r, "path", "Unknown Path")
            print(f"  Reader {i}: {r.__class__.__name__} - {path_str}")
            print(f"    Has Flora (2000008): {has_seg}")
            if has_seg:
                cov = r.coverage().get((0, 2000008)) or r.coverage().get((10, 2000008))
                print(f"    Coverage: {cov}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
