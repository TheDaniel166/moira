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
        
        print(f"Kernel Pool consists of {len(reader._readers)} readers:")
        for i, r in enumerate(reader._readers):
            has_seg = r.has_segment(0, 2000008) or r.has_segment(10, 2000008)
            # Inspect properties of SmallBodyKernel
            attrs = []
            for attr in ["_path", "path", "kernel_path", "_file", "file"]:
                if hasattr(r, attr):
                    attrs.append(f"{attr}={getattr(r, attr)}")
            attr_str = ", ".join(attrs)
            print(f"  Reader {i}: {r.__class__.__name__} ({attr_str})")
            print(f"    Has Flora (2000008): {has_seg}")
            if has_seg:
                # Let's see what segment type and properties it has
                # Let's inspect segment coverage
                cov = r.coverage().get((0, 2000008)) or r.coverage().get((10, 2000008))
                print(f"    Coverage: {cov}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
