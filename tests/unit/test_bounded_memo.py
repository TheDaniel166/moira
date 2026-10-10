"""Adversarial ownership and exact-key checks for reusable bounded computations."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import gc
import math
import weakref

import pytest

from moira._bounded_memo import binary64_key, bounded_memo


def test_binary64_identity_includes_signed_zero_and_adjacent_instants():
    values=(0.,-0.,2461324.,math.nextafter(2461324.,math.inf))
    cached=bounded_memo(lambda x:x,key=binary64_key,maxsize=4)
    for value in values*2:
        assert binary64_key(cached(value))==binary64_key(value)
    assert cached.cache_info()==(4,4,4,4)


@pytest.mark.parametrize('capacity',(0,1,2))
def test_lru_capacity_and_recomputation_do_not_change_results(capacity):
    calls=[]
    def computation(x):
        calls.append(x)
        return x*x
    cached=bounded_memo(computation,key=binary64_key,maxsize=capacity)
    for value in (1.,2.,1.,3.,2.,3.):
        assert cached(value)==value*value
        assert cached.cache_info().currsize<=capacity
    assert calls==({0:[1.,2.,1.,3.,2.,3.],1:[1.,2.,1.,3.,2.,3.],2:[1.,2.,3.,2.]}[capacity])
    cached.cache_clear()
    assert cached.cache_info()==(0,0,capacity,0)
    assert cached(3.)==9. and calls[-1]==3.


@pytest.mark.parametrize('capacity',(-1,True,1.5,None))
def test_invalid_capacity_is_refused(capacity):
    with pytest.raises(ValueError,match='nonnegative integer'):
        bounded_memo(lambda x:x,key=binary64_key,maxsize=capacity)


def test_failures_are_not_retained_and_recovery_is_computed():
    attempts=[]
    def calculation(x):
        attempts.append(x)
        if len(attempts)<=2:
            raise ValueError('source unavailable')
        return x
    cached=bounded_memo(calculation,key=binary64_key,maxsize=1)
    for _ in range(2):
        with pytest.raises(ValueError,match='source unavailable'):
            cached(1.)
        assert cached.cache_info().currsize==0
    assert cached(1.)==cached(1.)==1.
    assert len(attempts)==3


@dataclass(frozen=True)
class Vessel:
    """A frozen test vessel whose contents must also be immutable."""
    payload: object


@pytest.mark.parametrize('result',([1.],{'x':1.},Vessel([1.]),iter((1.,))))
def test_mutable_or_lazy_payload_cannot_poison_reuse(result):
    cached=bounded_memo(lambda:result,key=lambda:b'constant',maxsize=1)
    with pytest.raises(TypeError,match='immutable'):
        cached()
    assert cached.cache_info().currsize==0


def test_frozen_vessels_and_none_are_reusable():
    value=Vessel((1.,None,b'bits',Vessel(('nested',False))))
    cached=bounded_memo(lambda x:value if x else None,key=lambda x:bytes((x,)),maxsize=2)
    assert cached(True) is cached(True) is value
    assert cached(False) is cached(False) is None
    assert cached.cache_info().hits==2


def test_only_explicit_byte_keys_are_admitted_before_computation():
    calls=[]
    cached=bounded_memo(lambda x:calls.append(x),key=lambda x:x,maxsize=2)
    with pytest.raises(TypeError,match='exact bytes'):
        cached(1.)
    assert calls==[]


def test_keywords_share_only_when_the_owner_explicitly_defines_equivalence():
    def fn(x,*,scale=1.):
        return x*scale
    cached=bounded_memo(fn,key=lambda x,scale=1.:binary64_key(x,scale),maxsize=4)
    assert cached(2.)==cached(x=2.,scale=1.)==2.
    assert cached(2.,scale=3.)==6.
    assert cached.cache_info().hits==1


def test_each_owner_has_separate_dependencies_and_explicit_invalidation():
    first={'scale':2.}
    second={'scale':3.}
    a=bounded_memo(lambda x:x*first['scale'],key=binary64_key,maxsize=1)
    b=bounded_memo(lambda x:x*second['scale'],key=binary64_key,maxsize=1)
    assert a(4.)==8. and b(4.)==12.
    first['scale']=5.
    a.cache_clear()  # A changed bound dependency requires a new scope or invalidation.
    assert a(4.)==20. and b(4.)==12.


def test_cross_thread_hits_misses_inspection_and_invalidation_are_rejected():
    cached=bounded_memo(lambda x:x,key=binary64_key,maxsize=1)
    cached(1.)
    with ThreadPoolExecutor(max_workers=1) as executor:
        for fn in (lambda:cached(1.),lambda:cached(2.),cached.cache_clear,cached.cache_info):
            with pytest.raises(RuntimeError,match='creating thread'):
                executor.submit(fn).result()
    assert cached.cache_info()==(0,1,1,1)


def test_finished_scope_does_not_leave_a_global_reference_to_its_owner():
    class Owner:
        def compute(self,x):
            return Vessel(x)
    owner=Owner()
    cached=bounded_memo(owner.compute,key=binary64_key,maxsize=1)
    reference=weakref.ref(owner)
    assert cached(1.)==Vessel(1.)
    del cached,owner
    gc.collect()
    assert reference() is None


def test_reuse_is_independent_of_marriage_with_actual_naif_clock_conversion():
    from moira.julian import tt_to_tdb
    cached=bounded_memo(tt_to_tdb,key=binary64_key,maxsize=2)
    for jd in (2451545.,2461324.,2451545.,2461324.):
        assert binary64_key(cached(jd))==binary64_key(tt_to_tdb(jd))
    assert cached.cache_info()==(2,2,2,2)
