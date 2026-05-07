import math
from moira.moira_native import bisect, newton_safe, almost_equal

# --- Verification of the Forge's New Strength ---

def test_root_finding():
    """Verify that the native solvers can find the root of a known function."""
    # f(x) = sin(x), root at PI
    f = lambda x: math.sin(x)
    df = lambda x: math.cos(x)
    
    # Bisect
    res_b = bisect(f, 3.0, 4.0)
    assert almost_equal(res_b, math.pi), f"Bisect failed: {res_b}"
    
    # Safe Newton
    res_n = newton_safe(f, df, 3.0, 4.0)
    assert almost_equal(res_n, math.pi), f"Newton failed: {res_n}"

if __name__ == "__main__":
    try:
        test_root_finding()
        print("The Forge is strong. Its numerical intelligence is verified.")
    except Exception as e:
        print(f"The Forge encountered a resistance: {e}")
