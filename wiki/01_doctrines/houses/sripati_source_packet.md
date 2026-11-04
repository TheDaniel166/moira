# Śrīpati bhāva centres and boundaries

Source research and implementation contract. The authority is [Śrīpatipaddhati, V. Subrahmanya Sastri’s 1937 Sanskrit text and English translation](https://www.ebharatisampat.in/pdfs/ebharati-pdf-1621321809Sripatipadhati.pdf#page=23), chapter I, verses 4–9, printed pp. 6–12. The scan’s PDF page number is the printed page number plus 14 in this passage. The verses supply the construction. Sastri’s worked arithmetic and table supply numerical witnesses. The derivation uses the primary text and elementary circular arithmetic.

## Governing object

A figure consists of twelve ordered ecliptic centre longitudes and twelve junctions between adjacent centres. Chapter I.4–5 supplies the Ascendant (lagna) and culminating ecliptic point (madhya lagna). The worked text derives the Descendant and lower meridian point by adding or subtracting six signs. Verses I.6–7 use these four angles as the centres of houses 1, 4, 7 and 10 in zodiacal order. The eight remaining centres lie one third and two thirds of the way along each forward ecliptic quadrant.

Let A, I, D and M be the Ascendant, IC, Descendant and MC, all in the same zodiac frame. Lift their ordered cycle to one continuous turn, A < I < D < M < A + 360°. For successive anchors p and q, the centre sequence contributed by that quadrant is p, p + (q − p)/3 and p + 2(q − p)/3. Use the lifted A + 360° as the last endpoint. The two opposite pairs are 180° apart, so the first and second quadrant widths are complementary.

Verse I.8 bisects adjacent centres. The closing sandhi of house i is halfway forward from its centre to the next centre. For house 12, use the lifted centre of house 1. Normalize only the finished longitudes. The opening sandhi of house i is the closing sandhi of the preceding house. A house centre is a doctrinal anchor. Its distance to the opening sandhi is half the preceding centre spacing, and its distance to the closing sandhi is half the succeeding spacing. Those distances can differ at an angular house. The two half-spans of an angular house sum to 30°, while an intermediate house has the width of one third of its quadrant.

I.8 assigns zero house effect at an exact junction and distinguishes the effects on either side. I.9 describes proportional effect as the position moves from a junction toward the centre. Preserve junction identity separately from any generic half-open interval used by a chart consumer. Effect interpolation is distinct from the geometry and needs its own source verification before admission.

## Sastri’s worked example

Visually checked pp. 9–12 against the scan. Use the published anchors A = 14°31′46″ Aries and I = 7°42′11″ Cancer. The first forward quadrant measures 83°10′25″. Its exact third is 27°43′28⅓″, yielding centre 2 at 12°15′14⅓″ Taurus and centre 3 at 9°58′42⅔″ Gemini. The first house opens at 28°23′30⅙″ Pisces and closes at 28°23′30⅙″ Aries. Its Ascendant centre is roughly 16°08′ from the opening and 13°52′ from the closing boundary.

The following values are exact results of the printed anchors, displayed in absolute longitude and rounded here to 0.001 arcsecond.

| House | Centre | Closing sandhi |
|---:|---:|---:|
| 1 | 14°31′46.000″ | 28°23′30.167″ |
| 2 | 42°15′14.333″ | 56°06′58.500″ |
| 3 | 69°58′42.667″ | 83°50′26.833″ |
| 4 | 97°42′11.000″ | 113°50′26.833″ |
| 5 | 129°58′42.667″ | 146°06′58.500″ |
| 6 | 162°15′14.333″ | 178°23′30.167″ |
| 7 | 194°31′46.000″ | 208°23′30.167″ |
| 8 | 222°15′14.333″ | 236°06′58.500″ |
| 9 | 249°58′42.667″ | 263°50′26.833″ |
| 10 | 277°42′11.000″ | 293°50′26.833″ |
| 11 | 309°58′42.667″ | 326°06′58.500″ |
| 12 | 342°15′14.333″ | 358°23′30.167″ |

All twelve printed centres and eleven printed sandhis agree within half an arcsecond. The p. 12 table prints the 6/7 sandhi as sign 5, 23°23′30″ (173°23′30″). Its two printed neighbouring centres average to 178°23′30″ exactly. The opposite 12/1 sandhi is printed at 358°23′30″, independently confirming the 28° degree component. Preserve the printed row and its discrepancy in any source fixture.

## Implementation contract

Use Moira’s astronomical Ascendant and MC as the anchor provider. Sastri’s historical rising-time procedure explains the inputs in the source example. A modern angle provider is an explicit adapter, and the source comparison begins with the published anchor values. Keep centre and boundary longitudes in the same frame. Use the named shared quadrant-trisection geometry only after checking that its anchor order, direction, and degenerate-case semantics match this contract. Moira’s Porphyry code has the same trisection geometry, and the Vīrasimha muhurta path already distinguishes bhāva centres and sandhis under its own source. Neither existing caller defines Śrīpati’s source or API.

Moira registers Śrīpati as `SP`. The Python and chart REST results expose three sequences in house order. `house_centers` gives the bhāva centres, `cusps` gives the opening sandhis used for placement, and `sandhis` gives the closing sandhis. The Ascendant is the first centre. Moira requires distinct angular anchors in the verse’s forward order at every latitude and raises if the supplied anchors fail that condition.

At an exact junction, Moira’s generic placement assigns the point to the house that opens there and marks it `exact_on_cusp`. This is a membership convention. The zero effect in verse I.8 and the interpolation in I.9 belong to a separate strength calculation.

Use exact fractional arcseconds to regenerate the complete worked witness independently of the runtime. Test centres and edges separately, including the 12/1 wrap and the known printed 6/7 discrepancy. Then verify antipodal symmetry, rotation between zodiac frames, unequal angular half-spans, and explicit junction behavior. No external engine is needed as an oracle.
