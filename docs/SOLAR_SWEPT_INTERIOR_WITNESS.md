# Swept central-footprint interior witnesses

`moira.solar_swept_witness` provides a one-sided diagnostic for a specific
WGS-84 site and a caller-supplied closed UT1 interval. It tests the site at
explicitly supplied instants; it does not calculate or draw an event's
time-swept boundary.

At a sampled instant, the Sun and Moon must have separated foreground depth
intervals, one apparent disc must strictly contain the other, and the Sun's
center must lie strictly above the geometric horizon. Strict containment is
measured by `abs(moon_radius - sun_radius) - separation`; daylight is measured
by Sun-center altitude. Both margins are in radians and must exceed the
declared numerical guard. Equal radii, cone-apex ambiguity, grazing contacts,
and horizon equality do not create a positive witness.

The strict inequalities persist in an open neighborhood on the WGS-84
surface. Thus a positive snapshot puts the site in the **interior relative
to that surface** of the instantaneous visible total/annular footprint. That
footprint is contained in the union over the supplied interval, so the site
cannot lie on that union's surface-relative boundary. This inference applies
only to the declared model and to an interval containing the witness time.
It does not identify the boundary at other sites or times. The `1e-12`
radian minimum guard is a numerical threshold, not a certified bound on all
floating-point, ephemeris, shape, or atmospheric errors.

```python
from moira.eclipse import EclipseCalculator
from moira.julian import julian_day
from moira.solar_swept_witness import inspect_swept_central_interior

t = julian_day(2003, 5, 31, 4 + 8/60)
result = inspect_swept_central_interior(
    EclipseCalculator(), 64.02666666666667, -28.0,
    [t, t + 60/86400], interval_ut1=(t, t + 120/86400),
)
print(result.status, result.witness)
```

The example uses the rounded northern point at 04:08 in [NASA's 2003 path
table](https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html).
Under Moira's stated native model the Sun center is below the geometric
horizon at that listed instant, while the same site is strictly inside the
visible annular footprint 60 seconds later. The source's rounded coordinates,
time interpretation, and model differ from Moira's; this is a native-model
counterexample to identifying a time-stamped table limit with the boundary
of a full temporal union, not a claim of NASA parity.

The result records the site, full interval, tested instants through the
witness, UT1 and TT, identified ephemeris, angular margins, Earth/surface and
vector/horizon policies, and optional caller-provided lunation. All input
times are checked against the closed interval before ephemeris access;
lunation is provenance only and is not independently verified. The native
model uses zero-elevation WGS-84, Sun and Moon retarded to the Earth's
reception epoch, a geometric Sun-center horizon, and spherical limbs. It does
not include terrain, refraction, or separate observer-reception light-time.

If no strict snapshot is found the result is `unresolved`, with
`complete=False`. That is not evidence that the site is outside the union,
inside it, or on its boundary. Provider and unsupported-domain errors
propagate; they are not converted into a negative result.
