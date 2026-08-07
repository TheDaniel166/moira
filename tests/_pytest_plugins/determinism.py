"""Deterministic Python and Hypothesis execution policy."""

from __future__ import annotations

import random
from dataclasses import replace
import platform
import sys
from types import CodeType, FunctionType, ModuleType, SimpleNamespace

import pytest

from ._state import (
    _HARNESS_CONFIG_KEY,
    _HypothesisPolicy,
)


def _capture_python_implementation_provider() -> tuple[object, ...]:
    function = platform.python_implementation
    code = (
        object.__getattribute__(function, "__code__")
        if type(function) is FunctionType
        else None
    )
    globals_namespace = (
        object.__getattribute__(function, "__globals__")
        if type(function) is FunctionType
        else None
    )
    defaults = (
        object.__getattribute__(function, "__defaults__")
        if type(function) is FunctionType
        else None
    )
    kwdefaults = (
        object.__getattribute__(function, "__kwdefaults__")
        if type(function) is FunctionType
        else None
    )
    closure = (
        object.__getattribute__(function, "__closure__")
        if type(function) is FunctionType
        else None
    )
    function_namespace = (
        object.__getattribute__(function, "__dict__")
        if type(function) is FunctionType
        else None
    )
    function_items = (
        tuple(function_namespace.items())
        if type(function_namespace) is dict
        else ()
    )
    implementation = vars(sys).get("implementation")
    implementation_namespace = (
        object.__getattribute__(implementation, "__dict__")
        if type(implementation) is SimpleNamespace
        else None
    )
    implementation_name = (
        dict.get(implementation_namespace, "name")
        if type(implementation_namespace) is dict
        else None
    )
    if (
        type(platform) is not ModuleType
        or sys.modules.get("platform") is not platform
        or type(function) is not FunctionType
        or type(code) is not CodeType
        or globals_namespace is not vars(platform)
        or defaults is not None
        or kwdefaults is not None
        or closure is not None
        or type(function_namespace) is not dict
        or len(function_items) != 0
        or function.__module__ != "platform"
        or function.__name__ != "python_implementation"
        or function.__qualname__ != "python_implementation"
        or sys.modules.get("sys") is not sys
        or implementation is not sys.implementation
        or type(implementation) is not SimpleNamespace
        or type(implementation_namespace) is not dict
        or type(implementation_name) is not str
        or implementation_name != "cpython"
    ):
        raise RuntimeError("exact Python implementation provider is unavailable")
    return (
        platform,
        function,
        code,
        globals_namespace,
        defaults,
        kwdefaults,
        closure,
        function_namespace,
        function_items,
        sys,
        implementation,
        implementation_namespace,
        implementation_name,
    )


_PYTHON_IMPLEMENTATION_PROVIDER = _capture_python_implementation_provider()


def _register_hypothesis_profiles() -> bool:
    try:
        from hypothesis import settings, Verbosity
    except ImportError:
        return False

    parent = settings.get_profile("default")
    settings.register_profile(
        "moira-ci",
        parent=parent,
        max_examples=50,
        verbosity=Verbosity.quiet,
        database=None,
        derandomize=True,
        deadline=1000,
    )
    settings.register_profile(
        "moira-local",
        parent=parent,
        max_examples=100,
        verbosity=Verbosity.normal,
        derandomize=False,
        deadline=1000,
    )
    settings.register_profile(
        "moira-nightly",
        parent=parent,
        max_examples=1000,
        verbosity=Verbosity.normal,
        derandomize=False,
        deadline=None,
    )
    return True


_HYPOTHESIS_PROFILE_REGISTRAR = (_register_hypothesis_profiles,)
_HYPOTHESIS_AVAILABLE = _HYPOTHESIS_PROFILE_REGISTRAR[0]()


def _capture_hypothesis_profile_runtime_providers() -> tuple[object, ...]:
    import _thread
    import annotationlib
    import threading
    import typing

    return (
        typing,
        typing.Union,
        typing._GenericAlias,
        annotationlib,
        annotationlib.ForwardRef,
        _thread,
        _thread._local,
        threading,
        threading.local,
        threading._thread_local_info,
    )


_HYPOTHESIS_PROFILE_RUNTIME_PROVIDERS = (
    _capture_hypothesis_profile_runtime_providers()
    if _HYPOTHESIS_AVAILABLE
    else ()
)


def _capture_hypothesis_compat_stdlib_providers() -> tuple[object, ...]:
    import dataclasses
    import itertools

    return (
        dataclasses,
        dataclasses.asdict,
        itertools,
        getattr(itertools, "batched", None),
        dataclasses._asdict_inner,
        dataclasses._is_dataclass_instance,
        dataclasses.fields,
        dataclasses._ATOMIC_TYPES,
        dataclasses._FIELDS,
        dataclasses._FIELD,
        dataclasses.copy,
        dataclasses.copy.deepcopy,
    )


_HYPOTHESIS_COMPAT_STDLIB_PROVIDERS = (
    _capture_hypothesis_compat_stdlib_providers()
    if _HYPOTHESIS_AVAILABLE
    else ()
)


def _capture_hypothesis_coverage_disabled_outcome() -> tuple[object, ...]:
    import os
    from types import CellType, CodeType, FunctionType

    from hypothesis.internal import coverage as coverage_module
    from hypothesis.internal import validation
    from hypothesis.strategies._internal import strategies

    consumer_bindings = (
        (
            "hypothesis.internal.validation",
            validation,
            "check_function",
            validation.check_function,
        ),
        (
            "hypothesis.strategies._internal.strategies",
            strategies,
            "check_function",
            strategies.check_function,
        ),
    )
    check_function = coverage_module.check_function
    check = coverage_module.check
    raw_check = vars(check).get("__wrapped__")
    check_closure = object.__getattribute__(check, "__closure__")
    if (
        coverage_module.IN_COVERAGE_TESTS is not False
        or "HYPOTHESIS_INTERNAL_COVERAGE" in os.environ
        or type(os.getenv) is not FunctionType
        or type(object.__getattribute__(os.getenv, "__code__")) is not CodeType
        or type(check_function) is not FunctionType
        or type(object.__getattribute__(check_function, "__code__")) is not CodeType
        or type(check) is not FunctionType
        or type(object.__getattribute__(check, "__code__")) is not CodeType
        or type(raw_check) is not FunctionType
        or type(object.__getattribute__(raw_check, "__code__")) is not CodeType
        or type(check_closure) is not tuple
        or len(check_closure) != 1
        or type(check_closure[0]) is not CellType
        or check_closure[0].cell_contents is not raw_check
        or any(
            value is not check_function
            for _name, _module, _attribute, value in consumer_bindings
        )
    ):
        raise RuntimeError(
            "Hypothesis internal coverage must be exactly disabled"
        )
    return (
        coverage_module,
        coverage_module.IN_COVERAGE_TESTS,
        os,
        os.getenv,
        object.__getattribute__(os.getenv, "__code__"),
        os.environ,
        check_function,
        object.__getattribute__(check_function, "__code__"),
        check,
        object.__getattribute__(check, "__code__"),
        raw_check,
        object.__getattribute__(raw_check, "__code__"),
        check_closure,
        consumer_bindings,
    )


_HYPOTHESIS_COVERAGE_DISABLED_OUTCOME = (
    _capture_hypothesis_coverage_disabled_outcome()
    if _HYPOTHESIS_AVAILABLE
    else ()
)


def _exact_hypothesis_coverage_disabled_outcome(
    _anchor: tuple[object, ...] = _HYPOTHESIS_COVERAGE_DISABLED_OUTCOME,
    _capture: object = _capture_hypothesis_coverage_disabled_outcome,
    _namespace: dict[str, object] = globals(),
) -> tuple[object, ...]:
    if (
        dict.get(_namespace, "_HYPOTHESIS_COVERAGE_DISABLED_OUTCOME")
        is not _anchor
        or dict.get(
            _namespace,
            "_capture_hypothesis_coverage_disabled_outcome",
        )
        is not _capture
        or dict.get(
            _namespace,
            "_exact_hypothesis_coverage_disabled_outcome",
        )
        is not _exact_hypothesis_coverage_disabled_outcome
        or type(_anchor) is not tuple
        or len(_anchor) != 14
    ):
        raise RuntimeError(
            "Hypothesis internal coverage anchor must be exact"
        )
    return _anchor


def _capture_hypothesis_entropy_randomlike_provider() -> tuple[object, ...]:
    import sys
    import typing
    from types import (
        BuiltinFunctionType,
        CellType,
        CodeType,
        FunctionType,
        MappingProxyType,
        ModuleType,
    )

    from hypothesis.internal import compat, entropy

    random_class = vars(random).get("Random")
    random_like = vars(entropy).get("RandomLike")
    pypy = vars(compat).get("PYPY")
    graalpy = vars(compat).get("GRAALPY")
    free_threaded_cpython = vars(compat).get("FREE_THREADED_CPYTHON")
    sysconfig_module = vars(compat).get("sysconfig")
    sysconfig_vars = (
        vars(sysconfig_module).get("_CONFIG_VARS")
        if type(sysconfig_module) is ModuleType
        else None
    )
    free_threaded_raw = (
        dict.get(sysconfig_vars, "Py_GIL_DISABLED")
        if type(sysconfig_vars) is dict
        else None
    )
    free_threaded_expected = (
        not int.__eq__(free_threaded_raw, 0)
        if type(free_threaded_raw) is int
        else False
    )
    implementation_provider = _PYTHON_IMPLEMENTATION_PROVIDER
    implementation_function = (
        tuple.__getitem__(implementation_provider, 1)
        if type(implementation_provider) is tuple
        and len(implementation_provider) == 13
        else None
    )
    random_class_namespace = (
        type.__getattribute__(random_class, "__dict__")
        if type(random_class) is type
        else None
    )
    random_class_items = (
        tuple(random_class_namespace.items())
        if random_class_namespace is not None
        else ()
    )
    random_class_bases = (
        type.__getattribute__(random_class, "__bases__")
        if type(random_class) is type
        else ()
    )
    refcount_function = vars(entropy).get("_get_platform_base_refcount")
    refcount_code = (
        object.__getattribute__(refcount_function, "__code__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_globals = (
        object.__getattribute__(refcount_function, "__globals__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_defaults = (
        object.__getattribute__(refcount_function, "__defaults__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_kwdefaults = (
        object.__getattribute__(refcount_function, "__kwdefaults__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_closure = (
        object.__getattribute__(refcount_function, "__closure__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_namespace = (
        object.__getattribute__(refcount_function, "__dict__")
        if type(refcount_function) is FunctionType
        else None
    )
    refcount_namespace_items = (
        tuple(refcount_namespace.items())
        if type(refcount_namespace) is dict
        else ()
    )
    refcount_annotate = (
        object.__getattribute__(refcount_function, "__annotate__")
        if type(refcount_function) is FunctionType
        and "__annotate__" in vars(FunctionType)
        else None
    )
    refcount_annotate_code = (
        object.__getattribute__(refcount_annotate, "__code__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_globals = (
        object.__getattribute__(refcount_annotate, "__globals__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_defaults = (
        object.__getattribute__(refcount_annotate, "__defaults__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_kwdefaults = (
        object.__getattribute__(refcount_annotate, "__kwdefaults__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_closure = (
        object.__getattribute__(refcount_annotate, "__closure__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_namespace = (
        object.__getattribute__(refcount_annotate, "__dict__")
        if type(refcount_annotate) is FunctionType
        else None
    )
    refcount_annotate_items = (
        tuple(refcount_annotate_namespace.items())
        if type(refcount_annotate_namespace) is dict
        else ()
    )
    entropy_sys = vars(entropy).get("sys")
    getrefcount = vars(sys).get("getrefcount")
    getrefcount_self = (
        object.__getattribute__(getrefcount, "__self__")
        if type(getrefcount) is BuiltinFunctionType
        else None
    )
    getrefcount_module = (
        object.__getattribute__(getrefcount, "__module__")
        if type(getrefcount) is BuiltinFunctionType
        else None
    )
    getrefcount_name = (
        object.__getattribute__(getrefcount, "__name__")
        if type(getrefcount) is BuiltinFunctionType
        else None
    )
    getrefcount_qualname = (
        object.__getattribute__(getrefcount, "__qualname__")
        if type(getrefcount) is BuiltinFunctionType
        else None
    )
    getrefcount_text_signature = (
        object.__getattribute__(getrefcount, "__text_signature__")
        if type(getrefcount) is BuiltinFunctionType
        else None
    )
    platform_ref_count = vars(entropy).get("_PLATFORM_REF_COUNT")
    random_method_fingerprints: list[tuple[object, ...]] = []
    for method_name in ("seed", "getstate", "setstate"):
        method = (
            random_class_namespace.get(method_name)
            if type(random_class_namespace) is MappingProxyType
            else None
        )
        code = (
            object.__getattribute__(method, "__code__")
            if type(method) is FunctionType
            else None
        )
        globals_namespace = (
            object.__getattribute__(method, "__globals__")
            if type(method) is FunctionType
            else None
        )
        defaults = (
            object.__getattribute__(method, "__defaults__")
            if type(method) is FunctionType
            else None
        )
        kwdefaults = (
            object.__getattribute__(method, "__kwdefaults__")
            if type(method) is FunctionType
            else None
        )
        closure = (
            object.__getattribute__(method, "__closure__")
            if type(method) is FunctionType
            else None
        )
        closure_contents = (
            tuple(cell.cell_contents for cell in closure)
            if type(closure) is tuple
            and all(type(cell) is CellType for cell in closure)
            else ()
        )
        method_namespace = (
            object.__getattribute__(method, "__dict__")
            if type(method) is FunctionType
            else None
        )
        method_namespace_items = (
            tuple(method_namespace.items())
            if type(method_namespace) is dict
            else ()
        )
        annotate = (
            object.__getattribute__(method, "__annotate__")
            if type(method) is FunctionType
            and "__annotate__" in vars(FunctionType)
            else None
        )
        annotations = (
            object.__getattribute__(method, "__annotations__")
            if type(method) is FunctionType and annotate is None
            else None
        )
        method_module = (
            object.__getattribute__(method, "__module__")
            if type(method) is FunctionType
            else None
        )
        method_name_value = (
            object.__getattribute__(method, "__name__")
            if type(method) is FunctionType
            else None
        )
        method_qualname = (
            object.__getattribute__(method, "__qualname__")
            if type(method) is FunctionType
            else None
        )
        method_doc = (
            object.__getattribute__(method, "__doc__")
            if type(method) is FunctionType
            else None
        )
        if (
            type(method) is not FunctionType
            or type(code) is not CodeType
            or globals_namespace is not vars(random)
            or (
                method_name == "seed"
                and (
                    type(defaults) is not tuple
                    or defaults != (None, 2)
                )
            )
            or (method_name != "seed" and defaults is not None)
            or kwdefaults is not None
            or type(closure) is not tuple
            or len(closure) != 1
            or len(closure_contents) != 1
            or closure_contents[0] is not random_class
            or type(method_namespace) is not dict
            or any(
                type(name) is not str
                for name, _value in method_namespace_items
            )
            or type(annotations) is not dict
            or any(type(name) is not str for name in annotations)
            or annotate is not None
            or method_module != "random"
            or method_name_value != method_name
            or method_qualname != f"Random.{method_name}"
            or (method_doc is not None and type(method_doc) is not str)
        ):
            raise RuntimeError(
                "Hypothesis entropy RandomLike method provider must be exact"
            )
        random_method_fingerprints.append(
            (
                method_name,
                method,
                code,
                globals_namespace,
                defaults,
                kwdefaults,
                closure,
                closure_contents,
                method_namespace,
                method_namespace_items,
                annotations,
                annotate,
                method_module,
                method_name_value,
                method_qualname,
                method_doc,
            )
        )
    if (
        type(entropy) is not ModuleType
        or sys.modules.get("hypothesis.internal.entropy") is not entropy
        or type(random) is not ModuleType
        or sys.modules.get("random") is not random
        or type(random_class) is not type
        or random_like is not random_class
        or vars(entropy).get("random") is not random
        or vars(entropy).get("Random") is not random_class
        or sys.modules.get("typing") is not typing
        or vars(typing).get("TYPE_CHECKING") is not False
        or vars(entropy).get("TYPE_CHECKING") is not False
        or type(compat) is not ModuleType
        or sys.modules.get("hypothesis.internal.compat") is not compat
        or type(pypy) is not bool
        or type(graalpy) is not bool
        or type(free_threaded_cpython) is not bool
        or type(sysconfig_module) is not ModuleType
        or sys.modules.get("sysconfig") is not sysconfig_module
        or type(sysconfig_vars) is not dict
        or (
            free_threaded_raw is not None
            and (
                type(free_threaded_raw) is not int
                or free_threaded_raw not in (0, 1)
            )
        )
        or type(implementation_provider) is not tuple
        or len(implementation_provider) != 13
        or tuple.__getitem__(implementation_provider, 0) is not platform
        or vars(compat).get("platform") is not platform
        or vars(platform).get("python_implementation")
        is not implementation_function
        or type(implementation_function) is not FunctionType
        or object.__getattribute__(implementation_function, "__code__")
        is not tuple.__getitem__(implementation_provider, 2)
        or object.__getattribute__(implementation_function, "__globals__")
        is not tuple.__getitem__(implementation_provider, 3)
        or object.__getattribute__(implementation_function, "__defaults__")
        is not tuple.__getitem__(implementation_provider, 4)
        or object.__getattribute__(implementation_function, "__kwdefaults__")
        is not tuple.__getitem__(implementation_provider, 5)
        or object.__getattribute__(implementation_function, "__closure__")
        is not tuple.__getitem__(implementation_provider, 6)
        or object.__getattribute__(implementation_function, "__dict__")
        is not tuple.__getitem__(implementation_provider, 7)
        or tuple(object.__getattribute__(implementation_function, "__dict__").items())
        != tuple.__getitem__(implementation_provider, 8)
        or tuple.__getitem__(implementation_provider, 9) is not sys
        or tuple.__getitem__(implementation_provider, 10)
        is not sys.implementation
        or tuple.__getitem__(implementation_provider, 11)
        is not object.__getattribute__(sys.implementation, "__dict__")
        or tuple.__getitem__(implementation_provider, 12) != "cpython"
        or pypy is not False
        or graalpy is not False
        or free_threaded_cpython is not free_threaded_expected
        or vars(entropy).get("PYPY") is not pypy
        or vars(entropy).get("GRAALPY") is not graalpy
        or vars(entropy).get("FREE_THREADED_CPYTHON")
        is not free_threaded_cpython
        or type.__getattribute__(random_class, "__module__") != "random"
        or type.__getattribute__(random_class, "__name__") != "Random"
        or type.__getattribute__(random_class, "__qualname__") != "Random"
        or type(random_class_bases) is not tuple
        or len(random_class_bases) != 1
        or not all(type(base) is type for base in random_class_bases)
        or any(type(name) is not str for name, _value in random_class_items)
        or len(random_method_fingerprints) != 3
        or type(refcount_function) is not FunctionType
        or type(refcount_code) is not CodeType
        or refcount_globals is not vars(entropy)
        or refcount_defaults is not None
        or refcount_kwdefaults is not None
        or refcount_closure is not None
        or type(refcount_namespace) is not dict
        or len(refcount_namespace_items) != 0
        or type(refcount_annotate) is not FunctionType
        or type(refcount_annotate_code) is not CodeType
        or refcount_annotate_globals is not vars(entropy)
        or refcount_annotate_defaults is not None
        or refcount_annotate_kwdefaults is not None
        or refcount_annotate_closure is not None
        or type(refcount_annotate_namespace) is not dict
        or len(refcount_annotate_items) != 0
        or object.__getattribute__(refcount_annotate, "__module__")
        != "hypothesis.internal.entropy"
        or object.__getattribute__(refcount_annotate, "__name__")
        != "__annotate__"
        or object.__getattribute__(refcount_annotate, "__qualname__")
        != "__annotate__"
        or object.__getattribute__(refcount_annotate, "__doc__") is not None
        or object.__getattribute__(refcount_annotate_code, "co_firstlineno")
        != 66
        or object.__getattribute__(refcount_annotate_code, "co_argcount") != 1
        or object.__getattribute__(
            refcount_annotate_code,
            "co_posonlyargcount",
        )
        != 1
        or object.__getattribute__(
            refcount_annotate_code,
            "co_kwonlyargcount",
        )
        != 0
        or object.__getattribute__(refcount_annotate_code, "co_names")
        != ("Any", "int")
        or object.__getattribute__(refcount_annotate_code, "co_varnames")
        != ("format",)
        or object.__getattribute__(refcount_annotate_code, "co_consts")
        != (2, "r", "return")
        or object.__getattribute__(refcount_annotate_code, "co_freevars")
        != ()
        or object.__getattribute__(refcount_annotate_code, "co_cellvars")
        != ()
        or object.__getattribute__(refcount_function, "__module__")
        != "hypothesis.internal.entropy"
        or object.__getattribute__(refcount_function, "__name__")
        != "_get_platform_base_refcount"
        or object.__getattribute__(refcount_function, "__qualname__")
        != "_get_platform_base_refcount"
        or object.__getattribute__(refcount_function, "__doc__") is not None
        or object.__getattribute__(refcount_code, "co_firstlineno") != 66
        or object.__getattribute__(refcount_code, "co_names")
        != ("sys", "getrefcount")
        or entropy_sys is not sys
        or type(getrefcount) is not BuiltinFunctionType
        or getrefcount is not sys.getrefcount
        or getrefcount_self is not sys
        or getrefcount_module != "sys"
        or getrefcount_name != "getrefcount"
        or getrefcount_qualname != "getrefcount"
        or getrefcount_text_signature != "($module, object, /)"
        or type(platform_ref_count) is not int
        or platform_ref_count != 1
    ):
        raise RuntimeError(
            "Hypothesis entropy RandomLike provider must be exact"
        )
    return (
        entropy,
        random,
        random_class,
        random_like,
        vars(entropy).get("random"),
        vars(entropy).get("Random"),
        typing,
        vars(entropy).get("TYPE_CHECKING"),
        random_class_namespace,
        random_class_items,
        random_class_bases,
        tuple(random_method_fingerprints),
        compat,
        vars(entropy).get("PYPY"),
        pypy,
        vars(entropy).get("GRAALPY"),
        graalpy,
        vars(entropy).get("FREE_THREADED_CPYTHON"),
        free_threaded_cpython,
        implementation_provider,
        (
            refcount_function,
            refcount_code,
            refcount_globals,
            refcount_defaults,
            refcount_kwdefaults,
            refcount_closure,
            refcount_namespace,
            refcount_namespace_items,
            (
                refcount_annotate,
                refcount_annotate_code,
                refcount_annotate_globals,
                refcount_annotate_defaults,
                refcount_annotate_kwdefaults,
                refcount_annotate_closure,
                refcount_annotate_namespace,
                refcount_annotate_items,
                object.__getattribute__(refcount_annotate, "__module__"),
                object.__getattribute__(refcount_annotate, "__name__"),
                object.__getattribute__(refcount_annotate, "__qualname__"),
                object.__getattribute__(refcount_annotate, "__doc__"),
            ),
            object.__getattribute__(refcount_function, "__module__"),
            object.__getattribute__(refcount_function, "__name__"),
            object.__getattribute__(refcount_function, "__qualname__"),
            object.__getattribute__(refcount_function, "__doc__"),
            entropy_sys,
            sys,
            getrefcount,
            (
                getrefcount,
                getrefcount_self,
                getrefcount_module,
                getrefcount_name,
                getrefcount_qualname,
                getrefcount_text_signature,
            ),
            platform_ref_count,
        ),
        (
            sysconfig_module,
            sysconfig_vars,
            free_threaded_raw,
            free_threaded_expected,
        ),
    )


_HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER = (
    _capture_hypothesis_entropy_randomlike_provider()
    if _HYPOTHESIS_AVAILABLE
    else ()
)


def _exact_hypothesis_entropy_randomlike_provider(
    _anchor: tuple[object, ...] = _HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER,
    _capture: object = _capture_hypothesis_entropy_randomlike_provider,
    _namespace: dict[str, object] = globals(),
) -> tuple[object, ...]:
    if (
        dict.get(_namespace, "_HYPOTHESIS_ENTROPY_RANDOMLIKE_PROVIDER")
        is not _anchor
        or dict.get(
            _namespace,
            "_capture_hypothesis_entropy_randomlike_provider",
        )
        is not _capture
        or dict.get(
            _namespace,
            "_exact_hypothesis_entropy_randomlike_provider",
        )
        is not _exact_hypothesis_entropy_randomlike_provider
        or type(_anchor) is not tuple
        or len(_anchor) != 22
    ):
        raise RuntimeError(
            "Hypothesis entropy RandomLike anchor must be exact"
        )
    return _anchor


def activate_hypothesis_policy(
    config,
    *,
    test_mode: bool,
) -> _HypothesisPolicy:
    if not _HYPOTHESIS_AVAILABLE:
        raise pytest.UsageError(
            "Hypothesis is required by the Moira test harness; install the "
            "declared development dependencies."
        )

    from hypothesis import errors, settings

    explicit_profile = config.getoption(
        "--hypothesis-profile",
        default=None,
    )
    selected_profile = (
        explicit_profile or ("moira-ci" if test_mode else "moira-local")
    )
    try:
        settings.load_profile(selected_profile)
    except (errors.InvalidArgument, KeyError) as exc:
        raise pytest.UsageError(
            f"Unknown or invalid Hypothesis profile {selected_profile!r}."
        ) from exc

    return snapshot_hypothesis_policy()


def snapshot_hypothesis_policy() -> _HypothesisPolicy:
    from hypothesis import settings

    active = settings.default
    database_policy = (
        "disabled"
        if active.database is None
        else f"enabled:{type(active.database).__name__}"
    )
    return _HypothesisPolicy(
        profile=settings.get_current_profile_name(),
        max_examples=active.max_examples,
        database_policy=database_policy,
        derandomize=active.derandomize,
    )


def mark_property_test(item) -> None:
    if item.get_closest_marker("property") or not hasattr(item, "function"):
        return
    function = item.function
    if (
        hasattr(function, "hypothesis")
        or hasattr(function, "hypothesis_explicit_examples")
    ):
        item.add_marker(pytest.mark.property)


@pytest.hookimpl
def pytest_configure(config) -> None:
    random.seed(config.stash[_HARNESS_CONFIG_KEY].seed)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session) -> None:
    """Receipt the effective policy after all configure hooks have completed."""

    initial_policy = session.config.stash[_HARNESS_CONFIG_KEY]
    session.config.stash[_HARNESS_CONFIG_KEY] = replace(
        initial_policy,
        hypothesis=snapshot_hypothesis_policy(),
    )


@pytest.fixture(scope="session", autouse=True)
def _seed_test_random(request):
    """Reset Python's RNG after collection before test execution begins."""

    random.seed(request.config.stash[_HARNESS_CONFIG_KEY].seed)
