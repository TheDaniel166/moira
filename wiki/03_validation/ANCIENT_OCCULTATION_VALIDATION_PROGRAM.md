# Ancient Occultation Validation Program

This note defines the separate validation track for ancient occultations.

## Why It Is Separate

Ancient occultations do not belong in the same oracle family as modern and
future occultation path geometry.

Modern and future validation can rely on:
- IOTA graze and limit path publications
- machine-readable predicted path tables
- direct path-line and boundary comparison

Ancient validation cannot.

Its highest authority is instead:
- scholarly historical-astronomy record corpora
- published reductions of those records
- site-identification and chronology scholarship

So the validation mode changes from `path parity` to `historical event
reconstruction plausibility`.

## Program Boundary

This program owns:
- admissibility rules for ancient occultation records
- date/time reduction doctrine
- site-identification doctrine
- star/body identity doctrine for historical naming systems
- uncertainty classification for each record
- reconstructed local-event validation against reduced historical sources

This program does not own:
- modern/future path geometry parity
- IOTA prediction-path validation
- Swiss `where` parity

## Proposed Phases

### Phase 0 — Source Survey

Identify which corpora are actually admissible for Moira validation.

Expected source classes:
- ancient Chinese occultation/appulse catalogs
- peer-reviewed historical-astronomy reductions
- site-specific observational studies with explicit chronology notes

Deliverable:
- curated source list with provenance and admissibility notes

### Phase 1 — Admissibility Doctrine

Define what counts as a valid ancient validation record.

Each record must be explicit about:
- event kind
- observing site
- target identity
- dating basis
- uncertainty class
- source citation

Deliverable:
- `HistoricalOccultationRecord` doctrine and admission rules

### Phase 2 — Reduction Doctrine

Define how records are normalized into computational inputs.

Must cover:
- calendar conversion
- night-boundary interpretation
- local time phrasing
- site geolocation
- star-name mapping
- uncertainty propagation

Deliverable:
- reduction standard for ancient occultation records

### Phase 3 — Pilot Corpus

Build a small gold-standard pilot set.

Recommended size:
- 3 to 5 well-studied bright-star lunar occultations

Deliverable:
- machine-readable pilot corpus with reduction notes

### Phase 4 — Validation Harness

Validate Moira by reconstructing the local event at the historical site and
testing whether the reconstructed event is plausible within the stated
uncertainty envelope.

Expected assertion classes:
- occultation visible vs not visible
- disappearance / reappearance plausibility
- altitude above horizon
- near-graze plausibility where appropriate
- contact-window plausibility when the source warrants it

## Current Status

Status: deferred

Reason:
- Moira has the computational substrate
- Moira does not yet have the curated historical corpus and reduction doctrine

## Current Active Track

The active occultation validation program remains:
- `modern_future_occultation_path_validation`

Primary authority:
- IOTA graze/limit publications

Secondary authority:
- Swiss `where`

Ancient validation should not be represented as if it were already covered by
that modern/future track.
