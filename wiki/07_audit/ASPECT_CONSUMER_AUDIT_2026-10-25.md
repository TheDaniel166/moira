# Aspect Consumer Audit — 2026-10-25

## Scope and governing catalog

This audit covers the Moira engine repository and its REST API, as requested.
Workspace and public-website consumer repositories are outside this scope.
The source baseline is engine commit `95e45015047fe59adf17272b81dd7b032e6aa593`.

The [Complete Aspect Catalog](../02_standards/ASPECT_CATALOG.md) is the user-facing
reference: 46 standard and 28 explicitly optional longitude targets, 97 aliases,
22 harmonic presets, and two separately evaluated declination relationships.
Quindecile remains 24°, Tao 165°, and unqualified Tredecile 108°.

The audit traced registry imports, detector calls, facade delegation, named
selection and numeric-angle adapters, REST models/services/serializers, and
hard-coded technique tables. An AST inventory identified 28 production Python
files importing the catalog/detector/consumer symbols directly; facade mixins
and numeric or technique-specific consumers were reviewed separately.

## Findings and fixes

| Finding | Previous behavior | Corrected behavior |
|---|---|---|
| Synastry facade discarded falsey selectors | `False`, `0`, `""`, and other invalid empty containers bypassed direct-engine optional-set validation | Invalid supplied selectors reach the owning validator; explicit empty list/tuple selection and the direct synastry `None` sentinel retain their existing meanings |
| REST aspect-policy types were inconsistent | Some synastry, chart-wheel, and resonance inputs coerced booleans, strings, or integral floats into tiers/orb multipliers; some admitted non-finite multipliers | Shared before-validators enforce integer tiers, finite numeric multipliers, and boolean aspect-inclusion flags; endpoint-specific domain checks remain in place |
| Forecast validation occurred too late | A known alias could select a target unavailable at the requested tier or without its optional set, reaching chart construction first | REST forecast models reject unavailable selections before chart construction; direct computation and work-budget checks enforce the same selection |
| Forecast tuple aliases differed from JSON lists | Python tuple inputs skipped pre-normalization, so case/separator variants could fail Literal validation | Lists and tuples normalize aliases consistently and reject duplicates after canonical resolution |
| Selection policy was duplicated | Core detection, relationship forecasting, and REST work-budget enumeration assembled selections independently | A private registry resolver owns tier/optional membership, canonical name resolution, explicit ordering, and duplicate/unavailable-name rejection |
| Registered Septile Triangle was absent from automatic searches | Automatic and facade pattern paths admitted only major/common minor edges | Both paths explicitly scan standard `tier=2`, supplying Septile/Biseptile/Triseptile edges; REST pattern truth identifies the catalog and tier |
| Harmonic reference-orb documentation was stale | The standard claimed a 1° ordinary harmonic-chart reference default | The standard now states the implemented 12° projected/H1 default and distinguishes the separate 1° sampled transit-forecast policy |
| Duplicated API reference rows were stale | Some rows described obsolete point-detector signatures, treated the family profile as a harmonic projection, or claimed derived-chart tier 1 | Python reference rows now match the owning functions and optional selectors; REST derived-chart documentation states the implemented tier-0 default and explicit optional selection |

## Consumer coverage

| Consumer surface | Catalog, aliases, and orb behavior | Selection and outcome |
|---|---|---|
| [Registry](../../moira/aspect_registry.py), [standard definitions](../../moira/constants.py), [optional metadata](../../moira/optional_aspects.py) | Unique canonical definitions; declared aliases resolve to the same object; standard and optional default orbs retained | Shared selection adds only requested optional primitive fractions; default membership stays 46 |
| [Ordinary longitude detectors](../../moira/aspects.py) | `find_aspects`, `aspects_between`, `aspects_to_point`, and `aspects_from_longitudes` use canonical definitions and caller orb policy | All 74 targets are available with explicit optional sets; historical ordinary-detector tier defaults remain unchanged |
| [Public exports](../../moira/facade.py) and [facade core](../../moira/_facade_core.py) | Root, classical, predictive, and facade namespaces expose the registry; essentials delegates its basic detector/policy to the same owner | Facade inputs preserve policy precedence and optional-set validation |
| [Synastry](../../moira/synastry.py) and [relationship facade](../../moira/_facade_relationships.py) | Both aspect and contact paths use the owning pair detector/default orbs; contact truth preserves selection | Explicit selections override synastry policy selections; falsey-invalid facade inputs now fail consistently |
| [Relationship forecasting](../../moira/relationship_forecasting.py) and [REST forecasts](../../moira_server/services/forecasting.py) | Canonical names and aliases use shared membership resolution; default angle definitions are identical | Optional names require enabled sets; canonical deduplication, symmetric branches, and existing work budgets are retained |
| [Relationship REST](../../moira_server/services/relationship.py) and [serializers](../../moira_server/serializers/relationship.py) | Motion input accepts registered aliases and emits canonical names; serialized angles/orbs/classification come from engine vessels | Position-only, synastry, composite, and Davison analyses preserve optional-set receipts; optional discovery exposes exact fractions and aliases |
| [Chart-wheel primitives](../../moira_server/services/chart_wheel.py) | Target, orb, symbol, family, and stroke-key data are derived from admitted aspects | Configured optional sets reach the detector and policy receipt; strict tier/multiplier/flag typing now matches the general REST contract |
| [Asteroid family resonance](../../moira_server/services/asteroids.py) and [family filtering](../../moira/asteroid_families.py) | Family qualification retains the admitted aspect's geometry, classification, and orb | Optional selection reaches detection and provenance; family filtering does not redefine aspect membership |
| [Geodetic overlays](../../moira/geodetic_analysis.py) | Supplied `AspectPolicy` is passed to `aspects_to_point`; contacts and original policy are retained | A 74-target regression matrix checks every registered target and default orb through the overlay path |
| [Strength, graph, and family profiles](../../moira/aspects.py) | Consume canonical admitted `AspectData`, without another admission or replacement orb table | Every registered target preserves its edge, exact strength, and family classification in the regression matrix |
| [Named pattern detection](../../moira/patterns.py) and [pattern facade](../../moira/_facade_special.py) | Automatic admission scans all standard targets; pattern templates may impose their documented narrower edge ceilings | Septile Triangle is now available automatically and over REST; precomputed aspect inputs remain supported; no new optional pattern templates are inferred |
| [Harmonic engine](../../moira/harmonics.py) and [REST harmonics](../../moira_server/services/harmonics.py) | All 22 preset names agree; H8/H12 legacy labels resolve through the longitude registry; optional longitude orbs agree with `12/H` | Numeric harmonic projection and ordinary aspect detection retain separate policy surfaces; presets do not enable optional sets automatically |
| [Numeric transit searches](../../moira/transits_aspects.py), [predictive facade](../../moira/_facade_predictive.py), [batch engine](../../moira/batch.py), and REST transit/batch transport | Accept caller-supplied angle/orb specifications, including every registered angle; default numeric exact-hit orbs remain zero | Convert names with `resolve_aspect()` and supply `definition.angle`/`definition.default_orb` when catalog defaults are desired; the all-74 dispatch matrix verifies facade/batch transport without changing numeric search semantics |
| [Declination](../../moira/declination_aspects.py) and its REST models | Parallel/Contra-Parallel retain their signed-hemisphere tests and 1° declination default | Separate coordinate domain; no ecliptic turn fraction or optional longitude set is inferred |

## Deliberate technique boundaries

The complete longitude catalog is not a replacement for every technique's
admitted definition of an aspect:

- Whole-sign/Hellenistic rays, traditional moiety mode, classical perfection,
  void-of-course Moon, natal lunar-context contacts, Lilly longevity rules,
  and Tajika annual aspects retain their explicitly bounded aspect sets.
- Primary-direction aspect targets retain their admitted signed major-aspect
  constructions and separate mundane geometry; an ordinary ecliptic catalog
  addition does not establish a new primary-direction doctrine.
- Church of Light Astrodynes and progressed Astrodynes retain their own
  source-owned aspect/orb tables. Huber Age Point contacts remain their
  documented conjunction-only sampled product.
- Antiscia use transformed shadow points and their own contact orb. Their
  use of a conjunction motion witness does not admit other aspect geometries.
- Named-pattern coherence retains its frozen reference-orb doctrine and six
  admitted scoring templates. Unsupported templates continue to report their
  existing unavailable/not-assessed result instead of inventing scoring rules.
- Ordinary harmonic charts use a 12° projected/H1 reference by default.
  Sampled mixed-origin harmonic-transit forecasting retains its separate 1°
  default; range products retain the explicit default maximum harmonic of 32.

These boundaries were reviewed as intentional product/doctrine contracts.
They were not broadened by this audit.

## Verification

New regression witnesses cover falsey facade selectors; strict REST policy
types; unavailable forecast selection before chart construction; tuple/list
alias parity; the exact-turn Septile Triangle through direct, facade, and REST
paths; all 74 targets through strength/graph/family/geodetic consumers; all 97
aliases through motion and both forecast selection paths; all 22 preset names;
and all 74 angle/default-orb specifications through numeric facade/batch dispatch.

The numeric dispatch witness substitutes the search function to inspect the
forwarded specifications. It is transport evidence, not a JPL ephemeris or
event-time accuracy claim. Geometry-only witnesses use supplied longitudes;
they do not require or download planetary kernels. The focused regression
command and its final result are recorded with the publishing commit receipt.

No scientific golden artifacts, snapshots, tolerances, package version,
production deployment, or unrelated working-tree changes are part of this audit.

### Focused execution receipt

The isolated project runtime was Python 3.14.8, with source/distribution
version 6.10.2 and a rebuilt native extension imported from the same checkout.
**1,716 tests passed; 112 ephemeris/network cases were deselected** by the
explicit marker selection. No test failures or skips were reported. These are
local focused results, not a claim about hosted CI or ephemeris accuracy.

The selected modules and invocation were:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$tests = @(
    "tests/unit/test_aspects.py",
    "tests/unit/test_aspect_catalog.py",
    "tests/unit/test_aspect_consumer_contracts.py",
    "tests/unit/test_extended_aspect_admission.py",
    "tests/unit/test_optional_aspects.py",
    "tests/unit/test_aspect_motion_witness.py",
    "tests/unit/test_declination_aspects.py",
    "tests/unit/test_harmonics.py",
    "tests/unit/test_harmonic_transits.py",
    "tests/unit/test_relationship_forecasting.py",
    "tests/unit/test_moira_synastry.py",
    "tests/unit/test_synastry_public_api.py",
    "tests/unit/test_progressed_synastry.py",
    "tests/unit/test_public_api_drift.py",
    "tests/unit/test_classical_facade.py",
    "tests/unit/test_pattern_facade.py",
    "tests/unit/test_patterns.py",
    "tests/unit/test_patterns_public_api.py",
    "tests/unit/test_pattern_coherence_qualitative.py",
    "tests/unit/test_geodetic_analysis.py",
    "tests/unit/test_batch.py",
    "tests/unit/test_varshaphal.py",
    "tests/server/test_server_aspect_consumer_contracts.py",
    "tests/server/test_server_aspect_motion_witness.py",
    "tests/server/test_server_aspects_from_longitudes.py",
    "tests/server/test_server_optional_aspects.py",
    "tests/server/test_server_declination_aspects.py",
    "tests/server/test_server_declination_aspect_motion.py",
    "tests/server/test_server_harmonics_routes.py",
    "tests/server/test_server_forecasting_routes.py",
    "tests/server/test_server_relationship_routes.py",
    "tests/server/test_server_chart_wheel_routes.py",
    "tests/server/test_server_small_body_list_routes.py",
    "tests/server/test_server_patterns_policy.py",
    "tests/server/test_server_pattern_coherence_routes.py",
    "tests/server/test_server_natal_aspect_routes.py",
    "tests/server/test_server_batch_routes.py"
)
.\.venv\Scripts\python.exe -m pytest $tests `
    -m "not external_network and not requires_ephemeris" `
    -o "addopts=-ra --import-mode=importlib" -q --tb=short
```

The run also wrote a JUnit receipt outside the repository. All 12 touched
Python files passed the configured Ruff correctness checks with zero
diagnostics and parsed under Python 3.10 grammar. Touched-engine docstring
preflight passed for six files. Source-derived catalog tables, both Python
documentation examples, REST example geometry, local documentation links,
and the six scoped Git wiki outputs were checked. The repository
`scripts/check_doc_consistency.py` guard passed. An unrelated pre-existing
Light Box mirror difference was preserved rather than published with this scope.
