#!/usr/bin/env python
"""
Check what segment types are in asteroids.bsp and comets.bsp
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moira.spk_reader import SpkReader

kernels = [
    "kernels/asteroids.bsp",
    "kernels/comets.bsp",
]

for kernel_path in kernels:
    path = Path(kernel_path)
    if not path.exists():
        print(f"✗ {kernel_path} - NOT FOUND\n")
        continue
    
    print(f"=== {kernel_path} ===")
    
    try:
        with SpkReader(path) as reader:
            # Get all segments
            segment_types = set()
            body_count = 0
            
            for pair, segments in reader._segments_by_pair.items():
                body_count += 1
                for seg in segments:
                    seg_type = getattr(seg, 'data_type', 'unknown')
                    segment_types.add(seg_type)
            
            print(f"Bodies: {body_count}")
            print(f"Segment types: {sorted(segment_types)}")
            
            # Type 13 is Hermite interpolation
            # Type 2/3 are Chebyshev
            if 13 in segment_types:
                print("✓ Contains Type 13 (Hermite)")
            if 2 in segment_types or 3 in segment_types:
                print("✓ Contains Type 2/3 (Chebyshev)")
            
            print()
            
    except Exception as e:
        print(f"✗ Error: {e}\n")
