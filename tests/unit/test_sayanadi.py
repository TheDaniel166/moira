import pytest
from moira.avasthas import sayanadi_avastha

def test_sayanadi_avastha_bphs_example():
    # BPHS 45.30-33 Example given by Santhanam (and corrected arithmetic):
    # Sun in Krittika (3rd star from Ashwini, though technically Sun is 3).
    # Wait, the example: "The Sun in Krittika Nakshatra, 3rd Navamsa of Taurus, 
    # birth star Krittika, birth at 30gh 31vigh (31), ascendant in Scorpio."
    
    # Sidereal longitudes map:
    # Sun in Krittika 3rd Navamsa of Taurus = 26 deg 40 min to 30 deg. Let's use 38.0.
    # Moon in Krittika = Let's use 38.0.
    # Ascendant in Scorpio (8th sign). Let's use 225.0.
    
    sidereal_longitudes = {
        'Sun': 38.0,
        'Moon': 38.0,
    }
    
    lagna_lon = 225.0
    birth_ghati = 31
    first_syllable = 1 # 'Sa'
    
    res = sayanadi_avastha('Sun', sidereal_longitudes, lagna_lon, birth_ghati, first_syllable)
    
    assert res.planet == 'Sun'
    assert res.avastha_index == 3
    assert res.state == 'Netrapani'
    assert res.substate == 'Vicheshta'
    assert res.effect == "Always happy, wise, helpful to others, endowed with prowess and wealth, gain royal favours."
