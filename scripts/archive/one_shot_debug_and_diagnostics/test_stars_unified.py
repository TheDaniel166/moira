import math
from moira.stars import star_at, stars_near

jd = 2451545.0

sirius = star_at('Sirius', jd)
print('=== Sirius ===')
print(sirius)
print('  source:', sirius.source)
print('  has_gaia_data:', sirius.has_gaia_data)

algol = star_at('Algol', jd)
print()
print('=== Algol ===')
print(algol)
print('  source:', algol.source)
dist = algol.distance_ly
print('  distance_ly:', round(dist, 1) if not math.isnan(dist) else 'N/A')
print('  quality:', algol.quality)

print()
print('=== Stars near Aldebaran (orb=1.5) ===')
near = stars_near(69.8, jd, orb=1.5)
for s in near:
    name = s.name if s.name else '(unnamed)'
    d = str(round(s.distance_ly, 0)) + ' ly' if not math.isnan(s.distance_ly) else 'dist?'
    print(' ', name, 'lon=' + str(round(s.longitude, 3)),
          'mag=' + str(round(s.magnitude, 2)), d, 'src=' + s.source)
