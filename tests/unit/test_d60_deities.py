from moira.varga import shashtiamsha

def test_d60_deities_odd_sign():
    # Aries is odd (0). First 0.5 degrees -> Ghora (idx 0)
    vp1 = shashtiamsha(0.2)
    assert vp1.deity == "Ghora"
    
    # Aries 29.8 degrees -> 59th segment -> CandraRekha (idx 59)
    vp2 = shashtiamsha(29.8)
    assert vp2.deity == "CandraRekha"

def test_d60_deities_even_sign():
    # Taurus is even (1). First 0.5 degrees -> CandraRekha (idx 59)
    vp1 = shashtiamsha(30.2)
    assert vp1.deity == "CandraRekha"
    
    # Taurus 29.8 degrees -> 59th segment -> Ghora (idx 0)
    vp2 = shashtiamsha(59.8)
    assert vp2.deity == "Ghora"
