import pytest
from moira.degree_symbols import get_degree_index, get_sabian_symbol

def test_get_degree_index():
    assert get_degree_index(0.0) == 1
    assert get_degree_index(0.5) == 1
    assert get_degree_index(0.999) == 1
    assert get_degree_index(1.0) == 2
    assert get_degree_index(15.3) == 16
    assert get_degree_index(29.0) == 30
    assert get_degree_index(29.999) == 30
    
    with pytest.raises(ValueError):
        get_degree_index(-0.1)
        
    with pytest.raises(ValueError):
        get_degree_index(30.0)

def test_get_sabian_symbol():
    # Test boundary 1
    assert get_sabian_symbol("Aries", 0.0) == "A woman has risen out of the ocean, a seal is embracing her"
    # Test typical
    assert get_sabian_symbol("Aries", 0.5) == "A woman has risen out of the ocean, a seal is embracing her"
    # Test boundary 2
    assert get_sabian_symbol("Pisces", 29.99) == "A majestic rock formation resembling a face is idealized by a boy who takes it as his ideal of greatness, and as he grows up, begins to look like it"
    # Test invalid sign
    assert get_sabian_symbol("Ophiuchus", 15.0) is None
