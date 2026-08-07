"""Reviewed Phase 9 and Phase 10 registry of admitted validation claims."""

from __future__ import annotations

from _pytest_plugins.evidence_schema import (
    Comparison,
    CoverageTarget,
    DeclaredField,
    EvidenceClass,
    EvidenceContract,
    EvidenceSource,
    SourceSet,
    contract_payload,
    contract_sha256,
    freeze_registry,
    validate_contract,
    validate_registry,
)


_COORDINATE_SPHERE_INVERSE = EvidenceContract(
    claim_id="MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1",
    product_surface="public ecliptic/equatorial spherical coordinate transforms",
    evidence_class=EvidenceClass.INVARIANT,
    governing_object=(
        "one unit direction acted on by an orthogonal x-axis obliquity "
        "rotation and its transpose inverse, compared as a Cartesian "
        "direction rather than by singular longitude at a pole"
    ),
    nodeids=(
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_spherical_coordinate_inverse_relation",
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_spherical_coordinate_boundary_atlas",
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_spherical_coordinate_canary_detects_post_observation_bias",
    ),
    proves=(
        "both public transform directions close on the same unit-sphere direction over the admitted interior property domain",
        "the explicit seam and polar atlas closes under the separately declared conditioning tolerance",
        "returned right ascensions and longitudes are finite canonical representatives and returned latitudes remain finite spherical coordinates",
        "a finite one-degree post-observation latitude bias is rejected by the exact production predicate",
    ),
    does_not_prove=(
        "external frame authority, epoch-dependent obliquity accuracy, or any astronomical body position",
        "correctness of a coordinated but mutually inverse wrong rotation",
        "the equatorial/horizontal transforms, whose current inverse has a separately recorded counterexample",
        "public rejection semantics for nonfinite or out-of-domain arguments",
    ),
    authorities=SourceSet.not_applicable(
        "this claim is the independently derived orthogonal-rotation inverse invariant, not an external software comparison"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="reviewed public-coordinate metamorphic test protocol",
            locator="tests/metamorphic/test_coordinate_relations.py",
            version="phase10_python_ast_v1_sphere_relation_atlas_and_canary",
            sha256="185df3e2917880754f9c01dd3882b0b2ab5f55631dacdce937a3d1032499d94d",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_spherical_coordinate_inverse_relation",
                "test_spherical_coordinate_boundary_atlas",
                "test_spherical_coordinate_canary_detects_post_observation_bias",
            ),
        ),
        EvidenceSource(
            name="reviewed public-coordinate observation and predicate protocol",
            locator="tests/support/metamorphic_coordinates.py",
            version="phase10_python_ast_v1_sphere_observation_and_predicate",
            sha256="3049d548926afd4ee4219779eb31f33d36c38611e5d6de8420f627343237b2ac",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "SphericalInverseObservation",
                "spherical_unit_vector",
                "observe_spherical_inverse",
                "assert_spherical_inverse",
            ),
        ),
        EvidenceSource(
            name="reviewed typed metamorphic failure primitive",
            locator="tests/support/metamorphic.py",
            version="phase10_python_ast_v1_typed_relation_failure",
            sha256="718e8d8d87d4df770f31ada8e31c299769076990fe43cc4b3db8a67412ab1266",
            local=True,
            hash_mode="python_ast_v1",
            symbols=("MetamorphicViolation", "require_relation"),
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the generated cases and explicit boundary atlas are not an external or prior-output corpus"
    ),
    frame=DeclaredField.declared(
        "right-handed ecliptic and equatorial spherical axes related only by the supplied x-axis obliquity rotation"
    ),
    origin=DeclaredField.declared(
        "common unit-sphere origin; only direction is evaluated"
    ),
    timescale=DeclaredField.not_applicable(
        "obliquity is an explicit numeric input and no epoch is evaluated"
    ),
    correction_policy=DeclaredField.declared(
        "pure geometric rotation only; no precession, nutation, aberration, parallax, or refraction"
    ),
    comparisons=(
        Comparison(
            metric="interior maximum unit-vector angular separation",
            unit="degrees",
            rule="vector_angle",
            absolute=1.0e-10,
            basis=(
                "binary64 trigonometric round-off over source latitudes and declinations in [-89, 89] degrees; calibrated adversarial maximum remained below 4.1e-12 degrees"
            ),
        ),
        Comparison(
            metric="polar-atlas maximum unit-vector angular separation",
            unit="degrees",
            rule="vector_angle",
            absolute=2.0e-6,
            basis=(
                "the current tangent/asin public formulas are ill-conditioned adjacent to a spherical pole; the exact nextafter and 89.999999-degree atlas measured below 2.1e-7 degrees while retaining a tenfold reviewed envelope"
            ),
        ),
        Comparison(
            metric="finite canonical output coordinate membership",
            unit="degrees and categorical membership",
            rule="exact",
            basis=(
                "longitudes and right ascensions must inhabit [0, 360), while spherical latitudes must inhabit [-90, 90]"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "the invariant rotates abstract directions rather than named bodies"
    ),
    interval=DeclaredField.declared(
        "property angles [-1440, 1440] degrees, source latitudes/declinations [-89, 89] degrees, obliquity [-30, 30] degrees, plus exact and nextafter longitude seams and polar coordinates through +/-90 degrees"
    ),
    resource_capability=DeclaredField.not_applicable(
        "the invariant is deterministic, kernel-free, and network-free"
    ),
    execution_paths=(
        "python:moira.coordinates.ecliptic_to_equatorial",
        "python:moira.coordinates.equatorial_to_ecliptic",
    ),
    exclusions=(
        "pole longitude is representational only and is never compared as geometric truth",
        "the relation helper rejects invalid inputs before the public functions, so it makes no public-refusal claim",
        "Hypothesis inherits the receipted profile and the explicit atlas, not unguided randomness alone, owns seams and poles",
    ),
    expected_refusal=(
        "nonfinite or out-of-domain relation inputs fail before a production transform is called",
        "noncanonical output, out-of-domain latitude, or vector residual above the conditioning-specific bound raises a typed MetamorphicViolation",
        "the named one-degree post-observation canary must fail through the maximum vector-separation predicate",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/coordinates.py",
            qualname="ecliptic_to_equatorial",
            phases=("run",),
            protected=True,
        ),
        CoverageTarget(
            path="moira/coordinates.py",
            qualname="equatorial_to_ecliptic",
            phases=("run",),
            protected=True,
        ),
    ),
)


_LONGITUDE_QUOTIENT = EvidenceContract(
    claim_id="MOIRA-COORD-LONGITUDE-QUOTIENT-V1",
    product_surface="public longitude normalization quotient representative",
    evidence_class=EvidenceClass.INVARIANT,
    governing_object=(
        "the quotient circle S1 = R / 360Z represented by the half-open "
        "canonical interval [0, 360), including idempotence, signed-zero "
        "ownership, and periodic equivalence"
    ),
    nodeids=(
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_longitude_quotient_relation",
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_longitude_quotient_boundary_atlas",
        "tests/metamorphic/test_coordinate_relations.py::"
        "test_longitude_quotient_canary_detects_noncanonical_zero",
    ),
    proves=(
        "normalization returns a finite representative in [0, 360) and is idempotent over the admitted domain",
        "adding an admitted integer multiple of 360 degrees preserves the represented longitude within the declared circular bound",
        "a normalized zero owns the positive IEEE-754 zero sign",
        "a finite zero-to-360 post-observation mutation is rejected by the exact half-open predicate",
    ),
    does_not_prove=(
        "accuracy of any coordinate transform or astronomical longitude",
        "bit-identical periodicity after arbitrary unbounded floating-point additions",
        "public rejection semantics for NaN, infinity, or non-real arguments",
    ),
    authorities=SourceSet.not_applicable(
        "this claim is the mathematical quotient and canonical-representative invariant"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="reviewed longitude quotient metamorphic test protocol",
            locator="tests/metamorphic/test_coordinate_relations.py",
            version="phase10_python_ast_v1_longitude_relation_atlas_and_canary",
            sha256="bdd7bd556121de42c5c0d45e78b88acf82df1c020c3d74ab37415d29bbf43179",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_longitude_quotient_relation",
                "test_longitude_quotient_boundary_atlas",
                "test_longitude_quotient_canary_detects_noncanonical_zero",
            ),
        ),
        EvidenceSource(
            name="reviewed longitude observation and predicate protocol",
            locator="tests/support/metamorphic_coordinates.py",
            version="phase10_python_ast_v1_longitude_observation_and_predicate",
            sha256="eea3175947de4c5bd18d70958ee21d2dbebc1f06d3aee63263e8cfaa6084a465",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "LongitudeQuotientObservation",
                "observe_longitude_quotient",
                "assert_longitude_quotient",
            ),
        ),
        EvidenceSource(
            name="reviewed typed metamorphic failure primitive",
            locator="tests/support/metamorphic.py",
            version="phase10_python_ast_v1_typed_relation_failure",
            sha256="718e8d8d87d4df770f31ada8e31c299769076990fe43cc4b3db8a67412ab1266",
            local=True,
            hash_mode="python_ast_v1",
            symbols=("MetamorphicViolation", "require_relation"),
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the generated cases and exact seam atlas are not an external corpus"
    ),
    frame=DeclaredField.declared(
        "one-dimensional angular quotient with a [0, 360) degree representative"
    ),
    origin=DeclaredField.declared(
        "the canonical representative is measured from the caller's unchanged zero meridian"
    ),
    timescale=DeclaredField.not_applicable(
        "longitude normalization has no epoch or clock coordinate"
    ),
    correction_policy=DeclaredField.not_applicable(
        "the quotient operation applies no astronomical corrections"
    ),
    comparisons=(
        Comparison(
            metric="circular period-shift residual",
            unit="degrees",
            rule="circular",
            absolute=1.0e-12,
            basis=(
                "bounded binary64 addition of at most sixteen 360-degree periods measured by shortest circular separation; a 500,000-case calibration remained below 4.55e-13 degrees"
            ),
        ),
        Comparison(
            metric="canonical interval, idempotence, and positive-zero sign",
            unit="categorical and IEEE-754 identity",
            rule="exact",
            basis=(
                "a canonical quotient representative must be half-open, stable under re-normalization, and must not preserve a negative zero sign"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "the quotient applies to abstract angles rather than named bodies"
    ),
    interval=DeclaredField.declared(
        "generated base angles [-360, 360] degrees, integer shifts [-16, 16], and exact/nextafter seams at 0, 180, and 360 degrees"
    ),
    resource_capability=DeclaredField.not_applicable(
        "the invariant is deterministic, kernel-free, and network-free"
    ),
    execution_paths=("python:moira.coordinates.normalize_degrees",),
    exclusions=(
        "unbounded shifts whose floating addition discards the base angle are outside the admitted conditioning domain",
        "the relation helper rejects nonfinite inputs before production and therefore makes no public-refusal claim",
    ),
    expected_refusal=(
        "nonfinite, non-real, or out-of-range relation controls fail before normalization",
        "noncanonical, non-idempotent, negative-zero, or over-tolerance observations raise a typed MetamorphicViolation",
        "the named canonical-zero-to-360 canary must fail through the half-open range predicate",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/coordinates.py",
            qualname="normalize_degrees",
            phases=("run",),
            protected=True,
        ),
    ),
)


_TIMESCALE_HYBRID_INVERSE = EvidenceContract(
    claim_id="MOIRA-TIMESCALE-HYBRID-UT1-TT-INVERSE-V1",
    product_surface="public default hybrid UT1/TT clock transforms",
    evidence_class=EvidenceClass.INVARIANT,
    governing_object=(
        "the clock graph F(u) = u + DeltaT(u) / 86400 from JD UT1 to "
        "JD TT, inverted on the same hybrid source-selection surface, with "
        "omitted and explicitly named default policy spellings equivalent"
    ),
    nodeids=(
        "tests/metamorphic/test_timescale_relations.py::"
        "test_hybrid_ut1_tt_inverse_relation",
        "tests/metamorphic/test_timescale_relations.py::"
        "test_hybrid_ut1_tt_boundary_atlas",
        "tests/metamorphic/test_timescale_relations.py::"
        "test_hybrid_clock_rejects_nonfinite_and_extreme_inputs",
        "tests/metamorphic/test_timescale_relations.py::"
        "test_hybrid_inverse_canary_detects_one_second_mutation",
    ),
    proves=(
        "default hybrid UT1 to TT to UT1 closes within two maximum binary64 coordinate ULPs over the admitted proleptic-year interval",
        "omitted and explicit DeltaTPolicy(model='hybrid') spellings are bit-identical in both directions",
        "the exact and nextafter calendar-policy boundary atlas retains the same inverse and default-equivalence properties",
        "both public clock transforms reject nonfinite and grossly unrepresentable JD coordinates with ValueError",
        "a finite one-second post-observation bias is rejected by the exact production predicate",
    ),
    does_not_prove=(
        "historical or future Delta-T accuracy, EOP authenticity, or agreement with an external time authority",
        "calendar/JD conversion bijection or calendar input-refusal semantics",
        "NASA-canon, fixed, or physical Delta-T policy behavior",
        "sub-ULP preservation near JD zero or correctness outside proleptic years -1000 through 5000",
    ),
    authorities=SourceSet.not_applicable(
        "this is a structural inverse/default invariant over Moira's declared hybrid graph, not authority validation of Delta-T values"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="reviewed hybrid timescale metamorphic test protocol",
            locator="tests/metamorphic/test_timescale_relations.py",
            version="phase10_python_ast_v1_hybrid_relation_atlas_refusal_and_canary",
            sha256="c67c5b597c558670298b68888853e4b2f004454857e5de0158e7c719909f295b",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_hybrid_ut1_tt_inverse_relation",
                "test_hybrid_ut1_tt_boundary_atlas",
                "test_hybrid_clock_rejects_nonfinite_and_extreme_inputs",
                "test_hybrid_inverse_canary_detects_one_second_mutation",
            ),
        ),
        EvidenceSource(
            name="reviewed hybrid clock observation and predicate protocol",
            locator="tests/support/metamorphic_timescales.py",
            version="phase10_python_ast_v1_hybrid_observation_and_predicate",
            sha256="81747876125998bffb0d4a0a4a343ce40e8aa11decbe250fb39a8be83d577ad8",
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "HybridInverseObservation",
                "observe_hybrid_inverse",
                "assert_hybrid_inverse",
            ),
        ),
        EvidenceSource(
            name="reviewed typed metamorphic failure primitive",
            locator="tests/support/metamorphic.py",
            version="phase10_python_ast_v1_typed_relation_failure",
            sha256="718e8d8d87d4df770f31ada8e31c299769076990fe43cc4b3db8a67412ab1266",
            local=True,
            hash_mode="python_ast_v1",
            symbols=("MetamorphicViolation", "require_relation"),
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the generated coordinates and explicit boundary atlas are not an external corpus"
    ),
    frame=DeclaredField.not_applicable(
        "the claim compares clock coordinates rather than spatial frames"
    ),
    origin=DeclaredField.declared(
        "both coordinates use the Julian Day origin; only the time-scale coordinate differs"
    ),
    timescale=DeclaredField.declared(
        "input and recovered coordinates are UT1; the intermediate coordinate is TT; Delta-T is TT minus UT1 in seconds"
    ),
    correction_policy=DeclaredField.declared(
        "omitted default and explicit immutable DeltaTPolicy(model='hybrid') using the same JD-aware EOP priority and long-range fallback surface"
    ),
    comparisons=(
        Comparison(
            metric="maximum hybrid UT1 round-trip residual",
            unit="maximum binary64 coordinate ULPs",
            rule="absolute",
            absolute=2.0,
            basis=(
                "the bound scales by the largest ULP of the input, intermediate, and recovered JD coordinates and matches the strongest existing month-sweep covenant"
            ),
        ),
        Comparison(
            metric="omitted versus explicit named hybrid result",
            unit="binary64 Julian Day identity",
            rule="exact",
            basis=(
                "the documented omitted policy is DeltaTPolicy(model='hybrid') and the two spellings must select the identical path"
            ),
        ),
        Comparison(
            metric="nonfinite and grossly unrepresentable public input refusal",
            unit="exception type",
            rule="exact",
            basis=(
                "the public clock transforms already declare and implement finite representable JD guards"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "clock conversion is independent of an astronomical body"
    ),
    interval=DeclaredField.declared(
        "JD UT1 [1355817.5, 3547272.5], corresponding to proleptic Gregorian years -1000 through 5000, plus exact and nextafter policy seams at -1000, -500, 0, 500, 1600, 1700, 1800, 1860, 1900, 1920, 1941, 1955, 1961, 1986, 2005, 2026, 2050, 2150, and 5000"
    ),
    resource_capability=DeclaredField.declared(
        "kernel-free and network-free; the hybrid path may consume the packaged read-only EOP record where its admitted coverage applies"
    ),
    execution_paths=(
        "python:moira.julian.ut_to_tt",
        "python:moira.julian.tt_to_ut",
    ),
    exclusions=(
        "the one-ULP-scale relation excludes the ill-conditioned near-zero JD coordinate and all years outside the reviewed interval",
        "raw native calendar conversion is not called with invalid values because its refusal policy is not yet governed",
        "the canary mutates only an immutable observation and is predicate sensitivity, not Phase 11 source mutation",
    ),
    expected_refusal=(
        "the relation helper rejects nonfinite or out-of-interval property coordinates before clock transformation",
        "the public clock functions raise ValueError for NaN, infinity, and grossly unrepresentable finite JD values",
        "default-policy drift, a round-trip residual above two coordinate ULPs, or the named one-second canary raises a typed MetamorphicViolation",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/julian.py",
            qualname="ut_to_tt",
            phases=("run",),
            protected=True,
        ),
        CoverageTarget(
            path="moira/julian.py",
            qualname="tt_to_ut",
            phases=("run",),
            protected=True,
        ),
    ),
)


_SPK_CONTENT_IDENTITY = EvidenceContract(
    claim_id="MOIRA-SPK-CONTENT-IDENTITY-V1",
    product_surface="SpkReader content-derived ephemeris identity",
    evidence_class=EvidenceClass.INVARIANT,
    governing_object=(
        "one coherent DAF/SPK ASCII summary-label identity mapped to an "
        "immutable planetary/lunar ephemeris identity independently of pathname"
    ),
    nodeids=(
        "tests/unit/test_spk_kernel_identity.py::"
        "test_mixed_summary_identities_fail_closed_and_release_kernel",
        "tests/unit/test_spk_kernel_identity.py::"
        "test_spk_reader_identity_comes_from_summary_content_not_filename",
    ),
    proves=(
        "recognized coherent DE/LE summary labels determine the published identity rather than the filename",
        "the resulting identity vessel is immutable",
        "mixed recognized identities fail closed and release the opened kernel",
    ),
    does_not_prove=(
        "real BSP byte parsing or file authenticity",
        "JPL trajectory accuracy, segment coverage, frame correctness, or native support",
        "identity semantics for unexamined summary-label families",
    ),
    authorities=SourceSet.not_applicable(
        "this claim is an internal content/filename invariant, not an external-authority comparison"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="reviewed SPK identity executable test protocol",
            locator="tests/unit/test_spk_kernel_identity.py",
            version="phase9_python_ast_v1_exact_cases_and_assertions",
            sha256=(
                "bde82ba6cc1c973f55b07f8b884801b17f4b8d5deb47cd527c586d3e4d4ef02f"
            ),
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_mixed_summary_identities_fail_closed_and_release_kernel",
                "test_spk_reader_identity_comes_from_summary_content_not_filename",
            ),
        )
    ),
    corpora=SourceSet.not_applicable(
        "the claim compares no external or prior-output corpus"
    ),
    frame=DeclaredField.not_applicable(
        "kernel identity metadata is not a coordinate-frame product"
    ),
    origin=DeclaredField.not_applicable(
        "kernel identity metadata has no vector origin"
    ),
    timescale=DeclaredField.not_applicable(
        "kernel identity metadata does not evaluate an epoch"
    ),
    correction_policy=DeclaredField.not_applicable(
        "kernel identity metadata applies no astronomical correction model"
    ),
    comparisons=(
        Comparison(
            metric="summary label to immutable DE/LE/tidal identity mapping",
            unit="categorical identity plus arcseconds per century squared",
            rule="exact",
            basis=(
                "the admitted mapping and mixed-identity refusal are discrete "
                "policy products with no numerical tolerance"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "the synthetic segment is not used to establish any body ephemeris"
    ),
    interval=DeclaredField.not_applicable(
        "the identity mapping is independent of segment epoch coverage"
    ),
    resource_capability=DeclaredField.not_applicable(
        "the opened kernel and catalog are synthetic; no real planetary resource is admitted"
    ),
    execution_paths=(
        "python:moira.spk_reader.SpkReader.__init__",
        "python:moira.spk_reader._ephemeris_kernel_identity_from_catalog",
    ),
    exclusions=(
        "unrecognized but coherent labels remain representable as unknown and are outside this mapping claim",
        "malicious monkeypatching or in-process evidence forgery is outside the cooperative harness boundary",
    ),
    expected_refusal=(
        "mixed recognized summary identities raise ValueError and close the opened kernel",
        "unknown, malformed, or stale contract metadata fails pytest collection",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/spk_reader.py",
            qualname="SpkReader.__init__",
            phases=("run",),
            protected=True,
        ),
        CoverageTarget(
            path="moira/spk_reader.py",
            qualname="_ephemeris_kernel_identity_from_catalog",
            phases=("run",),
            protected=True,
        ),
    ),
)


_HOUSE_EQUATORIAL_ECLIPTIC_ROUND_TRIP = EvidenceContract(
    claim_id="MOIRA-HOUSE-EQUATORIAL-ECLIPTIC-ROUNDTRIP-V1",
    product_surface="house projection equatorial/ecliptic direction helpers",
    evidence_class=EvidenceClass.INVARIANT,
    governing_object=(
        "forward obliquity rotation of an ecliptic-plane unit direction into "
        "equatorial axes followed by the inverse rotation and circular longitude recovery"
    ),
    nodeids=(
        "tests/unit/test_house_projection_geometry.py::"
        "test_equatorial_ecliptic_round_trip",
    ),
    proves=(
        "the two named house-geometry helpers are inverse within the declared circular tolerance for the admitted longitude/obliquity grid",
        "recovered longitude remains in the canonical [0, 360) degree range",
    ),
    does_not_prove=(
        "the public moira.coordinates API or latitude-bearing three-dimensional transforms",
        "the astronomical truth of any obliquity model, epoch, house cusp, or frame realization",
        "conditioning outside the five longitudes and three obliquities in the admitted grid",
    ),
    authorities=SourceSet.not_applicable(
        "the proof is the independently derived inverse-rotation invariant rather than an external software oracle"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="reviewed house round-trip executable test protocol",
            locator="tests/unit/test_house_projection_geometry.py",
            version="phase9_python_ast_v1_exact_grid_and_assertions",
            sha256=(
                "4a4f8ea031fbf492bdf059521c0e6567394da61a439cfdc2c5d1f2ee57f81808"
            ),
            local=True,
            hash_mode="python_ast_v1",
            symbols=("test_equatorial_ecliptic_round_trip",),
        ),
        EvidenceSource(
            name="reviewed numeric assertion dependency protocol",
            locator="tests/support/numeric_assertions.py",
            version="phase9_python_ast_v1_house_assertion_closure",
            sha256=(
                "646e6749bd3c37af1814d5214685e2456350e4be6cb4aedc2ec124a581dcf875"
            ),
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "assert_canonical_longitude_degrees",
                "assert_circular_degrees",
            ),
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the claim compares no external or prior-output corpus"
    ),
    frame=DeclaredField.declared(
        "right-handed equatorial axes and ecliptic plane related by the supplied x-axis obliquity rotation"
    ),
    origin=DeclaredField.declared(
        "common unit-sphere origin; only direction is evaluated"
    ),
    timescale=DeclaredField.not_applicable(
        "obliquity is an explicit numeric input and no epoch-to-obliquity model is evaluated"
    ),
    correction_policy=DeclaredField.declared(
        "pure geometric rotation only; no precession, nutation, aberration, or refraction"
    ),
    comparisons=(
        Comparison(
            metric="circular recovered-minus-input ecliptic longitude",
            unit="degrees",
            rule="circular",
            absolute=1e-12,
            basis=(
                "binary64 forward/inverse rotation of normalized unit directions; "
                "the bound covers accumulated trigonometric round-off"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "the invariant rotates abstract directions rather than astronomical bodies"
    ),
    interval=DeclaredField.declared(
        "longitudes {0, 17.5, 90, 183.25, 359.9} degrees crossed with obliquities {22, 23.4392911, 24.5} degrees"
    ),
    resource_capability=DeclaredField.not_applicable(
        "the invariant is deterministic and kernel-free"
    ),
    execution_paths=(
        "python:moira.houses._equatorial_ecliptic_direction",
        "python:moira.houses._ecliptic_longitude_from_equatorial_vector",
    ),
    exclusions=(
        "degenerate, nonfinite, and latitude-bearing vector inputs are not exercised by this admitted grid",
        "cooperative coverage attribution is not a security boundary against hostile in-process code",
    ),
    expected_refusal=(
        "a noncanonical result or circular residual above 1e-12 degrees fails the test",
        "missing or malformed evidence metadata fails collection",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/houses.py",
            qualname="_equatorial_ecliptic_direction",
            phases=("run",),
            protected=True,
        ),
        CoverageTarget(
            path="moira/houses.py",
            qualname="_ecliptic_longitude_from_equatorial_vector",
            phases=("run",),
            protected=True,
        ),
    ),
)


_DOROTHEAN_TRIPLICITY_PINGREE = EvidenceContract(
    claim_id="MOIRA-DOROTHEAN-TRIPLICITY-PINGREE1976-V1",
    product_surface="Dorothean triplicity assignment doctrine",
    evidence_class=EvidenceClass.AUTHORITY,
    governing_object=(
        "the Dorothean day, night, and participating triplicity rulers for "
        "each of the four elemental sign groups under the named Pingree 1976 edition"
    ),
    nodeids=(
        "tests/unit/test_hellenistic_source_goldens.py::"
        "test_dorothean_triplicity_matches_the_named_pingree_table",
    ),
    proves=(
        "all twelve signs expose the source-owned element, day ruler, night ruler, and participating ruler",
        "sect selects the named day or night ruler for every admitted sign",
    ),
    does_not_prove=(
        "translation authenticity, manuscript consensus, or superiority over another historical lineage",
        "birth-chart sect determination, dignity scoring, interpretation, or any other Hellenistic doctrine",
        "the correctness of source tables not named by this claim",
    ),
    authorities=SourceSet.declared(
        EvidenceSource(
            name="Dorotheus of Sidon, Carmen Astrologicum, Book I chapter 1",
            locator=(
                "David Pingree edition and translation, Teubner, Leipzig, 1976"
            ),
            version="identified_edition_direct_table",
        ),
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="hand-transcribed Hellenistic source tables",
            locator="tests/golden/hellenistic_source_tables.json",
            version="hellenistic_source_tables_v1",
            sha256=(
                "b7ca01dfdc03b46d787f6ea981c88842547bc5fab636689bfedd39e673f8f291"
            ),
            local=True,
        ),
        EvidenceSource(
            name="reviewed Dorothean executable test protocol",
            locator="tests/unit/test_hellenistic_source_goldens.py",
            version="phase9_python_ast_v1_exact_source_assertions",
            sha256=(
                "6a720901b6afbaff4864ec5183487097a85843590f0dd70b67d99377696ea495"
            ),
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_dorothean_triplicity_matches_the_named_pingree_table",
            ),
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the named source-owned fixture is one reviewed table, not a statistical corpus"
    ),
    frame=DeclaredField.declared(
        "tropical zodiac sign identity grouped by fire, earth, air, and water triplicities"
    ),
    origin=DeclaredField.not_applicable(
        "categorical sign/ruler doctrine has no geometric origin"
    ),
    timescale=DeclaredField.not_applicable(
        "the doctrine table is timeless; only day/night sect is selected"
    ),
    correction_policy=DeclaredField.not_applicable(
        "the categorical doctrine applies no astronomical correction model"
    ),
    comparisons=(
        Comparison(
            metric="element and triplicity-ruler categorical identity",
            unit="zodiac sign, element, and planet names",
            rule="exact",
            basis=(
                "the fixture is independently hand-transcribed from the named edition and must never be regenerated from Moira output"
            ),
        ),
    ),
    bodies=DeclaredField.declared(
        "Sun, Moon, Mercury, Venus, Mars, Jupiter, and Saturn as source-named rulers"
    ),
    interval=DeclaredField.declared(
        "all twelve zodiac signs under both day-chart and night-chart sect branches"
    ),
    resource_capability=DeclaredField.declared(
        "read-only exact SHA-256-bound tests/golden/hellenistic_source_tables.json"
    ),
    execution_paths=(
        "python:moira.triplicity.triplicity_assignment_for",
    ),
    exclusions=(
        "online-witness availability is not required at test time",
        "the fixture records one identified edition and does not claim scholarly unanimity",
    ),
    expected_refusal=(
        "fixture content or hash drift fails contract validation before execution",
        "any source-table mismatch fails exact comparison without baseline regeneration",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/triplicity.py",
            qualname="triplicity_assignment_for",
            phases=("run",),
            protected=True,
        ),
    ),
)


_NUTATION_2000A_NATIVE_PARITY = EvidenceContract(
    claim_id="MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1",
    product_surface="packaged nutation scalar-series Python/native boundary",
    evidence_class=EvidenceClass.NATIVE_PARITY,
    governing_object=(
        "the exact SHA-256-bound packaged coefficient rows after the current "
        "parser materializes 1,358 luni-solar and 1,056 planetary 16-field "
        "terms, partitioned at the admitted j=0 boundaries and evaluated by "
        "the governing Python scalar path and admitted native path"
    ),
    nodeids=(
        "tests/unit/test_native_nutation_2000a.py::"
        "test_native_nutation_2000a_matches_scalar_reference",
    ),
    proves=(
        "native and governing Python series evaluations agree for delta psi and delta epsilon at four admitted TT epochs",
        "the admitted parser output contains exactly 1,358 luni-solar terms and 1,056 planetary terms, every term has 16 fields, and the j=0 partitions end at 1,320 and 1,037 respectively",
        "both evaluations consume those same admitted parsed sequences",
    ),
    does_not_prove=(
        "IERS coefficient authenticity, completeness against the published tables, or ERFA/SOFA authority agreement",
        "the parser's acceptance or rejection semantics, row-to-source transcription fidelity, or authenticity of the packaged files",
        "accuracy outside the four epochs or universal Python/native parity",
        "precession, Earth-orientation, frame, or downstream apparent-position correctness",
    ),
    authorities=SourceSet.not_applicable(
        "this claim is parity over hash-bound packaged parser output; it does not revalidate that output against IERS, SOFA, or another external authority"
    ),
    fixtures=SourceSet.declared(
        EvidenceSource(
            name="IAU 2000A luni-solar coefficient table",
            locator="moira/data/iau2000a_ls.txt",
            version="packaged table current at Phase 9 admission",
            sha256=(
                "6da73bfe10873ac815520d00fffd67114d647a34afebc5946cfc275e73693f32"
            ),
            local=True,
        ),
        EvidenceSource(
            name="reviewed nutation parity executable test protocol",
            locator="tests/unit/test_native_nutation_2000a.py",
            version="phase9_python_ast_v1_exact_epochs_counts_and_assertions",
            sha256=(
                "14a6d5f9bc990d6f501cedbc98e8d5dad3d8f1de2cda3d1b0a17fd0f3da3e8b5"
            ),
            local=True,
            hash_mode="python_ast_v1",
            symbols=(
                "test_native_nutation_2000a_matches_scalar_reference",
            ),
        ),
        EvidenceSource(
            name="IAU 2000A planetary coefficient table",
            locator="moira/data/iau2000a_pl.txt",
            version="packaged table current at Phase 9 admission",
            sha256=(
                "f0dff02c78809b629cc64e2a9fbeffaea5ae20f67e1a62a0ed966f8624807557"
            ),
            local=True,
        ),
    ),
    corpora=SourceSet.not_applicable(
        "the parity grid is explicit and is not an independent authority corpus"
    ),
    frame=DeclaredField.declared(
        "IAU 2000A nutation in longitude and obliquity in the model's equator/ecliptic convention"
    ),
    origin=DeclaredField.declared(
        "geocentric Earth-orientation model"
    ),
    timescale=DeclaredField.declared(
        "Julian Date in Terrestrial Time (TT)"
    ),
    correction_policy=DeclaredField.declared(
        "the admitted hash-bound parsed luni-solar and planetary sequences only; no external-oracle correction or authority comparison is applied"
    ),
    comparisons=(
        Comparison(
            metric="native-minus-Python delta psi",
            unit="degrees",
            rule="absolute",
            absolute=1e-13,
            basis=(
                "both paths evaluate the same admitted registered parsed sequences; "
                "the bound admits only floating-point evaluation-order residual"
            ),
        ),
        Comparison(
            metric="native-minus-Python delta epsilon",
            unit="degrees",
            rule="absolute",
            absolute=1e-13,
            basis=(
                "both paths evaluate the same admitted registered parsed sequences; "
                "the bound admits only floating-point evaluation-order residual"
            ),
        ),
    ),
    bodies=DeclaredField.not_applicable(
        "the result is an Earth-orientation series pair, not a body ephemeris"
    ),
    interval=DeclaredField.declared(
        "JD TT {2415020.5, 2451545.0, 2460310.5, 2488069.5}"
    ),
    resource_capability=DeclaredField.declared(
        "current project CPython native extension plus exact SHA-256-bound packaged table bytes whose current parser output is constrained to 1,358/1,056 16-field terms with j=0 boundaries 1,320/1,037"
    ),
    execution_paths=(
        "python:moira.nutation_2000a._nutation_python",
        "native:moira._moira_native.nutation_2000a via moira.moira_native",
    ),
    exclusions=(
        "Python line coverage cannot establish execution inside the C++ body",
        "the packaged files' authority lineage and the parser's fidelity to the source publication require separate external validation",
        "cooperative coverage contexts are not resistant to hostile in-process forgery",
    ),
    expected_refusal=(
        "an unavailable native extension fails the admitted parity test rather than skipping",
        "term-count, 16-field-shape, or j=0-boundary drift fails the admitted parity test",
        "missing, changed, or hash-mismatched coefficient tables fail contract validation",
    ),
    coverage_targets=(
        CoverageTarget(
            path="moira/nutation_2000a.py",
            qualname="_nutation_python",
            phases=("run",),
            protected=True,
        ),
        CoverageTarget(
            path="moira/nutation_2000a.py",
            qualname="nutation_2000a",
            phases=("run",),
            protected=True,
        ),
    ),
)


CONTRACTS = freeze_registry(
    (
        _COORDINATE_SPHERE_INVERSE,
        _DOROTHEAN_TRIPLICITY_PINGREE,
        _HOUSE_EQUATORIAL_ECLIPTIC_ROUND_TRIP,
        _LONGITUDE_QUOTIENT,
        _NUTATION_2000A_NATIVE_PARITY,
        _SPK_CONTENT_IDENTITY,
        _TIMESCALE_HYBRID_INVERSE,
    )
)


def _required_comparison(
    claim_id: str,
    metric: str,
    *,
    rule: str,
    unit: str,
) -> Comparison:
    """Return one reviewed comparison or fail closed on contract drift."""

    contract = CONTRACTS.get(claim_id)
    if contract is None:
        raise RuntimeError(f"reviewed evidence contract is missing: {claim_id}")
    matches = tuple(
        comparison
        for comparison in contract.comparisons
        if comparison.metric == metric
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"{claim_id} must define exactly one {metric!r} comparison"
        )
    comparison = matches[0]
    if (
        comparison.rule != rule
        or comparison.unit != unit
        or comparison.absolute is None
    ):
        raise RuntimeError(
            f"{claim_id} comparison {metric!r} no longer has the reviewed "
            f"{rule} {unit} absolute-tolerance semantics"
        )
    return comparison


HOUSE_ROUND_TRIP_COMPARISON = _required_comparison(
    "MOIRA-HOUSE-EQUATORIAL-ECLIPTIC-ROUNDTRIP-V1",
    "circular recovered-minus-input ecliptic longitude",
    rule="circular",
    unit="degrees",
)
COORDINATE_SPHERE_INTERIOR_COMPARISON = _required_comparison(
    "MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1",
    "interior maximum unit-vector angular separation",
    rule="vector_angle",
    unit="degrees",
)
COORDINATE_SPHERE_POLAR_COMPARISON = _required_comparison(
    "MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1",
    "polar-atlas maximum unit-vector angular separation",
    rule="vector_angle",
    unit="degrees",
)
LONGITUDE_QUOTIENT_COMPARISON = _required_comparison(
    "MOIRA-COORD-LONGITUDE-QUOTIENT-V1",
    "circular period-shift residual",
    rule="circular",
    unit="degrees",
)
NUTATION_DPSI_PARITY_COMPARISON = _required_comparison(
    "MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1",
    "native-minus-Python delta psi",
    rule="absolute",
    unit="degrees",
)
NUTATION_DEPS_PARITY_COMPARISON = _required_comparison(
    "MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1",
    "native-minus-Python delta epsilon",
    rule="absolute",
    unit="degrees",
)
TIMESCALE_HYBRID_INVERSE_COMPARISON = _required_comparison(
    "MOIRA-TIMESCALE-HYBRID-UT1-TT-INVERSE-V1",
    "maximum hybrid UT1 round-trip residual",
    rule="absolute",
    unit="maximum binary64 coordinate ULPs",
)


__all__ = [
    "CONTRACTS",
    "COORDINATE_SPHERE_INTERIOR_COMPARISON",
    "COORDINATE_SPHERE_POLAR_COMPARISON",
    "HOUSE_ROUND_TRIP_COMPARISON",
    "LONGITUDE_QUOTIENT_COMPARISON",
    "NUTATION_DEPS_PARITY_COMPARISON",
    "NUTATION_DPSI_PARITY_COMPARISON",
    "TIMESCALE_HYBRID_INVERSE_COMPARISON",
    "Comparison",
    "CoverageTarget",
    "DeclaredField",
    "EvidenceClass",
    "EvidenceContract",
    "EvidenceSource",
    "SourceSet",
    "contract_payload",
    "contract_sha256",
    "validate_contract",
    "validate_registry",
]
