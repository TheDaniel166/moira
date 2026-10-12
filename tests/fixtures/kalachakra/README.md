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
