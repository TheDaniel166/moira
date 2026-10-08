# VED-007: admission of the five remaining names

Baseline: engine `12ed2a1`, wiki `424799f`, 8 October 2026. The user authorized
finishing the five remaining names, including their source, engine and REST
work. The existing Abhijit/Brahma interfaces retain their contract.

## Reviewed sources and decisions

* **Godhuli:** [Vivaha Vrindavana](https://archive.org/details/in.ernet.dli.2015.329463),
  Keshava, with Sitarama Jha's Sanskrit/Hindi Vasantalakshmi commentary,
  first edition, Samvat 1991 (cover; catalogue dates it 1935), Master Khelari
  Lal and Sons, Benares. PDF 85–86, printed 72–73, chapter 9 vv.5–6.
  The inspected commentary explicitly says half a ghati before and after
  half-setting of the solar disc. One ghati is 24 elapsed minutes: the
  interval is midpoint ±12 minutes. Verse 5 requires the Sun still visible
  on Saturday and fully set on Thursday. Retain the whole geometry and
  separately partition it into excluded/not-excluded portions at upper-limb
  sunset; permit explicit geometry-only operation. Half-set is a centre
  crossing, **not** upper-limb sunset. Astronomical realization is an explicit
  modern convention: constant 34 arcminute refraction and 16 arcminute
  semidiameter, or a geometric-disc profile without refraction; level horizon,
  zero elevation, no terrain. Those constants are not attributed to Keshava.
* **Godhuli variant:** [Muhurta Chintamani](https://archive.org/details/muhurta-chintamani-hindi),
  Rama, Ramlal Avasthi commentary, Chandika Prasad Avasthi editor, Tejkumar
  Book Depot, tenth edition 2004. Vivaha vv.99–101, printed 151–153,
  PDF 160–162. Season-dependent optical descriptions are not equivalent to
  the fixed interval above. The texts also disagree about Moon/Lagna
  restrictions. Preserve this difference in the policy's attribution; do
  not claim a universal marriage election or compute historical social
  classifications. These are timing objects, not activity recommendations.
* **Vijaya:** [Muhurta Sadhana, Samjna vv.61–63](https://www.transliteral.org/pages/z130601001637/view)
  divides daylight into fifteen parts;
  [vv.68–69](https://www.transliteral.org/pages/z130601001913/view) names Vijaya
  as the eleventh in the Pauranika enumeration. Return fractions 10/15 to
  11/15 of actual sunrise-to-sunset daylight. This is neither a fixed clock
  time, a festival-specific Vijaya Dashami rule, nor a planetary Vijaya yoga.
  This is a digital primary-text witness with no identified print edition;
  do not invent an edition or author. Verse 65's fixed-clock Hindi gloss is
  not used to override verse 62's explicit division rule.
* **Amrita Siddhi:** the same digital witness, vv.78–79, gives seven
  weekday/Moon-nakshatra pairs: Sunday Hasta; Monday Mrigashira; Tuesday
  Ashwini; Wednesday Anuradha; Thursday Pushya; Friday Revati; Saturday Rohini.
  These are presence rules, not cancellation of every activity-specific
  prohibition. The name is not silently shared with Nitya Yoga, Anandadi
  Amrita, Choghadiya or Amrita Kalam.
* **Amirtha alternative:** [Kalaprakasika](https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf),
  Sanskrit with English translation by N. P. Subramania Iyer, Asian
  Educational Services 1982 (inspected title page). Chapter XXXV, printed
  199–201, PDF 236–238, has a different, larger weekday/nakshatra table.
  Admit it as a separately named selectable profile. No Sunday Amirtha entry
  appears in the complete reviewed Sunday table; report no match that day,
  without relabelling its Siddha entries as Amirtha.
* **Ravi Yoga:** Chintamani, Shubhashubha v.27, printed 13, PDF 22:
  inclusive Moon-nakshatra count from the Sun's nakshatra in {4,6,9,10,13,20}.
  Both Sun and Moon transitions matter. This is not natal Ravi Yoga or the
  angular-sum Nitya Yoga limb.
* **Sarvarthasiddhi:** same scan, vv.28–29, printed 13–14, PDF 22–23.
  Admit its seven weekday tables literally, with public weekday Monday=0
  and 27 equal sidereal nakshatras beginning at Ashwini.

Private scans, rendered leaves and text are in
`C:/dev/outputs/ved007-five-2026-10-08/`; the earlier Chintamani scan is in
`C:/dev/outputs/ved007-named-muhurta-2026-10-08/`. SHA256:

| Witness | SHA256 |
| --- | --- |
| Vivaha Vrindavana searchable PDF, 138 actual pages | `793cc3c454a0c383bb3784886cd19e702d310b67aa39a597748b148da02cdfc0` |
| Kalaprakasika, 490 pages | `d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074` |
| Chintamani, 207 pages | `9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777` |

The local library pass reused 219 extracted text files and searched relevant
filenames. Matching Amrita/Ravi references often described different objects.
It was not fresh OCR of the entire library and makes no absence claim. The
online primary scans above resolve the governing calculations; private scans
and modern translations are not redistributed in the repository.

## Computational and route decision

`admit_after_engine_work`: a new owning `special_muhurta` module supplies
pure solar-anchor composition, pure supplied-sidereal-longitude yoga
classification, and a dated composition with all five additions plus the
existing two-window result. The date endpoint owns the requested sunrise day,
not the civil-midnight day. Its weekdays remain Monday=0 throughout.

Use the existing reader, UT1 clocks, solar discovery and sidereal transforms.
Retain source anchors and root brackets. Solve every Sun/Moon nakshatra
transition within the requested sunrise day; overlapping root uncertainty
bands remain explicit, including possible very short occurrences inside them.
Never stretch a sunrise snapshot over the whole day. Missing solar anchors
must not erase independently computable windows. Polar absence is typed;
resource/coverage errors remain errors. All date discovery is bounded to the
previous, current and following civil dates. No native substrate change,
external ephemeris, package install or runtime dependency is required.

Three strict REST routes expose solar/direct, yoga/direct and complete day
results. Server code projects canonical vessels and delegates calculations.
Public exports and facade methods must retain owning identity and caller-owned
reader lifecycle. Generic Muhurta scoring/search is a separate product.

## Verification acceptance

1. Independently transcribed complete tables, every weekday/star combination,
   all Sun/Moon pairs, cyclic and exact-edge ownership; separate Amrita names.
2. Rational Vijaya and Godhuli fixtures, unequal daylight, Thursday/Saturday
   partitions, missing anchors and contradictory inputs, half-open membership
   and propagated numerical uncertainty.
3. Analytic moving Sun/Moon fixtures with wrap, Sun-only transitions, close
   transitions, unchanged full days and before-sunrise weekday ownership.
4. Real DE441 normal/DST/polar dates, both horizon and Amrita profiles,
   reader restoration, solar residual brackets, and existing published PAC
   component checks. This does not claim a published paired five-window oracle.
5. Strict REST admission before astronomy, canonical equality, both server
   startup resource paths, OpenAPI completeness, selected regressions, lint,
   generated reference/wiki checks and a reproducible execution receipt.

## Execution outcome

All five source-selected additions are implemented locally. The complete
[383-test receipt](../03_validation/SPECIAL_MUHURTA_VALIDATION_2026-10-08.md)
records source, analytic, real-DE441, transport and regression evidence,
including uncertainty and lifecycle checks. VED-007 is locally complete for
its seven named families and is included in the containing authorized
engine/wiki source-publication package. Runtime release and deployment remain
separate. See the execution receipt for publication scope.
