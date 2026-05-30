
import math
from bisect import bisect_left
from moira._spk_body_kernel import SmallBodyKernel, _hermite_eval_3d, T0, S_PER_DAY

def trace_apollo():
    shard = SmallBodyKernel('kernels/sb441_type13/sb441_type13_shard_016.bsp')
    seg = next(s for s in shard._kernel.segments if s.target == 2001862)
    states, epochs_jd, ws = seg._data
    
    t = 2451545.0
    idx = bisect_left(epochs_jd, t)
    half = ws // 2
    start = max(0, min(idx - half, len(epochs_jd) - ws))
    
    win_jd = epochs_jd[start:start + ws]
    win_t = [(jd - T0) * S_PER_DAY for jd in win_jd]
    t_sec = (t - T0) * S_PER_DAY
    
    pos = [axis[start:start + ws] for axis in states[:3]]
    vel = [axis[start:start + ws] for axis in states[3:]]
    
    print(f"t_sec: {t_sec}")
    print(f"win_t: {win_t}")
    print(f"Pos 0: {[p[0] for p in pos]}")
    print(f"Vel 0: {[v[0] for v in vel]}")
    
    # Manual Hermite Trace
    n = len(pos[0])
    m = 2 * n
    z = [0.0] * m
    for i, value in enumerate(win_t):
        z[2*i] = value
        z[2*i+1] = value
    
    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2*i] = pos[axis][i]
            prev[axis][2*i+1] = pos[axis][i]
            
    # First divided differences
    curr = [[0.0] * (m-1) for _ in range(3)]
    for i in range(m-1):
        if i % 2 == 0:
            for axis in range(3): curr[axis][i] = vel[axis][i//2]
        else:
            denom = z[i+1] - z[i]
            for axis in range(3): curr[axis][i] = (prev[axis][i+1] - prev[axis][i]) / denom
            
    print(f"First DivDiff (i=0): {[curr[ax][0] for ax in range(3)]}")
    print(f"First DivDiff (i=1): {[curr[ax][1] for ax in range(3)]}")
    
    res = _hermite_eval_3d(t_sec, win_t, pos, vel)
    print(f"Result: {res}")

if __name__ == "__main__":
    trace_apollo()
