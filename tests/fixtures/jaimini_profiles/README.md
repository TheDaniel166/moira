# VED-013 source and compatibility fixtures

Authority and decisions are in
`wiki/06_roadmap/VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md` and its
implementation plan. `sources.json` identifies the reviewed editions and
author-hosted sources. PDF coordinates are one-based and distinct from printed
pages. Source PDFs/OCR/rendered pages remain outside the repository.

These fixtures were prepared before the new evaluators:

- `chara_source_cases.json`: 24 printed sequence rows (288 cells), three
  method-1 and seven method-2 printed durations, and the twelve female-profile
  durations selected from prose. The printed Cancer value remains ten; the
  selected own-sign rule gives twelve. No claim of twelve printed matches.
- `argala_source_cases.json`: PVR Exercise 16's twelve by eight occupancy table,
  BPHS's hypothetical chart with the publisher's Rahu/Gemini erratum, and Rath's
  standard-nativity positions and bounded comparison witnesses.
- `source_conflicts.json`: printed versus selected values, the resolved erratum,
  and unresolved BPHS/PVR/Rath questions. They are not executable selector IDs.
- `legacy_regression.json`: twenty existing Argala outputs and both existing
  Chara cycle counts captured before repairs. This is implementation regression
  evidence, not independent source authority. Argala lineage text/receipt are
  intentionally excluded from the numeric compatibility comparison.

All source charts here specify signs, not fabricated historical degrees.
Synthetic degree cases in the tests establish selected clause and boundary
semantics; they do not add precision to the printed charts. Independent rational
arithmetic on the exact binary input checks quarter boundaries. Literal printed
sequence arrays are never generated through an engine helper.

One fixture preparation correction occurred during source validation: Rath's
article selects Sagittarius/Ketu using Jupiter's influence. The initial fixture
also asserted that Jupiter in Pisces did not aspect Gemini; that extra assertion
was not in the article. Independent Jaimini geometry shows that all three are
dual signs, so both Gemini and Sagittarius receive rasi drishti. C12 now records
both aspect witnesses as true, retains the source's winner separately, and
requires an indeterminate runtime comparison. No asymmetric aspect or invented
factor ranking was introduced to reproduce the printed judgment.

Refresh requires a reviewed witness/interpretation change. Never regenerate
expected answers from production output or treat software parity as a primary
source oracle. Fixture hashes identify evidence; they do not prove correctness.
