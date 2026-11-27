# Wave 4 primary-source checkpoint

The engine exposes two Moon-matching profiles and one KP chart profile through
Python and REST. This record covers the source rules and conversion choices for
the Wave 4 implementation in `moira/kuta.py` and `moira/kp.py`.

## Charak Ashtakoota

K. S. Charak's *Elements of Vedic Astrology*, chapter XXVII, scans 452–462,
defines the point tables and role order. The matrix rows take the bride's
category and the columns take the groom's. The factor order is Varna, Vashya,
Tara, Yoni, Graha Maitri, Gana, Bhakoota, and Nadi, with maxima from one to
eight points. In Tara the two inclusive counts are scored separately. Vashya
splits Sagittarius and Capricorn at 15°. The Yoni table uses Abhijit from
Capricorn 6°40′ up to 10°53′20″, while the other factors keep the 27 equal
birth stars. [Charak, chapter XXVII](https://astrofoxx.wordpress.com/wp-content/uploads/2018/11/jyotish_elements-of-vedic-astrology_k-s-charak-1.pdf#page=452)

The profile uses the printed scores in tables XXVII-1 through XXVII-8.
The Nadi exceptions on scan 460 cancel the blemish for qualifying common
signs or stars. The Bhakoota remarks on scan 459 qualify certain positional
results. The profile records those effects beside the table points because
the text gives the exceptions without replacement scores. The Moon-only
calculation has no other chart evidence for the Kuja Dosha discussion that
follows the worked score.

The source shows the bride's Moon at Pisces 5°33′, Uttara Bhadrapada, and
the groom's at Sagittarius 7°54′, Mula. Inclusive star counts are 21 and 8
respectively from the bride and groom. Reading the eight tables gives
0, ½, 1½, 2, 5, 0, 7, and 8, totaling **24 of 36**. The published pair
also exercises the Manava/Jalachara cell, the directional Varna comparison,
and common Jupiter rulership. [Charak, charts and worked score](https://astrofoxx.wordpress.com/wp-content/uploads/2018/11/jyotish_elements-of-vedic-astrology_k-s-charak-1.pdf#page=461)

## Iyer Porutham

N. P. Subramania Iyer's *Kalaprakasika*, chapter XIII, pp. 68–76, gives
ten independent checks and a minimum of five agreements. The result reports
the number of confirmed agreements. Neutral, adverse, and unresolved factors
each retain their own classification. The profile uses Iyer's directional
Rasi, friendship, Vasya, animal associations and Vedha sets, including the
three-member Mrigashira–Chitra–Dhanishtha set. For Rasyadhipathi, common or
reciprocally friendly lords give agreement and one-way friendship is neutral.
The primary Stree Deergha rule is an inclusive count above 13. [Iyer, chapter XIII](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf#page=105)

Iyer's p. 70 example names Punarvasu to Hasta as an exception to the general
seventh-star Dina restriction. With a bride's Moon at Gemini 24° and groom's
at Virgo 12°, counts are 7 and 22, the applied Dina agrees, and Mahendra
agrees. The checklist has seven confirmed agreements. The common Mercury
lord makes the applied Rasi result unresolved under the p. 76 cancellation
wording. Reversing the pair gives 22 for Dina and a disagreement. These
longitudes instantiate the printed stars for the fixture. The edition gives
the Dina example at star level. [Iyer, p. 70](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf#page=107)

The profile returns unresolved results where the 1917 text is incomplete or
contradictory.

- The p. 70 Chitra–Pushya example reverses the stated count. From Chitra to
  Pushya it is 22, and from Pushya to Chitra it is 7. Both directions retain
  the ambiguity in the named exception.
- The instructions on pp. 71–72 conflict for a shared star that straddles
  two signs. The same-sign Rasi outcome is also unspecified in the Rasi
  rules.
- The p. 72 Manushya list omits Uttara Phalguni, Purva Ashadha, Uttara
  Ashadha, and Purva Bhadrapada. Gana involving one of these stars is
  unresolved.
- The p. 76 wording joins common lords, friendly lords, and opposite signs.
  When any of those could affect an otherwise adverse Gana, Rasi, Rajju or
  Vedha, the base classification is kept and the applied result is unresolved.
  Explicit p. 74 Rasi sign-pair exceptions apply before this clause.

Both matching profiles accept two canonical sidereal longitudes in degrees.
The caller supplies their shared ayanamsa. Indexes are zero based and padas
are one based. A float exactly equal to the nearest representation of a
quarter boundary belongs to the following pada.

## Krishnamurti sign, star, sub, and sub-sub

Reader I uses Raphael's ephemeris and house tables with the Krishnamurti
ayanamsa. Reader VI, pp. 77–79, divides each of 27 equal stars into nine
Vimshottari proportions, ordered from the star lord. The same rotation
within each sub, ordered from its lord, reproduces the published sub-sub
examples in *Astro Secrets and Krishnamurti Padhdhati*, Part V. Reader VI's
printed proportional rule and the tabulated examples are used together.
[Reader I](https://archive.org/details/kpreader-1-casting-the-horoscopepdf)
[Reader VI](https://storage.yandexcloud.net/j108/library/3sf9ydin/K.S._Krishnamurti_-_Horary_Astrology_Krishnamurti_Padhdhati_Advanced_Stellar_System.pdf)
[Part V, pp. 171–172 and 202–206](https://jnanalaya.kailasa.ai/books/astro-secrets-kp-part5-742338/chapter-1-astro-secrets-kp-part5)

Each star is 48,000 arcseconds wide. In thirds of an arcsecond the star
width is 144,000, each sub has width 1,200 times its Vimshottari weight,
and each sub-sub has width 10 times the product of its own weight and its
parent's weight. The API returns exact integer endpoints in these units.
Intervals are half open and nearest-representable float endpoints start the
next interval. Sign divisions are computed independently of the stellar
ones. Horary number allocation is a separate calculation.

Reader III, pp. 503–504, compares Venus/Mars/Saturn from Taurus 27°53′20″
through its end with Mercury/Mars/Mercury from Gemini 0° up to 1°53′20″.
The fixture checks the Taurus-to-Gemini seam and both sub endpoints.
[Reader III, scan 515](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=515)

The chart printed on pp. 171–172 of Part V supplies four full chains.

| Point | Printed sidereal position | Sign, star, sub, sub-sub |
| --- | --- | --- |
| Moon | Aries 9°14′ | Mars, Ketu, Jupiter, Rahu |
| Mars | Gemini 2°53′ | Mercury, Mars, Venus, Venus |
| Ascendant | Cancer 21°38′ | Moon, Mercury, Sun, Moon |
| Descendant | Capricorn 21°38′ | Saturn, Moon, Venus, Jupiter |

The direct calculation reproduces those chains from the printed positions.
A DE441 chart composed for 8 June 1953, 09:12 IST, 22°34′ N, 88°24′ E
also reproduces all four chains within three arcminutes of the printed
positions. The printed clock and angles have minute precision and the
printed ayanamsa is 23°06′. Moira's modern profile uses its Krishnamurti
J2000 mean reference propagated with IAU 2006 precession and nutation in
longitude, returning the actual offset and path. The choice of mean or
true lunar node is explicit. The Placidus solver uses the same UT1/TT
pair as the geocentric planetary reductions and reports the effective
system. If the geometry cannot define ordered Placidus cusps, those
cusps are unavailable and the planet chains are still returned.

## Public surfaces

| Operation | Python function | REST |
| --- | --- | --- |
| Matching profile discovery | `kuta_profiles` | `GET /v1/kuta/profiles` |
| Two-Moon evaluation | `kuta_match` | `POST /v1/kuta/match` |
| KP profile discovery | `kp_profiles` | `GET /v1/kp/profiles` |
| KP subdivision | `kp_longitude` | `POST /v1/kp/longitude` |
| Reader-bound KP chart | `kp_chart_for_datetime` | `POST /v1/kp/chart` |

The regression fixtures cover the eight printed Charak factors, Iyer's
worked Dina exception and source ambiguities, all 108 pada boundaries, the
2,187 KP sub-sub intervals and their adjacent floats, and the historical
and modern DE441 chart cases. The separately tracked KP extensions are
significators, ruling planets, and period interpretation.
