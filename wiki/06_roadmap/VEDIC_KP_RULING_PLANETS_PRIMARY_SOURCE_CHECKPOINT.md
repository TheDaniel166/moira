# KP ruling planets

The engine evaluates the five direct ruling roles for an observation instant
and place. It uses the established Moira Krishnamurti sidereal partition.
The caller can supply the Moon, Ascendant and sunrise weekday, or resolve
those inputs with a bound ephemeris reader.

## Primary rules

K. S. Krishnamurti lists the weekday lord, the Moon's star lord, the Moon's
sign lord, the Ascendant's sign lord, and the Ascendant's rising star lord
in Reader III, p. 506. Reader VI, pp. 125–127, works through the same five
roles and prints each planet once in its summary even when it fills more
than one role. The result lists the five roles in the order used in those
worked examples. Its distinct planet list preserves the order of first
appearance. The list order is presentation order for this profile.
[Reader III, printed p. 506](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=518)
[Reader VI, printed pp. 125–127](https://storage.yandexcloud.net/j108/library/3sf9ydin/K.S._Krishnamurti_-_Horary_Astrology_Krishnamurti_Padhdhati_Advanced_Stellar_System.pdf#page=77)

Reader VI, p. 123, links Sunday through Saturday to Sun, Moon, Mars, Mercury,
Jupiter, Venus, and Saturn respectively. Reader III, p. 511, defines the
astrological day by successive local sunrises. Its p. 506 rectification
example calls 4:26 a.m. on 9 November 1942 a Sunday birth, although 9 November
was civil Monday. The prior civil date was Sunday. For dated inputs,
Moira uses the caller-selected sunrise definition and site time zone.
The default is the established Rashtriya upper-limb threshold. A unique
sunrise at or before the instant on the site's local date or immediately
preceding date supplies the weekday. The event instant itself starts the
new weekday. Sunrises outside that bounded date window are outside this
profile's search.
[Reader III, printed p. 511](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=523)
[Reader VI, printed p. 123](https://storage.yandexcloud.net/j108/library/3sf9ydin/K.S._Krishnamurti_-_Horary_Astrology_Krishnamurti_Padhdhati_Advanced_Stellar_System.pdf#page=76)

The optional Reader VI sign-agent rule uses the lord of the sign a node
occupies. The p. 123 examples explicitly connect this rule to the weekday,
Moon sign, and Ascendant sign roles. Either sign of a two-sign owner
qualifies. When both node longitudes are supplied, or when a mean or true
node mode is explicitly selected, the result appends admitted node agents
to the distinct planet list and returns the role evidence separately.
A node already present as a direct star lord appears once in the distinct
list. In the p. 223–224 loan example, Ketu in Virgo represents Mercury,
the lord of Wednesday. Conjunction, aspect, and star-based
representation and retrograde filtering are used in particular judgments
in the Readers and require separately owned selection rules.
[Reader VI, printed pp. 223–224](https://storage.yandexcloud.net/j108/library/3sf9ydin/K.S._Krishnamurti_-_Horary_Astrology_Krishnamurti_Padhdhati_Advanced_Stellar_System.pdf#page=126)

## Worked verification

Before implementation, the roles were calculated independently from the
printed longitudes using exact signs, 27 equal stars, and the weekday
table, or reconstructed from the printed signs and stars when the source
gave sectors.

| Source | Verified inputs | Five direct roles in source order | Distinct direct rulers |
| --- | --- | --- | --- |
| Reader VI pp. 125–126, Kandy telephone booking, 21 September 1969 | Sunday, Moon Capricorn 1°52′, Ascendant Libra 20°22′ | Sun, Sun, Saturn, Venus, Jupiter | Sun, Saturn, Venus, Jupiter |
| Reader VI p. 127, friend's arrival, 9 February 1969 | Sunday, Moon Libra/Swathi, Ascendant Taurus/Rohini | Sun, Rahu, Venus, Venus, Moon | Sun, Rahu, Venus, Moon |
| Reader III p. 506, moment of analysis, 7 April 1966 | Thursday, Moon Libra/Swathi, Ascendant Aries/Bharani | Jupiter, Rahu, Venus, Mars, Venus | Jupiter, Rahu, Venus, Mars |

Applying the separately verified p. 123 sign rule to the p. 125 nodal
positions gives Rahu in Aquarius as Saturn's agent and Ketu in Leo as
the Sun's agent. The p. 126 summary gives the direct list above. The two
outputs are independently inspectable.

The modern DE441 reconstruction of the telephone booking used the printed
09:00 local clock as UTC+05:30, latitude 7°28′ N, longitude 80°27′ E, and
the existing Moira Krishnamurti ayanamsa. The Moon stays in the same
printed sign and star. The reconstructed Ascendant is about Libra 19°47′,
roughly 35 arcminutes earlier than the printed Libra 20°22′ and on the
other side of the Swathi/Vishakha boundary. The doctrine fixture uses the
printed angles. The modern chart composition is independently exercised
by DE441 parity tests. The cause of the historical Ascendant difference
is unresolved.

## Engine and REST

- `kp_ruling_planets` and `POST /v1/kp/ruling-planets` accept canonical
  sidereal Moon and Ascendant angles, the resolved weekday (Monday=0), and
  optionally both sidereal node angles.
- `kp_ruling_planets_for_datetime` and `POST /v1/kp/chart/ruling-planets`
  accept an offset-aware instant, location, and site time zone. The resolved
  sunrise, TT epoch, ayanamsa path, and reader identity accompany the roles.
  An eastern Ascendant can be available when the full Placidus cusp figure
  is unavailable. When sunrise or the Ascendant is unavailable, the other
  roles remain in the result with explicit availability reasons.

The regression tests cover printed examples, repeated roles, node agents,
sign and star endpoints, the exact sunrise rollover, polar partial results,
and direct, facade, and HTTP parity.
