# KP period interpretation

This profile annotates each level of a natal Vimshottari line for
education, marriage, or service. It uses the Moira KP sidereal partition,
Placidus opening cusps, and the four direct house significator ranks.

## Primary rules

K. S. Krishnamurti's Reader III, pp. 68–70, ties the topic to the natal
star lord's occupied and owned houses and the character of the result
to the sub. Chandrakant R. Bhatt's *Nakshatra Chintamani*, pp. 22–27,
supplies the topic house sets and works through them for specific period
lords. Page 30 prints the planet, star-lord, and sub-lord house evidence
used in those examples. The discussion of joint periods on pp. 35–37
assesses the individual rulers and also considers reception, aspects
and transits in the full judgment. [Reader III, printed pp. 68–70](https://archive.org/download/kpreader-3-predictive-stellar-astro/kpreader-3-predictive-stellar-astro.pdf#page=82)
[Bhatt, printed pp. 22–27](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=31)
[Bhatt, printed pp. 30 and 35–37](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=39)

| Subject | Supporting houses | Opposing houses |
| --- | --- | --- |
| Education | 4, 9, 11 | 3, 8 |
| Marriage | 2, 7, 11 | 1, 6, 10 |
| Service | 2, 6, 10 | 1, 5, 9 |

For each active lord the result records its identity, occupancy and sign
ownership. The star-lord matches come from its occupied and cusp-owned
houses. Sub-lord matches use all four admitted direct significator ranks
with their underlying links. The node placements and star rulership
participate directly. Node representation, aspect, cusp-promise and
transit judgments are separate calculations.

The assessment expresses the direct evidence for the selected topic.

- A star with neither topic link gives `no_topic_indication`.
- A star or sub with links on both sides gives `mixed` when the star
  has a topic indication. The receipts give both sets of houses.
- An opposing sub link with a topic indication from the star gives
  `adverse`.
- A supporting star link and a supporting sub link give `supportive`.
- An indicated topic with no independent sub support or opposition, or
  an opposing star with a supporting sub, gives `unresolved`.

Those labels belong to each level of the line. The direct API takes
supplied lords starting at Mahadasha, with up to Antardasha,
Pratyantardasha, and Sookshma, including repeated identities.

## Worked examples

The chart inputs are from Bhatt's printed p. 11. The star/sub assignments
were reconstructed independently using rational angles. The occupation
and ownership information on p. 30 and the four direct rank columns on
p. 18 were read separately from the examples. [Printed chart inputs](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=20)
[Printed direct-rank table](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1620985353Naksatra-Chintamani-Chandrakant-Bhatt-R.pdf#page=27)

- **Education, Venus–Moon and Venus–Rahu (p. 24).** Moon at Pisces 21°49′
  and Rahu at Pisces 24°36′ both have Mercury as star lord, which owns
  education house 9. Moon's sub is the Sun, which owns house 8 and also
  signifies house 3 through Jupiter's star. Rahu's sub is Rahu, which gives
  the direct house 9 link through Mercury's star. The Moon Antardasha is
  adverse and the Rahu Antardasha is supportive, reproducing the author's
  contrasting education treatments.
- **Marriage, Venus–Rahu–Jupiter–Rahu (pp. 25, 29).** Rahu's star lord
  Mercury occupies supporting house 7 and owns opposing house 6. Rahu
  also has sub-lord evidence for supporting houses 2 and 7 and opposing
  house 6. The author's case emphasizes the supporting links. The engine
  includes the concurrent opposing links and reports mixed evidence.
- **Service, Sun Mahadasha (p. 26).** Jupiter occupies supporting house 10.
  The Sun's sub lord Saturn owns supporting house 2, as highlighted in the
  source, and opposing house 1, which the p. 30 table also prints. Both
  links are retained. The engine reports mixed evidence for this level.

## Dated composition

The dated operation solves the natal KP chart and calls the existing
Vimshottari active-period calculator using the natal tropical Moon and the
Krishnamurti ayanamsa. It copies the half-open UT1 intervals, including
the birth clipping and full bounds, from that result. Both existing
Vimshottari year bases remain selectable. The published examples use
their printed lords, while tests of the dated composition check the
engine clock independently.

- `kp_period_interpretation` and `POST /v1/kp/period-interpretation`
  accept supplied sidereal planet and cusp longitudes and a period line.
- `kp_period_interpretation_for_datetime` and
  `POST /v1/kp/chart/period-interpretation` return the active canonical
  periods and natal evidence. If ordered Placidus cusps are unavailable,
  the timing and the chart receipt are still returned and the
  interpretation is null.
