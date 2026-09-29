from moira.antiscia import find_antiscia, antiscia_to_point, AntisciaAspect

def test_find_antiscia_motion_state():
    positions = {"Sun": 45.0, "Moon": 135.5} # 45 (15 Taurus). Antiscion is 180 - 45 = 135 (15 Leo). Moon is 135.5 (15.5 Leo).
    # Moon is at 135.5, moving forward (+13 deg/day).
    # Sun is at 45.0, moving forward (+1 deg/day).
    # Sun's antiscion is moving backward (-1 deg/day).
    # Shadow is at 135, moving at -1. Moon is at 135.5, moving at +13.
    # Shadow moves to 134, Moon to 148.5. The distance increases! Thus, it should be separating.
    speeds = {"Sun": 1.0, "Moon": 13.0}
    
    results = find_antiscia(positions, orb=2.0, speeds=speeds)
    assert len(results) == 1
    contact = results[0]
    
    assert contact.motion_state == "separating"
    assert contact.applying is False

    # Now let's make it applying. Moon at 134.5 (behind shadow at 135).
    # Shadow moves to 134, Moon moves to 147.5. They will cross! Wait, no.
    # If Moon is at 134.5 moving at +13. Shadow at 135 moving at -1.
    # Relative motion is closing the gap. It is applying!
    positions = {"Sun": 45.0, "Moon": 134.5}
    results = find_antiscia(positions, orb=2.0, speeds=speeds)
    assert len(results) == 1
    contact = results[0]
    assert contact.motion_state == "applying"
    assert contact.applying is True

def test_antiscia_to_point_motion_state():
    positions = {"Sun": 45.0} # Antiscion 135
    speeds = {"Sun": 1.0}
    # Point at 134.5, moving at +1. Shadow at 135 moving at -1. Applying.
    results = antiscia_to_point(134.5, positions, point_name="Asc", orb=2.0, point_speed=1.0, speeds=speeds)
    assert len(results) == 1
    assert results[0].motion_state == "applying"
    assert results[0].applying is True

