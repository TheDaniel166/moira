## Moira Dignities Backend Standard

### 1. Governing rule

Moira keeps three things separate:

1. **astronomical and doctrinal truth** — what was evaluated and what matched;
2. **weight** — the value assigned by the selected scoring tradition;
3. **applied score** — the value actually counted under the selected scoring mode.

No policy preserves the former hybrid score. A selectable policy must represent
an admitted doctrine, a deliberate score projection, or truth-only tracking.

The canonical per-planet entry point is
`DignitiesService.calculate_dignities()`. The module-level wrappers and REST
routes are transports over the same computation.

---

## 2. Policy axes

`DignityComputationPolicy` owns four independent policy groups.

### 2.1 Essential tables

`EssentialDignityPolicy` selects:

| Field | Admitted values | Default |
|---|---|---|
| `doctrine` | `traditional_classic_7`, `modern_co_rulers` | `traditional_classic_7` |
| `bounds_doctrine` | Egyptian, Ptolemaic, Chaldaean day, Chaldaean night | Ptolemaic |
| `triplicity_doctrine` | Dorothean/Pingree 1976 | Dorothean/Pingree 1976 |
| `participating_ruler_policy` | ignore, award reduced | ignore |

The modern co-ruler table extends domicile and detriment only. It does not
silently extend exaltation, fall, triplicity, bounds, or faces.

### 2.2 Scoring and tracking

`DignityScoringPolicy.mode` admits:

| Mode | Essential testimony | Accidental testimony | Truth receipts |
|---|---:|---:|---|
| `william_lilly_1647` | scored | scored | retained |
| `essential_only` | scored | tracked with applied score 0 | retained |
| `unscored` | tracked with applied score 0 | tracked with applied score 0 | retained |

The Lilly mode is source-coherent and therefore requires Classic 7 rulers,
Ptolemaic bounds, the admitted Dorothean triplicity table, and no points for the
participating ruler. Modern rulerships and alternative bound tables remain
available through `essential_only` and `unscored`; they are not relabelled as a
Lilly total.

`DignityScoringPolicy.node_doctrine` selects the mean or true north-node
longitude for the dragon's-head and dragon's-tail testimonies.

### 2.3 Accidental admission

`AccidentalDignityPolicy` independently controls whether the engine evaluates
and exposes:

- house strength;
- direct/retrograde motion;
- swift/slow daily motion;
- lunar waxing/waning;
- oriental/occidental phase;
- solar condition;
- partile benefic and malefic aspects;
- node conjunctions;
- Regulus, Spica, and Algol conjunctions;
- besieging;
- planetary joys;
- sect, halb, and hayz.

An inclusion flag governs admission of that testimony. A scoring mode governs
whether an admitted match contributes its weight. These are different choices.

### 2.4 Reception

`MutualReceptionPolicy` is a top-level policy because mutual reception by house
or exaltation is essential testimony in the Lilly table. It is not an
accidental dignity.

`all_receptions` contains detected relations, `admitted_receptions` contains the
policy-allowed subset, and `scored_receptions` contains only mutual relations
whose truth record has `scored=True`.

---

## 3. William Lilly 1647 score

The default score is cumulative. A term or face never erases detriment or fall.
Every matching essential component contributes independently.

### 3.1 Essential weights

| Testimony | Weight |
|---|---:|
| domicile / mutual reception by house | +5 |
| exaltation / mutual reception by exaltation | +4 |
| active triplicity ruler | +3 |
| own bound or term | +2 |
| own face | +1 |
| detriment | -5 |
| fall | -4 |
| peregrine | -5 |

Peregrine means that none of the five positive essential dignities matched.
It can therefore coexist with a debility such as fall. A reception is retained
as its own essential receipt and does not erase the planet's zodiacal
peregrine state.

`essential_dignity` remains a deterministic primary display label.
`essential_truth.matched_components`, `essential_truth.receptions`, and
`essential_classification.kinds` are the complete non-erasing result.

### 3.2 Accidental weights

| Testimony | Weight |
|---|---:|
| houses 1 or 10 | +5 |
| houses 4, 7, or 11 | +4 |
| houses 2 or 5 | +3 |
| house 9 | +2 |
| house 3 | +1 |
| houses 6 or 8 | -2 |
| house 12 | -5 |
| direct (not Sun or Moon) | +4 |
| retrograde (not Sun or Moon) | -5 |
| swift / slow compared with Lilly's mean daily motion | +2 / -2 |
| superior oriental / occidental | +2 / -2 |
| Mercury or Venus occidental / oriental | +2 / -2 |
| Moon waxing / waning | +2 / -2 |
| cazimi | +5 |
| combust | -5 |
| under beams | -4 |
| free from combustion and beams | +5 |
| partile conjunction / trine / sextile with Jupiter or Venus | +5 / +4 / +3 |
| partile conjunction / opposition / square with Saturn or Mars | -5 / -4 / -3 |
| partile conjunction with north / south node | +4 / -4 |
| besieged by Mars and Saturn | -5 |
| Regulus / Spica / Algol conjunction | +6 / +5 / -5 |

The Sun and Moon have no direct/retrograde testimony. Missing motion or speed
data produces a typed `not_evaluable` receipt rather than a fabricated direct
or mean-motion state.

A stationary non-luminary is tracked explicitly as `stationary`: it receives
neither the direct nor retrograde weight. Its zero daily motion still qualifies
as slow relative to Lilly's mean-motion table and is scored separately there.

Partile aspects use a residual of less than one degree from the exact aspect.
The fixed-star conjunction limits are 6 degrees for Regulus and 5 degrees for
Spica and Algol, matching Lilly's worked examples.

### 3.3 Solar bands

Solar proximity is exclusive and is never re-labelled when a narrower band is
disabled:

| Band | Distance from Sun |
|---|---|
| cazimi | at most 17 arcminutes |
| combust | beyond cazimi through 8 degrees 30 arcminutes |
| under beams | beyond combustion through 17 degrees |
| clear | beyond 17 degrees |

The raw `SolarProximityTruth` exists independently of policy. Solar proximity
is not applicable to the Sun itself. It is evaluated for the Moon by default,
as Lilly explicitly treats the Moon as capable of combustion and being under
the Sun's beams; `include_for_moon=false` can suppress that testimony without
altering the raw proximity receipt.

---

## 4. Tracked but not silently scored

Hayz, halb, and planetary joy are preserved as named conditions with their
source and a weight of zero in the Lilly total. Their presence is not evidence
that Lilly assigned them points in the ready table.

Under the admitted al-Biruni section 496 doctrine:

- a diurnal planet seeks the diurnal hemisphere and a nocturnal planet the
  nocturnal hemisphere;
- hayz additionally requires a sign of the planet's gender;
- Sun, Jupiter, Saturn, and Mars are masculine;
- Moon and Venus are feminine;
- Mercury is common/neutral, so Moira does not invent a Mercury hayz result.

Mars is masculine and nocturnal. In a night chart it requires the appropriate
hemisphere and a masculine sign for hayz.

`DignityHorizonFrame` is the preferred horizon authority. The numbered-house
fallback remains available to raw callers and is explicitly identified in the
truth receipt.

---

## 5. Result contract

Every matched accidental condition exposes:

- `category`, `code`, and `label`;
- traditional `weight`;
- applied `score`;
- `scored`;
- `source`.

`AccidentalDignityEvaluationTruth` also records absent or unavailable
testimonies with an evaluation status and reason. Essential components expose
the same weight-versus-score distinction.

The principal invariants are:

- `essential_score` equals the sum of essential component and admitted mutual
  reception applied scores;
- `accidental_score` equals the sum of accidental condition applied scores;
- `total_score == essential_score + accidental_score`;
- unscored or not-evaluable testimony always has applied score 0;
- result labels, classifications, and structured truth remain aligned;
- input ordering does not change semantic output ordering.

The unified Hellenistic profile remains a deliberately score-free projection.
It consumes the same component truth but omits weights and scores from that
profile's transport contract.

---

## 6. REST and runtime support

The dignity chart service supplies the engine with:

- exact planetary longitude and longitude speed;
- explicit retrograde state;
- exact Ascendant/Midheaven horizon geometry;
- mean and true node positions;
- epoch-correct Regulus, Spica, and Algol positions.

The REST policy mirrors the engine policy: `essential`, `accidental`,
`reception`, and `scoring`. Response models expose component weights, applied
scores, scoring status, source, and accidental evaluation receipts.

---

## 7. Failure doctrine

The engine raises `ValueError` for malformed coordinates, duplicate supported
planets, incomplete or duplicate houses, contradictory speed/retrograde input,
or incoherent policy combinations. It does not silently coerce a modern or
alternative-table calculation into the Lilly mode.

---

## 8. Primary source anchors

- William Lilly, *Christian Astrology* (1647), printed pp. 57-84 and 113-116:
  mean motions, solar condition definitions, and the ready table of planetary
  fortitudes and debilities. The worked score examples at printed pp. 178-180
  establish the Regulus and Spica conjunction limits.
  [Public-domain facsimile](https://archive.org/details/b30338724)
- Claudius Ptolemy, *Tetrabiblos*, book I, on planetary gender: the Sun,
  Saturn, Jupiter, and Mars are masculine; the Moon and Venus are feminine;
  Mercury is common.
  [LacusCurtius transcription](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/1B*.html)
- al-Biruni, *The Book of Instruction in the Elements of the Art of Astrology*,
  section 496: the Halb hemisphere rule and the additional same-gender-sign
  condition for Hayz.
  [Wright translation facsimile](https://www.skyscript.co.uk/pdf/pubs/texts/albiruni/docs/albiruni.pdf)

---

## 9. Validation

Minimum focused validation:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.venv\Scripts\python.exe -m pytest tests\unit\test_dignities_scoring_policy.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_moira_dignities_and_lots.py -q
.venv\Scripts\python.exe -m pytest tests\server\test_server_dignities_routes.py -q
.venv\Scripts\python.exe -m pytest tests\server\test_server_hellenistic_profile.py tests\server\test_hellenistic_contract_openapi.py -q
```

The focused policy suite must cover cumulative essential testimony,
peregrine, house-specific weights, luminary motion exclusion, speed, lunar
phase, solar bands, partile aspects, nodes, fixed stars, besieging, reception,
hayz, bounds policy, triplicity participation, and all three scoring modes.
