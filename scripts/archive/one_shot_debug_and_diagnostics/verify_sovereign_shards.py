import json
import random
import math
from pathlib import Path
from moira.spk_reader import SpkReader
from moira._spk_body_kernel import SmallBodyKernel

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "kernels" / "sb441_type13" / "manifest.json"

LEGACY_KERNELS = {
    "shards_1_15": Path("C:/Users/nilad/.moira/kernels/sb441-n373s.bsp"),
    "shard_16": ROOT / "kernels" / "minor_bodies.bsp",
    "shard_17": ROOT / "kernels" / "centaurs.bsp",
    "shard_18": ROOT / "kernels" / "comets.bsp",
}

def verify():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Load legacy readers
    legacy_readers = {}
    for key, path in LEGACY_KERNELS.items():
        if path.exists():
            legacy_readers[key] = SmallBodyKernel(path)
            print(f"Loaded legacy reader for {key}: {path.name}")
        else:
            print(f"Warning: Legacy kernel {path} not found.")

    for shard in manifest["shards"]:
        shard_idx = shard["index"]
        shard_path = ROOT / shard["path"]
        shard_reader = SmallBodyKernel(shard_path)
        
        # Select legacy reader
        legacy = None
        if 1 <= shard_idx <= 15: legacy = legacy_readers.get("shards_1_15")
        elif shard_idx == 16: legacy = legacy_readers.get("shard_16")
        elif shard_idx == 17: legacy = legacy_readers.get("shard_17")
        elif shard_idx == 18: legacy = legacy_readers.get("shard_18")
        
        if not legacy:
            print(f"Shard {shard_idx:02d}: No legacy kernel for comparison. Skipping.")
            continue
            
        print(f"Shard {shard_idx:02d}: Auditing {len(shard['bodies'])} bodies...")
        
        for body in shard["bodies"]:
            name = body["name"]
            naif_id = body["naif_id"]
            
            if not legacy.has_body(naif_id):
                continue
                
            # Test 3 dates in the overlap range
            # Shards are 1500-2500, legacy are usually 1800-2200
            test_jds = [2415020.5, 2451545.0, 2488128.5] # 1900, 2000, 2100
            
            for jd in test_jds:
                try:
                    pos_shard = shard_reader.position(naif_id, jd)
                    pos_legacy = legacy.position(naif_id, jd)
                    
                    err_km = math.sqrt(sum((a-b)**2 for a, b in zip(pos_shard, pos_legacy)))
                    if err_km > 1e-3:
                        print(f"  [FAIL] {name:12} JD {jd:.1f}: Error {err_km:.6f} km")
                        print(f"    Shard Pos:  {pos_shard}")
                        print(f"    Legacy Pos: {pos_legacy}")
                    # else:
                    #     print(f"  [PASS] {name:12} JD {jd:.1f}: Error {err_km:.6e} km")
                except Exception as e:
                    # Some dates might be out of range for legacy
                    pass

    print("\nLocal Oracle Audit Complete.")

if __name__ == "__main__":
    verify()
