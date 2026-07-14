# Moira — Provenance & License Clarity

*This document answers, in one place, the questions a downstream developer or commercial user should be able to settle without reading source history: what Moira is licensed under, whether its implementation is independent, and how to read its earlier releases.*

---

## License

Moira is released under the **MIT License**, and will remain so. MIT permits commercial use, modification, and distribution — including building closed-source or paid products on top of Moira — with no copyleft and no AGPL obligations.

Moira was built deliberately as an independent, AGPL-free foundation, so that commercial builders can use it without the licensing entanglements that accompany Swiss Ephemeris–based stacks. That is the point of the project: a clean, permissively licensed engine you can ship commercially without contamination concerns.

## Independence of the implementation

Moira's astronomical and house-calculation code is **independently derived from primary sources** — spherical trigonometry, the defining geometric construction of each house system, and primary astronomical references (JPL DE441, IAU 2000A/2006) — and is validated against primary authorities (JPL Horizons, SOFA/ERFA, IERS). It does not incorporate Swiss Ephemeris source code.

A per-system account of the derivation basis, and of where Moira's discretionary choices diverge from convention, is published in [`HOUSE_SYSTEM_DIVERGENCE.md`](./wiki/01_doctrines/houses/HOUSE_SYSTEM_DIVERGENCE.md).

Note on resemblance: house geometry is mathematically forced — there is one correct way to trisect a semi-arc — so Moira's cusp values converge with any correct engine, including Swiss Ephemeris, at admissible latitudes. That convergence follows from shared mathematics and is **not** evidence of derivation.

## Astronomical data sources

The unified numbered-asteroid catalog is generated from JPL Horizons
heliocentric `VECTORS` states and materialized as Moira Type-13 shards. Its
ordered shard registration and per-body coverage exceptions are recorded in
`moira/kernels/asteroids/manifest.json`; the generated BSP files are separately
acquired runtime resources.

Icarus (1566) and Apollo (1862) are limited to their observational arcs because
their chaotic long-range solutions depend materially on the requested Horizons
interval. JPL SBDB is the authority only for those arc bounds and orbit-solution
identifiers; Horizons remains the authority for the vector samples. The exact
SBDB solution metadata used by a build is preserved in the manifest and unified
catalog metadata. Offline apparent-position fixtures use JPL Horizons
`OBSERVER`, center `500@399`, quantity 31, and are external authority evidence,
not self-generated Moira parity.

## Provenance history

Earlier in Moira's release history, during a licensing discussion with the Swiss Ephemeris authors, the house module carried — as a conservative precaution — an attribution notice referencing `swehouse.c`, and written permission was obtained from the authors. Moira's house implementation is independently derived from the mathematical definitions; the precautionary attribution was therefore determined to be unnecessary and was removed.

**Version timeline:**

| Releases | `swehouse.c` attribution notice | Status |
|---|---|---|
| 2.1.2 – 3.2.3 | Present (precautionary) | Available; retained for reproducibility |
| 3.2.4 and later | Removed | Independently derived; recommended for new work |

Earlier releases are intentionally left available rather than withdrawn, so that any pinned dependency continues to resolve. All releases are MIT-licensed.

## Guidance for downstream and commercial users

- **For new commercial or downstream work, build on 3.2.4 or later.** This line is independently derived and carries no third-party attribution.
- Moira is MIT-licensed across all releases; you may use, modify, and ship it commercially without copyleft obligations.
- The written permission referenced above was personal, precautionary diligence during the licensing discussion. The current implementation neither contains the referenced code nor relies on that permission.
- For license-scope questions about a specific use, use the project contact channel listed in the package or repository metadata.

---

*This document is the authoritative, standard-path record of Moira's license and provenance. It is intended to be discoverable without recourse to commit history.*
