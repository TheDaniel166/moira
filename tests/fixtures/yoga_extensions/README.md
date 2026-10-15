# VED-012 source fixtures

Owner: `moira/yoga_extensions.py`; evidence packet:
`wiki/06_roadmap/VEDIC_YOGA_EXTENSION_SOURCE_RESEARCH_2026-10-12.md`.

`source_cases.json` freezes 44 manually derived clause geometries. Every one
of the 21 admitted rule IDs has a positive and a counterexample; JP has
additional cases for its second movable-sign branch. Expected states were
specified from the research tables before running the evaluator. They are
not generated snapshots or a predictive-accuracy corpus. Supplementary unit
tests independently expand the wealth tables and royal branch geometry.

The separate `published_chart122` table transcribes Raman's printed D1/D9
signs. Its representative longitudes are **synthetic interior degrees**, not
published degrees and not a reconstruction of the historical birth chart.

| Witness | Passage; printed / one-based PDF pages | SHA-256 |
| --- | --- | --- |
| Sastri, *Jataka Parijata*, Vol. II, Ranjan | 7.14; 387 / 71 | `898de4c6f212c46e4376a64c3fd341bc64c8d11d6ace504a3acc25142a00b2dd` |
| Raman, *Three Hundred Important Combinations*, Motilal Banarsidass | 252; 245 / 255; Chart 122: 248 / 258 | `3d511f6237659d72ea590324fcc7c41c4403d2ac9266715872315b3d930646cc` |
| Santhanam, *BPHS*, Vol. I, Ranjan | 41.2–15: 402–405 / 401–404; 39.33–39: 395–396 / 394–395 | `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f` |

Exact printing years remain unestablished for these local scans. The
catalogue retains corpus-relative paths and the hash identifies the witness.
No copyrighted scans are redistributed in this fixture directory.

Refresh only after reviewing a changed source or explicitly selected
interpretation. Do not rewrite expected values to match current output.
BPHS 39.35 has a separate 84-case impossibility test for the rejected
all-to-all full-aspect reading; it has no executable formation fixture.
