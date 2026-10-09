# Muhurta Backend Standard

Version: 0.2
Date: 2026-10-09
Scope: current Muhurta classification, score, personal overlay and bounded sampled search; separate named/source assessments

The current governing contract is [Personalized Muhurta policy and sampled search](MUHURTA_PERSONAL_SEARCH_STANDARD.md).
It supersedes the June P-GAP-02 restrictions that described only four routes,
five transport weights and no personalized or search admission.

[Named Muhurta](NAMED_MUHURTA_STANDARD.md) separately owns seven named
timing/presence families. [Panchanga Shuddhi](PANCHANGA_SHUDDHI_STANDARD.md)
owns VED-008 source-selected restrictions/exceptions and solved day cells.
These additions preserve the legacy scoring rules below. References to
unadmitted local-sunrise/Lagna behavior below concern the generic sampled
search, not the separate dated assessment products.

Current REST products:

- `POST /v1/muhurta/direct/classification`
- `POST /v1/muhurta/direct/score`
- `POST /v1/muhurta/chart/classification`
- `POST /v1/muhurta/chart/score`
- `POST /v1/muhurta/personal/score`
- `POST /v1/muhurta/search`

Seven validated weights are exposed and echoed. Classification applies no
numeric weights, generic scoring five, and personalized scoring seven. The
reserved `use_classical_ashubha_yoga` field remains fixed to True in the engine;
it is not a REST selector. No alternative rule set is silently acknowledged.

The five Panchanga limbs and existing Tara/Chandra evaluator own judgment.
Scores retain the raw unbounded scale and complete component evidence. Search
uses a closed UT1 sample grid, reader-bound TT/TDB and true ayanamsa, splits at
rejected samples, and ranks complete observed runs before applying the cap.
Its brackets and endpoints describe sampled evidence, not continuous or exact
transition times. JD-weekday Vara is explicit; local sunrise search, Lagna,
activity advice, Western electional judgment and additional traditional rules
remain unadmitted.

The linked standard owns policy, source limits, typed results, numerical caps,
compatibility changes and structured errors. The [validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md)
owns actual verification and its limits. Git publication, release and deployment
must not be inferred from local implementation.
