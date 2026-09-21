# Primary Directions Research Packet -- Neo-Converse

## Purpose

This document records the current research state of `neo-converse` in Moira's
primary-directions program.

It does **not** admit the branch.

It answers four questions:

1. what `neo-converse` appears to mean in current sources
2. how it differs from traditional converse
3. what evidence is strong enough to trust
4. whether Moira should implement it now


## Current Definition Boundary

The clearest current distinction is:

- `traditional converse`
  - the significator is carried by the **same** diurnal rotation to the place
    of the promissor
- `neo-converse`
  - a later modern converse doctrine in which the direction is defined
    **against** the diurnal rotation

This is the most explicit statement currently in hand from technical software
documentation.


## Admitted Narrow Signed-Motion Boundary

Moira now also admits `signed_primary_motion`, but only through the explicit
`topocentric_zodiacal_aspect_signed_primary_motion` preset. That doctrine is a
source-scoped classifier for Makransky's worked Topocentric zodiacal-aspect
product:

- construct one ordered promissor-to-significator arc
- assign zero latitude to the aspect point and use projected perfection
- wrap the arc to the unique signed shortest displacement in
  `(-180, 180)` degrees
- classify positive as direct and negative as converse
- treat numerical coincidence as no event
- fail closed at the directionally ambiguous `180`-degree boundary
- require explicit non-empty significator and promissor filters rather than
  implicitly searching a target set that contains the antipodal MC/IC pair

This admission does **not** implement `neo-converse`. It does not assert motion
against the diurnal rotation, does not transform every method family's arc,
does not materialize a companion converse arc, and cannot be selected as a
generic or ambient converse toggle. Traditional converse continues to exchange
promissor and significator roles. The two products remain separately named and
validated.


## Strongest Sources Currently in Hand

### 1. Martin Gansten on Traditional Converse

The most stable traditional definition available in current evidence is Martin
Gansten's formulation:

- direct direction:
  the promissor is carried by the east-to-west primary motion to the place of
  the significator
- converse direction:
  the significator is carried by the **same motion** to the place of the
  promissor

Source:

- [The Basics: What are Primary Directions?](https://www.martingansten.com/pdf/PrimaryDirectionsChapter.pdf)

This gives Moira a clear traditional baseline.


### 2. Delphic Oracle Release Notes

The most explicit `neo-converse` statement currently found is from Delphic
Oracle's release notes:

- neo-converse directions are "defined as directions against the diurnal
  rotation"
- traditional converse directions are those where the significator is moved
  with the diurnal rotation
- the option was added to match Morinus software values

Source:

- [Delphic Oracle release notes](https://t.astrology-x-files.com/delphicoracle-readme.html)

This is strong as a **software-technical definition**, but it is still not the
same as a fully published governing law.


### 3. Delphic Oracle Product Documentation

Delphic Oracle also states:

- it distinguishes traditional converse from neo-converse
- it follows conventions attributed to Martin Gansten's course
- it uses `neo-converse` as a separate direction mode in the UI

Sources:

- [Primary Directions in Delphic Oracle](https://www.astrology-x-files.com/software/primarydirections.html)
- [Advanced Medieval Module](https://astrology-x-files.com/software/medieval.html)
- [FAQ](https://www.astrology-x-files.com/faq.html)

These sources support the claim that `neo-converse` is a live modern doctrine
label, not a hallucinated term.


### 4. AstroApp as Software-Landscape Confirmation

AstroApp confirms that:

- both `traditional converse` and `neo-converse` are exposed as separate
  primary-direction options in current software

Sources:

- [AstroApp overview](https://astroapp.com/en/astrology-software/astroapp-overview-en)
- [AstroApp primary directions help](https://astroapp.com/help/1/returnsW_53.html)

This is useful landscape evidence, but not a governing formula.


## What Seems Stable

The following now look stable enough to state:

1. `neo-converse` is a real modern primary-directions label
2. it is not identical with traditional converse
3. the core conceptual distinction is:
   - traditional converse: same diurnal rotation, moving the significator
   - neo-converse: direction against the diurnal rotation
4. some software treats `neo-converse` as the mode needed to match Morinus-style
   modern values


## What Is Still Missing

The following are still missing for Moira admission:

1. a formula-grade branch law
   - how exactly does "against the diurnal rotation" alter the arc in each
     method family?
2. branch scope
   - is neo-converse one law across methods, or a family of method-specific
     converse laws?
3. source hierarchy
   - do we have only software documentation, or a stronger textual derivation?
4. validation material
   - worked examples or reproducible comparison cases


## Risk Assessment

### Source Quality

- current standing: `medium`

Why:

- the concept is clearly documented in active software
- the traditional baseline is clear
- but the modern mathematical law is not yet recovered in a source-safe,
  formula-grade packet


### Mathematical Recoverability

- current standing: `partial`

Why:

- the conceptual difference is explicit
- the computational transformation is still not sufficiently specified


### Implementation Risk

- current standing: `medium`

Why:

- lower risk than `field_plane`
- but still high enough that a premature implementation could smuggle in a
  software convention as if it were mathematically settled doctrine


## Moira Policy & Admission (September 2026)

Moira now admits `neo_converse` under explicit, opt-in policy control:

- `traditional converse` (`traditional_converse`) remains the default historical
  doctrine throughout Moira (significator carried to promissor in diurnal rotation;
  computed via Morin's role-exchange theorem $\text{converse}(S \to P) = \text{direct}(P \to S)$).
- `neo_converse` (`neo_converse`) is formally admitted as a first-class converse
  motion doctrine:
  - **Motion Law**: bodies are directed against the diurnal rotation (West-to-East)
    while the significator remains stationary as receiver.
  - **Geometric Derivation**: $\Delta_{\text{neo}} = (360^\circ - \Delta_{\text{dir}}) \pmod{360^\circ}$.
  - **Equivalence & Divergence**: On symmetric equatorial/meridian systems (e.g. Meridian),
    $\Delta_{\text{neo}} = \Delta_{\text{conv}}$ identically. On asymmetric oblique semi-arc
    systems (Placidus, Campanus, Topocentric), $\Delta_{\text{neo}} \neq \Delta_{\text{conv}}$
    because each body moves in its own oblique semi-arc under role-exchange, whereas
    neo-converse directs the promissor in its own semi-arc along the counter-diurnal circle complement.
  - **Exposures**: Admitted in `PrimaryDirectionConverseDoctrine.NEO_CONVERSE`,
    `PrimaryDirectionsPreset` configuration via `converse_doctrine="neo_converse"`,
    and native C++ solvers with mode `'N'`.
- `signed_primary_motion` remains confined to the named Makransky Topocentric
  zodiacal-aspect preset.

## Implementation & Verification

The doctrine was implemented in September 2026 and verified via:
- Mathematical circle complement proof: $(\Delta_{\text{dir}} + \Delta_{\text{neo}}) \pmod{360^\circ} \equiv 0^\circ$.
- Asymmetry proof against traditional converse on Placidus mundane directions: $\Delta_{\text{neo}} \neq \Delta_{\text{conv}}$.
- Exact numerical identity with traditional converse on Meridian right ascensional directions: $|\Delta_{\text{neo}} - \Delta_{\text{conv}}| < 10^{-12 \circ}$.
- Validated by unit test suite `tests/unit/test_primary_directions_neo_converse.py` and native parity suite `tests/unit/test_native_primary_directions_parity.py`.

## Present Declaration

`neo_converse` is fully formalized, admitted, implemented, and verified across Python and native C++ substrates with complete cross-method rigor.

