"""Conditional enclosures of split lunar-eclipse serving vectors.

This module composes the guarded split TT/TDB conversion, a single concrete
direct-pair native type-2 reader, and the finite split light-time iteration.
It returns an enclosure only under explicit, *unattested* source, binary64,
``fsum`` and native-build premises carried by its receipt. The Earth and
Moon reception vectors and every possible Sun early-stop vector are bounded;
neither UT1, complete event search nor physical accuracy is certified.

No live integrity snapshot of the mapped kernel or loaded binary is taken.
Caller and platform must maintain the declared source/constant/build/fenv
premises throughout evaluation; the result is not an unconditional certificate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math
import struct
import sys
from types import SimpleNamespace

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import (
    ConditionalNativeType2Bounds,
    _rounded,
    _selected_descriptor,
    _snapshot_hash,
    conditional_native_type2_bounds,
    guarded_scalar_snapshot_evaluate,
)
from ._eclipse_time_bounds import ServingTdbEnvelope, bound_serving_split_tdb
from .constants import C_KM_PER_DAY
from .coordinates import vec_norm, vec_sub
from .corrections import _iterate_light_time
from .julian import _tt_to_tdb_split


class EclipseServingBoundsUnavailable(EnclosureUnavailable):
    """A serving enclosure has an unproved branch, source or resource domain."""


@dataclass(frozen=True, slots=True)
class ServingLightTimeIteration:
    """One possible emission delay and its conditional next-delay residual.

    The signed residual is ``next_delay_days - input_delay_days``. It is
    evaluated at the delay used to produce this iteration's Sun vector;
    it is not the residual at the subsequently returned delay and does not
    establish an error relative to an exact light-time fixed point. It inherits
    the parent receipt's unattested split-route and arithmetic premises.
    """

    emission_tt_offset_days: I
    sun_geocentric_km: tuple[I, I, I]
    next_delay_days: I
    input_delay_days: I

    @property
    def emission_delay_residual_days(self) -> I:
        """Enclose the exact difference of the represented delay values."""
        return self.next_delay_days - self.input_delay_days

    @property
    def rounded_emission_delay_residual_days(self) -> I:
        """Enclose the binary64 subtraction used by the stopping comparison."""
        return _rounded(self.emission_delay_residual_days)


@dataclass(frozen=True, slots=True)
class ConditionalLunarServingBounds:
    """A model-conditional enclosure, with unverified premises explicit.

    Under the stated premises the Sun box covers every possible return from
    the guarded finite split light-time loop, including early termination.
    It does not prove source immutability, native compiler flags, thread fenv,
    conversion/iteration convergence, UT1 coverage or physical accuracy.
    The default broad norm guard does not assume libm sqrt accuracy. The
    optional tighter norm requires the additional arithmetic premises named
    in ``arithmetic_model`` and ``tight_norm_assumptions_required``.
    """

    tt_anchor_jd: float
    reception_tt_offset_days: I
    sun_retarded_km: tuple[I, I, I]
    moon_geometric_km: tuple[I, I, I]
    initial_delay_days: I
    iterations: tuple[ServingLightTimeIteration, ...]
    time_usages: tuple[ServingTdbEnvelope, ...]
    spk_usages: tuple[ConditionalNativeType2Bounds, ...]
    route_calls: int
    arithmetic_model: str = (
        "binary64 RN; gradual underflow; fsum <=1 ulp; no unsafe native reassociation"
    )
    guarded_split_source_required: bool = True
    immutable_reader_and_constants_required: bool = True
    arithmetic_environment_attested: bool = False
    native_build_attested: bool = False
    source_and_kernel_attested: bool = False
    split_tdb_enclosed_conditionally: bool = True
    native_spk_enclosed_conditionally: bool = True
    finite_light_time_enclosed_conditionally: bool = True
    ut1_enclosed: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False
    tight_norm_assumptions_required: bool = False


@dataclass(frozen=True, slots=True)
class GuardedLunarSnapshotEvaluation:
    """One sample evaluated from the very coefficient snapshots bounded above.

    This is a different opt-in scalar snapshot policy, not an attestation of
    the legacy memory-mapped native evaluator. The native strict-build claim
    is self-reported; its independent build receipt is not verified here.
    Python time/vector arithmetic still has the declared conditional premises.
    """

    tt_jd: float
    sun_retarded_km: tuple[float, float, float]
    moon_geometric_km: tuple[float, float, float]
    light_time_days: float
    iterations_used: int
    snapshot_hashes: tuple[str, ...]
    build_contract_self_reported: str
    independent_build_receipt_verified: bool = False
    legacy_mapped_evaluator_certified: bool = False
    source_and_kernel_attested: bool = False
    python_arithmetic_environment_attested: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ServingKernelLunarSnapshotEvaluation:
    """A production-body-pair sample evaluated from bounded copied records.

    The actual body-pair code and the same native position kernel are used.
    The copied SPK records are pinned by their receipts, but no claim is made
    that the mapped file or loaded native image is independently attested.
    """

    tt_jd: float
    sun_retarded_km: tuple[float, float, float]
    moon_geometric_km: tuple[float, float, float]
    route_snapshot_hashes: tuple[str, ...]
    legacy_mapped_evaluator_certified: bool = False
    source_and_kernel_attested: bool = False
    arithmetic_environment_attested: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class FrozenLunarServingScope:
    """Prevalidated copied records and native operations for bounded samples.

    The numerical receipt is conditional on its stated source and arithmetic
    premises. Frozen data do not attest the loaded native binary, the physical
    sky, or totality of a search, and replaceable receipt fields are not a
    certificate. The native evaluator objects are retained so that calls do
    not need to reopen the original reader's mapped records.
    """

    bounds: ConditionalLunarServingBounds
    operations: tuple = field(repr=False, compare=False)
    records: tuple = field(repr=False, compare=False)
    snapshot_hashes: tuple[str, ...]
    source_and_kernel_attested: bool = field(default=False, init=False)
    arithmetic_environment_attested: bool = field(default=False, init=False)
    totality_certified: bool = field(default=False, init=False)
    complete_search_certified: bool = field(default=False, init=False)


def bound_conditional_lunar_serving_vectors(
    reader,
    tt_anchor_jd: float,
    tt_offset_days: I,
    *,
    max_route_calls: int = 32,
    max_records: int = 256,
    tight_norm: bool = False,
) -> ConditionalLunarServingBounds:
    """Enclose successful native lunar-vector calls under stated premises.

    ``tt_anchor_jd + tt_offset_days`` describes the exact represented TT
    reception inputs to consider. Each actual converter invocation may split
    that combined TT differently; the split-conversion bound is independent of that
    decomposition provided both represented inputs and their sum lie in the
    converter's admitted domain. If the outer TDB interval crosses a whole-day
    branch, or the native reader cannot prove an unambiguous direct type-2
    route and record, this routine raises ``EnclosureUnavailable``.

    Every actual rounded route sum/subtraction is outward-rounded. The guarded
    norm permits a conservative delay of zero through ``2*max(abs(xyz))/C``;
    that upper bound is rounded outward and does not assert sqrt accuracy.
    Its intentionally large width may force subdivision or unresolved results.
    An explicit ``tight_norm=True`` instead assumes Python float ``x**2``
    is correctly rounded as a binary64 square and ``math.sqrt`` is correctly
    rounded. It encloses the three squares, the two left-associated sums,
    the square root and the final division individually. These additional
    assumptions are not attested, and the conservative default is unchanged.
    A successfully returned box is conditional on unchanged guarded source,
    pinned represented constants and immutable serving records throughout.
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offsets must be a RationalInterval in days")
    if type(max_route_calls) is not int or not 1 <= max_route_calls <= 1024:
        raise ValueError("max_route_calls must be an integer from 1 to 1024")
    if type(max_records) is not int or not 1 <= max_records <= 256:
        raise ValueError("max_records must be an integer from 1 to 256")
    if type(tight_norm) is not bool:
        raise TypeError("tight_norm must be a bool")
    if not math.isfinite(C_KM_PER_DAY) or C_KM_PER_DAY <= 0:
        raise EclipseServingBoundsUnavailable("represented light speed must be positive and finite")

    source_hash: str | None = None
    route_calls = 0
    tdb_usages: list[ServingTdbEnvelope] = []
    spk_usages: list[ConditionalNativeType2Bounds] = []

    def route(center: int, target: int, tt_offsets: I):
        nonlocal route_calls, source_hash
        if route_calls >= max_route_calls:
            raise EclipseServingBoundsUnavailable("conditional route evaluation budget exhausted")
        route_calls += 1
        conversion = bound_serving_split_tdb(anchor, tt_offsets)
        absolute_tdb = I.point(anchor) + conversion.tdb_offset_days
        first_day, last_day = absolute_tdb.lo // 1, absolute_tdb.hi // 1
        if first_day != last_day or abs(first_day) >= 2**53:
            raise EclipseServingBoundsUnavailable("TDB whole-day branch requires subdivision")
        tdb_anchor = float(first_day)
        tdb_fraction = absolute_tdb - first_day
        state = conditional_native_type2_bounds(
            reader, center, target, tdb_anchor, tdb_fraction, max_records=max_records,
        )
        if state.source.frame_id != 1:
            raise EclipseServingBoundsUnavailable("serving route requires frame ID 1 (J2000)")
        identity = state.source.source_sha256_at_reader_open
        if source_hash is None:
            source_hash = identity
        elif identity != source_hash:
            raise EclipseServingBoundsUnavailable("serving route source identity changed")
        tdb_usages.append(conversion)
        spk_usages.append(state)
        return state.position_km

    def add(left, right):
        return tuple(_rounded(a + b) for a, b in zip(left, right))

    def subtract(left, right):
        return tuple(_rounded(a - b) for a, b in zip(left, right))

    def delay(vector):
        if tight_norm:
            squares = tuple(_rounded(component.square()) for component in vector)
            squared = _rounded(_rounded(squares[0] + squares[1]) + squares[2])
            if squared.lo < 0:
                raise EclipseServingBoundsUnavailable("tight norm square domain is ambiguous")
            norm = _rounded(squared.sqrt(128))
            return _rounded(norm / Fraction.from_float(C_KM_PER_DAY))
        # The split guard checks finite norm <= 2*max_component. When doubling
        # would overflow, every accepted finite norm is <= max binary64.
        peak = max(component.magnitude for component in vector)
        maximum_float = Fraction.from_float(sys.float_info.max)
        norm_upper = min(2 * peak, maximum_float)
        return _rounded(I(0, norm_upper) / Fraction.from_float(C_KM_PER_DAY))

    earth_from_emb = route(3, 399, tt_offset_days)
    emb = route(0, 3, tt_offset_days)
    earth = add(emb, earth_from_emb)
    moon = subtract(route(3, 301, tt_offset_days), earth_from_emb)
    sun_geometric = subtract(route(0, 10, tt_offset_days), earth)
    initial_delay = delay(sun_geometric)
    current_delay = initial_delay
    iterations: list[ServingLightTimeIteration] = []
    for _ in range(10):
        emission = tt_offset_days - current_delay
        sun = subtract(route(0, 10, emission), earth)
        next_delay = delay(sun)
        iterations.append(ServingLightTimeIteration(emission, sun, next_delay, current_delay))
        current_delay = next_delay
    sun_box = tuple(
        I(min(step.sun_geocentric_km[i].lo for step in iterations),
          max(step.sun_geocentric_km[i].hi for step in iterations))
        for i in range(3)
    )
    return ConditionalLunarServingBounds(
        anchor, tt_offset_days, sun_box, moon, initial_delay, tuple(iterations),
        tuple(tdb_usages), tuple(spk_usages), route_calls,
        arithmetic_model=(
            "binary64 RN; gradual underflow; fsum <=1 ulp; no unsafe native reassociation"
            + ("; float x**2 correctly rounded; sqrt correctly rounded" if tight_norm else "")
        ),
        tight_norm_assumptions_required=tight_norm,
    )


def evaluate_guarded_lunar_snapshot(
    bounds: ConditionalLunarServingBounds,
    tt_jd: float,
) -> GuardedLunarSnapshotEvaluation:
    """Re-evaluate one represented TT instant from the bounded record copies.

    All route calls use the exact immutable snapshot tuple and receipt stored
    in ``bounds``; each strict native scalar sample must fall inside the
    corresponding conditional SPK interval. The chosen TT and each actual
    emission epoch must remain within their previously bounded domains.
    The snapshot digest binds the claimed source receipt to the copied words;
    it does not prove their identity with the live source or attest the
    original memory map or a separate legacy evaluator.
    """
    if not isinstance(bounds, ConditionalLunarServingBounds):
        raise TypeError("conditional lunar serving bounds required")
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)) or not math.isfinite(tt_jd):
        raise ValueError("TT sample must be finite")
    tt = float(tt_jd)
    relative = Fraction.from_float(tt) - Fraction.from_float(bounds.tt_anchor_jd)
    if not bounds.reception_tt_offset_days.contains(relative):
        raise ValueError("TT sample is outside the bounded reception interval")
    if len(bounds.spk_usages) != 14 or len(bounds.iterations) != 10:
        raise EclipseServingBoundsUnavailable("lunar snapshot route receipt is incomplete")

    snapshots: list[str] = []
    build_contract: str | None = None

    def evaluate_route(index: int, center: int, target: int, tt_offset: float):
        nonlocal build_contract
        state = bounds.spk_usages[index]
        if (state.source.center, state.source.target) != (center, target):
            raise EclipseServingBoundsUnavailable("snapshot route does not match its receipt")
        whole, fraction = _tt_to_tdb_split(tt, tt_offset)
        if whole != state.jd_tdb:
            raise EclipseServingBoundsUnavailable("snapshot TDB whole-day branch changed")
        sample = guarded_scalar_snapshot_evaluate(state, fraction)
        if build_contract is None:
            build_contract = sample.build_contract_self_reported
        elif sample.build_contract_self_reported != build_contract:
            raise EclipseServingBoundsUnavailable("snapshot native build contract changed")
        snapshots.append(sample.record_snapshot_sha256)
        return sample.position_km

    earth_leg = evaluate_route(0, 3, 399, 0.0)
    emb = evaluate_route(1, 0, 3, 0.0)
    moon_leg = evaluate_route(2, 3, 301, 0.0)
    initial_sun = evaluate_route(3, 0, 10, 0.0)
    earth = tuple(a + b for a, b in zip(emb, earth_leg))
    moon = tuple(a - b for a, b in zip(moon_leg, earth_leg))
    if any(not box.contains(value) for box, value in zip(bounds.moon_geometric_km, moon)):
        raise ArithmeticError("guarded snapshot Moon escaped its conditional vector box")
    initial_delay = vec_norm(vec_sub(initial_sun, earth)) / C_KM_PER_DAY
    if not math.isfinite(initial_delay) or not bounds.initial_delay_days.contains(initial_delay):
        raise ArithmeticError("guarded snapshot initial delay escaped its conditional box")

    used = 0

    def emission(delay: float):
        nonlocal used
        if used >= len(bounds.iterations):
            raise EclipseServingBoundsUnavailable("snapshot iteration budget exhausted")
        phase = bounds.iterations[used]
        offset = relative - Fraction.from_float(delay)
        if not phase.emission_tt_offset_days.contains(offset):
            raise ArithmeticError("guarded snapshot emission escaped its conditional TT box")
        body = evaluate_route(4 + used, 0, 10, -delay)
        xyz = tuple(a - b for a, b in zip(body, earth))
        if any(not box.contains(value) for box, value in zip(phase.sun_geocentric_km, xyz)):
            raise ArithmeticError("guarded snapshot Sun escaped its conditional iteration box")
        used += 1
        return body

    sun, light_time = _iterate_light_time(earth, initial_sun, emission, guard_norm=True)
    if any(not box.contains(value) for box, value in zip(bounds.sun_retarded_km, sun)):
        raise ArithmeticError("guarded snapshot Sun escaped its conditional return box")
    if used < 1 or not bounds.iterations[used - 1].next_delay_days.contains(light_time):
        raise ArithmeticError("guarded snapshot delay escaped its conditional return box")
    if build_contract is None:
        raise EclipseServingBoundsUnavailable("no snapshot native build contract")
    return GuardedLunarSnapshotEvaluation(
        tt, sun, moon, light_time, used, tuple(snapshots), build_contract,
    )


def _freeze_lunar_serving_bounds(reader, bounds: ConditionalLunarServingBounds) -> FrozenLunarServingScope:
    """Check each bounded route once and retain its copied native operation."""
    if not isinstance(bounds, ConditionalLunarServingBounds):
        raise TypeError("conditional lunar serving bounds required")
    states = bounds.spk_usages
    if len(states) != 14 or len(bounds.iterations) != 10:
        raise EclipseServingBoundsUnavailable("lunar snapshot route receipt is incomplete")
    pairs = ((3, 399), (0, 3), (3, 301), (0, 10)) + ((0, 10),) * 10
    operations = []
    records = []
    hashes = []
    for pair, state in zip(pairs, states):
        center, target = pair
        if (state.source.center, state.source.target) != pair:
            raise EclipseServingBoundsUnavailable("lunar route source differs from its bound")
        digest = _snapshot_hash(
            state.source, state.record_snapshot, state.jd_tdb, state.offset_days,
            state.record_init, state.record_length, state.record_count, state.record_index,
            state.descriptor_start, state.descriptor_end,
        )
        if digest != state.record_snapshot_sha256:
            raise EclipseServingBoundsUnavailable("lunar route record identity mismatch")
        segment = _selected_descriptor(reader, center, target, state.jd_tdb, state.offset_days)
        if (float(segment.start_second) != state.descriptor_start
                or float(segment.end_second) != state.descriptor_end):
            raise EclipseServingBoundsUnavailable("lunar descriptor differs from its bound")
        try:
            loader = getattr(segment, "_load_native_evaluator", None)
            if not callable(loader):
                raise EclipseServingBoundsUnavailable("native lunar evaluator is unavailable")
            evaluator = loader()
            metadata_method = getattr(evaluator, "chebyshev_metadata", None)
            records_method = getattr(evaluator, "chebyshev_records", None)
            if not callable(metadata_method) or not callable(records_method):
                raise EclipseServingBoundsUnavailable("native lunar record metadata is unavailable")
            metadata = metadata_method()
        except EclipseServingBoundsUnavailable:
            raise
        except (OSError, RuntimeError) as exc:
            raise EclipseServingBoundsUnavailable("native lunar evaluator is unavailable") from exc
        if (len(state.record_snapshot) != 3 or not state.record_snapshot[0]
                or any(len(axis) != len(state.record_snapshot[0]) for axis in state.record_snapshot)
                or metadata != (state.record_init, state.record_length, state.record_count,
                                3, len(state.record_snapshot[0]))):
            raise EclipseServingBoundsUnavailable("lunar evaluator metadata differs from its bound")
        # Reconstruct the same copied-record digest produced by the interval
        # provider. It binds this selected descriptor's frame and raw payload
        # addresses, not just its times and dimensions. This is an observation
        # of the current evaluator, not an attestation of its live mapping.
        try:
            init, length, count, components, coefficient_count = metadata
            frame, start_word, end_word = int(segment.frame), int(segment.start_i), int(segment.end_i)
            source_hash = reader._source_identity.sha256
            if frame != state.source.frame_id or source_hash != state.source.source_sha256_at_reader_open:
                raise EclipseServingBoundsUnavailable("lunar descriptor frame or source identity changed")
            identity = hashlib.sha256()
            identity.update(b"moira-eclipse-type2-copied-records-v1\0")
            identity.update(
                f"{center} {target} {frame} {start_word} {end_word} {count} {components} {coefficient_count}\n".encode("ascii")
            )
            identity.update(struct.pack("<4d", float(segment.start_second), float(segment.end_second), init, length))
            for record_index in state.source.record_indices:
                current = records_method(record_index, 1)[0]
                if len(current) != 3 or any(len(axis) != coefficient_count for axis in current):
                    raise EclipseServingBoundsUnavailable("lunar source record layout changed")
                identity.update(f"{record_index}\n".encode("ascii"))
                for axis in current:
                    for value in axis:
                        identity.update(struct.pack("<d", value))
            if identity.hexdigest() != state.source.copied_records_sha256:
                raise EclipseServingBoundsUnavailable("lunar descriptor or source record identity changed")
        except EclipseServingBoundsUnavailable:
            raise
        except (AttributeError, TypeError, ValueError, OverflowError, OSError, RuntimeError, struct.error) as exc:
            raise EclipseServingBoundsUnavailable("lunar descriptor or source identity unavailable") from exc
        operation = getattr(evaluator, "_eclipse_position_from_copied_record", None)
        if not callable(operation):
            raise EclipseServingBoundsUnavailable("native copied-record position is unavailable")
        record = tuple(value for axis in state.record_snapshot for value in axis)
        operations.append(operation)
        records.append(record)
        hashes.append(digest)
    return FrozenLunarServingScope(bounds, tuple(operations), tuple(records), tuple(hashes))


def prepare_lunar_serving_snapshot(
    reader, tt_anchor_jd: float, tt_offset_days: I, *, tight_norm: bool = False,
) -> FrozenLunarServingScope:
    """Create fresh conditional bounds and freeze their fourteen native routes.

    This factory does not accept a caller-created bound receipt. It observes
    the reader and copies its selected records while preparing the scope;
    subsequent sample evaluation does not look up or read the live reader.
    A frozen scope is still replaceable data, not an attested certificate.
    """
    bounds = bound_conditional_lunar_serving_vectors(
        reader, tt_anchor_jd, tt_offset_days, tight_norm=tight_norm,
    )
    return _freeze_lunar_serving_bounds(reader, bounds)


def evaluate_lunar_frozen_snapshot(
    scope: FrozenLunarServingScope, tt_jd: float,
) -> ServingKernelLunarSnapshotEvaluation:
    """Run the lunar body-pair path on a prevalidated copied-record scope.

    This evaluates one represented sample only. The scope's arithmetic,
    binary, provenance and source premises are not independently attested;
    its existence does not establish complete-interval evaluation or absence.
    """
    if not isinstance(scope, FrozenLunarServingScope):
        raise TypeError("frozen lunar serving scope required")
    bounds = scope.bounds
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)):
        raise ValueError("TT sample must be finite")
    try:
        tt = float(tt_jd)
    except OverflowError as exc:
        raise ValueError("TT sample must be finite") from exc
    if not math.isfinite(tt):
        raise ValueError("TT sample must be finite")
    relative = Fraction.from_float(tt) - Fraction.from_float(bounds.tt_anchor_jd)
    if not bounds.reception_tt_offset_days.contains(relative):
        raise ValueError("TT sample is outside the bounded reception interval")
    states = bounds.spk_usages
    if len(states) != 14 or len(scope.operations) != 14 or len(scope.records) != 14 or len(scope.snapshot_hashes) != 14:
        raise EclipseServingBoundsUnavailable("frozen lunar route is incomplete")

    hashes: list[str] = []
    sun_calls = 0

    def position(center: int, target: int, jd: float, offset: float):
        nonlocal sun_calls
        pair = (center, target)
        if pair == (0, 3):
            index = 1
        elif pair == (3, 399):
            index = 0
        elif pair == (3, 301):
            index = 2
        elif pair == (0, 10):
            index = 3 + sun_calls
            sun_calls += 1
        else:
            raise EclipseServingBoundsUnavailable("unexpected lunar production route")
        if index >= len(states):
            raise EclipseServingBoundsUnavailable("lunar emission iteration budget exhausted")
        state = states[index]
        if ((state.source.center, state.source.target) != pair or jd != state.jd_tdb
                or not state.offset_days.contains(offset)):
            raise EclipseServingBoundsUnavailable("lunar route epoch or source differs from its bound")
        try:
            xyz = tuple(scope.operations[index](jd, offset, state.record_index, scope.records[index]))
        except (ValueError, OverflowError) as exc:
            raise EclipseServingBoundsUnavailable("native copied-record route was rejected") from exc
        if len(xyz) != 3 or any(not box.contains(value) for box, value in zip(state.position_km, xyz)):
            raise ArithmeticError("serving-kernel snapshot escaped its conditional bound")
        hashes.append(scope.snapshot_hashes[index])
        return xyz

    # The existing production function selects the split route through this
    # reader. The proxy never supplies a legacy route or silently falls back.
    from .eclipse import _eclipse_body_pair

    sun, moon = _eclipse_body_pair(
        tt, SimpleNamespace(_position_tdb_offset=position), sun_retarded=True, moon_retarded=False,
    )
    if (sun_calls < 2 or sun_calls > 11
            or any(not box.contains(value) for box, value in zip(bounds.sun_retarded_km, sun))
            or any(not box.contains(value) for box, value in zip(bounds.moon_geometric_km, moon))):
        raise ArithmeticError("production body pair escaped its conditional vector bound")
    return ServingKernelLunarSnapshotEvaluation(tt, tuple(sun), tuple(moon), tuple(hashes))


def evaluate_lunar_snapshot_with_serving_kernel(
    reader, bounds: ConditionalLunarServingBounds, tt_jd: float,
) -> ServingKernelLunarSnapshotEvaluation:
    """Run one lunar body-pair sample after prevalidating its copied routes.

    Missing capability, unexpected route calls, and mismatched receipts fail
    closed. The returned sample is not a route-totality, live-source or
    eclipse-search certificate.
    """
    if not isinstance(bounds, ConditionalLunarServingBounds):
        raise TypeError("conditional lunar serving bounds required")
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)):
        raise ValueError("TT sample must be finite")
    try:
        tt = float(tt_jd)
    except OverflowError as exc:
        raise ValueError("TT sample must be finite") from exc
    if not math.isfinite(tt):
        raise ValueError("TT sample must be finite")
    if not bounds.reception_tt_offset_days.contains(Fraction.from_float(tt) - Fraction.from_float(bounds.tt_anchor_jd)):
        raise ValueError("TT sample is outside the bounded reception interval")
    return evaluate_lunar_frozen_snapshot(_freeze_lunar_serving_bounds(reader, bounds), tt)
