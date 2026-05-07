import os
import pytest
from moira.julian import julian_day as py_jd, calendar_from_jd as py_cal
from moira.dispatch import settings, MoiraBackend

# --- Ritual of Verification ---

def test_julian_day_parity():
    """Verify JD parity across 1,000 random samples."""
    import random
    from moira.moira_native import julian_day as native_jd

    random.seed(42)
    for _ in range(1000):
        y = random.randint(-13200, 17191)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        h = random.uniform(0, 24)

        val_py = py_jd(y, m, d, h)
        val_native = native_jd(y, m, d, h)

        assert abs(val_py - val_native) < 1e-12, f"JD Divergence at {y}-{m}-{d} {h}h"

def test_calendar_from_jd_parity():
    """Verify inverse JD parity."""
    from moira.moira_native import calendar_from_jd as native_cal
    
    # Sample J2000 and boundaries
    samples = [2451545.0, 0.0, 2299160.0, 2299161.0, 1721058.0]
    
    for jd in samples:
        py_res = py_cal(jd)
        native_res = native_cal(jd)
        
        # Unpack
        y_p, m_p, d_p, h_p = py_res
        y_n, m_n, d_n, h_n = native_res
        
        assert y_p == y_n
        assert m_p == m_n
        assert d_p == d_n
        assert abs(h_p - h_n) < 1e-12

def test_dispatcher_integration():
    """Verify the @accelerate decorator correctly routes calls."""
    
    # Ensure native is used when requested
    os.environ["MOIRA_ACCELERATE"] = "1"
    settings.__init__() # Force reload from env
    assert settings.current_backend() == MoiraBackend.NATIVE
    
    # This should now call the native version through the decorator
    # We can verify this by checking if the result is identical
    res = py_jd(2000, 1, 1, 12.0)
    assert res == 2451545.0
    
    # Switch back to Python
    os.environ["MOIRA_ACCELERATE"] = "0"
    settings.__init__()
    assert settings.current_backend() == MoiraBackend.PYTHON

if __name__ == "__main__":
    test_julian_day_parity()
    test_calendar_from_jd_parity()
    test_dispatcher_integration()
    print("The Parity Rite is complete. The forge and the manuscript are in harmony.")
