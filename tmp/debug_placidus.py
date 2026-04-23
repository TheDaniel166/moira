import math
from pathlib import Path
from moira.houses import houses_from_armc
from moira.obliquity import true_obliquity
from moira.julian import ut_to_tt
from scripts.compare_swetest import _angular_diff, _parse_armc_iterations

fixture_text = Path('tests/fixtures/swe_t.exp').read_text(encoding='utf-8', errors='replace')
iters = _parse_armc_iterations(fixture_text)

# Find one failing case
for it in iters:
    if abs(it['armc'] - 9.414838) < 0.001 and abs(it['lat'] - 50.0) < 0.1 and it['hsys'] == 'P':
        jd_tt = ut_to_tt(it['jd_ut'])
        obliquity = true_obliquity(jd_tt)
        result = houses_from_armc(it['armc'], obliquity, it['lat'], 'P')
        print(f"ARMC: {it['armc']:.6f}  LAT: {it['lat']}  OBL: {obliquity:.6f}")
        print(f"MC  (9): exp={it['cusps'][9]:.4f}  got={result.cusps[9]:.4f}")
        print(f"ASC (0): exp={it['cusps'][0]:.4f}  got={result.cusps[0]:.4f}")
        for i in range(12):
            d = _angular_diff(result.cusps[i], it['cusps'][i])
            flag = ' <-- ERROR' if d > 1e-3 else ''
            print(f"  H{i+1:02d} (idx {i}): exp={it['cusps'][i]:.4f}  got={result.cusps[i]:.4f}  diff={d:.4f}{flag}")
        print()

        # Also verify residuals directly for the computed cusps
        eps = obliquity * math.pi / 180
        phi = it['lat'] * math.pi / 180
        armc_r = it['armc'] * math.pi / 180
        ic_r = armc_r + math.pi
        cos_eps = math.cos(eps)
        sin_eps = math.sin(eps)
        tan_phi = math.tan(phi)

        def lam_to_ra(lam):
            return math.atan2(math.sin(lam), cos_eps * math.cos(lam))

        def dsa(lam):
            s = max(-1.0, min(1.0, sin_eps * math.sin(lam)))
            dec = math.asin(s)
            arg = max(-1.0, min(1.0, -tan_phi * math.tan(dec)))
            return math.acos(arg)

        for cusp_idx, frac, label, upper in [(10, 1/3, 'H11 upper', True), (11, 2/3, 'H12 upper', True),
                                              (1, 2/3, 'H2 lower', False), (2, 1/3, 'H3 lower', False)]:
            lam = result.cusps[cusp_idx] * math.pi / 180
            ra = lam_to_ra(lam)
            d = dsa(lam)
            nsa = math.pi - d
            if upper:
                # Normalize ra to [armc_r-pi, armc_r+pi)
                ra_n = armc_r + ((ra - armc_r + math.pi) % (2*math.pi) - math.pi)
                f = ra_n - armc_r - frac * d
                print(f"  {label} residual: f = {math.degrees(f):.6f} deg  (should be ~0)")
            else:
                ra_n = ic_r + ((ra - ic_r + math.pi) % (2*math.pi) - math.pi)
                f = ra_n - ic_r + frac * nsa
                print(f"  {label} residual: f = {math.degrees(f):.6f} deg  (should be ~0)")
        break
