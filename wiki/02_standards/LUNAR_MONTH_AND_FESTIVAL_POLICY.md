# Lunar-month and festival policy surface — VED-023/024

**Date:** 6 October 2026.
**Owners:** [lunar-month engine](../../moira/lunar_month.py), [facade](../../moira/_facade_vedic.py), [request/response](../../moira_server/models/lunar_month.py), [service](../../moira_server/services/lunar_month.py), [serializer](../../moira_server/serializers/lunar_month.py), [router](../../moira_server/routers/panchanga.py).
**Status:** Bounded lunar-month implementation and festival research/admission policy. A universal festival calendar is not admitted.

The user explicitly selected festivals and lunar-month rules after Daily
Panchanga, and authorized source publication. These are separate products
from [VED-015](DAILY_PANCHANGA_STANDARD.md). An astronomical lunation is not
a sunrise-owned civil day, a regional month date, an era year or a selected
observance. Each result must identify which object it actually computes.

## 1. Source audit and decisions

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
adjustment of surrounding months in omission years. Moira presently retains
that astronomical evidence without claiming the full regional adjustment.

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
| Exceptional Purnimanta | `unsupported_intercalation`; null selected bounds/label and retained three-lunation evidence. This intentionally includes a conservative surrounding-month exclusion. |
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

## 5. Festival policy that must govern later admission

The following is Moira's proposed admission/transport contract, not a claim
that the sources above establish every rule. VED-024 currently evaluates as
`defer_for_source_completion`: an evidence packet and explicit admission
decision are present; named festival calculation is not yet admitted.

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

Suggested sequencing: complete exceptional month mapping first; establish
source-owned ritual window primitives; then admit a small catalogue with a
catalogue endpoint and bounded evaluation route together. Ekādaśī needs its
complete selected exceptional-case and pāraṇa doctrine before a claimed
fasting calendar. Janmāṣṭamī, Dīpāvalī, Śivarātri and regional solar festivals
must each receive independent rule packets. None is automatically admitted
by having a matching tithi or a date in PAC's list.

## 6. Verification and remaining boundary

Validation files:

- [analytic and assembly tests](../../tests/unit/test_lunar_month.py);
- [DE441 and PAC comparisons](../../tests/integration/test_lunar_month.py);
- [strict request/OpenAPI and HTTP parity](../../tests/server/test_server_lunar_month.py);
- existing public export audit, Vedic surface/facade and Panchanga neighbours.

The first focused run passed 82 cases and found one failed proposed
one-minute solar-ingress comparison. The 15 June 2026 ingress is about
64.5 seconds later than PAC's printed 12:53 IST. That residual remains unresolved and must not be described as passing
one-minute authority validation. At the printed instant, true-mode solar
longitude is 2.56435 arcseconds short of the boundary; mean mode is 4.75016
arcseconds beyond it. A simple mode substitution does not reconcile the
source. Independent root-side witnesses pass. The residual is now retained
as a separately classified diagnostic regression (64.4768 seconds, 0.1-second
regression bound), not a loosened institutional acceptance threshold. Three published conjunction timings and the selected month
labels are separate comparisons. A root bracket of 0.1 seconds does not
establish PAC reduction agreement.

Era years, regional solar civil dates, exceptional Purnimanta labeling,
Kshaya-year regional relabeling and a named festival catalogue remain open.
No website adoption, deployment, release, native calendar port or predictive
validity claim follows from this implementation. The bounded implementation is ready for source publication; remaining
source/exceptional-rule work remains open in VED-023/024.

### Verification receipt

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
