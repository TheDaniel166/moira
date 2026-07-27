# Hellenistic Source Validation and Admission Audit

Date: 2026-07-26
Scope: Moira C++ repository, Python-governed astrology engine and FastAPI
transport; website implementation is excluded from this gate.

## Outcome

Phase 6 replaces broad historical completion language with evidence-specific
claims:

- independently source-owned data now guards Dorothean triplicity rulers,
  planetary joy houses, all four admitted bounds doctrines, the ordinary
  Chaldean face cycle, the four lots selected by the unified profile, admitted
  Decennial L1/L2 arithmetic, and two disputed Zodiacal Releasing cases;
- runtime generation now inventories the actual engine anchors, curated import
  identities, route registrations, request schemas, and response schemas;
- supporting classical endpoints are explicitly distinguished from the
  dedicated score-free Hellenistic profile;
- Hermetic geometry, Decennial L3/L4, and interpretation are closed
  exclusions, not incomplete engine work;
- a capability being implemented does not by itself become a source-correctness
  or empirical-effect claim.

The current runtime views are:

- [generated capability matrix](HELLENISTIC_CAPABILITY_MATRIX.generated.md)
- [generated API inventory](HELLENISTIC_API_INVENTORY.generated.md)

## Evidence law

The audit uses five evidence classes:

| Evidence class | What it proves | What it does not prove |
|---|---|---|
| Independent source golden | Runtime data or arithmetic matches a datum transcribed from a named edition/witness | Astrological effects, interpretation, or an unrecorded variant |
| Source-locked literal test | A named catalog transcription matches its identified edition | Geometry not supplied by the edition |
| Policy regression | Moira consistently applies an explicit modern or disputed choice | That the choice is the only historical doctrine |
| Geometric/invariant test | Internal vessels, boundaries, dependencies, and algebra are coherent | Historical attribution or external agreement |
| Transport parity | Engine truth survives facade, serializer, REST, and OpenAPI transport | Doctrine completeness |

Every new golden records the authority, edition/location, units, interval
semantics where applicable, and numeric tolerance. The fixtures are
hand-authored and must never be regenerated from Moira output.

## Source-owned corpus

### Dorothean triplicity

Authority: Dorotheus of Sidon, *Carmen Astrologicum*, David Pingree edition and
translation (Teubner, 1976), Book I.1.

The direct table confirms:

- fire: Sun by day, Jupiter by night, Saturn participating;
- earth: Venus by day, Moon by night, Mars participating;
- air: Saturn by day, Mercury by night, Jupiter participating;
- water: Venus by day, Mars by night, Moon participating.

This re-check confirms that the corrected water triplicity currently in the
engine is source-consistent. It is not evidence for silently merging other
triplicity traditions into the named `DOROTHEAN_PINGREE_1976` doctrine.

Online witness:
[Dorotheus Book I](https://krasiancientastrology.com/wp-content/uploads/2016/11/dorotheus1.pdf).

### Planetary joys

The seven joy-house assignments are locked from Chris Brennan's 2013 source
synthesis, which identifies Paulus, Olympiodorus, Firmicus, and Rhetorius as
the primary locations:

`Mercury 1, Moon 3, Venus 5, Mars 6, Sun 9, Jupiter 11, Saturn 12`.

This evidence grade is deliberately recorded as a secondary synthesis with
identified primary locations. It locks the assignment table only; it does not
validate a strength score or interpretation.

Online witness:
[The Planetary Joys](https://library.keplercollege.org/wp-content/uploads/2022/01/the-planetary-joys.pdf).

### Bounds

Authority: Ptolemy, *Tetrabiblos* I.20/I.21, F. E. Robbins translation, Loeb
Classical Library 435 (1940):

- Egyptian table, pages 96-97;
- Chaldean construction and sect distinction, pages 100-103;
- Ptolemaic table, pages 108-109.

The golden owns both literal Egyptian/Ptolemaic tables and the complete
Chaldean construction rules. Tests check every segment and lookup boundary.
The Ptolemaic final Libra segment remains Mars because that reading alone
preserves the source-stated Saturn 57 and Mars 66 totals. Chaldean day/night
remain separate doctrines because Saturn/Mercury precedence reverses by sect.

Online witnesses:
[Robbins transcription](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/1B*.html)
and [Loeb 435 scan](https://en.wikisource.org/wiki/File:Loeb_435_-_Ptolemy_-_Tetrabiblos_by_Robbins_(1940).pdf).

### Ordinary Chaldean faces

Authority: Agrippa, *Three Books of Occult Philosophy*, Book II.37, J. F.
English translation (1651).

The source-owned datum is the repeating ruler cycle beginning at Aries zero:

`Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter`.

The witness is Renaissance, so the capability matrix labels this
`admitted_qualified`. It validates Moira's ordinary 36-face ruler cycle but
does not prove a Hellenistic date of origin and does not admit the separate
Hermetic name/star/rising family.

Online witness:
[University of Michigan EEBO transcription](https://quod.lib.umich.edu/e/eebo/A26565.0001.001/1:16.37).

### Unified-profile lots

Authority: Valens, *Anthologies*, Mark T. Riley translation:

- Fortune: II.3, annotated PDF page 119;
- Spirit/Daimon: II.22, page 170;
- Eros: IV.25 marginal note, page 396;
- Necessity: IV.25 marginal note, pages 396-397.

The golden locks projector, operand direction, night reversal, and a concrete
day/night case for only the four profile lots. The full lots catalog remains a
heterogeneous Hellenistic/medieval/modern catalog and is not promoted to a
single-authority validation claim.

Research ledger:
[Lots Source Verification](../05_research/lots/LOTS_SOURCE_VERIFICATION.md).

### Decennials L1/L2

Authority: Valens, *Anthologies* VI.6-8, Riley annotated PDF pages 494-502.

The golden locks:

- the 10-year, 9-month / 129-month major period;
- the minor-period units
  `Saturn 30, Jupiter 12, Mars 15, Sun 19, Venus 8, Mercury 20, Moon 25`;
- the 30-day symbolic month;
- the source sequence rule beginning from the admitted apheta and continuing
  in increasing zodiacal longitude.

Moira preserves that symbolic distribution coordinate separately from its
elapsed-Julian-day projection. The golden does not admit Decennial L3/L4.

### Zodiacal Releasing

Authority: Valens, *Anthologies* IV.4, Riley annotated PDF pages 329-333.

The source fixture owns two disputed cases:

- when Spirit and Fortune share a sign, the activity sequence begins in the
  following sign;
- the complete circuit is 211 symbolic months, after which excess time
  transfers to the opposite sign and continues from there.

The prose and explanatory arithmetic govern the 211-month case; the
inconsistent intervening table is not treated as a second algorithm.

Source fixture:
`tests/golden/hellenistic_zr_valens_iv4.json`.

Valens online witness:
[Riley annotated translation](https://www.skyscript.co.uk/pdf/pubs/texts/valens/griscti/docs/Valens-Anthologies.pdf).

### Hermetic catalog

The 36 names, planetary faces, edition pages, and source identifier remain
source-locked to Wilhelm Gundel, *Dekane und Dekansternbilder* (1936),
pages 379-383, transcribing British Library Harley MS 3731.

The complete edited text's opening passage begins from Aries and counts ten
degrees for each decan. Equal segmentation is therefore source-supported; the
modern equinox-fixed tropical realization and Ascendant composition remain
explicit projection policies pending admission and validation.

The identified edition does not supply the former fixed-star assignments, and
no located passage supports the removed sunset-MC/equal-night-hour algorithm.
Fixed-star access therefore fails closed. The night-hour function, vessels,
tests, server plumbing, and route definition were removed on 2026-07-26.
Any future Egyptian stellar decanal-clock work requires a separate table,
epoch, observer, event-semantics, visibility, and validation contract.

Official witnesses:
[Bavarian Academy Gundel edition](https://publikationen.badw.de/de/012511822)
and [British Library Harley MS 3731 catalogue](https://searcharchives.bl.uk/catalog/040-002049563).

## Policy and qualification findings

The following are intentionally not misrepresented as independent ancient
table goldens:

- completed-civil-anniversary profections and February 29 handling are explicit
  projection policies;
- solar proximity thresholds and the besieging enclosure orb are named
  computation policies;
- Halb/Hayz uses an identified medieval al-Qabisi/Bonatti lineage and remains
  labeled accordingly inside the classical condition component;
- whole-sign direction and overcoming tests validate the declared sign
  geometry and typed boundary behavior, not astrological effects;
- broad lot-catalog coverage remains source-by-source work beyond the four
  profile lots;
- planetary joy evidence is currently a source-cited modern synthesis rather
  than a new direct transcription of every ancient witness;
- Triacontaeteris remains outside this completed contract because prior
  research did not recover a sufficient first-principles algorithm;
- Valens distribution interpretation remains excluded; no generic
  distributor/receiver effects are fabricated.

## Generated runtime governance

`scripts/generate_hellenistic_inventory.py`:

1. imports every declared capability owner and verifies its runtime anchors;
2. records identity counts across `moira`, `moira.classical`, and
   `moira.facade` instead of assuming all classical helpers share one export
   tier;
3. requires identity parity for every `moira.hellenistic.__all__` symbol;
4. reads the current FastAPI OpenAPI registry;
5. records exact route, request schema, response schema, tag, and operation ID;
6. fails if an expected route family disappears;
7. fails if Hermetic, Triacontaeteris, or Decennial L3/L4 paths appear;
8. supports `--check`, and a unit test compares both committed generated files
   to fresh runtime rendering.

This makes future code/API drift fail the test gate instead of silently leaving
the capability matrix stale.

## Validation commands

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_hellenistic_source_goldens.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_hellenistic_inventory_generation.py -q
.\.venv\Scripts\python.exe scripts\generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
```

The final Phase 6 checkpoint must also run the existing Hellenistic dependency,
profile, export, serializer, REST, and OpenAPI suites under strict
known-issues mode. Test counts belong in the gate roadmap only after the final
run; they are not embedded as permanent capability claims here.

## Product boundary

This closes an engine validation/documentation gate. It does not publish or
update website documentation, deploy a server, or make an interpretive
astrology product. Website work may begin only as a separately authorized
implementation using these generated artifacts as the source of current
engine truth.
