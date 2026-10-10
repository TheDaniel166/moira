"""Bounded reuse of immutable computations within one explicitly owned scope.

Each wrapper owns one callable, one exact byte-key contract and its own finite
LRU. The caller binds stable dependencies (reader/source, frame and policy) in
that callable's lifetime, and includes every remaining input in the key. There
is no module cache, resource discovery, time quantization or failure caching.
This is private engine infrastructure, not a cross-request result service.
"""
from collections import OrderedDict
from dataclasses import fields, is_dataclass
from functools import wraps
from struct import pack
from threading import current_thread
from typing import NamedTuple


class MemoInfo(NamedTuple):
    """A detached observation of one computation's bounded reuse."""
    hits: int
    misses: int
    maxsize: int
    currsize: int


def binary64_key(*values):
    """Encode exact binary64 inputs, preserving signed zero and adjacent values."""
    return pack('!'+'d'*len(values), *values)


def _require_immutable(value):
    """Reject mutable payloads, including fields inside frozen data vessels."""
    if value is None or type(value) in (bool, int, float, str, bytes):
        return
    if type(value) is tuple:
        for item in value:
            _require_immutable(item)
        return
    if (not isinstance(value, type) and is_dataclass(value)
            and value.__dataclass_params__.frozen):
        for field in fields(value):
            _require_immutable(getattr(value, field.name))
        return
    raise TypeError('bounded memo results must be immutable values or frozen data vessels')


def bounded_memo(function, *, key, maxsize):
    """Bind one finite, thread-owned exact-input memo to an immutable computation.

    ``key`` must return bytes identifying all unfrozen inputs without rounding.
    The wrapper does not infer scientific equivalence, source identity or
    cancellation. Exceptions propagate and are never retained. Results must be
    primitives, tuples or recursively immutable frozen dataclasses. Keys and
    results are bounded by entry count; the owner must bound each payload too.
    ``cache_clear`` invalidates the scope; ``__wrapped__`` retains the original
    computation for differential validation. No cache hit replays side effects:
    metering, admission, resource leases and source checks belong outside it.
    """
    if type(maxsize) is not int or maxsize < 0:
        raise ValueError('maxsize must be a nonnegative integer')
    if not callable(function) or not callable(key):
        raise TypeError('a computation and exact byte-key callable are required')
    owner = current_thread()
    cache = OrderedDict()
    hits = misses = 0

    def check_owner():
        if current_thread() is not owner:
            raise RuntimeError('bounded memo belongs to its creating thread')

    @wraps(function)
    def compute(*args, **kwargs):
        nonlocal hits, misses
        check_owner()
        token = key(*args, **kwargs)
        if type(token) is not bytes:
            raise TypeError('bounded memo keys must be exact bytes')
        try:
            result = cache[token]
        except KeyError:
            misses += 1
            result = function(*args, **kwargs)
            _require_immutable(result)
            if maxsize:
                cache[token] = result
                if len(cache) > maxsize:
                    cache.popitem(last=False)
            return result
        cache.move_to_end(token)
        hits += 1
        return result

    def cache_info():
        check_owner()
        return MemoInfo(hits, misses, maxsize, len(cache))

    def cache_clear():
        nonlocal hits, misses
        check_owner()
        cache.clear()
        hits = misses = 0

    compute.cache_info = cache_info
    compute.cache_clear = cache_clear
    return compute
