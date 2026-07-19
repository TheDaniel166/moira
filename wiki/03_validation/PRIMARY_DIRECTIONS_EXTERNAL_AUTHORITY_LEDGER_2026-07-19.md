# Primary Directions External-Authority Ledger

## 1. Record status

- **Record date:** 2026-07-19
- **Scope:** narrow external numerical evidence for Campanus,
  Topocentric, zodiacal fixed-star, reflected-point, Ptolemaic-parallel,
  Placidian rapt-parallel, and Morinus aspect-context branches
- **Authority fixtures:**
  `tests/fixtures/primary_directions_campanus_topocentric_authority.json`,
  `tests/fixtures/primary_directions_special_target_authority.json`, and the
  corrected source labels in
  `tests/fixtures/primary_directions_ptolemy_examples.json`
- **Executable comparisons:**
  `tests/unit/test_primary_direction_campanus_topocentric_authority.py`,
  `tests/unit/test_primary_direction_special_target_authority.py`, and
  `tests/unit/test_primary_direction_ptolemy.py`
- **Purpose:** state exactly which published products the executable corpus
  compares, which checks are only internal invariants or regression evidence,
  and which branches remain unevaluable.

The evidence below is deliberately product-specific. A published worked
example can attest its named low-level law without validating every method,
target family, motion doctrine, epoch, or public search combination that uses
that law.

## 2. Evidence classes

This ledger keeps the following evidence classes separate:

- **External authority validation:** a current computation is compared with a
  numerical fact from an original or method-origin source under named input
  and product semantics.
- **External published-example comparison:** a later published worked example
  supplies the external numerical fact. This is useful external evidence, but
  is not silently promoted to a primary historical authority.
- **Cross-engine corroboration:** a secondary reconstruction or independent
  software calculation corroborates an original historical row.
- **Secondary-source corroboration:** a modern technical derivation or
  calculator adaptation supplies a bounded worked example.
- **Invariant or regression evidence:** Moira is compared with its own formula,
  branch rule, prior fixture value, engine result, or transport serialization.
  This detects drift and proves internal consistency; it is not external
  astronomical or historical validation.

The corpus-schema tests, the `1e-12` Campanus/Regiomontanus conjunction
agreement, the internal contra-parallel sign test, and direct-engine-versus-REST
parity all belong to the last class. They do not widen the external evidence
recorded below.

## 3. Campanus and Topocentric source-law evidence

The Campanus/Topocentric fixture preserves printed equatorial inputs rather
than silently substituting a modern reconstruction of the natal charts.

### 3.1 Campanus-Regiomontanus mundane conjunction

Bob Makransky's worked Prince Charles example directs the Sun as promissor to
Mercury as significator in mundo. The tested object is the narrow conjunction
law shared by the Campanus and Regiomontanus paths: form the significator pole,
place both objects under that pole, and subtract the significator's `W` from
the promissor's `W`.

| Quantity (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Significator pole | 21.27 | 21.266884721880288 | 0.03 |
| Significator `W` | 210.41 | 210.405005826081 | 0.03 |
| Promissor `W` under significator pole | 222.58 | 222.57942742883125 | 0.03 |
| Signed direct arc | 12.17 | 12.174421602750243 | 0.03 |

The source prints inputs and results to `0.01` degree. A complete
`+/-0.005`-degree corner sweep of the printed inputs places the reconstructed
arc in `[12.15846, 12.19038]` degrees; the `0.03`-degree gate encloses that
rounding domain. The exact equality of Moira's Campanus and Regiomontanus
results at `1e-12` is a separate internal invariant. This row does **not**
validate the wider Campanus mundane-aspect family.

### 3.2 Polich oblique ascension under a named pole

Vendel Polich's origin-text example supplies an eastern oblique ascension for
an ecliptic point at longitude `165.02666666666667` degrees, zero latitude,
under pole `51.53333333333333` degrees and obliquity
`23.439166666666665` degrees.

| Quantity (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Eastern oblique ascension | 158.75 | 158.74082783607466 | 0.02 |

The published result is tabular and printed to one arcminute. The
`0.02`-degree gate allows `1.2` arcminutes for printed-table interpolation and
rounding. It attests this named under-the-pole operation, not a complete chart
or every Topocentric direction.

### 3.3 Topocentric zodiacal aspect under the significator pole

Makransky's worked example uses Saturn as significator and a zero-latitude Moon
trine point as promissor. The tested signed object is again promissor `W` under
the significator pole minus significator `W`.

| Quantity (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Significator pole | 29.89 | 29.896316011196287 | 0.02 |
| Significator `W` | 151.26 | 151.26140957829284 | 0.02 |
| Promissor `W` under significator pole | 145.89 | 145.89100748389953 | 0.02 |
| Signed primary-motion arc | -5.37 | -5.370402094393285 | 0.02 |

The source prints equatorial inputs and results to `0.01` degree. A complete
`+/-0.005`-degree input corner sweep places the signed arc in
`[-5.38644, -5.35436]` degrees; the `0.02`-degree gate encloses that domain.

#### Motion-convention boundary

The source labels the `-5.37`-degree result **converse**. Moira's ordered raw
result is `354.6295979056067` degrees, whose signed circular form is the
source-matching `-5.370402094393285` degrees, but Moira's current
role-exchanged converse result is `5.4084796290214285` degrees. This is a
documented convention mismatch: the source is classifying the sign of primary
motion, while the admitted Moira converse doctrine exchanges promissor and
significator roles. The source-law comparison passes; public motion-label
parity is not claimed, and this ledger does not describe that doctrine gap as
fixed.

## 4. Special-target external comparisons

### 4.1 Lilly/Kolev Vega zodiacal projection to the Ascendant

The fixture converts Lilly's 1616-09-19 Julian chart date to
1616-09-29 Gregorian, reconstructs the stated UT1-proxy instant, resolves Vega
through Moira's sovereign star engine, explicitly suppresses the resolved
stellar latitude, and directs the resulting zodiacal point to the Ascendant by
the admitted Ptolemaic semi-arc law. This is a historical zero-latitude
zodiacal product, not a modern astrometric oracle for Lilly's catalog.

| Comparison (degrees) | Published/reconstructed | Moira | Absolute gate |
|---|---:|---:|---:|
| Vega longitude, Lilly | 280.0 | 279.94671064908306 | 0.06 |
| Direction arc, Lilly | 3.2333333333333334 | 3.15867227080156 | 0.10 |
| Vega longitude, Kolev reconstruction | 279.96666666666664 | 279.94671064908306 | 0.03 |
| Direction arc, Kolev reconstruction | 3.1666666666666665 | 3.15867227080156 | 0.02 |

The Lilly residuals are `0.05328935091694` degrees (`3.1974` arcminutes) in
longitude and `0.07466106253177` degrees (`4.4797` arcminutes) in arc. The
round-number `0.06`/`0.10` gates enclose those historical-catalog and chart-
reconstruction residuals; they are cross-model regression envelopes, not
uncertainty estimates. The Kolev residuals are `0.01995601758358` degrees
(`1.1974` arcminutes) and `0.00799439586511` degrees (`0.4797` arcminutes);
the `0.03`/`0.02` gates enclose the minute-printed reconstruction. Because the
complete computational inputs depend on Kolev's reconstruction, the effective
evidence class is cross-engine corroboration even though Lilly remains the
original authority for his published row.

### 4.2 Lilly Jupiter antiscion to the Ascendant

This row reflects Lilly's Jupiter longitude across the Cancer-Capricorn axis,
assigns zero latitude, and directs the antiscion to the Ascendant.

| Quantity (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Reflected longitude | 278.0833333333333 | 278.0833333333333 | 0.02 |
| Direction arc | 1.4 | 1.377903256028162 | 0.03 |

The reflection is exact at the stored precision. The arc residual is
`0.02209674397184` degrees (`1.3258` arcminutes); the `0.03`-degree gate
encloses the minute-printed historical/reconstruction residual. This is
external authority validation of the named planetary, zero-latitude antiscion
product only.

### 4.3 Sepharial Ptolemaic zodiacal parallel

Sepharial's illustration selects the Cancer ecliptic point whose declination
equals Uranus's published north declination (`23` degrees `24` arcminutes).
The branch-selecting longitude is explicit; it is not presented as Uranus's
radical longitude.

| Quantity (degrees) | Published | Moira/source arithmetic | Absolute gate |
|---|---:|---:|---:|
| Declination-equivalent longitude | 94.0 | 93.22323381173652 | 1.0 |
| Arc from the two published rising sidereal times | 80.5 | 80.5 | 1e-9 |

The source rounds the equivalent point to a whole degree, which governs the
`1.0`-degree longitude gate. The arc check is exact arithmetic over the two
published sidereal times, not a separate end-to-end direction search. This row
validates a parallel, not a contra-parallel.

The corrected Saturn row in
`primary_directions_ptolemy_examples.json` likewise preserves the source's
`6` degrees `54` arcminutes **south** declination and labels the projection a
parallel. Moira computes `342.4210029835662` degrees against the published
`342.6166666666667` degrees under the existing `0.25`-degree printed-table
gate; published rising-time arithmetic gives `11.5` degrees. The source calls
this Saturn to the Sun's place and never identifies it as a contra-parallel.

### 4.4 Leo/Griscti Placidian rapt parallels

The direct example uses Saturn's diurnal and the Moon's nocturnal semi-arcs
with the Moon taken by opposition in right ascension. The converse example
uses the source's forward converse construction.

| Product (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Direct rapt-parallel arc | 37.7 | 37.697679078635076 | 0.02 |
| Converse rapt-parallel arc | 36.86666666666667 | 36.86546721498743 | 0.02 |

The residuals are `0.00232092136492` degrees (`0.1393` arcminute) and
`0.00119945167924` degrees (`0.0720` arcminute). The `0.02`-degree gates allow
for the minute-rounded source inputs. These rows are secondary-source
corroboration through a modern calculator adaptation, not primary validation
from a page- and glyph-correlated Placidus transcription.

### 4.5 Borealis Morinus aspect context

The executable modern example starts from Jupiter at longitude
`203` degrees `34` arcminutes and latitude `+1` degree `10` arcminutes,
departing a northern maximum latitude of `1` degree `34` arcminutes. It applies
a positive `60`-degree sinister sextile along the Morinus aspect circle.

| Quantity (degrees) | Published | Moira | Absolute gate |
|---|---:|---:|---:|
| Projected longitude | 263.55 | 263.5517101359027 | 0.2 |
| Projected latitude | -0.3333333333333333 | -0.32207177424366357 | 0.2 |

The residuals are `0.0017101359027` degrees (`0.1026` arcminute) and
`0.01126155908967` degrees (`0.6757` arcminute). The conservative
`0.2`-degree gates are cross-source envelopes for a minute-rounded secondary
example, not claimed uncertainties. The worked equations use `60` degrees; a
closing prose reference to `30` degrees is treated as a source typo. This
single sextile does not externally validate quadrant continuation through
squares, trines, or opposition.

## 5. Explicitly unevaluable or deferred branches

No synthetic expected values are assigned to these branches:

| Branch | Why current evidence is insufficient | Evidence required |
|---|---|---|
| Fixed star, true latitude in mundo | Lilly's Vega row suppresses latitude; Vega proper is circumpolar in the reconstructed chart. | A named non-circumpolar star, epoch, complete chart geometry, true-latitude doctrine, and published arc. |
| Fixed star to planet | Accessible Lilly/Kolev rows do not provide a complete independently reproducible historical star coordinate set. | Page-correlated star identity/coordinates, chart geometry, latitude doctrine, significator coordinates, and published arc. |
| Node- or angle-sourced antiscia | The recovered Lilly corpus supplies planetary antiscia only. | An original worked direction explicitly reflecting a node or angle. |
| Antiscia `cum latitudine` | Lilly's latitude-aware doctrine differs from Moira's admitted zero-latitude primary-direction reflection. | A separate latitude-aware public doctrine and source-matched tests. |
| Ptolemaic contra-parallel | The recovered Sepharial Saturn row is explicitly south declination but is not labeled contra-parallel. | A published worked example that names the contra-parallel and supplies hemisphere and branch semantics. |
| Placidian rapt parallel from a primary text | Executable rows come from the Leo/Griscti adaptation. | A complete page-correlated Placidus transcription with identities, semi-arcs, RAs, meridian distances, and arc. |
| Morinus primary-source aspect context | The executable Churchill row is a modern derivation; Morin Book XXII has not been numerically transcribed. | A page-correlated primary-text example or licensed authoritative translation. |
| Morinus quadrant continuation | The published sextile remains on one arctangent branch. | Published worked values beyond the principal branch at square, trine, or opposition. |
| Wider Campanus mundane aspects | The Makransky row is a conjunction using the law shared with Regiomontanus. | Published Campanus-specific aspect examples with complete inputs. |
| Topocentric public motion labels | The signed-primary-motion and role-exchange converse doctrines give different positive magnitudes. | An explicit doctrine decision and separately validated public semantics; the present source-law result alone is insufficient. |

Internal unit tests do exercise node/angle reflections, contra-parallel
negation, Morinus quadrant continuity, fixed-star-to-planet paths, and wider
policy composition. Those remain invariant or regression evidence until the
external products named above are available.

## 6. Sources and rights/provenance

- Bob Makransky, *Primary Directions: A Primer of Calculation*, parts
  [1](https://www.scribd.com/document/48191844/Bob-Markansky-Primary-Directions-1)
  and
  [2](https://www.scribd.com/document/41581638/Makransky-primarydirections-2),
  Dear Brutus Press, 1988, ISBN `0-9677315-0-X`. The repository stores only
  minimal bibliographic metadata and numerical facts, not scans or substantive
  prose.
- Vendel Polich, *The Topocentric System*, translated by Jose M. Lebron,
  Editorial Regulus, 1975
  ([hosted scan](https://www.scribd.com/document/761716895/Polich-Vendel-The-Topocentric-System)).
  The repository stores only minimal bibliographic metadata and numerical
  facts.
- William Lilly, *Christian Astrology*, 1659, pp. 765-768
  ([public-domain scan](https://en.wikisource.org/wiki/File:Christian_Astrology_(Lilly,_1659).djvu)).
  The fixture cites original numerical facts and does not reproduce page
  images.
- Rumen Kolev, *William Lilly and His Method of Primary Directions*, 1998
  ([hosted PDF](https://babylonianastrology.com/downloads/Lilly1.pdf)). The
  hosted PDF does not state a license; the fixture retains only limited
  numerical facts and a citation.
- Sepharial, *Directional Astrology*, chapter X, 1921
  ([hosted excerpt](https://astroamerica.com/primary.pdf)). The underlying
  United States pre-1929 work is public domain; the host URL is retained for
  provenance.
- Alan Leo, calculator adaptation by Jane Griscti, *Primary Directions*, 2010
  ([hosted PDF](https://maestrosdelsaber.com/wp-content/uploads/ftp-files/Astrologia/Astro%20a%20Leo%2C%20Alan/Astro%20Leo%2C%20Alan%20-%20Primary%20Directions.pdf)).
  The adaptation bears a copyright notice; only limited numerical facts and a
  citation are retained.
- Alexey Borealis, *A Circle of Mundane Aspects*, 2024
  ([technical article](https://morinus-astrology.com/circle-of-aspects/)). The
  site does not state a license; only limited numerical facts and a citation
  are retained.
- Jean-Baptiste Morin, *Astrologia Gallica*, 1661, Book XXII, Section II,
  Chapters 2-3
  ([ETH Bibliothek scan](https://www.e-rara.ch/download/pdf/1871945.pdf),
  [DOI](https://doi.org/10.3931/e-rara-1874)). The scan carries the Public
  Domain Mark. It is currently provenance for a deferred primary-source
  comparison, not an executable numerical oracle.

No third-party scan or long source passage is bundled in these fixtures.

## 7. Executed evidence receipt

With downloads disabled and strict known-issue expiry enabled, the focused
authority slice was executed through the project Python 3.14 environment:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_primary_direction_campanus_topocentric_authority.py `
  tests\unit\test_primary_direction_special_target_authority.py -q
```

Result: `12 passed`. This receipt exercises the exact fixture products and
internal visibility covenants described above. It does not run a live network
oracle, reconstruct every historical chart, validate the additive REST
vessels, or turn the listed deferrals into supported branches.

## 8. Supportable statement

> Moira now has externally anchored, product-specific numerical evidence for
> one shared Campanus-Regiomontanus mundane conjunction law, two Topocentric
> under-the-pole laws, one historical zero-latitude Vega direction, one
> planetary antiscion, one Ptolemaic parallel, direct and converse Placidian
> rapt-parallel examples, and one Morinus sextile projection. The evidence
> classes and model differences remain explicit. It does not establish full
> method-family parity, primary-source coverage for every special target, or
> agreement between the source's signed-motion label and Moira's current
> role-exchange converse doctrine.
