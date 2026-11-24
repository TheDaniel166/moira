# Ayanamsa Doctrine Standard

Version: 0.2 (draft)<br>
Date: 2026-11-24<br>
Status: implemented (Phases A–D and Python Galactic anchors)<br>
Scope: `moira/ayanamsa_doctrine.py`, the doctrinal branch of
`moira/sidereal.py`, `moira/galactic_ayanamsa.py`, and REST admission of the
previously supported doctrinal families

Research basis:
`wiki/05_research/fixed_stars/AYANAMSA_ANCHORS_IN_ORIGINAL_TEXTS.md` (original
texts, Pingree & Morrissey 1989, Kharegat 1895) and
`wiki/05_research/fixed_stars/STAR_ANCHORED_AYANAMSA_DOCTRINE.md`.

---

## 1. Problem

Moira computes every ayanamsa, but the result does not say what kind of
claim a system makes. The research shows three layers that are easily
conflated:

- **Verse:** the texts start the zodiac at the end of the Revatī *segment*
  (Sūrya Siddhānta i.27), count from an epoch, and give star positions in
  *polar* longitude (Grahalāghava 11.2 says so in the verse).
- **Commentary:** commentators of about 1600 (Raṅganātha, Mallāri) find the
  zero point by sighting the Revatī star on a polar-axis ring and say the
  star positions must be re-observed in other periods. Oscillating
  precession rules come from commentators (Parameśvara, Sūryadeva).
- **Modern convention:** the "True" modes hold a star at a fixed *ecliptic*
  longitude. Their target values come from particular texts (Citrā 180° and
  Revatī 359°50′ from the Sūrya Siddhānta alone) or from none (Mūla 240°).

The standard covers (A) provenance, (B–D) the three textual families, and
the typed Galactic anchor conventions in §2.5.

## 2. Governing objects

### 2.1 Provenance record (Phase A)

`AyanamsaDoctrine` is a passive, immutable record per system:

| Field | Meaning |
|---|---|
| `system` | the system's name |
| `family` | `epoch_polynomial`, `star_anchored_ecliptic`, `textual_formula`, `polar_star`, `trepidation_reconstruction`, `galactic_anchor`, or `user_defined` |
| `layer` | `modern_convention`, `verse`, `commentary`, `reconstruction`, or `user_supplied` |
| `definition` | one sentence stating what is held fixed |
| `anchor_star`, `anchor_identification` | star catalogue name and identification where applicable. Galactic records use `anchor_identification` for the compact source or plane |
| `anchor_target_deg`, `anchor_coordinate` | the target and its `ecliptic`, `polar`, or `galactic_node` coordinate, where applicable |
| `identification_certainty` | `beyond_doubt`, `in_doubt`, `conventional`, or none (Pingree & Morrissey 1989, Tables 5, 7–8) |
| `attestations` | the textual values for this star: source, date, value, coordinate, latitude |
| `zero_epoch` | the stated zero year, where one exists |
| `sources`, `caveats` | citations and plain-language limits |

`ayanamsa_doctrine(system)` returns the record for a named system or a
doctrinal value. `AyanamsaComputationTruth` gains `doctrine_family`,
`doctrine_layer` and `doctrine_terms` (the family's resolved parameters, such
as the Śaka year or the libration phase), so every computed value says what it
is. The REST systems list carries the record.

### 2.2 Grahalāghava formula (Phase B)

Gaṇeśa, Grahalāghava (1520) 2.7: *atha vedābdhyabdhyūnaḥ kharasahṛtaḥ śako
'yanāṃśāḥ*, "the Śaka year less 444, divided by 60, gives the ayanāṃśa".

    A(S) = (S − 444) / 60 degrees

No star is involved. The verse takes a year number. Moira's date mapping,
stated in the result:

- **Year number.** The year that begins in the spring of Common Era year `Y`
  is numbered `Y − 77` under `year_convention="current"` (default; Mallāri
  glosses the year as *vartamāna*, current) or `Y − 78` under `"elapsed"`.
- **Year boundary.** A year begins when the mean tropical Sun reaches that
  year's own ayanamsa, `A(S)`: the system's mean Meṣa saṅkrānti. The mean Sun
  is `L0 = 280.46646 + 36000.76983 T` (Meeus, *Astronomical Algorithms*,
  25.2), already used by `moira.coordinates`. This boundary is a Moira
  reconstruction: the verse names no boundary.
- **Stepping.** `stepping="annual"` (default) holds `A(S)` for the whole year,
  as the text does. `"continuous"` interpolates linearly between consecutive
  boundaries; it is a documented smoothing.
- **Mode.** `"mean"` returns the formula value against the mean equinox;
  `"true"` adds nutation in longitude Δψ, as every polynomial system does, so
  sidereal longitudes stay free of nutation.

Checks: Śaka 1534 → 18°10′ (Viśvanātha), 1809 → 22°45′ (Dikshit), 1920 →
24°36′ (Rao & Uma).

### 2.3 Siddhantic polar star (Phase C)

A star held at a fixed **polar longitude of date**: the longitude of the
ecliptic point on the star's hour circle (Ranganātha on SS viii.12; Gaṇeśa
11.2). This is Raṅganātha's "re-observe" doctrine computed for every date.

Derivation. A point on the ecliptic at longitude `λp` has right ascension `α`
with `tan α = tan λp cos ε`. The star at ecliptic `(λ, β)` has
`tan α = (sin λ cos ε − tan β sin ε) / cos λ`. Equating the right ascensions:

    λp = atan2(sin λ cos ε − tan β sin ε, cos λ cos ε)

with `ε` the obliquity of date. `λp = λ` when `β = 0`. The ayanamsa is
`λp(star, date) − target`.

Values, from the original texts only:

| Nakṣatra | Star (catalog) | Sūrya Siddhānta | Grahalāghava | Certainty |
|---|---|---|---|---|
| Aśvinī | β Ari (Sheratan) | 8° | 8° | beyond doubt |
| Puṣya | δ Cnc (Asellus Australis) | 106° | 106° | beyond doubt |
| Citrā | α Vir (Spica) | 180° | 183° | in doubt (α or 76 Vir) |
| Mūla | λ Sco (Shaula) | 241° | 242° | in doubt (λ Sco or 45 Oph) |
| Revatī | ζ Psc (Revati) | 359°50′ | 0° | beyond doubt, dim |

`PolarStarAyanamsa(source, nakshatra, star_product="astrometric")`. The star
product follows the star-technique policy (FIXED_STARS_BACKEND_STANDARD.md
§5.0): astrometric by default, apparent as a choice. `mode="true"` uses the
true ecliptic and obliquity of date; `"mean"` removes Δψ from the star's
longitude and uses the mean obliquity (the true and mean ecliptics of date
share one plane, so this is exact).

A companion `siddhantic_polar_to_ecliptic(dhruvaka, vikshepa, obliquity)`
reduces a catalogue entry to ecliptic coordinates (the inverse construction,
used to reproduce the texts' internal frame with their 24° obliquity).

The polar family is a typed value, not a set of `Ayanamsa` names: the
`UserDefinedAyanamsa` admission criteria require a demonstrated user
community for a named constant, which these modes lack.

### 2.4 Trepidation reconstructions (Phase D)

Both are oscillating rules, stated as reconstructions with every choice
named.

**Sūrya Siddhānta libration** (iii.9–10; libration reading in Parameśvara
1432 and Raṅganātha 1603). Phase in revolutions
`φ = cycles × D / 1,577,917,828`, where `D` is days since the Kali epoch
(JD 588465.5, midnight 17/18 February 3102 BCE) and 1,577,917,828 is the Sūrya
Siddhānta's civil days per Mahāyuga. The doḥ (`bhuja`) of `φ` times 3/10 gives
the magnitude, at most 27°. Sign: negative in the first half-cycle, positive
in the second. The 600-cycle reading puts zero at Kali 3600 (499 CE) and
reproduces Burgess's worked value, 20°24′38.67″ for 1 January 1860, which
fixes the sign and phase. `cycles_per_mahayuga` is 600 (Raṅganātha; default)
or 30 (the reading Bhāskara II reports).

**The ±24° rule** (quoted by Sūryadeva Yajvan, born 1191, from unnamed
authors; not in the Āryabhaṭīya). Kali years `K = D / 365.25868…` (the
Āryabhaṭa year, 1,577,917,500 days per Mahāyuga). With
`x = (K − 3600) mod 5808`, the bhuja-years are reduced into quadrants of
1,452 years and times 2/121 give degrees: at most ±24°, zero at Kali 3600,
positive in the first half-cycle. The result is attributed to the
commentarial tradition, never to Āryabhaṭa.

Both use JD days as civil days. A different epoch hour moves the value by
less than 0.2″ per day.

### 2.5 Galactic anchors

`GalacticAyanamsa(preset)` is an immutable Python selection accepted by the
scalar, computation-truth, longitude conversion, and nakshatra APIs. The
public `jd` is UT. The sidereal engine converts it once to TT. This technique
uses the IAU 2006 P03 bias–precession and obliquity pair and admits TT dates
within ±50 Julian centuries of J2000, inclusive.

| Preset ID | Anchor | Sidereal target |
|---|---|---:|
| `centre_sagittarius` | Sgr A* ecliptic longitude | 240° |
| `centre_gil_brand` | Sgr A* ecliptic longitude | `210° + 90° × (3 − √5) / 2` |
| `centre_cochrane` | Sgr A* ecliptic longitude | 270° |
| `centre_wilhelm` | Ecliptic point at Sgr A*'s right ascension | 246°40′ |
| `centre_mid_mula` | Sgr A* ecliptic longitude | 246°40′ |
| `equator_allwise_2024` | AllWISE 2024 plane node | 240° |
| `equator_liu_2011` | Liu–Zhu–Zhang 2011 plane node | 240° |
| `equator_liu_2011_mid_mula` | Same 2011 node, with the opposite node at 6°40′ Gemini | 246°40′ |

The centre presets use `sagittarius_a_star` from `moira.cosmic_references`,
the SIMBAD-backed physical compact-source direction at J2000. Its position is
held fixed in ICRS, with precession and, in true mode, nutation applied to the
frame. The geometric calculation uses zero proper motion and includes neither
annual aberration nor observer effects. The formal Galactic longitude origin
and the Shaula anchor of `True Mula` have their own identities.

For `mean`, reduce the chosen direction in the mean frame of date. For `true`,
rotate it into Moira's IAU 2006/2000A true equatorial frame and use true
obliquity. Wilhelm uses the same polar-longitude construction as §2.3, applied
to Sgr A* with the selected frame and obliquity. For the plane presets, orient
the ecliptic intersection as `north_ecliptic × north_galactic`. In ecliptic
axes this is `(-pole_y, pole_x, 0)`. This orientation selects the Sgr A* side
at J2000 and continues through other dates without a longitude-based switch.

Subtract the sidereal target from the effective anchor's tropical longitude.
The scalar and `ayanamsa_unwrapped_deg` retain the signed difference, such
as −3.148285° for Cochrane at mean J2000. `ayanamsa_deg` reduces that value
modulo 360. A missing catalogue identity or undefined intersection raises an
error. The computation truth records the effective longitude and target,
preset ID, projection, coordinate authority, fixed source epoch and equinox.
For Wilhelm it also records the direct ecliptic longitude and the applied
polar longitude. In true mode `nutation_longitude_deg` reports the term used
in the frame rotation, which is an input to the hour-circle projection.

The 2011 presets use RA 192.9029799920833°, Dec +27.1031092144444° in ICRS,
the proposed pole closest to the transformed 1958 pole whose plane goes
through Sgr A*. AllWISE uses the empirical pole RA 192.936°, Dec +26.602°,
derived from its equatorial node and inclination, with respective reported
uncertainties of 0.055° and 0.032°. At mean J2000, AllWISE gives 30.363342° at
the 240° target, 20.407′ above the transformed 1958 solution. These selected
planes are technique inputs. Moira's Galactic coordinates follow their own
[backend standard](GALACTIC_BACKEND_STANDARD.md).
[Liu, Zhu & Zhang 2011, §4](https://arxiv.org/html/1010.3773) ·
[Liu et al. 2024, equations (30) and (35)](https://doi.org/10.3847/1538-3881/ad6dd5)

The target conventions have independent provenance. Gil Brand gives the
golden-section construction and Cochrane describes his Capricorn setting.
Astrodienst documents Koch's 0° Sagittarius setting, the Dhruva hour circle,
and the 0° Sagittarius and mid-Mūla node conventions. Wilhelm's 2001 custom
offset of 20°11′11″ is within five arcseconds of the direct mean J2000
mid-Mūla construction. The direct and Dhruva constructions differ by about
8′24″ at that epoch. This supports the direct selection under its descriptive
name. Usha–Shashi's calculation rule remains unverified from the original
lesson. [Gil Brand](https://www.astrologie-zentrum.net/index.php/de/publikationen?catid=8&id=5%3Aumrechnung&view=article) ·
[Cochrane](https://www.astrosoftware.com/cpnew/a_and_v/ayanamsha.html) ·
[Astrodienst, §§2.8.7–2.8.8](https://www.astro.com/swisseph/swisseph.htm) ·
[Wilhelm's 2001 correspondence](https://www.indiadivine.org/content/topic/1178279-ayanamsha-and-galactic-center/)

```python
from moira.galactic_ayanamsa import GalacticAyanamsa
from moira.sidereal import ayanamsa_with_truth

truth = ayanamsa_with_truth(jd_ut, GalacticAyanamsa("equator_allwise_2024"), mode="mean")
```

### 2.6 Galactic alignment epoch recipes

Both recipes supply a J2000 reference to `UserDefinedAyanamsa`. Use
`mode="mean"` to reproduce the stated epoch offsets. Dates away from the
anchor use Moira's IAU 2006 general precession.

- **Mardyks / Skydram.** Adopt the documented 30° at the September equinox of
  1998 as a mean offset. The USNO lists 23 September, 05:37 UT, to the minute.
  Treat that time as UTC at the published resolution. With TT − UTC = 63.184 s,
  subtract Moira's general precession at the resulting TT from 30° to get
  `UserDefinedAyanamsa(reference_value_j2000=30.017793882)`. Astrodienst
  documents the exact 30° convention and cites the 1991 article and later
  correspondence. The original article text remains unchecked.
  [Astrodienst](https://www.astro.com/swisseph/swisseph.htm) · [USNO seasons](https://aa.usno.navy.mil/data/Earth_Seasons)
- **Fiorenza.** Adopt `UserDefinedAyanamsa(reference_value_j2000=25.0)`, his
  epoch-2000 value for a nominal node at 5° Sagittarius. From this reference,
  Moira gives 24°18′06″ at Julian epoch 1950.0, about 10″ below Fiorenza's
  table value of 24°18′16″. [Fiorenza's article and table](https://www.scribd.com/doc/170809282/Sidereal1)

## 3. Ambiguity policy

- No family guesses a missing choice. Every textual ambiguity is a named
  parameter with a stated default and source, reported in `doctrine_terms`.
- Existing named systems keep their values, names and paths. Their records
  state their layer; the "True" modes are labelled modern ecliptic
  conventions.
- Downstream surfaces that need a named system (certified Gochara windows,
  Muhurta search, Kalachakra, REST Gochara/Muhurta) refuse a doctrinal value
  with a clear error; they do not convert it silently.

## 4. Validation

| Object | Evidence class | Check |
|---|---|---|
| Provenance records | invariant | every `Ayanamsa.ALL` system has one; star, target and product agree with the computing tables |
| Grahalāghava | authority (published worked values) | Śaka 1534, 1809, 1920; boundary continuity; annual step = 1′ |
| Polar longitude | authority (ERFA) | star right ascension of date from ERFA, `λp = atan2(sin α, cos α cos ε)`; five stars, four epochs, at most 0.00001″ (tolerance 0.001″) |
| Polar reduction | authority (Burgess) and invariant | Citrā 180°/2°S at 24° → 180°49′/1°50′S; round trip |
| SS libration | authority (Burgess) | 20°24′38.67″ at JD 2400410.5; reproduced to 0.0003″ (tolerance 0.01″) |
| ±24° rule | invariant | zero at Kali 3600; ±24° at the quadrant years; period 5,808 years |
| Galactic anchors | authority (ERFA) and invariants | eight presets, both modes, eight Julian TT epochs from 1600 to 2400 and both P03 bounds, 160 frame/projection checks. Maximum circular residual 0.000436″ (tolerance 0.001″). Checks include plane membership, node orientation, polar projection, and existing public conversions. This measures numerical agreement at the sampled dates and fixed source parameters |
| Galactic alignment epoch recipes | invariant and source comparison | Skydram reproduces 30° at the adopted equinox minute and Fiorenza reproduces 25° at J2000 with Moira's mean precession policy |
| REST | contract | requests with `ayanamsa_doctrine`; mutually exclusive with a named system |

Tests: `tests/unit/test_ayanamsa_doctrine.py`,
`tests/integration/test_ayanamsa_polar_erfa.py`,
`tests/unit/test_galactic_ayanamsa.py`,
`tests/integration/test_galactic_ayanamsa_erfa.py`,
`tests/server/test_server_ayanamsa_doctrine.py`.
