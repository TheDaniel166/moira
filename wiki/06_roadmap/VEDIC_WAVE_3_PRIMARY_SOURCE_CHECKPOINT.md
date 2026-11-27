# Wave 3 primary-source checkpoint

## Annual Tithi Pravesha

P. V. R. Narasimha Rao's 29 June 2014 version defines the return at the
exact natal Moon-minus-Sun angle in a lunation with the natal lunation's
tropical Sun sign at conjunction. Rao compares a sidereal conjunction-sign
variant in the same paper. Ayanamsa affects the sidereal conjunction label.
The Sun–Moon difference uses a common longitude frame. Keep the search rule
and the chart's displayed zodiac as separate settings.
[Rao, definition and Example 1](https://www.vedicastrologer.org/articles/pp_tp.pdf#page=2)

Example 1 fixes 12 September 1971 at 08:25 IST in Guntur. A narrowly
bracketed DE441 replay used apparent geocentric Sun and Moon of date, UT1
for the root, and IERS-based UTC conversion. It computed the natal
elongation as 274.429574523°. Three conjunction roots establish the
following sign choices. True Pushya is the Moira setting used for the
sidereal sign comparison.

| Conjunction | Rao's IST | Moira's IST | Tropical sign | Sidereal sign |
| --- | --- | --- | --- | --- |
| Natal lunation, 21 Aug 1971 | 04:24:02 | 04:23:20.66 | Leo | Leo |
| Earlier candidate, 30 Jul 1992 | 01:05:43 | 01:05:09.93 | Leo | Cancer |
| Later candidate, 28 Aug 1992 | 08:12:25 | 08:11:52.10 | Virgo | Leo |

The tropical candidate returns on 22 August 1992 at 00:14:01.91 IST and
the sidereal candidate on 20 September at 09:47:44.34 IST. Rao prints
00:14:02 and 09:47:45, respectively. The residuals are within 0.002
arcseconds for both phase returns. The conjunctions differ by 33–41 seconds
under the tested ephemeris and time reduction. Their sign classifications
agree. These are local roots around printed examples. Full return-year
candidate enumeration is the next verification step.
[Rao, Example 1](https://www.vedicastrologer.org/articles/pp_tp.pdf#page=4)

Rao explicitly permits repeated conjunction-sign months. His definition
and Example 1 leave an unresolved selection if a target year contains
multiple eligible lunations. Establish the bounded return-year contract
and report the eligible candidates and their uncertainty before choosing a
default. Moira's `lunar_month` has a reusable wrapped-angle boundary solver.
Its current month labels use sidereal ingress counts and do not supply
Rao's tropical conjunction-sign identity.

## Monthly Tajika

Balabhadra's *Hāyanaratna* §8.1, p. 893, sets the true solar longitude of
month 1 at the annual revolution and advances it by one zodiac sign per
month. The mean-motion table and 30-day multiples supply approximations
for finding the event, followed by true solar and clock corrections.
Moira can test a modern projection by solving the annual sidereal Sun
longitude plus `30° × (month − 1)` between consecutive annual returns.
That profile would use the engine's solar longitude at each instant and
needs an independent check against the annual Varshaphal anchor.
[Gansten's critical edition, §8.1](https://brill.com/display/book/9789004433717/BP000010.pdf)

In the Shāh Shujāʿ example, pp. 919–923, the numerical annual target is
2 signs, 22°48′32″. The second month's target is 3 signs, 22°48′32″.
The corrected trial longitude of 3 signs, 20°54′57″ follows from the
printed angular difference of 1°53′35″. The running exposition on p. 921
gives 3 signs, 20°24′57″ at that line, which would give a difference of
2°23′35″. The Sanskrit on p. 920 has 20°54′57″ there. The source's
6,815″ divided by 3,437″ per day gives about 1 day, 58 ghaṭīs,
58 palas. Adding that to 3 days, 24 ghaṭīs, 51 palas yields 5 days,
23 ghaṭīs, 49 palas at the printed precision. The book selects
Monday at 23 ghaṭīs 49 palas after sunrise. The alternate arithmetic
also reaches that clock value after rounding and corrections. Its
mean longitude of 3 signs, 22°11′26″ minus 1°15′23″ implies 3 signs,
20°56′03″, where the printing gives 2 signs. The following difference
of 112′29″ independently supports 3 signs.
[Gansten's critical edition, §8.3](https://brill.com/display/book/9789004433717/BP000010.pdf)

The historical clock comparison needs its own fixture. Gansten's note 26
places the modern annual return 8 h 20 min later than the historical
clock. A DE441 monthly projection should therefore be validated against
the exact solar-longitude target and an independent bracket. It should
record the historical computation separately, including the printed
inconsistencies.

## Rath Narayana Dasha

The 206-page scan extends the existing [Jaimini research
packet](VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md#36-rath-narayana-researched-separately-named).
Tables 10–14, pp. 52–55, witness the general modality order, Saturn's
forward adjacent order, Ketu's reversed modality order, and ordinary and
reversed antardasha orders. Table 14's printed Scorpio row ends with
repeated 4 and 3 where the prose and the requirement to visit each sign
once imply 6 and 7. Preserve this reading in the fixture notes.
[Rath, Tables 10–14](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf#page=52)

The Standard Nativity in Table 17 starts Pisces and follows the forward
dual order in Table 10. Its first-cycle durations sum to 70 years. The
same order with duration `12 − d` gives 74 years in the second cycle.
The table on p. 65 omits Pisces, which has a zero complement, retains
Capricorn with zero duration, and gives Virgo 11 source years but only
one year between its two printed dates. The corrected 11-year Virgo
interval implied by the arithmetic is 2069–2080. Subsequent printed
years on that page would each move ten years later. Treat zero periods
as source evidence and choose explicitly how they appear in an interval
schedule.
[Rath, Table 17 and second cycle](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf#page=64)

Table 20 supplies a joint Saturn–Ketu exception. Both are in the Scorpio
starting sign. Ketu's 27°39′ is counted backward within the sign as
2°21′. Saturn's 14°23′ wins, yielding the forward adjacent sequence
Scorpio, Sagittarius, Capricorn and onward. The wider seed and co-lord
strength ordering, tie behavior, and antardasha direction when the
mahadasha sign and antardasha starting sign have different parity still
need complete worked-case collation before admission.
[Rath, Table 20 and discussion](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf#page=71)

## Verified timing profiles

Wave 2 reached GitHub main at
[`63f9311`](https://github.com/TheDaniel166/moira/commit/63f9311c201d125e700575549f8bca45d0facd6a).
This record accompanies the three Wave 3 calculation profiles.

### Full-year Tithi Pravesha search

The civil Gregorian return year and its timezone are explicit Moira
inputs. Rao aligns lunar years to solar years and gives a conjunction-sign
matching rule. The 2014 paper gives no rule for choosing between repeated
matches. Eligibility is determined by the phase return's UT1 instant
within the half-open civil year. The owning conjunction can occur in
the previous civil year. The search brackets the entire year, and each
candidate carries its conjunctions, angular target, numerical bracket, and
residual. A conjunction sign or year boundary lying inside a bracket can
produce an ambiguous result.

The two 1992 published cases were also found by a full-year DE441 search.
The tropical result matched the printed 22 August 00:14:02 IST within one
second, and the sidereal comparison matched 20 September 09:47:45 IST
within one second. Reusing Rao's 13 July 1975 16:02 IST natal input with a
2020 query yields two tropical Cancer conjunctions and returns on
26 June and 25 July IST. The 2020 search is an independent Moira regression.
It reports both candidates and leaves the chart unselected. The chart at
a unique return carries apparent geocentric positions, a named ayanamsa,
and the requested local house geometry.
[Rao's definition and worked examples](https://www.vedicastrologer.org/articles/pp_tp.pdf#page=2)

### Monthly Tājika ephemeris projection

The modern profile `hayanaratna_sidereal_ephemeris` uses exactly the
sidereal Varshaphal instant for month 1. The remaining monthly instants
are the 30° increments of the natal sidereal Sun within the interval
bounded by that anchor and the next annual return. Each solved month
reports its UT1 bracket and residual. The requested timezone displays
the resulting instant and does not set the annual search basis.

For the modern comparison of Shujāʿ's nativity, the test uses 2 July 1616
at 13:59 on Moira's UTC display scale as an explicit approximation for
Gansten's 19:00 local apparent time. The independently bracketed Lahiri
and DE441 month 2 arrives on 3 August 1648 around 04:32:15.18 on that
display scale. This validates the modern longitude projection with the
declared natal approximation. The historical 23 ghaṭīs 49 palas fixture
checks the mixed-radix arithmetic independently. A full historical
clock calculator would require the period tables and the observer,
calendar, and clock conventions in the source.
[Gansten, critical edition §8.3](https://www.wisdomlib.org/hinduism/book/hayanaratna-the-jewel-of-annual-astrology/d/doc1500995.html)

### Rath natal D1 with resolved strength

The alternative copy of the 2004 edition preserves the Aries and Taurus
rows of Table 12 clipped in the 206-page PDF. These supply the missing
movable and fixed reverse rows. The derivation matches the remaining
printed rows in Tables 10–14 after correcting the duplicated entries in
Table 14's Scorpio row. Independent worked cases cover both Saturn and
Ketu in the starting sign and a difference between the parity of the
mahadasha and antardasha starting signs. In Wadiyar's Table 25, Cancer
starts in Libra and proceeds to Scorpio and Sagittarius, while Saturn in
Taurus sends the Cancer-seeded antardashas of Taurus forward.
[Rath, 2004 copy, Tables 10–14](https://storage.yandexcloud.net/j108/library/6fhh7uus/Sanjay_Rath_-_Narayana_Dasa.pdf#page=26) ·
[Rath, Table 25](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf#page=95)

The supplied D1 profile automatically applies occupant count, rāśi
conjunction/aspect support and occupant dignity for opposite signs. For
dual lords it applies placement in or outside the ruled sign, occupancy
of the lords' signs, and equal-duration conjunctions. It accepts
`resolved_strength` and `resolved_co_lords` as explicit evidence for
remaining decisions. A tie of Saturn and the reversed Ketu degree
remains unresolved. Missing antardasha strength leaves the affected major
period available with an unresolved subperiod decision.

The duration rule uses Rath's Phalita dignity table. This creates a
specific difference with Table 17, whose Aquarius entry gives Rahu in
Gemini eight years without the exaltation increment in Table 8. Scorpio
also illustrates why co-lord strength cannot be completed by silently
combining every listed rule. The source treats Mars and Ketu as equally
supported there and uses the longer period, while applying the Phalita
exaltation rule to the comparison would give Ketu in Sagittarius a
dignity advantage. The profile retains the explicit Table 8 duration
rule and marks unresolved co-lords instead of inventing precedence.
The published Table 20 durations reproduce all 12 first-cycle periods,
including the zero complement of the Pisces period.

The first-cycle durations and the twelve-year complements have exact
integer source-year lengths. Antardashas divide the parent length by
twelve. Zero durations remain in the sequence with empty projected
intervals and no active ownership. UT1 projection requires a birth
epoch and a named Moira year basis. The reported clock is a numerical
projection of the source-year intervals. Rath also uses true solar
anniversaries in the book's dated examples.
[Rath, duration rules and tables](https://scienceoflight.net/wp-content/uploads/extra/Narayana%20Dasa%20by%20Sanjay%20Rath.pdf#page=39)

## Local verification

The three calculation profiles are available in Python, the Moira facade,
and five additive REST operations. The 208-test focused regression passed
with zero skips on Python 3.14.8, including 70 DE441 resource receipts.
The reviewed REST capability map validates 75 decisions. The REST route
inventory is current, and the focused Ruff and docstring checks passed.
