import pytest

from moira.constants import sign_of
from moira.planets import PlanetData
from moira.houses import HouseCusps, assign_house, HouseSystem
from moira.aspects import aspects_between

def test_sign_boundary_preserves_strict_float_threshold() -> None:
    # 29.9999999999 is strictly Aries
    lon_aries_10 = 29.9999999999
    assert sign_of(lon_aries_10)[0] == "Aries"
    
    # 29.99999999999 is strictly Aries
    lon_aries_11 = 29.99999999999
    assert sign_of(lon_aries_11)[0] == "Aries"
    
    # 29.999999999999 is strictly Aries
    lon_aries_12 = 29.999999999999
    assert sign_of(lon_aries_12)[0] == "Aries"

    # 30.000000000000 is strictly Taurus
    lon_taurus = 30.000000000000
    assert sign_of(lon_taurus)[0] == "Taurus"

def test_planet_data_preserves_unrounded_longitude() -> None:
    lon = 29.999999999999
    pd = PlanetData(
        name="TestBody",
        longitude=lon,
        latitude=0.0,
        distance=1.0,
        speed=1.0,
        retrograde=False
    )
    
    # Structural identity is preserved
    assert pd.sign == "Aries"
    assert pd.longitude == lon

    # Even formatting does not corrupt the strict internal data
    deg, m, s = pd.longitude_dms
    assert deg == 29
    assert m == 59
    # The seconds will be extremely close to 60.0
    assert abs(s - 60.0) < 0.001

def test_house_boundary_preserves_strict_float_threshold() -> None:
    # Create fake cusps where House 1 starts at 0.0 and House 2 starts at 30.0
    cusps = tuple(float(i * 30) for i in range(12))
    from moira.houses import HouseSystemClassification, HouseSystemFamily, HouseSystemCuspBasis
    
    cls = HouseSystemClassification(
        family=HouseSystemFamily.WHOLE_SIGN,
        cusp_basis=HouseSystemCuspBasis.ECLIPTIC,
        latitude_sensitive=False,
        polar_capable=True
    )
    hc = HouseCusps(
        system=HouseSystem.WHOLE_SIGN,
        effective_system=HouseSystem.WHOLE_SIGN,
        classification=cls,
        cusps=cusps,
        asc=0.0,
        mc=270.0,
        armc=270.0
    )
    
    # Body at 29.999999999999 is in House 1
    placement = assign_house(29.999999999999, hc)
    assert placement.house == 1
    assert placement.exact_on_cusp is False
    
    # Body at exactly 30.0 is in House 2
    placement2 = assign_house(30.000000000000, hc)
    assert placement2.house == 2
    assert placement2.exact_on_cusp is True

def test_aspect_engine_does_not_coerce_floats() -> None:
    # Body 1 at 0.0
    pd1 = PlanetData("B1", 0.0, 0.0, 1.0, 1.0, False)
    
    # Body 2 at exactly 90.0
    aspects_exact = aspects_between("B1", 0.0, "B2", 90.0)
    assert aspects_exact[0].orb == 0.0
    
    # Body 2 at 89.999999999999
    aspects_fuzzy = aspects_between("B1", 0.0, "B3", 89.999999999999)
    
    # The aspect engine should recognize it's not EXACTLY 90.0
    assert aspects_fuzzy[0].orb > 0.0
