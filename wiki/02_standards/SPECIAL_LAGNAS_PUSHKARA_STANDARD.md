# Special Lagnas and Pushkara source standard

## Primary texts

| Text and passage | Evidence used |
| --- | --- |
| *Brihat Parasara Hora Sastra*, R. Santhanam, vol. I, 5.2–8, printed pp. 62–64 | PDF pp. 61–63 of the inspected library scan. The verses define 5, 2½ and 1 ghati per sign from the Sun at sunrise. Santhanam's notes give one worked case for all three. [Public scan](https://www.horasad.com/download/ebooks/BRIHAT_PARASHARA_HORA_SHASTRA_1.pdf) |
| P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated Approach*, §§5.2–5.4 and 5.8 | Printed pp. 45–47 and 50 (PDF pp. 57–59 and 62). Examples 7–9 establish the rates and provide a second arithmetic witness. Exercise 8 identifies the previous civil day's sunrise for a birth before dawn. [Author's PDF](https://vedicastrologer.org/articles/vedic_astro_textbook.pdf#page=57) |
| Vidya Madhava, *Vidyamadhaviyam*, ed. R. Shama Sastry, Mysore 1923, part I, 1.18, with Vishnusarma's *Muhurthadipika* | Printed pp. 30–31 (PDF pp. 61–62). The verse and commentary give the Pushkara degree groups. The commentary on p. 31 enumerates the two Navamsas in each sign group. [Primary scan](https://archive.org/download/in.ernet.dli.2015.325850/2015.325850.The-Vidyamadhaviyam.pdf#page=61) |
| Vaidyanatha, *Jataka Parijata*, V. Subrahmanya Sastri, vol. I, 1.58 | Printed p. 39 (PDF p. 45 of the inspected library scan). The verse and translation give twelve Bhaga degrees. Sastri's translation names the Moon as the subject. [Public scan](https://astrofoxx.wordpress.com/wp-content/uploads/2018/11/jataka-parijata-vol-1.pdf) |

The relevant pages were checked as images. SHA-256 of the four inspected PDFs in
table order is `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f`,
`1cafa828f34764ed5e85816882df2e8f0bc014c5c57ccdb27169416e117fd4db`,
`29d103473dd2de4c0fd7ddf1e27f758dd766f412786ef43280834599a2ca3c95` and
`392d1b15e86824f78339ddda0a9c358372f7be69d9f6aeece24d8d0e7c782dc1`.

## Special Lagnas

Let `g` be the elapsed time since the selected sunrise in 24-minute ghatis.
Advance the sidereal longitude of the Sun at that sunrise by `6g`, `12g` and
`30g` degrees for Bhava, Hora and Ghati respectively. Wrap each result at 360°.

| Witness | Seed and time since sunrise | Bhava | Hora | Ghati |
| --- | --- | --- | --- | --- |
| Santhanam notes, 5.2–8 | 132° and 12 ghatis 30 vighatis (18,000 s) | 207° | 282° | 147° |
| Rao Examples 7–9 | 294°17′ and 766 min | 125°47′, recomputed | 317°17′ | 171°47′ |
| Rao Exercise 8 and answers | 42°11′ and 20 h 52 min 30 s | 355°18′30″, derived | 308°26′ | 167°48′30″ |

Rao's Example 7 advances the Bhava point by 766° and prints 340°17′. His
stated 15°/hour rate and the Santhanam witness give an advance of 191°30′ and
the result 125°47′. Rao prints the Hora and Ghati answers for Exercise 8. The
Bhava value in that row is derived using its verified rate.

`special_lagnas(sun_sidereal_longitude, elapsed_seconds)` takes a finite
sidereal seed in `[0, 360)` and finite nonnegative elapsed seconds.
`special_lagnas_for_datetime` takes an offset-aware birth instant, observer
coordinates and explicit local timezone. It uses the unique sunrise on the
birth's local date when it is at or before birth. Before dawn, or when that
date has no sunrise, it checks the immediately preceding local date. A
non-unique sunrise on the relevant date or no eligible sunrise yields an
unavailable result. Equality at the emitted sunrise starts the new interval.

The dated calculation uses the same civil-date boundary rules and solar event
finder as [Daily Panchanga](DAILY_PANCHANGA_STANDARD.md). A civil date adjacent
to a wholly skipped date can yield input validation failure under the shared
civil-boundary contract. Moira uses elapsed UT1 seconds and the apparent
geocentric Sun with true-mode ayanamsa at the selected sunrise. The default
horizon is the Rashtriya upper-limb policy at a level horizon and zero
elevation. The USNO upper-limb and geometric-center options are selectable.
These horizon and clock choices describe Moira's astronomical composition.
The receipt gives the examined sunrise candidates, applied context and chosen
anchor when available. The astronomical root and model limit the accuracy of
the dated result, with Ghati advancing fastest.

## Pushkara

The 1923 commentary assigns the following one-based Navamsa ordinals.
The partition uses Moira's exact D-9 rule on the supplied binary longitude.

| Sign group | Signs | Ordinals | Exact spans within the sign |
| --- | --- | --- | --- |
| Fire | Aries, Leo, Sagittarius | 7 and 9 | [20°, 23°20′), [26°40′, 30°) |
| Earth | Taurus, Virgo, Capricorn | 3 and 5 | [6°40′, 10°), [13°20′, 16°40′) |
| Air | Gemini, Libra, Aquarius | 6 and 8 | [16°40′, 20°), [23°20′, 26°40′) |
| Water | Cancer, Scorpio, Pisces | 1 and 3 | [0°, 3°20′), [6°40′, 10°) |

| Bhaga profile | Aries through Pisces, one-based degree ordinal | Source subject |
| --- | --- | --- |
| `jataka_parijata_sastri` | 21, 14, 18, 8, 19, 9, 24, 11, 23, 14, 19, 9 | Moon |
| `vidyamadhaviyam_1923` | 21, 14, 24, 7, 21, 14, 24, 7, 21, 14, 24, 7 | Sign degree |

The texts supply degrees or ordinal divisions. Moira represents the *n*th
Bhaga as the half-open sign interval `[n - 1, n)`, with no additional orb.
`pushkara(sidereal_longitude, bhaga_profile=...)` requires explicit Bhaga
profile selection and returns both geometric comparisons and their distinct
source references. The Bhaga source subject remains visible when the input
comes from a chart body. Chart composition includes the sidereal epoch and
ayanamsa in the existing chart provenance.

The passages supply tables and sign-group examples. Numerical witnesses were
calculated separately from those tables. Aries 20°30′ is Libra Navamsa
(ordinal 7) and inside the 21st Bhaga under both tables. Gemini 17°30′ is a
Pushkara Pisces Navamsa (ordinal 6) and is inside the Sastri 18th Bhaga.
Vishnusarma's 24th Bhaga for Gemini instead contains 23°30′.

## Public entry points and checks

The calculations and result types are exported through `moira`,
`moira.facade` and `moira.vedic`. The `Moira` instance exposes both direct
calculations, reader-bound Special Lagnas, and `pushkara_for_chart`.

| Request | HTTP endpoint |
| --- | --- |
| Resolved sunrise seed and elapsed seconds | `POST /v1/special-lagnas/from-sunrise` |
| Offset-aware birth instant, coordinates and timezone | `POST /v1/special-lagnas/birth` |
| Sidereal longitude and explicit Bhaga profile | `POST /v1/varga/pushkara` |
| Chart body, offset-aware instant and explicit Bhaga profile | `POST /v1/varga/chart/pushkara` |

Verification covers the printed Lagna results and the corrected Bhava example,
108 Navamsa divisions and their adjacent representable boundary values, both
twelve-entry Bhaga tables, strict API admission, and Python/HTTP parity.
DE441 cases include the 22 September 2026 Rashtriya Panchang station/date,
a pre-sunrise birth over a daylight-saving change, the emitted sunrise
boundary, a polar unavailable result, and chart-derived lunar Pushkara.
