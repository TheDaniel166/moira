# KP house significators

This engine profile applies the four direct links between a graha and a
house in the Krishnamurti method. It accepts the seven classical planets,
Rahu, and Ketu. The twelve opening cusps and all nine planetary longitudes
use the same sidereal frame. The reader-bound entry point uses the existing
Moira Krishnamurti ayanamsa, declared node mode, and strict Placidus geometry.

## Primary rules and decisions

Krishnamurti's *Predictive Stellar Astrology*, Reader III, p. 405, gives
the relative strength of house occupants, planets in their stars, owners,
and planets in the owners' stars. Chandrakant R. Bhatt's *Nakshatra
Chintamani*, pp. 14–18, gives the same four direct relationships and
works them through a complete chart. The cusp is the opening point of
the house in Bhatt's method. The sign on that opening supplies the owner.
[Reader III, printed p. 405](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=417)
[Bhatt, printed pp. 14–18](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=23)

| Rank | Direct link | Evidence returned |
| --- | --- | --- |
| 1 | The graha is in a star ruled by a house occupant | The occupant |
| 2 | The graha occupies the house | The graha itself |
| 3 | The graha is in a star ruled by the cusp sign owner | The owner |
| 4 | The graha owns the sign at the opening cusp | The owner |

The interval includes its opening cusp and excludes the following cusp.
The input starts at house 1 and advances through one zodiac cycle. Direct
comparisons against the supplied angles preserve ownership at a cusp and
on both adjacent floats. Multiple cusps in one sign use the same owner.
No house ownership is assigned to intercepted signs or to the nodes.
Both nodes can occupy a house and rule stars, as demonstrated in the
published examples.

A graha appears once in each applicable house row, with its strongest
numerical rank and supporting links for all ranks it qualifies for. Grahas
with the same rank are tied. Their display order follows the engine's
planet order. Ranks are ordinal and do not express a numerical score.

The sources also describe weaker conjunction and aspect links and nodal
representation. Bhatt discusses influence near a cusp separately from
the single-house placements in the four direct columns of the p. 18
worked table. For example, the p. 15 tables record mixed cusp influence
for Rahu and Ketu, and p. 18 places them in houses 2 and 8 respectively.
The implementation follows the direct columns of p. 18 and the
single-house rule above. The association, near-cusp, and representation
rules remain separate extensions. [Bhatt, printed pp. 3–5 and 17–20](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=12)

## Worked verification

**Bhatt's example birth horoscope 1.** The cusp and graha longitudes are
printed on p. 11. Independent rational arithmetic reproduced all 48
direct-rank cells of the 12-house table on p. 18 before implementation.
In house 4, Mercury and Jupiter occupy Saturn's star and give rank 1.
Saturn occupies house 4 and gives rank 2. Ketu occupies Mars's star and
gives rank 3. Mars owns the Aries opening cusp and gives rank 4. In house
10, Venus gives rank 1 from Jupiter's star and also gives rank 4 as the
owner of the Libra cusp. The regression asserts all 48 cells, including
empty ranks and this multiple-link case.
[Bhatt's input longitudes](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=20)
[Bhatt's worked table](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=27)

**Reader III's overseas chart.** On pp. 314–315 Rahu is in its own star
and occupies the ninth house, while Mercury is in its own star and
owns the ninth and twelfth cusps. This yields Rahu at ranks 1 and 2 and
Mercury at ranks 3 and 4 for house 9. House 12 is vacant and Mercury gives
ranks 3 and 4 there. The house 3 text says Jupiter has no star occupants,
but the chart prints the Moon at Libra 26°21′, within Jupiter's Vishakha
star. The result follows the printed longitude and includes the Moon at
rank 3. An obscured last digit in Venus's printed minute is immaterial
across Sagittarius 25°10′–25°19′.
[Reader III, worked chart](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=326)

## Public contract

- `kp_significators` and `POST /v1/kp/significators` take the nine graha
  longitudes and twelve ordered cusps. They return twelve rows with rank
  evidence and the planet placements used to derive them.
- `kp_significators_for_datetime` and `POST /v1/kp/chart/significators`
  calculate the same rows from the existing KP chart. If ordered Placidus
  cusps are unavailable, the result contains the chart, planet chains,
  and cusp availability reason, with a null significator result.

Tests exercise the printed examples, duplicates and malformed cusp order,
exact cusp ownership and neighboring floats, and direct, facade, and REST
parity with DE441 for both node modes and an unavailable Placidus figure.
