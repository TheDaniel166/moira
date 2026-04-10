# Stellar Heliacal Validation Sources (2026-04-09)

Purpose:
- define the admissible source families for expanding stellar heliacal validation beyond the current Sirius anchor
- distinguish strong candidate oracles from weak or unusable source types
- keep future stellar heliacal validation tied to explicit provenance

Primary repo inputs:
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`
- `wiki/03_validation/HELIACAL_CLOSURE_AUDIT_2026-04-09.md`
- `wiki/03_validation/VALIDATION_ASTRONOMY.md`
- `wiki/02_standards/SOTHIC_BACKEND_STANDARD.md`
- `moira/stars.py`
- `moira/sothic.py`

## 1. Current Baseline

The current stellar heliacal validation basis is real but narrow:

- Sirius / Sothic historical anchor
- delegated comparison between `visibility_event(...)` and the stellar heliacal branch
- documentation in `VALIDATION_ASTRONOMY.md` that treats this as an implemented slice, not broad closure

This means the immediate problem is not:
- "find any star-related source"

It is:
- "find stellar heliacal sources with enough observational meaning to serve as a real oracle family"

## 2. Source Ranking

### Tier A: strongest candidate source families

These are the best candidates for future admitted validation corpora.

#### A1. Historically explicit first-visibility records tied to a named star, site, and calendar context

Examples of acceptable shape:
- a named star
- a named observing region or latitude band
- an explicit historical year or date range
- a described heliacal first-visibility or last-visibility event

Why this family is strong:
- it measures the actual event semantics Moira claims to model
- it preserves the observational meaning of heliacal appearance
- it supports star-specific validation rather than generic photometric inference

Current Moira precedent:
- Sirius / Sothic anchor via Censorinus and the Sothic doctrine layer

#### A2. Scholarly modern reconstructions of historical heliacal risings using explicit astronomical assumptions

Acceptable shape:
- source states the star
- source states observer location or latitude
- source states observational criterion or solar depression rule
- source states reconstructed event date or day range

Why this family is strong:
- it can provide a historically meaningful yet computationally legible oracle
- assumptions are inspectable rather than hidden

#### A3. Published observational studies focused on stellar heliacal visibility criteria

Acceptable shape:
- star-class examples
- explicit criterion law
- explicit site conditions
- published event predictions or observed windows

Why this family is strong:
- it is closer to the real visibility problem than generic ephemeris output
- it may support validation across multiple bright stars

Repo doctrinal precedent:
- `BEYOND_SWISS_EPHEMERIS.md` already names Schaefer and Helmantel as modern research lineage relevant to heliacal work

### Tier B: useful secondary families

These can support diagnostics or partial validation, but should not be the summit oracle by themselves.

#### B1. Stable internal delegation checks

Examples:
- `visibility_event("Sirius", ...)` agrees with `moira.stars.heliacal_rising_event(...)`

Use:
- confirms subsystem routing and doctrinal separation

Limit:
- not an external oracle

#### B2. Fixed-star positional reference corpora

Examples already present in the repo:
- `tests/fixtures/stars_swetest_reference.json`
- ERFA-oriented star position validation in `VALIDATION_EXPERIMENTAL.md`

Use:
- validates star positions and propagation substrate

Limit:
- does not validate heliacal event semantics directly

#### B3. Multiple-star orbital or resolvability references

Examples:
- Sirius AB orbit spot checks

Use:
- may matter for special stars where companion contamination affects visibility discussion

Limit:
- still not a heliacal event oracle by itself

### Tier C: weak or inadmissible source families

These should not govern stellar heliacal validation.

#### C1. Generic astrology websites listing "heliacal rising dates"

Reason for rejection:
- weak provenance
- hidden assumptions
- often no explicit observer location or criterion law

#### C2. Swiss output by itself

Reason for rejection:
- Swiss can be a comparison layer
- it is not a primary stellar heliacal authority
- parity to Swiss does not establish observational truth

#### C3. Pure star-position references without event semantics

Reason for rejection:
- they validate substrate position, not visibility event reality

## 3. Best Candidate Expansion Strategy

The cleanest next stellar validation expansion is not a broad random star list.

It should be a staged corpus:

1. retain Sirius as the historical anchor
2. add a small bright-star family with strong observational or scholarly visibility literature
3. only then widen to a larger named-star batch

## 4. Candidate Corpus Design

### Stage 1: anchor family

Keep:
- Sirius / Sothic

Reason:
- already doctrinally anchored in Moira
- already connected to a named historical record

### Stage 2: bright-star comparative family

Desired star qualities:
- bright
- historically prominent
- low ambiguity of identity
- broad latitudinal observability

Likely candidate types:
- first-magnitude stars with strong historical visibility traditions
- stars already prominent in Moira's sovereign registry and doctrine layers

Reason:
- these maximize the chance of finding usable historical or scholarly references

### Stage 3: doctrine stress family

Desired properties:
- different declinations
- different brightness levels
- different seasonal and twilight contexts

Reason:
- this tests whether the same visibility doctrine behaves credibly across varied stellar geometry

## 5. What a Future Admitted Stellar Oracle Row Must Contain

Minimum fields:
- star name
- source citation
- source kind
- observer latitude
- observer longitude or named site
- date or date range
- event kind
- source visibility criterion if stated
- comparison tolerance
- notes on uncertainty or calendrical reconstruction

Without these fields, a stellar heliacal source should not enter the admitted validation matrix.

## 6. Recommended Claim Discipline

Safe wording now:
- "stellar heliacal validation is presently anchored by the Sirius / Sothic slice"

Unsafe wording now:
- "stellar heliacal visibility is broadly validated across the named-star surface"

Safe wording after a small expanded corpus:
- "stellar heliacal validation covers a small historically and observationally grounded bright-star corpus"

## 7. Immediate Next Artifacts

The source-discovery step now has its intake artifact:
- `wiki/03_validation/STELLAR_HELIACAL_CANDIDATE_SOURCE_LEDGER_2026-04-09.md`

The next useful artifacts after this source note are:
- `wiki/03_validation/STELLAR_HELIACAL_VALIDATION_CORPUS_2026-04-09.md`
- `wiki/03_validation/STELLAR_HELIACAL_CASE_LEDGER_2026-04-09.md`

That keeps the order correct:
- source discovery
- oracle admission
- validation design
- case-ledger capture
- test implementation

## 8. Final Judgment

The stellar heliacal validation problem is not a math problem first.

It is an oracle problem:
- find sources that describe real stellar first-visibility events with usable assumptions
- reject weak convenience lists
- preserve Sirius as the anchor until a broader corpus is justified
