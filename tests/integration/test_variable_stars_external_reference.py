"""
tests/integration/test_variable_stars_external_reference.py

External-reference spot checks for moira.variable_stars.

Authority:
  AAVSO VSX detail page for bet Per / Algol:
  https://vsx.aavso.org/index.php?revid=296937&view=detail.top

Published ephemeris on the cited page:
  Epoch  = HJD 2455565.33243 (primary minimum)
  Period = 2.867323862 d

  GCVS pages mirrored by VSNET:
  Delta Cephei: https://www.kusastro.kyoto-u.ac.jp/vsnet/gcvs2/CEPdel.html
  Eta Aquilae:  https://www.kusastro.kyoto-u.ac.jp/vsnet/gcvs2/AQLeta.html

Published ephemerides on the cited pages:
  Delta Cephei: Epoch JD 2436075.445, Period 5.366341 d (maximum)
  Eta Aquilae:  Epoch JD 2436084.656, Period 7.176641 d (maximum)

Scope:
  This is a narrow external trust anchor for the variable-star subsystem.
  It does not attempt to validate every catalog entry against external catalogs.
"""

from moira.variable_stars import next_minimum, phase_at, variable_star


AAVSO_ALGOL_EPOCH_HJD = 2455565.33243
AAVSO_ALGOL_PERIOD_DAYS = 2.867323862
GCVS_DELTA_CEP_EPOCH_JD = 2436075.445
GCVS_DELTA_CEP_PERIOD_DAYS = 5.366341
GCVS_ETA_AQL_EPOCH_JD = 2436084.656
GCVS_ETA_AQL_PERIOD_DAYS = 7.176641


def test_algol_catalog_entry_matches_aavso_vsx_ephemeris():
    algol = variable_star("Algol")
    assert algol.epoch_jd == AAVSO_ALGOL_EPOCH_HJD
    assert algol.period_days == AAVSO_ALGOL_PERIOD_DAYS
    assert algol.epoch_is_minimum is True


def test_algol_phase_is_zero_at_aavso_epoch():
    algol = variable_star("Algol")
    assert abs(phase_at(algol, AAVSO_ALGOL_EPOCH_HJD)) < 1e-12


def test_algol_next_minimum_tracks_aavso_linear_ephemeris():
    algol = variable_star("Algol")
    start = AAVSO_ALGOL_EPOCH_HJD + 20.25 * AAVSO_ALGOL_PERIOD_DAYS
    expected = AAVSO_ALGOL_EPOCH_HJD + 21.0 * AAVSO_ALGOL_PERIOD_DAYS
    actual = next_minimum(algol, start)
    assert actual is not None
    assert abs(actual - expected) < 1e-12


def test_delta_cephei_catalog_entry_matches_gcvs_ephemeris():
    delta_cep = variable_star("Delta Cephei")
    assert delta_cep.epoch_jd == GCVS_DELTA_CEP_EPOCH_JD
    assert delta_cep.period_days == GCVS_DELTA_CEP_PERIOD_DAYS
    assert delta_cep.epoch_is_minimum is False


def test_delta_cephei_phase_is_zero_at_gcvs_epoch():
    delta_cep = variable_star("Delta Cephei")
    assert abs(phase_at(delta_cep, GCVS_DELTA_CEP_EPOCH_JD)) < 1e-12


def test_eta_aquilae_catalog_entry_matches_gcvs_ephemeris():
    eta_aql = variable_star("Eta Aquilae")
    assert eta_aql.epoch_jd == GCVS_ETA_AQL_EPOCH_JD
    assert eta_aql.period_days == GCVS_ETA_AQL_PERIOD_DAYS
    assert eta_aql.epoch_is_minimum is False


def test_eta_aquilae_phase_is_zero_at_gcvs_epoch():
    eta_aql = variable_star("Eta Aquilae")
    assert abs(phase_at(eta_aql, GCVS_ETA_AQL_EPOCH_JD)) < 1e-12
