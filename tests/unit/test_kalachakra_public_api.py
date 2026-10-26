"""Module/root/vedic/facade exports and reader-free instance operations."""
import importlib
import pytest
from moira import Moira
from moira.kalachakra_policy import PROFILE_ID, PROFILE_IDS


@pytest.mark.parametrize('profile_id',PROFILE_IDS)
def test_export_identity_and_supplied_sidereal_parity(profile_id):
    owner = importlib.import_module('moira.kalachakra')
    seed = owner.KalachakraSeed('sidereal',45.8)
    expected = owner.kalachakra_sequence(seed,profile_id=profile_id)
    for name in ('moira','moira.facade','moira.vedic'):
        module = importlib.import_module(name)
        for symbol in owner.__all__:
            assert symbol in module.__all__
            assert getattr(module,symbol) is getattr(owner,symbol)
        assert module.kalachakra_sequence(seed,profile_id=profile_id) == expected
    # Deliberately no reader attribute: pure facade operations must remain pure.
    assert Moira.kalachakra_sequence(object(),seed,profile_id=profile_id) == expected
    assert Moira.kalachakra_profiles(object()) == owner.kalachakra_profiles()
    epoch = owner.KalachakraEpoch('jd_utc',2451545)
    projected = Moira.project_kalachakra_sequence(object(),expected,birth_epoch=epoch,year_basis='savana_360')
    assert Moira.current_kalachakra_periods(object(),projected,epoch).status == 'active'


def test_invalid_facade_inputs_do_not_touch_reader():
    from moira.kalachakra import KalachakraInputError, KalachakraSeed, KalachakraEpoch
    from datetime import datetime,timezone
    with pytest.raises(KalachakraInputError):
        Moira.kalachakra_for_datetime(object(),datetime(2000,1,1,tzinfo=timezone.utc),
            profile_id='candidate',ayanamsa_system='Lahiri')
    with pytest.raises(KalachakraInputError):
        Moira.kalachakra_sequence(object(),KalachakraSeed('tropical',12,'Lahiri'),
            profile_id=PROFILE_ID,birth_epoch=KalachakraEpoch('jd_utc',1e100))
