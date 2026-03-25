"""
Generative Ritual — three-phase test object for Moira's test suite.

A Ritual separates three concerns that most tests collapse together:

    Summon   — call the engine without presupposing what it will produce.
    Witness  — record the revealed truth as a snapshot or golden baseline.
    Covenant — assert structural and relational invariants on that truth.

This makes it possible to write tests that discover and freeze engine behavior
rather than tests that merely confirm already-known values. The ritual reveals;
the covenant judges what was revealed.

Do not instantiate Ritual directly. Use the ``ritual`` pytest fixture defined
in conftest.py, which wires snapshot and golden automatically.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Callable, Iterable, Sequence


class Ritual:
    """
    Three-phase test object: summon, witness, covenant.

    Attributes:
        node_id: The pytest node ID of the owning test, for diagnostics.
    """

    def __init__(
        self,
        snapshot_fn: Callable[[str, Any], None],
        golden_fn: Callable[[str, Any], None],
        test_node_id: str,
    ) -> None:
        self._snapshot   = snapshot_fn
        self._golden     = golden_fn
        self.node_id     = test_node_id

    # ------------------------------------------------------------------
    # Phase 2 — Witness
    # ------------------------------------------------------------------

    def witness(self, name: str, value: Any, *, as_golden: bool = False) -> Any:
        """
        Record the summoned value as canonical witnessed truth.

        Returns ``value`` unchanged so the call can be inlined inside
        the summon expression::

            chart = ritual.witness("chart_j2000", engine.chart(jd))

        Args:
            name:      Snapshot / golden file key (must be unique per test session).
            value:     The summoned engine output to record.
            as_golden: If True, record as a golden file (externally validated truth
                       from Horizons, ERFA, or SWE) rather than a snapshot baseline.

        Returns:
            value, unchanged.
        """
        serialized = self._serialize(value)
        if as_golden:
            self._golden(name, serialized)
        else:
            self._snapshot(name, serialized)
        return value

    # ------------------------------------------------------------------
    # Cross-witness — dual computation agreement
    # ------------------------------------------------------------------

    def cross_witness(
        self,
        a: Any,
        b: Any,
        *,
        keys: list[str] | None = None,
        abs_tol: float | None = None,
        label: str = "",
    ) -> None:
        """
        Assert that two independently summoned values agree.

        Use for symmetry checks, dual-path agreement, or cross-module
        consistency. If ``keys`` is given, only those attributes or dict
        keys are compared. If ``abs_tol`` is given, float comparisons use
        absolute tolerance instead of equality::

            ab = engine.aspect(positions["Sun"], positions["Moon"])
            ba = engine.aspect(positions["Moon"], positions["Sun"])
            ritual.cross_witness(ab, ba, keys=["orb", "angle"],
                                 label="aspect symmetry")

        Args:
            a:       First summoned value.
            b:       Second summoned value.
            keys:    Attribute or dict keys to compare. Compares whole objects
                     if None.
            abs_tol: Optional absolute tolerance for float comparisons.
            label:   Human-readable description shown in assertion messages.
        """
        suffix = f" ({label})" if label else ""

        if keys:
            for key in keys:
                av = _get(a, key)
                bv = _get(b, key)
                if abs_tol is not None and isinstance(av, float) and isinstance(bv, float):
                    assert abs(av - bv) <= abs_tol, (
                        f"Cross-witness float mismatch on '{key}'{suffix}: "
                        f"|{av} - {bv}| = {abs(av - bv):.2e} > tol {abs_tol:.2e}"
                    )
                else:
                    assert av == bv, (
                        f"Cross-witness mismatch on '{key}'{suffix}: {av!r} != {bv!r}"
                    )
        else:
            assert a == b, f"Cross-witness mismatch{suffix}: {a!r} != {b!r}"

    # ------------------------------------------------------------------
    # Temporal covenant — continuity / monotonicity over a sequence
    # ------------------------------------------------------------------

    def temporal_covenant(
        self,
        sequence: Sequence[Any],
        predicate: Callable[[Any, Any], bool],
        *,
        label: str = "temporal covenant",
    ) -> None:
        """
        Assert that ``predicate(a, b)`` holds for every consecutive pair.

        Use for continuity, monotonicity, bounded-step, or ordering
        invariants over time series::

            lons = [engine.planet(jd, "Sun").longitude for jd in jds]
            ritual.temporal_covenant(
                lons,
                lambda a, b: (b - a) % 360 < 2.0,
                label="Sun moves < 2 degrees per day",
            )

        Args:
            sequence:  Ordered sequence of values (one per time step).
            predicate: Called with consecutive pairs (a, b). Must return True.
            label:     Description shown in assertion messages.
        """
        if len(sequence) < 2:
            return
        for i, (a, b) in enumerate(zip(sequence, sequence[1:])):
            assert predicate(a, b), (
                f"{label} failed at step {i} → {i + 1}: {a!r} → {b!r}"
            )

    # ------------------------------------------------------------------
    # Contradiction — taboos of the engine
    # ------------------------------------------------------------------

    def taboo(self, name: str, condition: bool, *, context: str = "") -> None:
        """
        Assert that ``condition`` is False — this must never happen.

        A taboo is a law of the engine that no input may violate. Unlike a
        covenant (which asserts what IS true), a taboo asserts what CANNOT
        be true::

            pos = engine.planet(jd, "Sun")
            ritual.taboo("retrograde_sun", pos.is_retrograde,
                         context=f"JD {jd}")

            ritual.taboo("negative_distance", pos.distance < 0,
                         context=f"{body} at JD {jd}")

        Args:
            name:      Canonical name of the broken law (used in the message).
            condition: The forbidden condition. Must be False.
            context:   Optional description of the input state at time of check.

        Raises:
            AssertionError: If ``condition`` is True.
        """
        if condition:
            raise AssertionError(
                f"Taboo violated: '{name}'"
                + (f" — {context}" if context else "")
            )

    def sweep_taboo(
        self,
        name: str,
        items: Iterable[Any],
        forbidden: Callable[..., bool],
        *,
        context: Callable[..., str] | None = None,
        unpack: bool = True,
    ) -> None:
        """
        Check a taboo across many items, collecting all violations before failing.

        Unlike a single ``taboo`` call inside a loop (which stops at the first
        failure), ``sweep_taboo`` runs every item and reports all violations
        together. Use this when the sweep is large and partial failure is
        informative::

            jds    = [2451545.0 + i * 10 for i in range(100)]
            bodies = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

            ritual.sweep_taboo(
                "negative_distance",
                items=[(jd, body) for jd in jds for body in bodies],
                forbidden=lambda jd, body: engine.planet(jd, body).distance < 0,
                context=lambda jd, body: f"{body} at JD {jd:.1f}",
            )

            ritual.sweep_taboo(
                "cusp_out_of_range",
                items=reference_jds,
                forbidden=lambda jd: any(
                    not (0 <= c < 360)
                    for c in calculate_houses(jd, 51.5, 0.0, "P").cusps
                ),
                context=lambda jd: f"JD {jd:.1f}",
                unpack=False,
            )

        Args:
            name:     Canonical name of the law being checked.
            items:    Iterable of inputs. Each item is unpacked as ``*args``
                      into ``forbidden`` and ``context`` when ``unpack=True``
                      and the item is a tuple; otherwise passed as a single arg.
            forbidden: Called per item. Returns True if the taboo is violated.
            context:   Optional callable returning a description string per item.
                       Shown in the violation report.
            unpack:   If True (default), tuple items are unpacked into ``forbidden``
                      and ``context`` as positional arguments.

        Raises:
            AssertionError: If any item violates the taboo, listing all violations.
        """
        violations: list[str] = []

        for item in items:
            args: tuple
            if unpack and isinstance(item, tuple):
                args = item
            else:
                args = (item,)

            if forbidden(*args):
                ctx = context(*args) if context is not None else repr(item)
                violations.append(ctx)

        if violations:
            n = len(violations)
            lines = "\n  ".join(violations)
            raise AssertionError(
                f"Taboo '{name}' violated at {n} point{'s' if n != 1 else ''}:\n  {lines}"
            )

    # ------------------------------------------------------------------
    # Oracle — round-trip purity
    # ------------------------------------------------------------------

    def round_trip(
        self,
        value: Any,
        forward: Callable[[Any], Any],
        backward: Callable[[Any], Any],
        *,
        label: str = "",
        abs_tol: float | None = None,
        witness_name: str | None = None,
    ) -> Any:
        """
        Assert that ``backward(forward(value))`` recovers ``value``.

        The canonical purity test: if a transformation is lossless, composing
        it with its inverse must return the original exactly (or within
        ``abs_tol`` for floating-point paths).

        Optionally records the intermediate and recovered values as snapshots
        when ``witness_name`` is given, which aids debugging when a round-trip
        breaks::

            ritual.round_trip(
                dt,
                forward=jd_from_datetime,
                backward=datetime_from_jd,
                label="datetime → JD → datetime",
            )

            ritual.round_trip(
                longitude,
                forward=lambda lon: ecliptic_to_vector(lon, 0.0, 1.0),
                backward=lambda v: vector_to_ecliptic(v)[0],
                label="longitude → vector → longitude",
                abs_tol=1e-9,
                witness_name="lon_vector_roundtrip",
            )

        Args:
            value:        The original value to transform and recover.
            forward:      Transform applied first.
            backward:     Transform applied to the intermediate to recover value.
            label:        Description shown in assertion messages.
            abs_tol:      Absolute tolerance for float comparisons. Uses strict
                          equality when None.
            witness_name: If given, snapshots intermediate and recovered values
                          under ``{witness_name}_intermediate`` and
                          ``{witness_name}_recovered``.

        Returns:
            The intermediate value (output of ``forward``), for further inspection.
        """
        suffix = f" ({label})" if label else ""
        intermediate = forward(value)
        recovered    = backward(intermediate)

        if witness_name:
            self._snapshot(f"{witness_name}_intermediate", self._serialize(intermediate))
            self._snapshot(f"{witness_name}_recovered",    self._serialize(recovered))

        if abs_tol is not None:
            _assert_approx_equal(value, recovered, abs_tol=abs_tol, label=f"round-trip{suffix}")
        else:
            assert value == recovered, (
                f"Round-trip{suffix} is not lossless:\n"
                f"  Original:  {value!r}\n"
                f"  Recovered: {recovered!r}"
            )

        return intermediate

    # ------------------------------------------------------------------
    # Oracle — dual-path equivalence
    # ------------------------------------------------------------------

    def dual_path(
        self,
        fn_a: Callable[[], Any],
        fn_b: Callable[[], Any],
        *,
        label: str = "",
        abs_tol: float | None = None,
        keys: list[str] | None = None,
    ) -> Any:
        """
        Assert that two callables computing the same quantity agree.

        Neither path is assumed to be ground truth — the covenant is pure
        agreement. This is how compilers test themselves: run two backends
        on the same input and assert their outputs match::

            ritual.dual_path(
                lambda: engine.planet(jd, "Sun", sidereal=True).longitude,
                lambda: engine.planet(jd, "Sun", sidereal=False).longitude
                        - engine.ayanamsa(jd),
                label="sidereal = tropical − ayanamsa",
                abs_tol=1e-6,
            )

            ritual.dual_path(
                lambda: calculate_houses(jd, lat, lon, "P"),   # Placidus
                lambda: engine.houses(jd, lat, lon, "P"),      # public API path
                keys=["cusps"],
                label="internal vs public API",
            )

        Args:
            fn_a:    First computation (called with no arguments).
            fn_b:    Second computation (called with no arguments).
            label:   Description shown in assertion messages.
            abs_tol: Absolute tolerance for float comparisons.
            keys:    Attribute or dict keys to compare. Compares whole objects
                     if None.

        Returns:
            The result of ``fn_a()``, for further covenants.
        """
        a = fn_a()
        b = fn_b()
        self.cross_witness(
            a, b,
            keys=keys,
            abs_tol=abs_tol,
            label=label or "dual path",
        )
        return a

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize(self, value: Any) -> Any:
        """
        Convert engine output to a JSON-serializable form for witnessing.

        Priority:
          1. ``.to_dict()`` — preferred Moira result vessel protocol
          2. ``dataclasses.asdict()`` — for plain dataclass objects
          3. list / tuple — recurse element-wise
          4. dict — recurse value-wise
          5. Fallback — return as-is (int, float, str, bool, None)
        """
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return dataclasses.asdict(value)
        if isinstance(value, (list, tuple)):
            return [self._serialize(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        return value


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _get(obj: Any, key: str) -> Any:
    """Retrieve a key from a dict or an attribute from an object."""
    if isinstance(obj, dict):
        return obj[key]
    return getattr(obj, key)


def _assert_approx_equal(
    expected: Any,
    actual: Any,
    *,
    abs_tol: float,
    label: str = "",
) -> None:
    """
    Recursively assert approximate equality for floats; strict equality otherwise.

    Handles scalars, lists/tuples (element-wise), and dicts (value-wise).
    Used by ``Ritual.round_trip`` to compare original and recovered values.
    """
    suffix = f" ({label})" if label else ""

    if isinstance(expected, float) and isinstance(actual, float):
        assert abs(expected - actual) <= abs_tol, (
            f"Approx mismatch{suffix}: "
            f"|{expected} - {actual}| = {abs(expected - actual):.2e} > tol {abs_tol:.2e}"
        )
    elif isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        assert len(expected) == len(actual), (
            f"Length mismatch{suffix}: {len(expected)} != {len(actual)}"
        )
        for i, (e, a) in enumerate(zip(expected, actual)):
            _assert_approx_equal(e, a, abs_tol=abs_tol, label=f"{label}[{i}]")
    elif isinstance(expected, dict) and isinstance(actual, dict):
        assert expected.keys() == actual.keys(), (
            f"Key mismatch{suffix}: {set(expected.keys())} != {set(actual.keys())}"
        )
        for k in expected:
            _assert_approx_equal(expected[k], actual[k], abs_tol=abs_tol, label=f"{label}.{k}")
    else:
        assert expected == actual, (
            f"Mismatch{suffix}: {expected!r} != {actual!r}"
        )
