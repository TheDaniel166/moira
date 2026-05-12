import time
from moira import Moira, Body
from moira.julian import ut_to_tt
from moira.planets import _npe_body_route_segment_specs
from moira.coordinates import vec_sub, vec_add, icrf_to_ecliptic

m = Moira()
# We must use the DE441 reader directly for _npe_body_route_segment_specs
de441 = m._reader._readers[0]

jd_start = 2451545.0
jd_end = jd_start + 365.25 * 5
step = 1.0
jds = [jd_start + i * step for i in range(int((jd_end - jd_start)/step))]

start = time.perf_counter()

# Ensure we have the handle
handle = de441._kernel._handle

# Prepare routes
# Earth = SSB -> EMB -> Earth = (0,3) + (3,399)
# Jupiter = SSB -> Jupiter = (0,5)
# Note: Earth is 399, EMB is 3. We can just use de441._segment_for to find the segments!
earth_emb_seg = de441._segment_for(0, 3, ut_to_tt(jd_start))
emb_earth_seg = de441._segment_for(3, 399, ut_to_tt(jd_start))
jup_seg = de441._segment_for(0, 5, ut_to_tt(jd_start))

# Create requests
requests = []
jds_tt = [ut_to_tt(jd) for jd in jds]

for jd_tt in jds_tt:
    requests.append((int(earth_emb_seg.start_i), int(earth_emb_seg.end_i), int(earth_emb_seg.data_type), jd_tt))
    requests.append((int(emb_earth_seg.start_i), int(emb_earth_seg.end_i), int(emb_earth_seg.data_type), jd_tt))
    requests.append((int(jup_seg.start_i), int(jup_seg.end_i), int(jup_seg.data_type), jd_tt))

raw = handle.batch_segment_position_requests(requests)

lons = []
for i in range(len(jds)):
    idx = i * 3
    ssb_emb = raw[idx]
    emb_earth = raw[idx+1]
    ssb_jup = raw[idx+2]
    
    ssb_earth = vec_add(ssb_emb, emb_earth)
    earth_to_jup = vec_sub(ssb_jup, ssb_earth)
    
    # Simple ecliptic longitude (ignoring obliquity for speed, or using coarse obliquity)
    # Actually icrf_to_ecliptic uses true obliquity, but we can just use 23.4392911
    from moira.julian import nutation_2000a
    # Geometric longitude
    ecl = icrf_to_ecliptic(earth_to_jup[0], earth_to_jup[1], earth_to_jup[2], 23.4392911)
    lons.append(ecl)

elapsed = time.perf_counter() - start
print(f"Time to batch requests and compute {len(jds)} longitudes: {elapsed:.4f} seconds")
