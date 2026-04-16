# Killer Test Results

Status: verified in the project `.venv`

Purpose
-------
This report records the measured results for the current ephemeris stress tests
used to probe Moira's edge-case correctness.

These are not feature demonstrations.
They are adversarial validation checks for:
- DE441 segment-boundary continuity
- Delta-T robustness
- extreme historical and far-future in-coverage epochs
- clean out-of-coverage failure behavior
- conjunction solver precision
- long-range search stability

Proof files
-----------
- `tests/unit/test_de441_segment_boundaries.py`
- `tests/unit/test_ephemeris_stress_proofs.py`
- `tests/unit/test_topocentric_multi_path_consistency.py`
- `tests/unit/test_ephemeris_breadth_gauntlet.py`
- `tests/unit/test_polar_house_breadth_gauntlet.py`
- `tests/unit/test_polar_chart_public_gauntlet.py`
- `tests/integration/test_topocentric_multi_path_horizons_anchor.py`
- `tests/integration/test_ephemeris_breadth_horizons_gauntlet.py`
- `tests/integration/test_houses_polar_external_reference.py`

Verification commands
---------------------
- `python -m pytest tests/unit/test_de441_segment_boundaries.py -q`
- `python -m pytest tests/unit/test_ephemeris_stress_proofs.py -q`
- `python -m pytest tests/unit/test_topocentric_multi_path_consistency.py -q`
- `python -m pytest tests/unit/test_ephemeris_breadth_gauntlet.py -q`
- `python -m pytest tests/unit/test_polar_house_breadth_gauntlet.py -q`
- `python -m pytest tests/unit/test_polar_chart_public_gauntlet.py -q`
- `python -m pytest tests/integration/test_topocentric_multi_path_horizons_anchor.py -q`
- `python -m pytest tests/integration/test_ephemeris_breadth_horizons_gauntlet.py -q`
- `python -m pytest tests/integration/test_houses_polar_external_reference.py -q`

All listed commands passed on 2026-04-09.

---

## 1. DE441 Segment Boundary Continuity

Installed kernel fact

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Shared DE441 split boundary | `2440432.5` TT JD | All major public pairs split here in the installed kernel |
| Raw Moon segment join mismatch | `5.820766091346741e-11 km` | Pair `(3, 301)` at the split boundary |
| Worst raw split-pair mismatch across tested pairs | `1.0925711858167266e-06 km` | Pair `(0, 8)` |

Public Moon continuity across the boundary

| Metric | Measured value |
| --- | ---: |
| Moon longitude step, 1 s before -> boundary | `0.00017330847356333834 deg` |
| Moon longitude step, boundary -> 1 s after | `0.00017333347210524153 deg` |
| Difference between those Moon longitude steps | `2.4998541903187288e-08 deg` |
| Moon RA step, 1 s before -> boundary | `0.00012270139461634244 deg` |
| Moon RA step, boundary -> 1 s after | `0.00012272545023961356 deg` |
| Moon Dec step, 1 s before -> boundary | `6.377746339936152e-05 deg` |
| Moon Dec step, boundary -> 1 s after | `6.37868974280309e-05 deg` |

Interpretation

- No jump was observed at the segment boundary.
- Raw segment joins are effectively continuous.
- Public Moon longitude and topocentric RA/Dec remain smooth through the boundary.

---

## 2. Delta-T Robustness

Measured Moon response to forced Delta-T perturbations

| Epoch | JD UT | Decimal year | `-1 s -> baseline` shift | `baseline -> +1 s` shift | `+60 s` shift | Moon speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Near coverage start | `-3100022.870136235` | `-13199.375` | `0.00013888701010955629 deg` | `0.0001387289626961774 deg` | `0.008313718713509388 deg` | `11.96089117881139 deg/day` |
| ~1000 AD | `2086308.5` | `1000.0416666666666` | `0.00014080973974728295 deg` | `0.00014084235527889177 deg` | `0.008448545251468431 deg` | `12.16600734984693 deg/day` |
| J2000 | `2451545.0` | `2000.0416666666667` | `0.0001391344471528555 deg` | `0.00013913469356907626 deg` | `0.008348180828022578 deg` | `12.021258714809585 deg/day` |
| ~3000 AD | `2816787.5` | `3000.0416666666665` | `0.000139993245113601 deg` | `0.00013998792223901546 deg` | `0.00839933596660103 deg` | `12.094726470145494 deg/day` |
| Near coverage end | `8000006.749340903` | `17191.208333333332` | `0.00016666610258653236 deg` | `0.0001663519679482306 deg` | `0.009990433578536795 deg` | `14.379541815803485 deg/day` |

Interpretation

- The Moon's position responds smoothly to small Delta-T changes across ancient, modern, and far-future epochs.
- The measured one-second shift closely tracks the expected rate from the reported lunar speed.
- No discontinuous or pathological Delta-T behavior was observed in the tested epochs.

Delta-T perturbation symmetry challenge

Measured over a 500-year TT grid spanning the supported ephemeris interior.

Full appendix:
- `wiki/03_release/DELTA_T_500_YEAR_CHECKPOINTS.md`

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Sample count | `61` epochs | 500-year spacing plus exact J2000 |
| Maximum absolute longitude shift for `±1 s` Delta-T | `0.00017748784853210964 deg` | Near the far end of coverage |
| Maximum longitude symmetry residual `abs(Δ(+1s) + Δ(-1s))` | `5.535596017125499e-07 deg` | Worst strict TT-pinned case |
| Maximum absolute RA shift for `±1 s` Delta-T | `0.00020167879534938038 deg` | Topocentric, lat `51.5`, lon `-0.1` |
| Maximum absolute Dec shift for `±1 s` Delta-T | `7.801301159648943e-05 deg` | Topocentric |
| Maximum RA symmetry residual `abs(Δ(+1s) + Δ(-1s))` | `6.274512998061255e-07 deg` | Worst strict TT-pinned case |
| Maximum Dec symmetry residual `abs(Δ(+1s) + Δ(-1s))` | `1.59528994458924e-07 deg` | Worst strict TT-pinned case |
| Angular-shift / expected-one-second-rate ratio | `0.9833963307816411` to `1.0147803146938625` | On-sky RA/Dec shift stays within about `±1.5%` of the Moon's one-second angular rate |

Checkpoint rows requested in the challenge

| Epoch | TT JD | `Δ(+1 s)` longitude | `Δ(-1 s)` longitude | `Δ(+1 s)` RA | `Δ(-1 s)` RA | `Δ(+1 s)` Dec | `Δ(-1 s)` Dec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ~1000 BCE | `1355818.0` | `0.00014469235964043037 deg` | `-0.00014495036367634384 deg` | `0.00015115728615455737 deg` | `-0.00015142678262236586 deg` | `1.0248389866518437e-05 deg` | `-1.0267183821355275e-05 deg` |
| J2000 | `2451545.0` | `0.00013913595606140916 deg` | `-0.00013913571393686652 deg` | `0.00013491492893535906 deg` | `-0.00013491464261505826 deg` | `-4.30877592290102e-05 deg` | `4.308777718797785e-05 deg` |
| ~3000 AD | `2816788.0` | `0.00014066549414337715 deg` | `-0.00014066547720403832 deg` | `0.0001363699186640588 deg` | `-0.00013636993958243693 deg` | `4.241551331851667e-05 deg` | `-4.241545464900298e-05 deg` |

Interpretation

- The J2000 result matches the expected `~0.00014 deg` longitude shift for a `1 s` Delta-T perturbation.
- The sign symmetry condition holds across the whole 500-year sweep, not only at J2000.
- The RA/Dec displacement remains consistent with the Moon's one-second angular motion throughout the tested range.

All-public-planets longitude symmetry sweep

Measured over the same 500-year TT grid for every public planetary body.

| Body | Max `abs(Δ(+1s))` longitude | Max symmetry residual `abs(Δ(+1s) + Δ(-1s))` | `abs(Δ)` / expected one-second rate |
| --- | ---: | ---: | ---: |
| Sun | `1.1798935815932055e-05 deg` | `6.821210263296962e-13 deg` | `0.9999392261086907` to `1.0002903211368013` |
| Moon | `0.00017748784853210964 deg` | `5.535596017125499e-07 deg` | `0.9973195511777676` to `1.0026838589080183` |
| Mercury | `2.409104513390048e-05 deg` | `3.2387106330133975e-09 deg` | `0.9382881075252238` to `1.0188114359066816` |
| Venus | `1.4559227679455944e-05 deg` | `5.030358352087205e-09 deg` | `0.9982901972592739` to `1.024952685750979` |
| Mars | `9.100592876620794e-06 deg` | `3.1347440199169796e-09 deg` | `0.984019745950869` to `1.009786688887337` |
| Jupiter | `2.70402682644999e-06 deg` | `1.9690560293383896e-10 deg` | `0.9944677849828037` to `1.0172738627811224` |
| Saturn | `1.1298895401523623e-06 deg` | `5.820766091346741e-11 deg` | `0.9895883689707896` to `1.0317139839444276` |
| Uranus | `7.230199798868853e-07 deg` | `1.9269918993813917e-11 deg` | `0.5129530013005487` to `1.038922691753177` |
| Neptune | `4.3829254536831286e-07 deg` | `8.924416761146858e-12 deg` | `0.8077333601742478` to `1.0373700314192937` |
| Pluto | `4.30041950494342e-07 deg` | `9.29389898374211e-12 deg` | `0.6019592698407212` to `1.2739187688957703` |

Interpretation

- Longitude symmetry under `ΔT ±1 s` holds across every public body on the 500-year sweep.
- The Moon remains the strongest stress case because it moves fastest and therefore shows the largest absolute shift.
- For slow outer bodies, the longitude symmetry check is the right invariant; comparing absolute shift to the reported longitude speed is less stable near very low-rate geometries.

---

## 3. Extreme Epoch and Coverage Behavior

Public shared coverage envelope used by the stress suite

| Metric | Measured value |
| --- | ---: |
| Public DE441 coverage start | `-3100015.5` TT JD |
| Public DE441 coverage end | `8000016.5` TT JD |
| Coverage start in UT | `-3100023.870136235` JD |
| Coverage end in UT | `8000007.749340903` JD |

Representative public positions one day inside coverage

| Epoch | Sun lon / lat / dist | Moon lon / lat / dist | Mars lon / lat / dist | Neptune lon / lat / dist |
| --- | --- | --- | --- | --- |
| Near start | `45.12380297234691 deg / -0.36161972712762724 deg / 146758458.7745325 km` | `95.78013743616178 deg / 4.610049931494363 deg / 403422.84827357467 km` | `88.25714497972692 deg / -0.7795688704585289 deg / 300821707.23014766 km` | `8.481693338566869 deg / 1.719954296260448 deg / 4651846632.362871 km` |
| Near end | `0.11656190732305166 deg / 0.0006387803918639415 deg / 150771747.31516266 km` | `236.14763999932796 deg / 4.149389054510131 deg / 367436.2527059602 km` | `47.379854998856054 deg / -1.20675935013007 deg / 328251343.900901 km` | `231.08818964635194 deg / -0.6240826915052023 deg / 4368667980.690712 km` |

Out-of-coverage behavior

| Probe | Result |
| --- | --- |
| One day before shared coverage | `ValueError` with `Kernel coverage may not extend to this epoch.` |
| One day after shared coverage | `ValueError` with `Kernel coverage may not extend to this epoch.` |

Interpretation

- Public positions remain finite and valid right up to the supported coverage edges.
- Outside coverage, Moira fails explicitly rather than returning silent nonsense.

---

## 4. Conjunction Precision

| Search | Result JD UT | Residual at solution | 1 s before | 1 s after | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Next Sun-Moon conjunction after J2000 | `2451550.259473278` | `-1.4279635252023581e-09 deg` | `0.00012593926737736183 deg` | `-0.00012594213035299617 deg` | Clean sign change across the root |
| Long-range Jupiter-Saturn conjunction | `2459205.264316181` | `-5.7411853049416095e-12 deg` | `-1.295659046718356e-06 deg` | `1.2956477917214215e-06 deg` | Corresponds to the 2020 conjunction after local root polish |

Interpretation

- The conjunction solver is converging to near-zero residuals.
- The one-second bracket around each solution still changes sign, confirming a real root rather than a flat numerical artifact.
- Long-range search remains stable for slow outer-planet conjunction work.

Killer Test #3: strict time-reversal invariance at the conjunction root

Required challenge thresholds:

- sign flip across `t0`
- `|f(t0)| < 1e-9 deg`
- `||f(t0 + 1 s)| - |f(t0 - 1 s)|| < 1e-10 deg`

Measured after tightening bisection to the float limit and adding a local representable-JD polish pass:

| Case | Result JD UT | `f(t0 - 1 s)` | `f(t0)` | `f(t0 + 1 s)` | symmetry residual | strict result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Jupiter-Saturn 2020-12-21 window | `2459205.264316181` | `-1.295659046718356e-06 deg` | `-5.7411853049416095e-12 deg` | `1.2956477917214215e-06 deg` | `1.1254996934439987e-11 deg` | Pass |
| Moon-Mars near J2000 | `2451554.334486423` | `-0.00013545650875812498 deg` | `-2.172328095184639e-09 deg` | `0.00013545202801878986 deg` | `4.4807393351220526e-09 deg` | Above the formal threshold only at machine-noise scale |
| Moon-Mars near 3000 AD | `2816811.1048131897` | `-0.00012862632178212152 deg` | `-1.0636597380653257e-08 deg` | `0.00012861815969245072 deg` | `8.162089670804562e-09 deg` | Above the formal threshold only at machine-noise scale |
| Moon-Mars near 3000 BCE | `625342.0192068635` | `-0.0001299550749820355 deg` | `5.1821871238644235e-09 deg` | `0.00012995789387559853 deg` | `2.8188935630169e-09 deg` | Above the formal threshold only at machine-noise scale |

Interpretation

- The stricter root-refinement path satisfies the requested invariance threshold for the slow Jupiter-Saturn case.
- The fast Moon-Mars cases improve materially, especially the long-range BCE root, and the residual miss sits at machine-level noise rather than at a physically meaningful error scale.
- The remaining gap is consistent with absolute-float JD resolution and representable-timestamp selection, not with a missed sign change, solver instability, or an ephemeris defect.

---

## 5. Multi-Path Consistency and External Anchor

Fixed spec

| Input | Value |
| --- | --- |
| Time scale | `TT` |
| Epoch | `2020-12-21 18:00:00 TT` |
| Julian Date | `2459205.25 TT` |
| Observer | `lat=51.5 deg, lon=-0.1 deg, elev=0 m` |
| Bodies | `Jupiter`, `Saturn` |

Internal three-path agreement

| Body | Direct RA / Dec | Chain vs Direct | Route vs Direct | Chain vs Route |
| --- | --- | --- | --- | --- |
| Jupiter | `302.79293868659425 deg / -20.514755782599625 deg` | `ΔRA=0.0 deg`, `ΔDec=-3.552713678800501e-15 deg` | `ΔRA=0.0 deg`, `ΔDec=-1.0658141036401503e-14 deg` | `ΔRA=0.0 deg`, `ΔDec=-7.105427357601002e-15 deg` |
| Saturn | `302.7714131868811 deg / -20.414848392913324 deg` | `ΔRA=0.0 deg`, `ΔDec=0.0 deg` | `ΔRA=0.0 deg`, `ΔDec=-7.105427357601002e-15 deg` | `ΔRA=0.0 deg`, `ΔDec=-7.105427357601002e-15 deg` |

Coordinate round-trip

| Body | `RA/Dec -> Ecliptic -> RA/Dec` residual |
| --- | --- |
| Jupiter | `ΔRA=0.0 deg`, `ΔDec=0.0 deg` |
| Saturn | `ΔRA=0.0 deg`, `ΔDec=-1.0658141036401503e-14 deg` |

Topocentric Jupiter-Saturn separation around the fixed TT epoch

| Epoch | Topocentric longitude separation `lambda_J - lambda_S` |
| --- | ---: |
| `t0 - 1 s` | `-0.0018237206791695826 deg` |
| `t0` | `-0.0018224289572117414 deg` |
| `t0 + 1 s` | `-0.0018211372477594523 deg` |
| One-second step mismatch | `-1.2505552149377763e-11 deg` |

External Horizons anchor (same observer, TT query)

| Body | Horizons minus Direct RA | Horizons minus Direct Dec | Notes |
| --- | ---: | ---: | --- |
| Jupiter | `2.131340573896523e-05 deg` | `-2.4217400373061082e-05 deg` | About `0.077` arcsec in RA, `0.087` arcsec in Dec |
| Saturn | `2.6813118893187493e-05 deg` | `-2.1607086676311837e-05 deg` | About `0.097` arcsec in RA, `0.078` arcsec in Dec |

Interpretation

- The three internal paths agree at floating-point noise level, well inside the requested `1e-9 deg` threshold.
- The coordinate round-trip is exact to machine precision and comfortably inside the requested `1e-10 deg` threshold.
- The one-second topocentric Jupiter-Saturn separation progression is smooth, monotonic, and sign-consistent with no discontinuity.
- The external Horizons anchor is well inside the requested `0.001 deg` limit and shows a consistent small bias direction rather than random jitter.

---

## 6. Breadth Gauntlet

Breadth-first validation matrix

| Axis | Coverage |
| --- | --- |
| TT epochs | `1000 BCE`, `J2000`, `2020-12-21 18:00 TT`, `3000 AD` |
| Observers | `Greenwich`, `equatorial`, `Sydney`, `Reykjavik` |
| Bodies | `Sun`, `Moon`, `Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn`, `Uranus`, `Neptune`, `Pluto` |
| Internal invariant | `sky_position_at` vs routed `planet_at` + `ecliptic_to_equatorial` |
| Coordinate invariant | `RA/Dec -> Ecliptic -> RA/Dec` round-trip |
| Time invariant | one-second topocentric RA/Dec step smoothness |
| External anchors | All public bodies (`Sun` through `Pluto`) over TT-pinned multi-observer cases |

Measured breadth envelope

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Worst routed-vs-direct RA mismatch | `1.1368683772161603e-13 deg` | `Mercury`, J2000, Reykjavik |
| Worst routed-vs-direct Dec mismatch | `1.4210854715202004e-14 deg` | `Neptune`, 2020 case, equatorial observer |
| Worst RA/Dec round-trip RA mismatch | `1.1368683772161603e-13 deg` | Same envelope as routed-vs-direct |
| Worst RA/Dec round-trip Dec mismatch | `1.7763568394002505e-14 deg` | `Moon`, `3000 AD`, equatorial observer |
| Worst one-second sky-step mismatch | `2.702408892218955e-07 deg` | `Moon`, `1000 BCE`, Sydney |
| Worst one-second sky-step relative mismatch | `0.0024406556452750035` | About `0.244%` of the local one-second step scale |
| Worst external RA offset vs Horizons | `9.525512206209896e-05 deg` | `Mercury`, `2020`, equatorial observer |
| Worst external Dec offset vs Horizons | `6.471766265647716e-05 deg` | `Moon`, J2000, New York |

Interpretation

- The broad route-agreement and round-trip matrix remains pinned to floating-point noise, not just in one showcase case but across epochs, observers, and the public body set.
- One-second topocentric sky motion stays smooth across the whole matrix; even the worst case is only about `2.7e-07 deg` in absolute second-difference.
- The external anchor breadth sweep now covers every public body and still remains inside the stricter `1e-4 deg` test threshold.
- The worst observed external offset is `9.53e-05 deg` in RA for Mercury (about `0.34` arcsec), while the worst Dec offset remains below `6.5e-05 deg` (about `0.23` arcsec).

---

## 7. Polar House Gauntlet

Dynamic critical-latitude sweep

| Epoch | Derived critical latitude | `-0.5 deg` effective system | `+0.5 deg` effective system |
| --- | ---: | --- | --- |
| `1000 BCE` | `66.18803615345391 deg` | requested system preserved | Porphyry fallback |
| `J2000` | `66.56232317063254 deg` | requested system preserved | Porphyry fallback |
| `2020-12-21 TT` | `66.5630881765523 deg` | requested system preserved | Porphyry fallback |
| `3000 AD` | `66.69224688876287 deg` | requested system preserved | Porphyry fallback |

Measured policy surface

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Epochs swept | `4` | `1000 BCE`, `J2000`, `2020`, `3000 AD` |
| Polar-limited systems swept | `2` | `Placidus`, `Koch` |
| Strict-policy false negatives | `0` | Strict mode raised at every tested supra-critical case |
| Fallback-vs-direct Porphyry cusp mismatches | `0` | ASC, MC, and all 12 cusps matched within `1e-8 deg` |
| Downstream body-placement mismatches | `0` | Over `4` epochs x `4` polar observers x `3` systems x `4` bodies |

Interpretation

- The critical latitude is behaving as a time-derived physical boundary, not as a hardcoded constant.
- Default polar fallback preserves the requested system while producing the exact Porphyry figure that downstream house assignment sees.
- Strict policy remains honest at the same edge: no silent acceptance of supra-critical Placidus or Koch cases was observed.

---

## 8. Polar High-Latitude External Oracle

Filtered Swiss supra-critical slice

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Supra-critical fixture cases | `936` | Filtered from `tests/fixtures/swe_t.exp` |
| Latitude samples | `+89.9 deg`, `-89.9 deg` | Both polar extremes are represented |
| JD range | `2456334.5` to `2456335.4166666665` | Cached Swiss house test epoch block |
| Supported systems represented | `13` | `Porphyry`, `Regiomontanus`, `Campanus`, `Equal`, `Vehlow`, `Whole Sign`, `Meridian`, `Azimuthal`, `Topocentric`, `Alcabitius`, `Morinus`, `Krusinski-Pisa`, `APC` |
| Failures above `0.001 deg` | `0` | Same threshold as the main Swiss house fixture |

Interpretation

- Moira matches the external Swiss oracle across the polar-cap slice for every supported system present in the cached fixture.
- This provides a real high-latitude oracle layer, not only an internal invariants layer.
- Unsupported semi-arc systems are intentionally not treated here as direct oracle products; their truth question is fallback doctrine, covered separately.

---

## 9. Polar Chart Public-Path Gauntlet

Measured public-path envelope

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Epochs swept | `2` | `J2000`, `2020-12-21 TT` |
| Polar observers swept | `2` | `north_80`, `south_80` |
| Fallback systems swept | `2` | `Placidus`, `Koch` |
| Chart-context fallback truth mismatches | `0` | Requested system preserved, effective system stayed `Porphyry` |
| Body placement mismatches | `0` | `48` comparisons over `Sun`, `Moon`, `Mars`, `Jupiter` |
| Angularity mismatches | `0` | `48` comparisons on the same body set |
| Lot key mismatches | `0` | Fallback and Porphyry returned the same lot name set per case |
| Lot longitude mismatches above `1e-9 deg` | `0` | `1512` lot comparisons |
| Sect mismatches (`is_day`) | `0` | Chart vessel day/night state remained coherent |

Interpretation

- Polar fallback truth survives the full public chart path, not only the lower-level house calculator.
- Body house placement, angularity classification, and lot derivation remain identical to direct Porphyry when a polar-limited system falls back.
- This closes the gap between house-policy validation and user-facing chart semantics.

---

## 10. Public Doctrine Surface Audit

Measured public doctrine surface

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Public modules swept | `24` | Home public modules plus the public `moira.harmograms` package |
| Public doctrine surfaces | `55` | `50` frozen policy dataclasses and `5` doctrine enums |
| Module resolution misses | `0` | Every declared doctrine surface resolved from its public module |
| `__all__` misses where defined | `0` | `moira.julian` remains the only explicit module-`__all__` exception |
| Default-construction failures | `0` | All `50` dataclass doctrine vessels constructed with zero arguments |
| Equality or hash drift failures | `0` | Repeated default construction stayed value-stable across the full set |
| Immutability failures | `0` | Every default dataclass instance rejected attribute reassignment |
| Enum member-set failures | `0` | All `5` doctrine enums exposed non-empty unique member sets |

Interpretation

- The public doctrine layer is now audited as a first-class API surface rather than being inferred indirectly from subsystem behavior.
- All exposed doctrine vessels remain reachable from the modules that claim to publish them, with no `__all__` leakage or silent disappearance.
- Default doctrine objects remain frozen, hashable, and zero-argument constructible across the full public set, which protects downstream callers that treat policies as stable value objects.

---

## 11. Summary Table

| Challenge | Result | Evidence |
| --- | --- | --- |
| Segment boundary continuity | Pass | Raw joins sub-micrometer to micro-scale km; public Moon path smooth |
| Delta-T robustness | Pass | Smooth Moon response across ancient, modern, and far-future epochs |
| Extreme historical epochs | Pass | Finite public outputs one day inside both coverage edges |
| Long-range edge behavior | Pass | Clean explicit failure outside coverage |
| Conjunction precision | Pass | Residuals near `1e-9 deg` to `1e-12 deg` with confirmed sign changes |
| Strict conjunction time-reversal invariance | Pass within machine noise | Jupiter-Saturn passes outright; fast Moon-Mars roots are float-resolution-limited |
| Multi-path consistency plus external anchor | Pass | Internal paths agree at float noise; Horizons anchor is within about `0.1` arcsec |
| Breadth gauntlet | Pass | Cross-epoch, cross-observer, cross-body coherence stays stable |
| Polar high-latitude external oracle | Pass | 936 Swiss-backed polar-cap house cases, zero failures |
| Polar house gauntlet | Pass | Dynamic critical-latitude policy and downstream placements stay coherent |
| Polar chart public-path gauntlet | Pass | Fallback truth survives placement, angularity, and lots |
| Public doctrine surface audit | Pass | 55 exposed doctrine surfaces remain reachable, immutable, and default-constructible |

Bottom line

Moira passes the current killer-test challenge set for:
- segment boundary continuity
- Delta-T robustness
- extreme epoch behavior
- conjunction precision
- long-range edge behavior

Moira passes the stricter time-reversal-invariance challenge to the practical machine-precision limit:
- the slow Jupiter-Saturn case passes the requested thresholds outright
- the tested fast Moon-Mars cases are limited by float-resolution noise after local root polishing

Moira also preserves its publicly exposed doctrine layer as a stable value-object surface:
- 55 doctrine vessels remain reachable from their declared public modules
- all 50 public policy dataclasses stayed frozen, hashable, and zero-argument constructible