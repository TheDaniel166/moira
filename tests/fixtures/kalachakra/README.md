# Kalachakra independent source fixtures

`source_cases.json` was transcribed and its exact-rational checks passed before
the calculator was written. Frozen SHA-256:
`f646f4ab82907988da8cdff128785a62e0c9502a66019c15c70885505952f823`.

The independent oracle is `tests/unit/test_kalachakra_sources.py`. It reads these
rows, weights, source examples and the separate 24-position comparison rings;
it imports no Moira code. Runtime tests compare against it, never regenerate it
from the implementation. Source PDF fingerprints and coordinates are in the
JSON and the canonical research packet. Full books/OCR are not redistributed.

Literal printed and exact derived values are separate fields. Rao's continuation,
ADs and ten-entry exercise are competing-method evidence, not expectations for
Santhanam. Source witnesses are exact sexagesimal rationals; public binary64
inputs have separately bounded conversion error. No empirical calendar/date
oracle or software-export parity is asserted by these source-year fixtures.

## Rao 2000 extension, 26 October 2026

`rao_2000_source_cases.json` was frozen and passed its independent arithmetic
checks before the profile runtime was added. SHA-256:
`99075505715be0a25da0bdd2116e327474d19eee66b0c9918308885951e461bb`.
Its owner is `tests/unit/test_kalachakra_rao_sources.py`, which imports no Moira
code. The oracle traverses the separately transcribed 24-position Table 43
rings; the implementation advances through the sixteen nine-occurrence rows.
The packet distinguishes printed Examples 95-97 / Exercise 34 from derived
fractions and the cross-profile input discriminator. KC-03's membership
correction remains explicit. The original fixture above is unchanged.

`santhanam_compatibility_2026_10_26.json` freezes 648 pre-extension transport
cases at engine `caec99b` plus the local error-classification repair: all 108
pada midpoints, levels 1/2, and source-only / 360-day / 365.25-day output.
Projected cases include current results at birth and the final endpoint.
SHA-256:
`e7d22d56e104cc180aa344bb7886d45e7271b6f29ba37c1b35177082cf95d7ba`.
This is compatibility evidence generated from the previous engine, not an
independent source or astronomy oracle. Neither fixture may be regenerated
from the new runtime to resolve a disagreement.

## Markati context supplement, 26 October 2026

The original Rao fixture's pair-only `gati` entries are incomplete as a
Markati oracle: the same directed pair appears in ordinary and reversing
portions of Table 43. Preserve that historical file and its fingerprint.
`rao_2000_markati_contexts.json` supplies the missing context from Table 43
and section 24.3.3(2), printed pages 290 and 297. SHA-256:
`9bded4c5fc07341c350dc5d5967fc657f9cce8b0d1ae104b2104cee6dc1e5450`.

The four cases distinguish two source-described reversals from two ordinary
progressions. Ring positions, input longitudes and output ordinals are labelled
as derived evidence. The independent source test checks the four-sign contexts,
their zodiac directions and the derived input/path mapping before comparison
with runtime output. The runtime uses neighboring source rows; the oracle
uses the independently transcribed 24-position ring. The supplement was frozen
before the runtime repair, and does not change existing balance, period or
Santhanam regression fixtures.
