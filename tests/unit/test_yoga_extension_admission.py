"""Shared legacy/extension admission and truthful unavailable motion evidence."""

from dataclasses import replace
import pytest
from moira import yogas
from moira.yoga_extensions import evaluate_yoga_extensions
from moira.yoga_extension_policy import YogaExtensionPolicy

BASE = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mars": 20.0,
    "Mercury": 160.0,
    "Jupiter": 245.0,
    "Venus": 185.0,
    "Saturn": 280.0,
}
PROFILE = "jp_sastri_7_14_v1"
FAMILIES = [
    getattr(yogas, n)
    for n in (
        "pancha_mahapurusha_yogas",
        "chandra_yogas",
        "surya_yogas",
        "nabhasa_yogas",
        "raja_yogas",
        "dhana_yogas",
        "evaluate_yogas",
    )
]


@pytest.mark.parametrize("function", FAMILIES)
@pytest.mark.parametrize("bad", [True, "12", None, float("nan"), float("inf")])
def test_legacy_public_families_reject_bad_longitudes(function, bad):
    with pytest.raises(ValueError):
        function(BASE | {"Sun": bad}, 5.0)
    with pytest.raises(ValueError):
        function(BASE, bad)


@pytest.mark.parametrize("function", FAMILIES)
def test_legacy_missing_unknown_and_wrong_policy_are_not_silent(function):
    with pytest.raises(ValueError):
        function({p: v for p, v in BASE.items() if p != "Mars"}, 5.0)
    with pytest.raises(ValueError):
        function(BASE | {"Pluto": 3}, 5.0)
    with pytest.raises(ValueError):
        function(BASE, 5.0, policy={})


@pytest.mark.parametrize(
    "bad", [True, "1", None, float("nan"), float("inf"), -1, 360, 1e300]
)
def test_extension_canonical_angles_reject_hostile_values(bad):
    with pytest.raises(ValueError):
        evaluate_yoga_extensions(BASE | {"Sun": bad}, 5.0, profile_ids=(PROFILE,))
    with pytest.raises(ValueError):
        evaluate_yoga_extensions(BASE, bad, profile_ids=(PROFILE,))


@pytest.mark.parametrize(
    "ids", [(), [], None, PROFILE, ("unknown",), (PROFILE, PROFILE), [True], {PROFILE}]
)
def test_extension_profile_selection_is_explicit_and_bounded(ids):
    with pytest.raises(ValueError):
        YogaExtensionPolicy(ids)
    with pytest.raises(ValueError):
        evaluate_yoga_extensions(BASE, 5.0, profile_ids=ids)


@pytest.mark.parametrize("value", ["false", 0, 1, None, {}, []])
def test_legacy_policy_boolean_is_not_truthiness(value):
    with pytest.raises(ValueError):
        yogas.YogaPolicy(budhaditya_combustion_cancel=value)


@pytest.mark.parametrize(
    "speeds", [{"Mars": True}, {"Mars": "0"}, {"Mars": float("nan")}, {"Pluto": 1}, []]
)
def test_optional_motion_requires_known_bodies_and_finite_numbers(speeds):
    with pytest.raises(ValueError):
        yogas.evaluate_yogas(BASE, 5.0, planet_speeds=speeds)


def test_legacy_modulo_compatibility_and_classifier_admission():
    assert yogas.evaluate_yogas(BASE, 5.0) == yogas.evaluate_yogas(
        {p: v + 360 for p, v in BASE.items()}, 365.0
    )
    with pytest.raises(ValueError):
        yogas.benefic_malefic_classification({})
    with pytest.raises(ValueError):
        yogas.benefic_malefic_classification(BASE | {"Sun": True})


def test_unknown_motion_is_not_observed_direct_motion():
    # Mercury Pisces; Jupiter Taurus; Aries Lagna/Moon. Neither lord is
    # angular from Lagna/Moon, mutually angular, or aspects Mercury.
    lons = BASE | {"Mercury": 333.0, "Moon": 5.0, "Jupiter": 35.0}

    def get(speeds=None):
        return next(
            y
            for y in yogas.raja_yogas(lons, 5.0, planet_speeds=speeds)
            if y.name == "Neecha Bhanga (Mercury)"
        )

    missing = get()
    assert not missing.formed and missing.formation_state == "indeterminate"
    assert (
        missing.conditions[-1].evaluation_state == "not_evaluated"
        and not missing.conditions[-1].satisfied
    )
    assert get({"Mercury": 0.1}).formation_state == "not_formed"
    assert get({"Mercury": -0.1}).formation_state == "formed"
    with pytest.raises(ValueError):
        replace(missing, formation_state="formed")
    with pytest.raises(ValueError):
        replace(missing.conditions[-1], satisfied=True)
