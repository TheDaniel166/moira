# Vedic numbered divisions, Prashna sphutas, and Choghadiya

## 64th Navamsa and 22nd Drekkana

**Profile `jataka_parijata_inclusive`.** Vaidyanatha Dikshita, *Jataka Parijata*,
V.56 in V. Subramanya Sastri's Ranjan Publications edition, vol. I, p. 269.
The verse counts 22 from the natal Lagna's Drekkana and 64 from the Moon's
Navamsa. I.25 names the sign lords, I.30 gives the sign, fifth and ninth
assignments for the three Drekkanas, and I.32–33 gives the element-wise
Navamsa sequences. The Sanskrit witnesses identify the same starting
references. [Sastri volume I, p. 269](https://astrofoxx.wordpress.com/wp-content/uploads/2018/11/jataka-parijata-vol-1.pdf#page=275) ·
[Sanskrit text, chapters I and V](https://sanskritdocuments.org/doc_z_misc_sociology_astrology/jAtakapArijAtaH.html)

Count the occupied cell as 1. Advance 63 of 108 D9 cells or 21 of 36 D3 cells,
wrapping at the end of the zodiac. Either offset spans exactly seven signs
and preserves the ordinal within the eighth sign. The API reports the
physical cell as a half-open interval of integral zodiac arcseconds, alongside
its projected sign and lord. The starting cell is partitioned on the exact
binary input longitude and rational cell width. Sastri's note below V.56 calls
the target the first cell of the eighth sign. Inclusive counting yields the
first cell only when the occupied cell is first. Moira follows the verse's
count, supported by the following printed examples.

- B. V. Raman's *Prasna Marga*, part I, p. 286 gives a projected Moon D9
  in Leo and the 64th in Scorpio, ruled by Mars. A Moon at Aries 15° gives
  that Leo seed and falls in the fifth D9 cell. The target lies in the fifth
  cell of Scorpio and also projects to Scorpio. [Raman, p. 286](https://storage.yandexcloud.net/j108/library/touvip7g/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_I%29.pdf#page=315)
- K. S. Charak's commentary on *Jatakalankara*, Chart V-1, pp. 133–134, shows
  Virgo 27°31′ Lagna and Leo 24°31′ Moon. The inclusive D3 count selects
  Aries 20°–30°, projects to Sagittarius and gives Jupiter. The Moon
  projects to Scorpio D9. Its 64th lies in the eighth D9 cell of Pisces and
  projects to Aquarius, ruled by Saturn. The published commentary names both
  lords. [Chart V-1](https://storage.yandexcloud.net/j108/library/zipzradp/K.S._Charak_-_Jatakalankara.pdf#page=68)

Python's chart convenience method takes a chart with a geocentric Moon and
its co-epoch tropical Lagna. REST derives the geocentric Moon and the local
Lagna in the shared sidereal chart context. With the published Boston time
and coordinates, Moira's DE441 and Lahiri produce a Moon within one arcminute
of Charak's 24°31′ Leo and reproduce both projected lords.

## Prashna Marga sphutas

**Profile `prasna_marga_raman_1991`.** *Prasna Marga*, part I, B. V. Raman,
second edition (Motilal Banarsidass, 1991), V.17–18 and notes, pp. 162–163.
Add Lagna, Moon and Gulika for Tri-sphuta. Add the Sun for Chatus-sphuta.
Add Rahu for Pancha-sphuta. Reduce by complete 360° cycles at each stage. The
printed five inputs, in this order, are 43°09′, 18°29′, 64°26′, 301°12′ and
6°09′. Converting to arcminutes gives 2,589 + 1,109 + 3,866 = 7,564
(126°04′). Adding 18,072 and subtracting 21,600 gives 4,036 (67°16′).
Adding 369 gives 4,405 (73°25′).
[Verses and worked example](https://storage.yandexcloud.net/j108/library/touvip7g/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_I%29.pdf#page=191)

Raman's notes on pp. 160–162 distinguish the end-of-Saturn-eighth Gulika
from the Māndi clock in general usage. For this text, he directs the reader
to use the Māndi clock for Gulika. The 30-ghati tables agree with the existing
Upagrahas Māndi tables. From Sunday onward the daytime numbers are
26, 22, 18, 14, 10, 6, 2 and nighttime numbers are 10, 6, 2, 26, 22, 18, 14.
Scale the selected number by the actual UT1 arc divided by 30. The notes'
Friday 30-ghati day gives Māndi at 6 ghatis after sunrise, versus 7½ for
end-of-Saturn-eighth Gulika. Saturday's 34-ghati night gives
`34 × 14 / 30 = 15.866…` ghatis from sunset.
[Gulika and Māndi notes](https://storage.yandexcloud.net/j108/library/touvip7g/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_I%29.pdf#page=189)

For dated charts, use the weekday of the governing sunrise in the requested
civil timezone and retain the arc and the Gulika-defining instant. The
sidereal ascendants at the question and Māndi instants each use their own
bound TT and the same named ayanamsa policy. The question Sun and Moon are
apparent geocentric positions. Rahu is the lunar ascending node, with the
caller explicitly selecting mean or true in the true ecliptic of date.
The text provides Rahu's longitude in the worked example and leaves the
modern node model unspecified. Ayanamsa selection and the horizon threshold
are modern materialization choices. Lahiri and the Rashtriya upper-limb
threshold are the defaults. The dated response discloses absent or ambiguous
solar anchors, undefined Lagna, or an unavailable required ayanamsa anchor.

## Choghadiya

**Profile `sirohi_1916`.** The Gujarati appendix of the *Samadhishatakam*
edition published by Shri Jain Gyan Prasarak Mandal, Sirohi, records both
weekday tables on pp. 232–233. The seven columns are Sunday through
Saturday and each row starts a named interval. The names are Udvega, Amrita,
Roga, Labha, Shubha, Chala and Kala in the order shown in the first daylight
row. The spelling Chala follows the printed table. Number Sunday 0 and let
the slot index start at 0. The day name's index is `(weekday + 5*slot) % 7`.
The night index is `(weekday + 4 + 4*slot) % 7`. All 112 entries are checked
against a separate transcription of the printed tables. The API accepts
Monday=0 through Sunday=6 and converts to the source column numbering.
[Day table](https://archive.org/download/in.ernet.dli.2015.341009/page/n248.jpg) ·
[Night table](https://archive.org/download/in.ernet.dli.2015.341009/page/n249.jpg)

Satya Prakash Dwivedi's *Sampoorna Panchang Gyan* gives the proportional rule
for daytime and nighttime and demonstrates weekday ownership after midnight.
Sunrise to sunset and sunset to the following sunrise each have eight equal
intervals. His Friday 27 March 2009 example starts at 05:58 with Chala,
Labha and Amrita, using a 91-minute rounded step. The Tuesday 28 October
2008 Diwali example starts the night at 17:18 with Kala and runs through
Wednesday 01:18 in the rounded Amrita slot. The source's night length of
31 ghatis 56 palas implies steps of 95 minutes 48 seconds. The unrounded
Amrita slot is 23:41:12–01:17:00.
[Dwivedi's Choghadiya and Diwali sections](https://pdf.upayogibooks.com/storage/media/tjRivVtcvmm7zGHIT0jefnw0CVwnxJzpPDkGOtJO.pdf)

The Durban Panchang 2026, pp. 14–15, gives a separate full worked day.
For 3 February the three local anchors are 05:27:39, 18:51:58 and 05:28:31
the next morning. The calculated day and night steps are 6,032.375 and
4,774.125 seconds. Using the published anchors reproduces all 16 printed
starts within 0.875 seconds. Wednesday's 00:10:15 Amrita start is printed as
part of Tuesday night's row. The Durban compilers acknowledge other almanacs.
The Durban fixture tests the partition and names with the published times
as inputs. [Durban Panchang, pp. 14–15](https://ssdspurohitmandal.org.za/wp-content/uploads/2025/07/PanchangChogadia2026Final.pdf#page=14)

The dated calculation uses Moira's reader and civil-date solar event search.
The two sunrise dates must each provide a unique rise with one sunset
between them. The sunset can occur after midnight. Each interval is half-open
in UT1, with one shared boundary at sunset. Local displays come from the
same UT1 boundaries across midnight or a clock change. The astronomy
threshold remains explicit, with the Rashtriya upper-limb definition as
default. A missing or ambiguous anchor produces an unavailable schedule.
