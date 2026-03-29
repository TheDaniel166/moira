# Primary Directions Parallel Family Matrix

## Purpose

This document turns the parallel-family question into explicit Moira policy.

It does **not** assume that all "parallels" are one computational object.
It classifies each recoverable branch by:

- geometry family
- directional object
- governing law
- source quality
- Moira policy status
- next action

The rule is strict:

- no branch is admitted by label alone
- no branch is admitted globally if its law is method-bound
- no branch is widened beyond the recoverable mathematics


## Governing Policy

### Constitutional Rule

In primary directions, a parallel is admitted first as a **relation class**,
not as a generic target class.

Only a method with an explicit governing law may realize that relation as a
derived projected point or other computational endpoint.

### Source Rule

For a parallel branch to be admitted, Moira requires:

1. an explicit mathematical law
2. a clear doctrinal meaning
3. a runtime realization specific enough to encode
4. validation material strong enough to test

If one of these is missing, the branch is deferred.


## Branch Matrix

| Branch | Geometry Family | Directional Object | Governing Law in Hand | Source Quality | Moira Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- |
| `Ptolemaic zodiacal parallel` | `Ptolemy / semi-arc`, `in_zodiaco` | declination-equivalent derived zodiacal point | **Yes**. Solve the declination-equivalent ecliptic point from `sin(delta) = sin(eps) * sin(lambda)`, then measure by the active Ptolemaic sub-law (`RA`, `OA/OD`, or proportional semi-arc) | strong enough for narrow admission | `implemented` | keep as verified narrow branch |
| `Ptolemaic zodiacal contra-parallel` | `Ptolemy / semi-arc`, `in_zodiaco` | declination-equivalent derived zodiacal point with reflected declination | **Yes**. Same as above, with declination reflected to the opposite sign of the relation before solving the ecliptic equivalent | strong enough for narrow admission | `implemented` | keep as verified narrow branch |
| `Placidian mundane parallel` | `Placidian classic / semi-arc`, `in_mundo` | meridian-distance / semi-arc relational perfection | **Partially**. The historical material supports proportion by semi-arc and meridian distance, but the precise normalized law still needs one clean formula packet before runtime admission | moderate | `research_candidate` | extract a formula-grade law from one primary technical source before implementation |
| `Placidian mundane rapt parallel` | `Placidian classic / semi-arc`, `in_mundo` | joint motion of both bodies under primary motion | **Yes, narrowly**. The recoverable calculation is proportion-based: combine the relevant semi-arcs, compare them to the right-ascension difference, derive a secondary distance, then take the difference from the primary meridian distance | moderate-to-strong for narrow reconstruction | `next_candidate` | implement one narrow direct branch, then validate against published worked examples |
| `Placidian converse rapt parallel` | `Placidian classic / semi-arc`, `in_mundo`, converse | joint converse motion of both bodies | **Yes, narrowly**. Same family as above, but the converse branch uses converse semi-arcs and a converse right-ascension relation before deriving the secondary distance | moderate for narrow reconstruction | `candidate_after_direct_rapt` | implement only after the direct rapt branch is validated |
| `Regiomontanian parallels` | `Regiomontanus` | unclear: may be under-the-pole, mundane, or mixed by sub-branch | **No single source-safe law in hand** | weak | `deferred` | do not implement until one explicit branch law is recovered |
| `Campanian parallels` | `Campanus` | unclear: likely tied to wider mundane branch, not generic target doctrine | **No single source-safe law in hand** | weak | `deferred` | do not implement until one explicit branch law is recovered |
| `Topocentric parallels` | `Topocentric` | unclear: likely method-specific and pole-law dependent | **No single source-safe law in hand** | weak | `deferred` | do not implement until one explicit branch law is recovered |
| `Morinian parallels` | `Morinus` | unresolved relative to Morinian aspect-plane doctrine | **No explicit primary-direction law in hand** | weak | `deferred` | leave out of runtime until formula-grade evidence appears |
| `Generic global parallel target family` | cross-family | universal target point | **No**. This is doctrinally false on current evidence | strong enough to reject globally | `rejected` | keep rejected as a global consumer target class |


## Concrete Moira Policy

### Declared Implementable Now

These branches are concrete enough to stand as policy:

- `Ptolemaic zodiacal parallel`
- `Ptolemaic zodiacal contra-parallel`

They are admitted as:

- relation-first branches
- method-specific derived-point realizations
- not as generic global target classes

### Declared Implementable Next

The next parallel branch Moira should implement is:

- `Placidian mundane rapt parallel`

Why:

- it has the clearest remaining formula trail
- it stays inside an already sovereign geometry family
- it is a real parallel-family expansion rather than a new doctrinal frontier
- it can be validated against published worked examples

### Declared Deferred

These remain deferred:

- `Regiomontanian parallels`
- `Campanian parallels`
- `Topocentric parallels`
- `Morinian parallels`

Reason:

- the label survives
- software may expose the label
- but Moira does not yet have one branch law explicit enough to encode

### Declared Rejected

This remains rejected:

- global consumer-facing `Parallel` as a target class

Reason:

- it collapses a relation doctrine into a false generic target ontology


## Implementation Order

The parallel family should proceed in this order:

1. keep the current Ptolemaic zodiacal `parallel` / `contra-parallel` branch
   stable
2. implement `Placidian mundane rapt parallel` direct
3. validate it against published worked examples
4. implement `Placidian converse rapt parallel` only if the direct branch
   validates cleanly
5. reassess whether any non-Placidian families have gained a source-safe branch
   law

The stop rule is explicit:

- if no explicit governing law is recovered for a branch, the branch stays
  deferred


## Mathematical Notes

### Ptolemaic Zodiacal Parallel Family

The current narrow law is:

1. take the source declination
2. preserve it for `parallel`, reflect it for `contra-parallel`
3. solve the equivalent ecliptic longitude from the declination relation
4. measure the resulting directional arc through the active Ptolemaic sub-law:
   - `MC/IC` by `RA`
   - `ASC/DSC` by `OA/OD`
   - non-angular points by proportional semi-arcs

This is already encoded and tested in Moira.

### Placidian Mundane Rapt Parallel Family

The recoverable direct-family pattern is:

1. identify the relevant semi-arcs of the two bodies
2. form the required semi-arc sum
3. form the relevant right-ascension difference
4. use proportionality to derive a secondary distance
5. compare primary and secondary meridian distances to obtain the arc

The converse family follows the same proportion logic, but with converse
semi-arcs and converse right-ascension handling.

This is precise enough to declare a next implementation target, but not yet
admitted in runtime until the law is reduced to one explicit code-grade formula
packet.


## Sources Used

### Strongest Current Sources

- Alan Leo, *Primary Directions*:
  direct and converse rapt-parallel worked examples and zodiacal parallel /
  declination-equivalent examples
  `https://maestrosdelsaber.com/wp-content/uploads/ftp-files/Astrologia/Astro%20a%20Leo%2C%20Alan/Astro%20Leo%2C%20Alan%20-%20Primary%20Directions.pdf`
- AstroAmerica, *Primary Directions*:
  Ptolemaic proportional-semi-arc basis and declination-equivalent zodiacal
  practice
  `https://astroamerica.com/primary.pdf`
- Heaven Astrolabe, "Calculating rapt parallels, Placido method":
  modern technical reconstruction of Placidian rapt-parallel arithmetic from
  Placido tables
  `https://heavenastrolabe.wordpress.com/2010/08/20/calculating-rapt-parallels-placido-method/`

### Supporting Ecosystem Sources

- Halloran / Kolev software material:
  confirms that `mundo parallels` and `mundo rapt parallels` are treated as
  real Placidian branches in the wider software ecosystem
  `https://www.halloran.com/placidus.htm`
- AstroApp help:
  confirms current software exposure of `mundane parallels` and
  `ASC-axis parallels` in `In Mundo`
  `https://astroapp.com/help/1/returnsW_53.html`
- PyMorinus site:
  confirms that `rapt parallels` are treated as a recognizable research branch,
  though not thereby source-verified
  `https://sites.google.com/site/pymorinus/`


## Present Declaration

Moira now has a concrete parallel-family policy:

- the Ptolemaic zodiacal branch is admitted
- the next implementation target is Placidian mundane rapt parallels
- wider method families remain deferred until their governing law is explicit
- the global-target abstraction remains rejected
