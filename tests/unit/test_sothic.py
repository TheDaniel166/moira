from __future__ import annotations

import pytest

from moira.sothic import (
    EPAGOMENAL_BIRTHS,
    _EGYPTIAN_YEAR_DAYS,
    _SOTHIC_EPOCH_139_JD,
    days_from_1_thoth,
    egyptian_civil_date,
    predicted_sothic_epoch_year,
    sothic_drift_rate,
)


def test_egyptian_civil_date_epoch_is_1_thoth() -> None:
    date = egyptian_civil_date(_SOTHIC_EPOCH_139_JD)

    assert date.month_name == "Thoth"
    assert date.month_number == 1
    assert date.day == 1
    assert date.season == "Akhet"
    assert date.day_of_year == 1
    assert date.epagomenal_birth is None
    assert date.computation_truth is not None
    assert date.computation_truth.jd == _SOTHIC_EPOCH_139_JD
    assert date.computation_truth.epoch_jd == _SOTHIC_EPOCH_139_JD
    assert date.computation_truth.wrapped_day_index == 0
    assert date.classification is not None
    assert date.classification.calendar_kind == "egyptian_civil"
    assert date.classification.wrap_kind == "mod_365"


def test_egyptian_civil_date_handles_month_and_epagomenal_boundaries() -> None:
    end_of_thoth = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 29)
    start_of_phaophi = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 30)
    first_epagomenal = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 360)
    fifth_epagomenal = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 364)

    assert end_of_thoth.month_name == "Thoth"
    assert end_of_thoth.day == 30

    assert start_of_phaophi.month_name == "Phaophi"
    assert start_of_phaophi.month_number == 2
    assert start_of_phaophi.day == 1

    assert first_epagomenal.month_name == "Epagomenal"
    assert first_epagomenal.month_number == 13
    assert first_epagomenal.day == 1
    assert first_epagomenal.epagomenal_birth == EPAGOMENAL_BIRTHS[0]

    assert fifth_epagomenal.month_name == "Epagomenal"
    assert fifth_epagomenal.day == 5
    assert fifth_epagomenal.epagomenal_birth == EPAGOMENAL_BIRTHS[4]


def test_days_from_1_thoth_wraps_cleanly() -> None:
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD) == pytest.approx(0.0, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD + 10.25) == pytest.approx(10.25, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD + _EGYPTIAN_YEAR_DAYS + 2.5) == pytest.approx(2.5, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD - 1.0) == pytest.approx(364.0, abs=1e-12)


def test_sothic_rising_preserves_computation_truth_without_changing_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 10.5)

    entries = s.sothic_rising(29.8, 31.3, 139, 139)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.jd_rising == pytest.approx(_SOTHIC_EPOCH_139_JD + 10.5, abs=1e-12)
    assert entry.computation_truth is not None
    assert entry.computation_truth.star_name == "Sirius"
    assert entry.computation_truth.latitude == pytest.approx(29.8, abs=1e-12)
    assert entry.computation_truth.longitude == pytest.approx(31.3, abs=1e-12)
    assert entry.computation_truth.epoch_jd == pytest.approx(_SOTHIC_EPOCH_139_JD, abs=1e-12)
    assert entry.computation_truth.arcus_visionis == pytest.approx(10.0, abs=1e-12)
    assert entry.computation_truth.search_days == 400
    assert entry.computation_truth.jd_rising == pytest.approx(entry.jd_rising, abs=1e-12)
    assert entry.computation_truth.drift_days == pytest.approx(entry.drift_days, abs=1e-12)
    assert entry.computation_truth.cycle_position == pytest.approx(entry.cycle_position, abs=1e-12)
    assert entry.classification is not None
    assert entry.classification.result_kind == "sothic_rising"
    assert entry.classification.star_kind == "sirius_heliacal"
    assert entry.classification.detection_kind == "delegated_heliacal_rising"
    assert entry.classification.tolerance_mode == "none"
    assert entry.egyptian_date.computation_truth is not None
    assert entry.egyptian_date.computation_truth.jd == pytest.approx(entry.jd_rising, abs=1e-12)


def test_sothic_epochs_preserve_epoch_detection_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    monkeypatch.setattr(
        s,
        "sothic_rising",
        lambda latitude, longitude, year_start, year_end, epoch_jd, arcus_visionis, policy=None: [
            s.SothicEntry(
                year=139,
                jd_rising=_SOTHIC_EPOCH_139_JD,
                date_utc=None,
                calendar_year=139,
                calendar_month=7,
                calendar_day=20,
                day_of_year=201,
                drift_days=0.0,
                cycle_position=0.0,
                egyptian_date=s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD, epoch_jd),
            )
        ],
    )

    epochs = s.sothic_epochs(29.8, 31.3, 139, 139, tolerance_days=1.0)

    assert len(epochs) == 1
    epoch = epochs[0]
    assert epoch.drift_days == pytest.approx(0.0, abs=1e-12)
    assert epoch.computation_truth is not None
    assert epoch.computation_truth.star_name == "Sirius"
    assert epoch.computation_truth.latitude == pytest.approx(29.8, abs=1e-12)
    assert epoch.computation_truth.longitude == pytest.approx(31.3, abs=1e-12)
    assert epoch.computation_truth.tolerance_days == pytest.approx(1.0, abs=1e-12)
    assert epoch.computation_truth.jd_rising == pytest.approx(_SOTHIC_EPOCH_139_JD, abs=1e-12)
    assert epoch.classification is not None
    assert epoch.classification.result_kind == "sothic_epoch"
    assert epoch.classification.star_kind == "sirius_heliacal"
    assert epoch.classification.detection_kind == "delegated_heliacal_rising"
    assert epoch.classification.tolerance_mode == "epoch_tolerance"


def test_predicted_sothic_epoch_year_uses_simple_cycle_arithmetic() -> None:
    assert predicted_sothic_epoch_year(139, 1) == pytest.approx(1599.0, abs=1e-12)
    assert predicted_sothic_epoch_year(139, -1) == pytest.approx(-1321.0, abs=1e-12)
    assert predicted_sothic_epoch_year(-1321, -1) == pytest.approx(-2781.0, abs=1e-12)


def test_sothic_drift_rate_recovers_wrapped_linear_trend() -> None:
    entries = []
    drift = 360.0
    for year in range(0, 10):
        entries.append(type("Entry", (), {"year": year, "drift_days": drift}))
        drift = (drift + 0.242) % _EGYPTIAN_YEAR_DAYS

    rate = sothic_drift_rate(entries)
    assert rate == pytest.approx(0.242, abs=1e-6)


def test_phase3_inspectability_properties_are_derived_only() -> None:
    import moira.sothic as s

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    assert date.calendar_kind == "egyptian_civil"
    assert date.wrap_kind == "mod_365"

    truth = s.SothicComputationTruth(
        star_name="Sirius",
        latitude=29.8,
        longitude=31.3,
        epoch_jd=_SOTHIC_EPOCH_139_JD,
        arcus_visionis=10.0,
        search_days=400,
        jd_start=_SOTHIC_EPOCH_139_JD - 200.0,
        jd_rising=_SOTHIC_EPOCH_139_JD,
        drift_days=0.0,
        cycle_position=0.0,
    )
    classification = s.SothicComputationClassification(
        result_kind="sothic_rising",
        star_kind="sirius_heliacal",
        detection_kind="delegated_heliacal_rising",
        tolerance_mode="none",
    )
    entry = s.SothicEntry(
        year=139,
        jd_rising=_SOTHIC_EPOCH_139_JD,
        date_utc=None,
        calendar_year=139,
        calendar_month=7,
        calendar_day=20,
        day_of_year=201,
        drift_days=0.0,
        cycle_position=0.0,
        egyptian_date=date,
        computation_truth=truth,
        classification=classification,
    )
    assert entry.result_kind == "sothic_rising"
    assert entry.star_kind == "sirius_heliacal"
    assert entry.detection_kind == "delegated_heliacal_rising"
    assert entry.tolerance_mode == "none"


def test_phase3_invariant_drift_fails_loudly() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="wrapped_day_index"):
        s.EgyptianCalendarTruth(
            jd=_SOTHIC_EPOCH_139_JD,
            epoch_jd=_SOTHIC_EPOCH_139_JD,
            elapsed_days=0.0,
            wrapped_day_index=365,
        )

    with pytest.raises(ValueError, match="classification must match computation_truth"):
        s.SothicEpoch(
            year=139,
            jd_rising=_SOTHIC_EPOCH_139_JD,
            date_utc=None,
            calendar_year=139,
            calendar_month=7,
            calendar_day=20,
            drift_days=0.0,
            computation_truth=s.SothicComputationTruth(
                star_name="Sirius",
                latitude=29.8,
                longitude=31.3,
                epoch_jd=_SOTHIC_EPOCH_139_JD,
                arcus_visionis=10.0,
                search_days=400,
                jd_start=_SOTHIC_EPOCH_139_JD - 200.0,
                jd_rising=_SOTHIC_EPOCH_139_JD,
                drift_days=0.0,
                tolerance_days=1.0,
            ),
            classification=s.SothicComputationClassification(
                result_kind="sothic_rising",
                star_kind="sirius_heliacal",
                detection_kind="delegated_heliacal_rising",
                tolerance_mode="none",
            ),
        )


def test_phase4_default_policy_preserves_existing_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 3.0)

    default_entries = s.sothic_rising(29.8, 31.3, 139, 139)
    explicit_entries = s.sothic_rising(29.8, 31.3, 139, 139, policy=s.DEFAULT_SOTHIC_POLICY)

    assert len(default_entries) == 1
    assert len(explicit_entries) == 1
    assert default_entries[0].jd_rising == pytest.approx(explicit_entries[0].jd_rising, abs=1e-12)
    assert default_entries[0].computation_truth is not None
    assert explicit_entries[0].computation_truth is not None
    assert default_entries[0].computation_truth.search_days == explicit_entries[0].computation_truth.search_days
    assert default_entries[0].computation_truth.arcus_visionis == pytest.approx(
        explicit_entries[0].computation_truth.arcus_visionis,
        abs=1e-12,
    )


def test_phase4_explicit_policy_can_narrow_doctrine(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    calls: list[dict[str, float | int]] = []

    def _fake_heliacal(*args, **kwargs):
        calls.append(kwargs)
        return _SOTHIC_EPOCH_139_JD + 5.0

    monkeypatch.setattr(s, "_heliacal_rising", _fake_heliacal)

    policy = s.SothicComputationPolicy(
        heliacal=s.SothicHeliacalPolicy(arcus_visionis=11.5, search_days=365),
        epoch=s.SothicEpochPolicy(tolerance_days=5.0),
        prediction=s.SothicPredictionPolicy(cycle_length_years=1461.0),
    )

    entries = s.sothic_rising(29.8, 31.3, 139, 139, policy=policy)
    epochs = s.sothic_epochs(29.8, 31.3, 139, 139, policy=policy)
    predicted = s.predicted_sothic_epoch_year(139, 1, policy=policy)

    assert len(entries) == 1
    assert calls[0]["arcus_visionis"] == pytest.approx(11.5, abs=1e-12)
    assert calls[0]["search_days"] == 365
    assert entries[0].computation_truth is not None
    assert entries[0].computation_truth.arcus_visionis == pytest.approx(11.5, abs=1e-12)
    assert entries[0].computation_truth.search_days == 365
    assert len(epochs) == 1
    assert epochs[0].computation_truth is not None
    assert epochs[0].computation_truth.tolerance_days == pytest.approx(5.0, abs=1e-12)
    assert predicted == pytest.approx(1600.0, abs=1e-12)


def test_phase4_invalid_policy_fails_clearly() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="SothicComputationPolicy"):
        s.sothic_rising(29.8, 31.3, 139, 139, policy="bad")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="arcus_visionis must be positive"):
        s.sothic_rising(
            29.8,
            31.3,
            139,
            139,
            policy=s.SothicComputationPolicy(
                heliacal=s.SothicHeliacalPolicy(arcus_visionis=0.0),
            ),
        )


def test_phase5_relations_are_explicit_and_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    assert date.relation is not None
    assert date.relation.kind == "egyptian_calendar"
    assert date.relation.basis == "civil_calendar_anchor"
    assert date.relation.anchor == "censorinus_139_epoch"
    assert date.relation_kind == "egyptian_calendar"

    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 2.0)
    entry = s.sothic_rising(29.8, 31.3, 139, 139)[0]
    assert entry.relation is not None
    assert entry.relation.kind == "sothic_rising"
    assert entry.relation.basis == "sirius_heliacal_rising"
    assert entry.relation.star_name == "Sirius"
    assert entry.relation_kind == "sothic_rising"


def test_phase5_relation_drift_fails_loudly() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="relation must match computation truth"):
        s.SothicEpoch(
            year=139,
            jd_rising=_SOTHIC_EPOCH_139_JD,
            date_utc=None,
            calendar_year=139,
            calendar_month=7,
            calendar_day=20,
            drift_days=0.0,
            computation_truth=s.SothicComputationTruth(
                star_name="Sirius",
                latitude=29.8,
                longitude=31.3,
                epoch_jd=_SOTHIC_EPOCH_139_JD,
                arcus_visionis=10.0,
                search_days=400,
                jd_start=_SOTHIC_EPOCH_139_JD - 200.0,
                jd_rising=_SOTHIC_EPOCH_139_JD,
                drift_days=0.0,
                tolerance_days=1.0,
            ),
            classification=s.SothicComputationClassification(
                result_kind="sothic_epoch",
                star_kind="sirius_heliacal",
                detection_kind="delegated_heliacal_rising",
                tolerance_mode="epoch_tolerance",
            ),
            relation=s.SothicRelation(
                kind="sothic_rising",
                basis="sirius_heliacal_rising",
                anchor="censorinus_139_epoch",
                star_name="Sirius",
            ),
        )


def test_phase6_relation_helpers_are_derived_only() -> None:
    import moira.sothic as s

    calendar_relation = s.SothicRelation(
        kind="egyptian_calendar",
        basis="civil_calendar_anchor",
        anchor="censorinus_139_epoch",
    )
    rising_relation = s.SothicRelation(
        kind="sothic_rising",
        basis="sirius_heliacal_rising",
        anchor="censorinus_139_epoch",
        star_name="Sirius",
    )
    epoch_relation = s.SothicRelation(
        kind="sothic_epoch",
        basis="sirius_heliacal_rising",
        anchor="censorinus_139_epoch",
        star_name="Sirius",
    )

    assert calendar_relation.is_calendar_relation is True
    assert calendar_relation.is_sothic_rising_relation is False
    assert rising_relation.is_sothic_rising_relation is True
    assert rising_relation.is_sothic_epoch_relation is False
    assert epoch_relation.is_sothic_epoch_relation is True

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    assert date.has_relation is True
    assert date.relation_kind == "egyptian_calendar"
    assert date.relation_basis == "civil_calendar_anchor"
    assert date.relation_anchor == "censorinus_139_epoch"


def test_phase6_invalid_relation_shapes_fail_loudly() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="must not preserve star_name"):
        s.SothicRelation(
            kind="egyptian_calendar",
            basis="civil_calendar_anchor",
            anchor="censorinus_139_epoch",
            star_name="Sirius",
        )

    with pytest.raises(ValueError, match="must preserve Sirius"):
        s.SothicRelation(
            kind="sothic_epoch",
            basis="sirius_heliacal_rising",
            anchor="censorinus_139_epoch",
            star_name="Regulus",
        )


def test_phase7_condition_profiles_are_derived_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    assert date.condition_profile is not None
    assert date.condition_state == "calendar_anchor"

    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 2.0)
    entry = s.sothic_rising(29.8, 31.3, 139, 139)[0]
    assert entry.condition_profile is not None
    assert entry.condition_state == "annual_rising"
    assert entry.condition_profile.star_kind == "sirius_heliacal"
    assert entry.condition_profile.tolerance_mode == "none"

    epoch = s.sothic_epochs(29.8, 31.3, 139, 139, tolerance_days=5.0)[0]
    assert epoch.condition_profile is not None
    assert epoch.condition_state == "epoch_alignment"
    assert epoch.condition_profile.star_kind == "sirius_heliacal"
    assert epoch.condition_profile.tolerance_mode == "epoch_tolerance"


def test_phase7_condition_profile_drift_fails_loudly() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="condition profile must match computation truth"):
        s.SothicEntry(
            year=139,
            jd_rising=_SOTHIC_EPOCH_139_JD,
            date_utc=None,
            calendar_year=139,
            calendar_month=7,
            calendar_day=20,
            day_of_year=201,
            drift_days=0.0,
            cycle_position=0.0,
            egyptian_date=s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD),
            computation_truth=s.SothicComputationTruth(
                star_name="Sirius",
                latitude=29.8,
                longitude=31.3,
                epoch_jd=_SOTHIC_EPOCH_139_JD,
                arcus_visionis=10.0,
                search_days=400,
                jd_start=_SOTHIC_EPOCH_139_JD - 200.0,
                jd_rising=_SOTHIC_EPOCH_139_JD,
                drift_days=0.0,
                cycle_position=0.0,
            ),
            classification=s.SothicComputationClassification(
                result_kind="sothic_rising",
                star_kind="sirius_heliacal",
                detection_kind="delegated_heliacal_rising",
                tolerance_mode="none",
            ),
            relation=s.SothicRelation(
                kind="sothic_rising",
                basis="sirius_heliacal_rising",
                anchor="censorinus_139_epoch",
                star_name="Sirius",
            ),
            condition_profile=s.SothicConditionProfile(
                result_kind="sothic_entry",
                condition_state=s.SothicConditionState("epoch_alignment"),
                relation_kind="sothic_epoch",
                relation_basis="sirius_heliacal_rising",
                star_kind="sirius_heliacal",
                tolerance_mode="epoch_tolerance",
            ),
        )


def test_phase8_chart_condition_profile_is_deterministic_and_aligned(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 2.0)
    entry = s.sothic_rising(29.8, 31.3, 139, 139)[0]
    epoch = s.sothic_epochs(29.8, 31.3, 139, 139, tolerance_days=5.0)[0]

    chart = s.sothic_chart_condition_profile(
        egyptian_dates=[date],
        entries=[entry],
        epochs=[epoch],
    )

    assert chart.profile_count == 3
    assert chart.calendar_anchor_count == 1
    assert chart.annual_rising_count == 1
    assert chart.epoch_alignment_count == 1
    assert len(chart.strongest_profiles) == 1
    assert chart.strongest_profiles[0].condition_state.name == "epoch_alignment"
    assert len(chart.weakest_profiles) == 1
    assert chart.weakest_profiles[0].condition_state.name == "calendar_anchor"


def test_phase8_chart_condition_profile_drift_fails_loudly() -> None:
    import moira.sothic as s

    profile = s.SothicConditionProfile(
        result_kind="sothic_epoch",
        condition_state=s.SothicConditionState("epoch_alignment"),
        relation_kind="sothic_epoch",
        relation_basis="sirius_heliacal_rising",
        star_kind="sirius_heliacal",
        tolerance_mode="epoch_tolerance",
    )

    with pytest.raises(ValueError, match="must match profiles|must sum to profile total"):
        s.SothicChartConditionProfile(
            profiles=(profile,),
            calendar_anchor_count=1,
            annual_rising_count=0,
            epoch_alignment_count=0,
            strongest_profiles=(profile,),
            weakest_profiles=(profile,),
        )


def test_phase9_condition_network_profile_is_deterministic_and_aligned(monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.sothic as s

    date = s.egyptian_civil_date(_SOTHIC_EPOCH_139_JD)
    monkeypatch.setattr(s, "_heliacal_rising", lambda *args, **kwargs: _SOTHIC_EPOCH_139_JD + 2.0)
    entry = s.sothic_rising(29.8, 31.3, 139, 139)[0]
    epoch = s.sothic_epochs(29.8, 31.3, 139, 139, tolerance_days=5.0)[0]

    network = s.sothic_condition_network_profile(
        egyptian_dates=[date],
        entries=[entry],
        epochs=[epoch],
    )

    assert network.node_count == 5
    assert network.edge_count == 3
    assert [node.node_id for node in network.nodes] == [
        "anchor:censorinus_139_epoch",
        "date:001:01:01",
        "entry:139",
        "epoch:139",
        "star:Sirius",
    ]
    assert [edge.relation_kind for edge in network.edges] == [
        "egyptian_calendar",
        "sothic_rising",
        "sothic_epoch",
    ]
    assert [edge.condition_state for edge in network.edges] == [
        "calendar_anchor",
        "annual_rising",
        "epoch_alignment",
    ]
    assert network.isolated_nodes == ()
    assert len(network.most_connected_nodes) == 1
    assert network.most_connected_nodes[0].node_id == "star:Sirius"


def test_phase9_condition_network_profile_drift_fails_loudly() -> None:
    import moira.sothic as s

    node = s.SothicConditionNetworkNode(
        node_id="star:Sirius",
        kind="star",
        incoming_count=0,
        outgoing_count=1,
    )
    edge = s.SothicConditionNetworkEdge(
        source_id="star:Sirius",
        target_id="entry:139",
        relation_kind="sothic_rising",
        relation_basis="sirius_heliacal_rising",
        condition_state="annual_rising",
    )

    with pytest.raises(ValueError, match="must match edges"):
        s.SothicConditionNetworkProfile(
            nodes=(
                s.SothicConditionNetworkNode(
                    node_id="entry:139",
                    kind="entry",
                    incoming_count=0,
                    outgoing_count=0,
                ),
                node,
            ),
            edges=(edge,),
            isolated_nodes=(),
            most_connected_nodes=(node,),
        )


def test_phase10_malformed_inputs_fail_deterministically() -> None:
    import moira.sothic as s

    with pytest.raises(ValueError, match="jd must be finite"):
        s.egyptian_civil_date(float("nan"))

    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        s.sothic_rising(95.0, 31.3, 139, 139)

    with pytest.raises(ValueError, match="year_end must be greater than or equal to year_start"):
        s.sothic_rising(29.8, 31.3, 140, 139)

    with pytest.raises(ValueError, match="tolerance_days must be non-negative"):
        s.sothic_epochs(29.8, 31.3, 139, 139, tolerance_days=-1.0)

    with pytest.raises(ValueError, match="cycle_length_years must be positive"):
        s.predicted_sothic_epoch_year(139, 1, cycle_length_years=0.0)


def test_phase10_drift_rate_and_network_fail_loudly_on_malformed_state() -> None:
    import moira.sothic as s

    bad_entries = [type("Entry", (), {"year": idx, "drift_days": float(idx)}) for idx in range(4)]
    with pytest.raises(ValueError, match="at least 5 entries"):
        s.sothic_drift_rate(bad_entries)

    malformed_entries = [type("Entry", (), {"year": idx, "drift_days": float(idx)}) for idx in range(5)]
    malformed_entries[2] = type("Entry", (), {"year": 2, "drift_days": float("nan")})
    with pytest.raises(ValueError, match="drift_days must be finite"):
        s.sothic_drift_rate(malformed_entries)

    with pytest.raises(ValueError, match="kind prefix"):
        s.SothicConditionNetworkNode(
            node_id="bad:Sirius",
            kind="star",
            incoming_count=0,
            outgoing_count=0,
        )
