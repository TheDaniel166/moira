"""Forward clock totality is separate from a successful value enclosure."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_stage3_route_obligations import prove_stage3_clock_route_obligations


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('epoch,branch',[(1421936.2171787173,'historical_hpiers'),
    (2459891.96,'direct_eop'),(2763363.8118256605,'future_scenario')])
@pytest.mark.parametrize('policy',['native','canon_catalog'])
def test_selected_clock_and_identity_routes_have_finite_execution(planetary_reader,epoch,branch,policy):
    result = prove_stage3_clock_route_obligations(planetary_reader,epoch,I(F(-1,6),F(1,6)),policy=policy)
    assert result.clock_branch==(branch if policy=='native' else 'canon_catalog_monthly')
    assert result.forward_totality_under_declared_premises
    assert result.direct_identity_routes_covered and result.historical_raw_identity_guard_covered
    assert result.identity_descriptor_count==4
    assert 0<result.compensated_recovery_max_iterations<=8
    assert not result.legacy_split_fallback_possible
    assert not result.physical_accuracy_certified


def test_route_obligation_rejects_an_unsupported_reader():
    with pytest.raises(EnclosureUnavailable,match='direct reader'):
        prove_stage3_clock_route_obligations(object(),2451545.,I(-1,1))


@pytest.mark.requires_ephemeris
def test_unproved_ancient_clock_branch_fails_closed(planetary_reader):
    with pytest.raises(EnclosureUnavailable,match='not yet proved'):
        prove_stage3_clock_route_obligations(planetary_reader,800000.,I(-1,1))
