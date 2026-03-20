import sys
sys.path.insert(0, '.')
import math
from moira.stars import star_at, stars_near

jd = 2451545.0

for name in ['Algorab', 'Alphecca', 'Fomalhaut', 'Denebola', 'Zavijava']:
    try:
        s = star_at(name, jd)
        dist = round(s.distance_ly, 1) if not math.isnan(s.distance_ly) else 'N/A'
        print(name.ljust(12), 'G=' + str(round(s.magnitude, 2)),
              'src=' + s.source, 'dist=' + str(dist), 'quality=' + str(s.quality))
    except Exception as e:
        print(name + ': ERROR', e)

print()
print('=== stars_near Aldebaran lon=69.8 orb=2.0 ===')
near = stars_near(69.8, jd, orb=2.0)
for s in near:
    name = s.name if s.name else '(unnamed)'
    dist = str(round(s.distance_ly, 0)) + ' ly' if not math.isnan(s.distance_ly) else 'dist?'
    print(' ', name.ljust(20), 'lon=' + str(round(s.longitude, 3)),
          'mag=' + str(round(s.magnitude, 2)), dist.ljust(12), 'src=' + s.source)
