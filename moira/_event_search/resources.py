"""Metered reader loans with pinned pool ordering and no ownership transfer."""
from contextlib import contextmanager

class MeteredReader:
    """RITE: Borrowed-reader accounting

    THEOREM: Delegate computations to the serving reader while charging the request meter and rejecting closure.

    RITE OF PURPOSE:
        Delegate computations to the serving reader while charging the request meter and rejecting closure.

    LAW OF OPERATION:
        Dependencies: borrowed reader, request work meter.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Borrowed resource lifetime and serving-reader identity.

    Borrow a reader and meter its public computational entry points.

    Resource identity/coverage are delegated unchanged. This proxy owns no
    resource and cannot close or mutate the caller's reader. Evaluator closures
    are wrapped as well, preventing lower-level fast paths escaping the meter.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_search.MeteredReader",
      "risk": "medium",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "__getattr__",
          "close"
        ]
      },
      "state": {
        "mutable": true,
        "owners": [
          "one computation request"
        ]
      },
      "effects": {
        "signals_emitted": [],
        "io": [
          "borrowed reader and source-table access"
        ]
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": [
          "public doctrine changes"
        ]
      }
    }
    [/MACHINE_CONTRACT]"""
    _CALLS = frozenset(('position','position_tdb','position_and_velocity',
        'position_and_velocity_tdb','position_and_velocity_tdb_with_receipt'))

    def __init__(self, reader, meter):
        self._reader, self._meter = reader,meter
        # A prewarmed owner may already have thread-local point contexts. Do
        # not inherit them through __getattr__: they hold the owner's reader
        # and would bypass this request's meter (and frozen pool ordering).
        from threading import local
        from ..planets import _READER_CACHE_LOCAL_ATTR
        setattr(self, _READER_CACHE_LOCAL_ATTR, local())

    def __getattr__(self,name):
        if name=='_primary_planetary_reader':
            # Native bulk admission unwraps this accessor and would bypass
            # this request's meter and frozen route owner.
            raise AttributeError(name)
        value = getattr(self._reader,name)
        if name in self._CALLS:
            def call(*args,**kwargs):
                self._meter.tick('reader_calls')
                return value(*args,**kwargs)
            return call
        if name in ('evaluator','evaluator_tdb'):
            def evaluator(*args,**kwargs):
                original = value(*args,**kwargs)
                def call(*a,**k):
                    self._meter.tick('reader_calls')
                    return original(*a,**k)
                return call
            return evaluator
        return value

    def close(self):
        raise RuntimeError('marriage calculation borrows its reader and cannot close it')


@contextmanager
def borrow_reader(reader,meter):
    """Pin a pool's reader order while retaining the original lifetime lease.

    A lease alone protects close, but does not stop additions creating newer
    snapshots. The private pool below has its own frozen order and caches;
    it never closes any of its borrowed readers.
    """
    from ..spk_reader import KernelPool
    if not isinstance(reader,KernelPool):
        yield MeteredReader(reader,meter)
        return
    class FrozenPool(KernelPool):
        """RITE: Pinned reader ordering

        THEOREM: Preserve the leased reader order while rejecting pool additions and resource closure.

        RITE OF PURPOSE:
            Preserve the leased reader order while rejecting pool additions and resource closure.

        LAW OF OPERATION:
            Dependencies: leased pool snapshot.
            Mutable caches and counters belong to one request; computational calls
            remain on its owning thread. Only returned immutable evidence is shared.
            No resource ownership transfers and no missing evidence becomes success.

        Canon: KernelPool snapshot lease; the original pool retains resource ownership.

        [MACHINE_CONTRACT v1]
        {
          "scope": "class",
          "id": "moira._muhurta_marriage_search.FrozenPool",
          "risk": "medium",
          "api": {
            "frozen": [],
            "internal": [
              "add",
              "close"
            ]
          },
          "state": {
            "mutable": true,
            "owners": [
              "one computation request"
            ]
          },
          "effects": {
            "signals_emitted": [],
            "io": [
              "borrowed reader and source-table access"
            ]
          },
          "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only",
            "owner_thread_only_mutation": true
          },
          "failures": {
            "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
          },
          "succession": {
            "stance": "terminal"
          },
          "agent": {
            "autofix": "allowed",
            "requires_human_for": [
              "public doctrine changes"
            ]
          }
        }
        [/MACHINE_CONTRACT]"""
        def add(self,reader):
            raise RuntimeError('marriage reader order is immutable')
        def close(self):
            raise RuntimeError('marriage pool does not own its readers')
    with reader._read_lease() as snapshot:
        pinned=FrozenPool(snapshot.readers)
        borrowed=MeteredReader(pinned,meter)
        borrowed.source_pool_generation=snapshot.generation
        yield borrowed
