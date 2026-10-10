"""Santhanam BPHS ch.45, printed pp.455-456 (PDF pp.454-455).
Sun is 7deg12min Taurus. Exact Moon/Lagna degrees are synthetic cell samples.
"""
from moira.avasthas import sayanadi_avastha


def test_sayanadi_avastha_bphs_example():
    result = sayanadi_avastha("Sun", {"Sun": 30 + 7 + 12 / 60, "Moon": 37.2}, 225, 31, 4)
    assert (result.planet, result.avastha_index, result.state, result.substate) == ("Sun", 3, "Netrapani", "Vicheshta")
    trace = result.trace
    assert (trace.planet_nakshatra, trace.planet_multiplier, trace.navamsa_ordinal,
            trace.moon_nakshatra, trace.lagna_sign, trace.total) == (3, 1, 3, 3, 8, 51)
    assert (trace.stage1_remainder, trace.stage2_remainder) == (1, 0)
    assert result.effect == "Always happy, wise, helpful to others, endowed with prowess and wealth, gain royal favours."
    assert result.effect_provenance.audit_status == "not_source_certified"
    assert result.effect_provenance.conditions_evaluated is False
