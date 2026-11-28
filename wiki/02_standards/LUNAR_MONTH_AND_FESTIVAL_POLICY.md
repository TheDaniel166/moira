# Lunar-month and festival policy surface — VED-023/024

**Date:** 6 October 2026.
**Owners:** [lunar-month engine](../../moira/lunar_month.py), [facade](../../moira/_facade_vedic.py), [request/response](../../moira_server/models/lunar_month.py), [service](../../moira_server/services/lunar_month.py), [serializer](../../moira_server/serializers/lunar_month.py), [router](../../moira_server/routers/panchanga.py).
**Status:** Astronomical lunar months, named intercalation profiles and festival research/admission policy.

The user explicitly selected festivals and lunar-month rules after Daily
Panchanga, and authorized source publication. These are separate products
from [VED-015](DAILY_PANCHANGA_STANDARD.md). An astronomical lunation is not
a sunrise-owned civil day, a regional month date, an era year or a selected
observance. Each result must identify which object it actually computes.

## 1. Initial source audit and decisions

| Source | Evidence inspected | Admission decision |
| --- | --- | --- |
| IMD/PAC, *Rashtriya Panchang*, 1948 Saka Era, 2026–27 | Official [English archive](https://packolkata.imd.gov.in/download/EnglishRP2627.zip), obtained through the [institutional download page](https://packolkata.imd.gov.in/rashtriya-panchang-english.php). Preface PDF 4; explanation PDF 11–12, printed vi–vii; regional month table PDF 17–18, printed xii–xiii; festival list PDF 6–8, printed i–iii; selected dated rows PDF 35, 43, 50, printed 15, 23, 30. Regional table PDF 17 also rendered and visually inspected. | `admit_now` for a named modern astronomical month context with explicit Moira reduction policy; bounded fixtures below. Published festival dates are comparison evidence, not a complete rule catalogue. |
| S.K. Chatterjee, *Indian Calendars*, DOI [10.1017/S0252921100105901](https://doi.org/10.1017/S0252921100105901) | Author's [six-page paper](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/S0252921100105901), especially printed 93–94, PDF 3–4. | `admit_now` for the declared ordinary astronomical assembly; `defer` exceptional regional relabeling. This paper supplies the astronomical method, not primary verses for every ritual. |
| Gauḍīya Vedānta Publications, *Vaiṣṇava Calendar 2026–2027*, Mathurā–Vṛndāvana | Publisher's [36-page PDF](https://www.purebhakti.com/resources/ebooks-magazines/bhagavat-patrika/calendars/562-2026-27-vaisnava-calendar-english-vrindavan/file), doctrinal sections printed 4–12, PDF 4–12; declared locality, lineage and primarily Sūrya-siddhānta calculations on cover. | `research_only` for a separately named Gauḍīya profile. Provides viddhā, Mahā-dvādaśī and pāraṇa leads; not an authority for Smārta or all Vaiṣṇava communities. No code or calendar dataset imported. |
| ISKCON Juhu Mumbai, [Ekādaśī calculation explanation](https://www.iskconmumbai.com/blog/hare-krishna-blogs-1/how-to-calculate-ekadasi-fasting-days-10), dated 28 December 2025 | Institution's account of aruṇodaya and pure/mixed Ekādaśī. | `research_only`; concise explanatory prose cannot settle all exceptional fasting cases. |
| B.V. Raman, *A Manual of Hindu Astrology*, local database scan | `C:\dev\ASTROLOGY-BOOKS-DATABASE\Books by Authors\BV Raman\A Manual of Hindu Astrology by BV Raman.pdf`; PDF 81–84, printed 52–55, rendered and read. Earlier daily work also inspected PDF 59/74. SHA256 `439f877fd4a52f309f67e9e427a912daff7241cfdfb180605e6e6eba9af5b60a`; 155 pages; edition/date not established by this scan. | Almanac and calculation context only. These pages do not supply a festival selection catalogue. No claimed Raman festival rule is admitted. |

Official archive ZIP SHA256:
`fe3cb9fc27647fafc92cedfab3e25d53d19bbfb49e4949a8436312641174a835`.
Contained `RP 1948 SE Final.pdf`, 193 pages, SHA256:
`a8816abe4fae7fc0f0e4349a3d91eef00cfc0044a5f050b1b3bfe826847f9eaa`.
The preface is dated 10 October 2025; the calendar covers 2026–27.
Copies/renders under ignored `tmp/pdfs/` are research aids, not runtime data
dependencies or redistributed licensed corpora.

The local database filename inventory was searched for calendar, Panchanga,
Muhurta, Siddhanta, Dharma, Nirnaya, Vrata and festival titles. It includes
Siddhanta Shiromani translation `.doc` files and Muhurta chart collections;
neither filenames nor chart examples establish ritual authority. No
identified Dharma Sindhu/Nirnaya Sindhu edition was found by that search.
This is a filename search, not a claim that every page of the database was
OCR-searched. A 332-page Sewell/Dikshit *Indian Calendar* scan was also acquired
from [IGNCA](https://ignca.gov.in/Asi_data/34958.pdf), hash
`8c9a225f6a28e33a8ab9bc274c4b853de4a666dd9fd5f9a081df3912d82a4b71`;
text extraction did not establish its relevant passages, so it is an
unadmitted research lead.

## 2. What the research changes

The PAC explanation names lunar months by the solar sign containing their
initial conjunction. Its intercalation uses nirayana ingresses; its separate
fixed-offset saura and national calendars have different conventions.
Those solar calendars must not be silently substituted for the month engine.

Chatterjee describes intercalation through two conjunctions within a solar
month and omission when a solar month contains none. He also discusses
adjustment of surrounding months in omission years. The structural profile
retains the astronomical evidence and the named profiles below apply
explicit alternative mappings.

The official regional table is a concrete counterexample to treating every
Purnimanta period as an uninterrupted full-moon interval: in 2026 it gives
Jyaishtha Vadi on 2 May, Jyaishtha Adhika Sudi on 17 May, Adhika Vadi on
1 June and Nija Sudi on 15 June. Ordinary fortnight mapping is useful but
does not settle this exceptional sequence.

The publisher's Gauḍīya calendar distinguishes sunrise from aruṇodaya, pure
and mixed tithis, eight Mahā-dvādaśī types, and separate pāraṇa rules. Its
geometric-center sunrise convention differs from PAC's upper-limb
convention. These are separate doctrine and astronomical policy choices.
The Mumbai explanation corroborates the aruṇodaya concern within its own
lineage; it is not a complete executable exceptional-case specification.

## 3. Admitted astronomical object and ambiguity

`lunar_month_at(jd_ut1, *, policy=None, reader=None)` owns an instant in UT1.
It computes apparent geocentric ecliptic-of-date Sun/Moon longitudes through
the reader-bound native ephemeris substrate; Python owns month policy and
assembly. Longitude difference supplies conjunction/opposition. Sidereal
solar longitude uses the selected existing ayanamsa in `true` mode.

The object is assembled from three contiguous conjunction-to-conjunction
lunations: preceding, containing and following the instant. Each carries its
opening solar rashi, certain ingresses, uncertain ingress brackets, structural
label and any omitted month name. No mean synodic period generates dates.

| Policy/result | Explicit contract |
| --- | --- |
| System | `amanta` default; `purnimanta` explicit. Python requires `LunarMonthSystem`; REST admits its string values. |
| Ayanamsa | Existing named registry, `Lahiri` default, normalized aliases. Selected system is echoed; it can move solar ingress/naming but cannot move conjunction/opposition. |
| Solver | Default 0.1 seconds, admissible 0.01–1 seconds. Bracket width is numerical evidence, not observational or institutional agreement. |
| Search | ±65 days around the requested instant; one-day angular steps; steps must advance positively by less than half the relevant span. Require surrounding conjunctions and 20–40 day lunation lengths; invalid trajectories/resource failures raise. |
| Input bounds | Finite real JD in [−10000000, 10000000], permitting representable subsecond bracketing. Kernel coverage still governs actual computability. Booleans and numeric strings are rejected. |
| Root vessel | Kind, angular target, lower/upper UT1 bracket, and entered-side `jd_ut1`. Conjunction/opposition are 0°/180° phase; solar ingress is a 30° multiple. |
| Ownership | Half-open periods, with the entered boundary owning its instant. A request inside a solved phase bracket is `boundary_ambiguous`; `uncertain_phase_boundaries` retains the actual witnesses and no selected period/label is fabricated. |
| Near-coincident ingress | If a solar bracket overlaps a conjunction bracket, preserve it as uncertain. Do not use floating-point root order to force an Adhika/Kshaya decision. |
| Amanta naming | Solar rashi 0–11 maps to Vaisakha through Chaitra. Zero certain ingresses gives `adhika`; one gives `ordinary`; two gives `ksaya_context` with the intervening omitted name. The latter is structural evidence, not a regional combined-month label. |
| Ordinary Purnimanta | Only when all three surrounding lunations are certain and ordinary: full-moon bounds, current amanta label during Shukla, following label during Krishna. |
| Exceptional Purnimanta | The default `structural` policy retains its conservative surrounding-month exclusion and typed unavailability. Select `sewell_dikshit_gauna` for the sourced split and omission rules below. |
| Provenance | Source identifiers, origin/frame, sidereal mode, timescale, naming/intercalation rules, search bounds, ownership and actual reader binding. |

The public vessels reject contradictory labels, omitted names, ingress order,
phase targets, noncontiguous lunations and available/unavailable claims.
`ordinary` is a structural classification; it does not automatically assert
every regional Suddha/Nija usage or era-year adjustment.

## 4. Python and REST

Eight names are curated by identity through `moira`, `moira.facade` and
`moira.vedic`: `LunarMonthSystem`, `LunarMonthPolicy`, `CalendarBoundary`,
`LunarMonthLabel`, `LunarLunation`, `LunarMonthProvenance`, `LunarMonthResult`
and `lunar_month_at`. `Moira.lunar_month_at` binds the caller-owned engine
reader; the function never closes it and restores reader context on failure.

```python
from datetime import datetime, timezone
from moira import Moira, LunarMonthPolicy, LunarMonthSystem
from moira.julian import jd_from_datetime, utc_to_ut1

engine = Moira()
jd = utc_to_ut1(jd_from_datetime(datetime(2026, 9, 22, tzinfo=timezone.utc)))
result = engine.lunar_month_at(
    jd, policy=LunarMonthPolicy(system=LunarMonthSystem.AMANTA)
)
assert result.status == "available"
assert result.label.name == "Bhadrapada"
```

`POST /v1/panchanga/lunar-month` has strict typed models, public-facade service
delegation and complete canonical serialization. It takes an astronomical
instant; location/timezone belong to a separate daily/observance composition.

```json
{
  "jd_ut1": 2461305.5,
  "policy": {
    "system": "amanta",
    "ayanamsa_system": "Lahiri",
    "solver_tolerance_seconds": 0.1
  }
}
```

Available and domain-unavailable computations return typed HTTP 200 responses.
Invalid input returns the existing structured HTTP 422 envelope. Resource and
solver exceptions retain the server's existing error mapping. Extra fields,
including an invented festival or observer policy, are rejected. The transport
contains every engine field plus the boundary's derived `jd_ut1` property.

## 5. Exceptional Purnimanta and regional Kshaya naming

These opt-in values of `LunarMonthPolicy.naming_profile` are available
through Python and the lunar-month REST policy. Profile names identify the
source rule. The geographic names in Leow's headings are his terminology.

| Profile | System | Selected month and evidence |
| --- | --- | --- |
| `structural` | Either | Original bounded assessment. The three structural lunations keep their opening signs, counts and omission names. |
| `sewell_dikshit_gauna` | Purnimanta | One Adhika lunation owns both fortnight labels and runs from new moon to new moon. The preceding Krishna fortnight takes the regular name, from full moon to new moon. The following regular Shukla fortnight bears `nija`, from new moon to full moon. For a two-ingress omission, the ordinary full-moon pairing uses the opening name and carries the omission as `ksaya_context`. |
| `leow_eastern` | Amanta | Keep the earlier Adhika. Starting just after the two-ingress lunation, move each name back one through the later Adhika, which becomes ordinary. The two-ingress lunation keeps the opening name as ordinary. |
| `leow_northwestern` | Amanta | Make the earlier Adhika ordinary. Starting just after it, move each name forward one through the two-ingress lunation. Keep the later Adhika. |
| `dharmasindhu_dual` | Amanta | Keep both Adhikas and both names of the two-ingress lunation. Its opening name is `label.name` and the second is `paired_month_name`. Both names own the same astronomical lunation. Tithi-half ritual assignment requires its own rule and is outside this result. |

The regional Amanta profiles use the two-ingress lunation and its nearest
zero-ingress companions within five lunations on either side. This
accommodates Leow's Figure 14, including a companion across the Chaitra
sequence. The phase scan extends to ±480 days for an explicitly selected
regional profile, so the engine can inspect both companions when the caller
is at either end of the group. Readers must cover the selected scan. Exact
month bounds remain the local solved conjunctions. `regional_lunations`
retains the contiguous structural evidence used for the mapping. An
overlapping ingress and conjunction needed for a choice yields
`boundary_ambiguous`. An unresolved, definite two-ingress group yields
`unsupported_intercalation`. Labels remain null in both cases.

### Source and worked-example verification

- Bhāskara II, *Siddhānta Śiromaṇi*, Grahagaṇita, Madhyamādhikāra,
  Adhimāsa-nirṇaya 6 and the Vāsanā commentary, defines the zero- and
  two-ingress cases and describes the flanking intercalations. This
  establishes the structural criterion. [Sanskrit witness, printed p. 84](https://sa.wikisource.org/wiki/पृष्ठम्:सिद्धान्तशिरोमणिः.djvu/129)
- Sewell and Dikshit, *The Indian Calendar* (1896), §§45–46 and 51,
  printed pp. 26–27 and 30–31, gives the opening-sign convention and works
  the Gauna split around Adhika Vaisakha. Its suppression diagram pairs the
  two Margasirsha fortnights and omits Pausha. The 1948 SE PAC Gauna Mana
  table independently shows Jyaishtha Krishna on 2 May 2026, Adhika
  Shukla on 17 May, Adhika Krishna on 1 June and Nija Shukla on 15 June,
  followed by Ashadha Krishna on 1 July. All five identities were reproduced
  at noon IST using DE441, with adjoining solved phase bounds within 0.2 s
  of each other. The table supplies civil-date labels. [Sewell and Dikshit, pp. 26–27](https://ignca.gov.in/Asi_data/34958.pdf#page=43)
  [Sewell and Dikshit, §51](https://ignca.gov.in/Asi_data/34958.pdf#page=47)
  [Rashtriya Panchang 1948 SE regional table](https://packolkata.imd.gov.in/panchang/gu/regional-calendars)
- Leow Choon Lian, *Indian Calendars* (NUS, 2000–01), Figure 13 and
  Table 14, printed pp. 42–44, gives the complete comparison for the
  1540–41 worked ingress pattern. An independent transcription from the
  figure reproduced all 27 entries in the three columns. The author's
  raw astronomy for this figure differs from the DE441/Lahiri geometry
  at the same dates, so the fixture uses the published ingress order.
  The same author's Table 12 independently identifies the modern
  1963–64 Margasirsha omission with Kartika/Chaitra and the 1982–83
  Magha omission with Asvina/Phalguna. DE441 reproduces both event groups.
  The printed comparison plus these event groups tests the profile
  algorithms without attributing their output to a historical local
  almanac. [Author's study, Table 14](https://telibrary.com/wp-content/uploads/2022/08/Indian-Calender-Article.pdf#page=43)
- The Jiwaji *Astronomical Ephemeris* for 1983, printed pp. 3 and 5,
  PDF pp. 14–15, gives the two tithi 30 endings around the two-ingress
  lunation. The printed times are 14 January 10:38 IST and 13 February
  06:02 IST. The DE441 conjunctions are 13.48 s and 10.75 s earlier,
  respectively, within the 60 s comparison bound. The month names
  in the page headings follow the Indian civil calendar, as stated in
  the preface. [Jiwaji ephemeris, 1983](https://www.mpssbhopal.org/jiwajipanchang/ASTRONOMICAT%20EPHEMERIS%20OF%20GEOCENTRIC%20PLACES%20OF%20PLANETS%20FOR%201983.pdf#page=14)
- Kāśīnātha Upādhyāya, *Dharmasindhu*, First Pariccheda, Malamāsa-vicāra,
  Kṣaya-māsa example, works the Dhanus and Makara ingresses in a single
  Margasirsha–Pausha lunation, with Asvina and Phalguna as the added
  companions. It assigns the two month names to the two halves of each
  tithi for specific purposes. The engine returns the paired names.
  Ritual decisions, including the application's choice of a half-tithi
  boundary convention, require a separate admission. [Sanskrit text and translation](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=1&t=path)

## 6. Festival rule admission

Moira admits festival rules by named profile and verified branch. VED-024
currently has bounded admission for the first Mahāśivarātri profile.
The source packet below defines its supported cases and the decisions
that still require source completion.

Every catalogue entry must carry a stable rule/version ID, a particular
festival identity, edition/page/verse or operational authority, scope of
community/region, astronomy policy and all selection decisions. A single
`smarta`/`vaishnava` switch is too coarse: the actual admitted profile must
identify which source family it applies.

| Policy axis | Required explicit choice/evidence |
| --- | --- |
| Calendar identity | Amanta/Purnimanta or named regional solar calendar; stable month identity and aliases. No Gregorian-date cache presented as sovereign computation. |
| Intercalation | Per-rule ordinary/Adhika eligibility and Kshaya/split-month handling. No global “no festivals in Adhika” assumption. Unsupported month evidence prevents selection. |
| Astronomical basis | Moira modern ephemeris reduction and selected ayanamsa/sunrise convention. A traditional Sūrya-siddhānta calendar is a different model; retaining a rule's tradition does not imply numerical reproduction of its calendar. |
| Criterion | Exact tithi/nakshatra/weekday/solar-ingress predicate and its required witness interval. Sunrise, pre-dawn offset, local meridian transit, fraction of daylight, sunset interval, moonrise or fractional night must each have their own mathematical definition. |
| Temporal ownership | Gregorian local date versus sunrise day and the date receiving a night observance; aware UTC/local displays plus UT1 event truth. DST and skipped civil dates follow explicit daily rules. |
| Viddha | Which preceding/following tithi contaminates which instant/window; exact equality and uncertainty behavior. Do not infer a whole fasting decision from one clean sunrise. |
| Repeated tithi | Candidate dates, independently computed overlap/purity evidence and the source-owned first/second/maximum-overlap/tie rule. “Repeated” is evidence, not automatic first-day selection. |
| Skipped tithi | Source-owned preceding/following-day fallback, or unavailable/ambiguous outcome. Do not pretend the tithi was absent astronomically. |
| Multiple conditions | Explicit conjunction, precedence, and exclusions among tithi, nakshatra, weekday and solar/ritual windows. Never synthesize a rule by matching a published date. |
| Fasting versus festival | Distinct observance kind. Named Mahā-dvādaśī rules and pāraṇa constraints must be evaluated where required, with witnesses beyond the target civil date. |
| Neighbouring days | A declared lookbehind/lookahead sufficient for the rule. Border days in a requested range need the same context as interior days; absence of an in-range candidate cannot silently mean no festival. |
| Polar/ambiguous events | Reuse daily unavailable evidence. A midnight or surrogate-sunrise fallback requires its own explicitly sourced policy; none is assumed. |
| Numerical sensitivity | Overlapping event/predicate brackets produce ambiguous candidates. Solver tolerance must not become a ritual grace period or observational accuracy claim. |
| Reasons | Preserve each predicate/witness, rejected candidate, precedence decision and source citation. No unexplained auspiciousness score determines a ritual date. |
| Status | `selected`, `not_applicable`, `ambiguous`, `unavailable`, `excluded_by_profile` and `unsupported_rule` must remain distinguishable. An empty list must not conceal incomplete evaluation. |
| Catalogue/REST | Read-only catalogue reports source/profile/admission state; only admitted rules become executable choices. Strict bounded search and typed per-rule results; no arbitrary executable expressions supplied by callers. |

This requires a source-owned programme, not twelve mechanically repeated
phases. The next finite rule packet should include one ordinary case, every
source-required exception, counterexamples for competing traditions, exact
boundary cases and an explicit decision on any missing rule branch.

The current catalogue and evaluation route expose the first source-owned
ritual window. Ekādaśī needs its selected exceptional-case and pāraṇa
doctrine before admission as a fasting calendar. Janmāṣṭamī, Dīpāvalī and
regional solar festivals each require independent rule packets.

### VED-024 first source packet — Mahāśivarātri

**28 November 2026.** The engine exposes the ordinary date, selected-morning
vow and conditional next-morning pāraṇa under
`mahashivaratri_dharmasindhu_later_v1`. Exceptional month eligibility and
pāraṇa outside the admitted geometry remain in source research.

Kāśīnātha Upādhyāya's *Dharmasindhu*, second Pariccheda, Māgha-māsa,
Śivarātri and Pāraṇanirṇaya, was checked in the Sanskrit transcription
of the Nirṇaya Sāgara 1888 edition (Kṛṣṇaśāstrī Navare) and against the
Marathi translation. The target is Krishna Caturdaśī in Amanta Māgha,
which the *Nirṇayasindhu* identifies as Krishna Caturdaśī in Purnimanta
Phālguna. That correspondence holds for the ordinary calendar.
[Dharmasindhu, Śivarātri](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=19&t=path)
· [Marathi translation](https://www.transliteral.org/pages/z80505114958/view)
· [Nirṇayasindhu, Mahāśivarātri](https://whm.cdsharma.in/dharma-nirnay?g=ns&p=32&t=path)

For the *Dharmasindhu* reading, Niśītha is the eighth muhūrta of the
night. With sunset `S` and following sunrise `R`, the modeled window is
`[S + 7(R−S)/15, S + 8(R−S)/15)` in UT1. The date label belongs to the
sunrise day containing the sunset, including when the window itself is
wholly after civil midnight.

| Caturdaśī coverage of the two candidate Niśīthas | Decision |
| --- | --- |
| Exactly one has coverage | Select that night. |
| One full and one partial | Select the full night in either order. |
| Both full or both partial | Hemādri as reported by the *Kaustubha* selects earlier. The later-night authorities reported by *Dharmasindhu* select later. |
| Neither has coverage | Select the later day. |

The *Nirṇayasindhu* itself records another arddharātra definition in its
Madhava citation and uses pradoṣa in some two-night decisions. Its detailed
rule requires a separately identified profile.

#### Worked date and geometry witnesses

The daily Panchanga supplied solar crossings under the Rashtriya
upper-limb policy. Caturdaśī was separately bracketed at elongations
336° and 348° with DE441 and checked against the daily tithi coverage
and structural Amanta month. Times are displayed to the second in each
local clock. The published witnesses establish the dates selected by
their institutions.

| Locality | Solved Caturdaśī interval | Niśītha coverage | Published date |
| --- | --- | --- | --- |
| Sringeri `13.4167, 75.2500`, IST | 15 Feb 2026 17:05:21 to 16 Feb 17:34:34 | 15 Feb full, window 16 Feb 00:18:22–01:07:33. 16 Feb absent. | 15 Feb. [Sringeri event](https://www.sringeri.net/events/mahashivaratri-2026) |
| Kolkata `22.5726, 88.3639`, IST | 6 Mar 2027 12:04:02 to 7 Mar 13:46:50 | 6 Mar full, window 23:23:13–00:11:59. 7 Mar absent. | 6 Mar. [Rashtriya Panchang, festival row 81](https://packolkata.imd.gov.in/panchang/index.php/en/festivals) |
| Palani `10.4503, 77.5161`, IST | 13 Feb 2018 22:34:56 to 15 Feb 00:46:48 | 13 Feb full, window 14 Feb 00:09:35–00:58:28. 14 Feb partial, window 15 Feb 00:09:34–00:58:25. | 13 Feb, explicitly selected in response to the Palani pandits' question. [Sringeri Jagadguru's decision](https://vijayayatra.sringeri.net/archiveyatra/palani-april-22-23-2017/) |
| Kolkata `22.5726, 88.3639`, IST | Same geocentric 2018 tithi | Both full. Windows 13 Feb 23:25:17–00:15:48 and 14 Feb 23:25:18–00:15:44. | 14 Feb holiday. [West Bengal holiday list](https://msme.wb.gov.in/cmsholiday) |
| New York City `40.752, -73.816`, EST | 26 Feb 2025 00:38:56–22:25:08 | Both absent. The 25 Feb window ends on 26 Feb at 00:33:28. The 26 Feb window starts at 23:41:57. The source fallback selects 26 Feb. | 26 Feb. The probe uses metropolitan coordinates. [Bronx Puja Committee announcement](https://bronxpujacommittee.com/maha-shiva-ratri/) |

Two more runs isolate sunrise ownership from ritual-window coverage.
At Jerusalem (`31.778, 35.235`, UTC+02:00) the 26–27 February 2025
sunrises were in tithis 28 and 30. The intervening Caturdaśī covered the
entire 26 February Niśītha. At Kauai (`22.075, -159.500`, UTC−10:00)
Caturdaśī owned the 13 and 14 February 2018 sunrises. It covered the
13 February Niśītha and ended before the 14 February Niśītha. These are
calculated geometry cases.

#### Intercalation and fasting admission

- At 23:45 IST on 11 February 1983, the solved tithi is Krishna
  Caturdaśī. VED-023 gives Pausha with omitted Magha under the
  structural policy, Pausha under the Eastern mapping, Magha under
  the North Western mapping, and Pausha/Magha under the dual profile.
  The Prasanthi Nilayam archive records Mahāśivarātri on 11 February.
  That is an observed Kshaya-year date. The general rule for weighting
  the two month identities remains to be established for a named
  ritual lineage. [1983 event recording](https://saicast.org/1983/19830211Purna.html)
  · [Dated discourse](https://saispeaks.sathyasai.org/discourse/ever-auspicious-lord)
- The *Dharmasindhu* procedure places the vow in the morning after daily
  rites. *Śivapurāṇa*, Koṭirudrasaṃhitā 38.25–31, begins with the morning
  of the observance day, gives the daily rites and the vow in sequence,
  then gives the night worship. *Puruṣārthacintāmaṇi*, Upavāsa-nirṇaya,
  expressly keeps the morning saṅkalpa even when the tithi chosen for
  the main rite starts after sunset. Moira applies that ordering to
  the sunrise day selected by the Niśītha rule. The result places
  the vow after the practitioner's daily rites on that morning.
  [Dharmasindhu, Vrata procedure](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=20&t=path)
  · [Śivapurāṇa 4.38.25–31](https://vedapath.app/en/shiva-purana/kotirudra/38)
  · [Puruṣārthacintāmaṇi, Upavāsa-nirṇaya](https://vishvasa.github.io/kalpAntaram/dharmaH/nibandhaH/viShNubhaTTaH/puruShArthachintAmaNiH/#:~:text=%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%BE%E0%A4%A4%E0%A4%B0%E0%A4%BE%E0%A4%B0%E0%A4%AD%E0%A5%8D%E0%A4%AF)
- The *Pāraṇanirṇaya* author's reconciliation gives the tithi ending when
  Caturdaśī leaves insufficient time for the daily rites and pāraṇa or
  when Darśa śrāddha and related rites apply during the remainder of that
  day. Otherwise pāraṇa is within Caturdaśī after the preparations. The
  three-yāma discussion introduces the reported readings of Mādhava and
  others. The admitted branch uses Kāśīnātha's subsequent conditions.
  [Dharmasindhu, Pāraṇanirṇaya](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=20&t=path)
  · [Marathi translation](https://www.transliteral.org/pages/z80505115136/view)

#### Worked checks for the remaining branches

At Sringeri on 15 February 2026, sunrise was 06:52:09 IST and
Caturdaśī began at 17:05:21. The institution's dated report records
morning worship on the 15th and the first of the four night services
at 19:30. This independently witnesses that the observance begins
on the selected day before the physical tithi starts. The placement
of the personal vow comes from the ritual texts above.
[Sringeri's report](https://www.srisharadapeetham.org/events/mahashivaratri-2026)

At Palani the Jagadguru selected 13 February 2018. Caturdaśī began at
22:34:56 IST, after the sunset of the selected day. The same morning
directive applies, with the physical tithi at sunrise reported separately.
[Palani date decision](https://vijayayatra.sringeri.net/archiveyatra/palani-april-22-23-2017/)

At Prasanthi Nilayam, the 1983 tithi ran from 11 February 01:05:12 to
12 February 03:41:14 IST. The elapsed-time midpoint was 14:23:13 and
the 342° elongation crossing was 14:24:49 on the 11th. The entire chosen
night's Niśītha, 00:08:12–00:57:41 on the 12th, falls in the later
half under both calculations. The following Adhika Phālguna Caturdaśī
covered the 12 March night, a separate astronomical candidate that the
Eastern regional mapping calls Māgha. The *Dharmasindhu* assigns half
tithis to paired months and permits rites with no other occasion in
intercalary months. Its worked ritual applications distinguish annual
death rites, anniversaries and recurring Māgha-snāna. The
*Smṛtimuktāvalī* affirms that duties of an omitted month can be performed
in the paired lunation. The source decision still needed for this
festival is whether and when to apply that duty rule to its entire
vrata, including first observance, and how the half-tithi affects
night selection. [Dharmasindhu, Kṣaya-māsa and Malamāsa](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=1&t=path)
· [Smṛtimuktāvalī, Śūnyamāsa-nirṇaya](https://sa.wikisource.org/wiki/स्मृतिमुक्तावलिः)
· [1983 event recording](https://saicast.org/1983/19830211Purna.html)

At Kolkata in 2018, the later night's Niśītha ended at 00:15:44 IST,
Caturdaśī at 00:46:48 and the following sunrise was at 06:08:47,
all on 15 February. This differs from New York, where the ending
precedes the selected Niśītha. *Puruṣārthacintāmaṇi* recognizes a
scriptural exception for certain nighttime tithi-end observances.
The *Dharmasindhu* combines its conditional time rule with a procedure
that places bath and renewed worship at dawn after the vigil. The
sources reviewed do not establish a precedence between the pre-dawn
tithi ending and completion of the vigil for the selected later
night, or for the neither-night fallback. Both cases remain
`unsupported_rule` for pāraṇa.
[Puruṣārthacintāmaṇi, Śivarātri-pāraṇa](https://vishvasa.github.io/kalpAntaram/dharmaH/nibandhaH/viShNubhaTTaH/puruShArthachintAmaNiH/#:~:text=%E0%A4%87%E0%A4%A4%E0%A4%BF%20%E0%A4%B6%E0%A4%BF%E0%A4%B5%E0%A4%B0%E0%A4%BE%E0%A4%A4%E0%A5%8D%E0%A4%B0%E0%A4%BF%E0%A4%AA%E0%A4%BE%E0%A4%B0%E0%A4%A3%E0%A4%A8%E0%A4%BF%E0%A4%B0%E0%A5%8D%E0%A4%A3%E0%A4%AF%E0%A4%83)
· [Dharmasindhu, Pāraṇanirṇaya and Vrata procedure](https://whm.cdsharma.in/dharma-nirnay?g=ds&p=20&t=path)

#### Implemented contract

The [engine evaluator](../../moira/observances.py) and the
[Panchanga REST routes](../02_services/REST_API_REFERENCE.md#panchanga-routes)
take one local Gregorian date and a location with an IANA timezone or
fixed UTC offset. The catalogue names the source, later-night precedence,
Lahiri and Rashtriya upper-limb convention. A request for the neighboring
date can return `not_applicable` with the winning `selected_date` and
the two candidate windows. A zero-duration touch has no coverage.
The engine tests all possible coverage classes from the brackets and
returns `ambiguous` if they could select different dates.

The solar search examines civil dates from two days before local tithi
onset through one day after its ending, with the next sunrise for each
night. The angular scan looks for Caturdaśī within the requested date
and its two immediate neighbors and pads that three-day span by two UT1
days on each side to capture complete crossings. The shared lunar
solver advances hourly, bracketing 336° and 348° to 0.1 s. The daily
solar crossings are independently sign-checked on the existing
topocentric altitude signal over a nominal 0.1 s interval centered on
each crossing. Niśītha bounds follow from those solar bounds in UT1.
Missing solar context yields `unavailable`. The seconds describe
numerical brackets.

The `vow` result identifies the selected morning and the sequence
after daily rites. The `sunrise_tithi` field compares that sunrise with
the physical tithi brackets and can report boundary uncertainty
independently of the selected morning. For paired Māgha geometry,
`date_result.paired_magha` carries both half-tithi boundaries for
comparison. The date result still reflects the current intercalation
admission.

Conditional pāraṇa applies where the tithi spans the sunrise following
the selected night. The practitioner supplies whether Darśa śrāddha
applies and, when it does not, the time on that following local date
when the required preparations allow them to break the fast. A readiness
time strictly before the tithi ending yields the half-open window
`[readiness, tithi end)`. When readiness is at or after the ending,
or Darśa applies, the result carries the ending boundary and the
`at_tithi_end` directive. If a comparison straddles the retained
brackets it produces `ambiguous`. Missing personal context and
unsupported astronomical branches are visible separately from the
date decision.

At Sringeri the verified ending is about 17:34:34 IST on 16 February
2026. With practitioner readiness at 08:00 and no Darśa obligation,
the supplied witness gives a window from 08:00 to that ending.
Readiness at 18:00 gives the end-of-tithi directive, as does applicable
Darśa. The readiness times are worked inputs. In the New York
neither-night fallback the ending precedes the selected Niśītha and
the next sunrise. The evaluator retains the selected date and reports
`unsupported_rule` for pāraṇa. The omitted-Māgha 1983 replay retains
both the structural omission and the Dharmasindhu paired name, with
`unsupported_rule` for the date.

Verification covers [pure precedence and exact contacts](../../tests/unit/test_observances.py),
[DE441 source and geometry cases](../../tests/integration/test_observances.py)
and [HTTP/OpenAPI parity](../../tests/server/test_server_observances.py).
The focused run passed 301 tests, including the adjacent daily Panchanga,
lunar-month and Vedic export suites, with DE441 and downloads disabled.

## 7. Verification and remaining boundary

Validation files:

- [analytic and assembly tests](../../tests/unit/test_lunar_month.py);
- [DE441 and PAC comparisons](../../tests/integration/test_lunar_month.py);
- [strict request/OpenAPI and HTTP parity](../../tests/server/test_server_lunar_month.py);
- existing public export audit, Vedic surface/facade and Panchanga neighbours.

The first focused run passed 82 cases and found a failed proposed
one-minute solar-ingress comparison: the 15 June 2026 ingress was 64.4768
seconds later than PAC's printed 12:53 IST. Follow-up reconciliation proved
that the shared ayanamsa scalar incorrectly used the FW rotation angle
instead of IAU 2006 general precession `p_A`. Correcting that astronomical
quantity closes the discrepancy. All 13 PAC 1948 SE solar ingresses now pass
the **original 60-second gate**, with a maximum measured residual of 25.296
seconds and about 0.33 seconds at the June instant. No constant was fitted
and no authority threshold was loosened. Independent ERFA scalar validation
and the complete source/measurement/compatibility receipt are in
[Sidereal general-precession reconciliation](../03_validation/SIDEREAL_GENERAL_PRECESSION_RECONCILIATION.md).
Three published conjunction timings and the selected month labels remain
separate comparisons. Printed minute precision and an internal 0.1-second
root bracket do not establish subsecond external reduction agreement.

Era years, regional solar civil dates, additional historical conventions,
dual-month ritual assignment and a named festival catalogue remain open.

### Original structural-profile verification receipt

Project Python 3.14.3, engine 6.9.9, required native extension
`moira/_moira_native.cp314-win_amd64.pyd`, local
`C:\Users\nilad\.moira\kernels\de441.bsp`. No downloads during tests;
`MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_lunar_month.py tests/integration/test_lunar_month.py tests/server/test_server_lunar_month.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

The final focused run passed **87 tests**, no skips/failures, with 29 DE441
resource receipts and one content probe. The broader regression
command selected those files plus daily unit/integration/server tests,
`test_api_surface_adversarial_audit.py`, `test_vedic_surface_completeness.py`,
`test_vedic_facade.py` and existing Panchanga route/service tests:
**247 passed**, no skips/failures, 61 DE441 resource receipts and one content
probe. That run preceded the final additional phase-bracket vessel guards;
the final focused run exercises the complete final month contract.

Scoped Ruff is clean. The remaining touched curation files retain their
existing diagnostics: root 59, facade 5, server model curation 1; comparison
against the actual HEAD source by diagnostic code/message introduced none.
The saved Python and JSON examples were executed with the actual local
kernel and typed request/service/serializer, not merely parsed. REST-reference
sync/check and documentation consistency passed; generated-wiki/whitespace
publication gates are run on the staged package.

The source/lineage inspection follows the declared geometric object,
continuous forward phase, explicit bracket ownership and named result
relations. No external engine/calendar code, runtime third-party dependency,
mean-period date generator or post hoc index repair was introduced.

The package changes the owner module, root/facade/Vedic curation, facade
reader wrapper, strict models/service/serializer/router/tag description,
three focused test files and the public surface audit. Canonical API/REST,
Home, P9-01 design/ledger and remaining-work register point here. Existing
Panchanga/daily computations and astronomical/native substrate are unchanged.

### Daily foundation publication receipt

Before this extension, VED-015 and the backlog supersession documents were
published with wiki first: wiki `4c12d88b9825d562be38f7d3b67c37a703449735`,
engine `0b34f22841eb6b5f7dace9128b4d01cc11c480d3`. Both exact remote refs were
verified. Later source publication still does not imply release/deployment.
