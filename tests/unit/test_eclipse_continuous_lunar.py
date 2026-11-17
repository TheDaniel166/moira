"""Fixed-record continuous lunar reference and signed derivative bounds."""
from decimal import Decimal, localcontext
from dataclasses import replace
from fractions import Fraction
import struct

import pytest

from moira import _eclipse_continuous_lunar as continuous
from moira import julian
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.constants import C_KM_PER_DAY


def _decimal_model(model, t, sun_iterations=10):
    """Independent decimal recurrences and finite iterations as a witness."""
    with localcontext() as context:
        context.prec = 120
        pi = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068")

        def sine(value):
            value %= 2 * pi
            if value > pi:
                value -= 2 * pi
            if value < -pi:
                value += 2 * pi
            result = term = value
            for n in range(1, 100):
                term *= -(value * value) / Decimal((2 * n) * (2 * n + 1))
                result += term
            return result

        def dec(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        k = Decimal.from_float(julian._NAIF_DELTET_K_SECONDS)
        m0 = Decimal.from_float(julian._NAIF_DELTET_M0_RADIANS)
        m1 = Decimal.from_float(julian._NAIF_DELTET_M1_RADIANS_PER_SECOND)
        eb = Decimal.from_float(julian._NAIF_DELTET_EB)
        light_speed = Decimal.from_float(C_KM_PER_DAY)
        records = {(r.center, r.target): r for r in model.records}

        def tdb(tt):
            correction = Decimal(0)
            for _ in range(12):
                mean = m0 + m1 * Decimal(86400) * (tt + correction - Decimal(2451545))
                correction = k / Decimal(86400) * sine(mean + eb * sine(mean))
            return tt + correction

        def position(pair, tt):
            record = records[pair]
            seconds = (tdb(tt) - Decimal(2451545)) * Decimal(86400)
            x = Decimal(2) * (seconds - dec(record.record_start_seconds)) / dec(record.record_length_seconds) - 1
            values = []
            for coefficients in record.coefficients:
                p0, p1 = Decimal(1), x
                value = dec(coefficients[0])
                if len(coefficients) > 1:
                    value += dec(coefficients[1]) * p1
                for coefficient in coefficients[2:]:
                    p0, p1 = p1, 2 * x * p1 - p0
                    value += dec(coefficient) * p1
                values.append(value)
            return tuple(values)

        def add(a, b):
            return tuple(x + y for x, y in zip(a, b))

        def sub(a, b):
            return tuple(x - y for x, y in zip(a, b))

        emb, earth_leg, moon_leg = (position(pair, t) for pair in ((0, 3), (3, 399), (3, 301)))
        earth = add(emb, earth_leg)
        moon = sub(moon_leg, earth_leg)
        sun = sub(position((0, 10), t), earth)
        delay = sum(x * x for x in sun).sqrt() / light_speed
        for _ in range(sun_iterations):
            sun = sub(position((0, 10), t - delay), earth)
            delay = sum(x * x for x in sun).sqrt() / light_speed
        return sun, moon


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_continuous_reference_encloses_independent_decimal_values_and_derivatives(planetary_reader, tt, monkeypatch):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    model = continuous.build_continuous_lunar_reference(planetary_reader, tt, offsets)
    # Future subdivisions must use the frozen copies, not re-read a live SPK.
    monkeypatch.setattr(continuous, "bound_serving_type2_polynomial",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record re-read")))
    bounds = continuous.enclose_continuous_lunar_reference(model, offsets)
    assert bounds.continuous_on_domain and bounds.differentiable_on_domain
    assert bounds.fixed_sun_iterations == 10
    assert not bounds.source_and_kernel_attested and not bounds.legacy_evaluator_enclosed
    assert model.uniform_init_intlen_reference_only and bounds.uniform_init_intlen_reference_only
    assert not model.raw_record_mid_radius_verified and not bounds.raw_record_mid_radius_verified
    assert len(bounds.clock_usages) == 11
    with localcontext() as context:
        context.prec = 75
        center = Decimal.from_float(tt)
        delta = Decimal("0.0000001")
        sun, moon = _decimal_model(model, center)
        before = _decimal_model(model, center - delta)
        after = _decimal_model(model, center + delta)
        for boxes, values in ((bounds.sun_geocentric_km, sun), (bounds.moon_geocentric_km, moon)):
            assert all(box.contains(Fraction(value)) for box, value in zip(boxes, values))
        for index, boxes in enumerate((bounds.sun_derivative_km_per_tt_day, bounds.moon_derivative_km_per_tt_day)):
            rate = tuple((a - b) / (2 * delta) for a, b in zip(after[index], before[index]))
            assert all(box.contains(Fraction(value)) for box, value in zip(boxes, rate))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_selected_de441_file_records_match_uniform_reference_metadata(planetary_reader, tt):
    """Check selected on-disk record words, not live mapped-kernel integrity.

    NAIF SPK Required Reading, type 2, specifies record MID/RADIUS as the
    Chebyshev normalization: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html
    This witness covers twelve records at three epochs, not all DE441 records.
    """
    model = continuous.build_continuous_lunar_reference(planetary_reader, tt, I.point(0))
    with open(planetary_reader._path, "rb") as source:
        for record in model.records:
            segment = continuous._select_descriptor(
                planetary_reader._segments_for_pair(record.center, record.target),
                record.source.interval_seconds_tdb,
            )
            count = len(record.coefficients[0])
            word_count = 2 + 3 * count
            source.seek((segment.start_i - 1 + record.record_index * word_count) * 8)
            raw = source.read(word_count * 8)
            assert len(raw) == word_count * 8
            values = struct.unpack(("<" if segment._little_endian else ">") + "d" * word_count, raw)
            midpoint, radius = map(Fraction.from_float, values[:2])
            assert midpoint == record.record_start_seconds + record.record_length_seconds / 2
            assert radius == record.record_length_seconds / 2
            assert tuple(map(Fraction.from_float, values[2:])) == tuple(
                coefficient for axis in record.coefficients for coefficient in axis
            )


@pytest.mark.requires_ephemeris
def test_continuous_reference_rejects_record_seams_and_outside_subcells(planetary_reader):
    tt = 2459891.9582497696
    model = continuous.build_continuous_lunar_reference(planetary_reader, tt, I.point(0))
    with pytest.raises(ValueError, match="outside"):
        continuous.enclose_continuous_lunar_reference(model, I.point(1))
    record = model.records[0]
    seam = float(Fraction(2451545) + record.record_start_seconds / 86400)
    with pytest.raises(EnclosureUnavailable):
        continuous.build_continuous_lunar_reference(planetary_reader, seam, I(Fraction(-1, 10), Fraction(1, 10)))


@pytest.mark.requires_ephemeris
def test_insufficient_emission_horizon_is_unknown(planetary_reader):
    model = continuous.build_continuous_lunar_reference(
        planetary_reader, 2459891.9582497696, I.point(0), max_light_delay_days=Fraction(1, 1000),
    )
    with pytest.raises(EnclosureUnavailable, match="horizon"):
        continuous.enclose_continuous_lunar_reference(model, I.point(0))


@pytest.mark.requires_ephemeris
def test_sun_fixed_point_certificate_bounds_independent_decimal_witness(planetary_reader):
    tt = 2459891.9582497696
    model = continuous.build_continuous_lunar_reference(planetary_reader, tt, I.point(0))
    result = continuous.certify_continuous_sun_light_time(model, I.point(0))
    assert result.continuous_fixed_point_unique
    assert 0 <= result.contraction_factor < 1
    assert result.delay_map_image_days.lo >= 0
    assert result.delay_map_image_days.hi <= model.max_light_delay_days
    assert result.last_next_delay_error_days <= result.sun_emission_delay_error_days
    assert not result.raw_record_mid_radius_verified and not result.legacy_evaluator_enclosed
    with localcontext() as context:
        context.prec = 110
        ten, _ = _decimal_model(model, Decimal.from_float(tt), sun_iterations=10)
        twenty, _ = _decimal_model(model, Decimal.from_float(tt), sun_iterations=20)
        assert all(abs(Fraction(a - b)) <= result.sun_position_component_error_km
                   for a, b in zip(ten, twenty))


@pytest.mark.requires_ephemeris
def test_sun_fixed_point_certificate_uses_frozen_coefficients_not_receipt_bounds(planetary_reader):
    model = continuous.build_continuous_lunar_reference(planetary_reader, 2459891.9582497696, I.point(0))
    baseline = continuous.certify_continuous_sun_light_time(model, I.point(0))
    records = list(model.records)
    sun_index = next(index for index, record in enumerate(records) if record.target == 10)
    source = records[sun_index].source
    source = replace(source, speed_upper_km_per_second=Fraction.from_float(C_KM_PER_DAY),
                     position_km=(I.point(10 ** 15),) * 3)
    records[sun_index] = replace(records[sun_index], source=source)
    metadata_changed = continuous.certify_continuous_sun_light_time(replace(model, records=tuple(records)), I.point(0))
    assert metadata_changed.contraction_factor == baseline.contraction_factor
    assert metadata_changed.delay_map_image_days == baseline.delay_map_image_days
    axes = [list(axis) for axis in records[sun_index].coefficients]
    axes[0][1] += Fraction(1, 1000)
    records[sun_index] = replace(records[sun_index], coefficients=tuple(tuple(axis) for axis in axes))
    coefficients_changed = continuous.certify_continuous_sun_light_time(replace(model, records=tuple(records)), I.point(0))
    assert coefficients_changed.contraction_factor != baseline.contraction_factor


@pytest.mark.requires_ephemeris
def test_sun_fixed_point_certificate_rejects_bad_coefficient_model(planetary_reader):
    model = continuous.build_continuous_lunar_reference(planetary_reader, 2459891.9582497696, I.point(0))
    records = list(model.records)
    index = next(i for i, record in enumerate(records) if record.target == 10)
    axes = [list(axis) for axis in records[index].coefficients]
    axes[0][0] += 10 ** 15
    records[index] = replace(records[index], coefficients=tuple(tuple(axis) for axis in axes))
    with pytest.raises(EnclosureUnavailable, match="horizon|contraction|closed"):
        continuous.certify_continuous_sun_light_time(replace(model, records=tuple(records)), I.point(0))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("case", ["not_contraction", "not_closed"])
def test_sun_fixed_point_certificate_gates_coefficient_bounds(planetary_reader, monkeypatch, case):
    model = continuous.build_continuous_lunar_reference(planetary_reader, 2459891.9582497696, I.point(0))
    vectors = continuous.enclose_continuous_lunar_reference(model, I.point(0))
    # Isolate the certificate's own closure/contraction gates from the prior
    # finite-iterate guard, which can reject these artificial models earlier.
    monkeypatch.setattr(continuous, "enclose_continuous_lunar_reference", lambda *_: vectors)
    records = list(model.records)
    index = next(i for i, record in enumerate(records) if record.target == 10)
    axes = [list(axis) for axis in records[index].coefficients]
    axes[0][1 if case == "not_contraction" else 0] += 10 ** 15
    records[index] = replace(records[index], coefficients=tuple(tuple(axis) for axis in axes))
    with pytest.raises(EnclosureUnavailable, match="contraction" if case == "not_contraction" else "closed"):
        continuous.certify_continuous_sun_light_time(replace(model, records=tuple(records)), I.point(0))
