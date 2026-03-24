import sys, traceback
sys.path.insert(0, r"c:\Users\nilad\OneDrive\Desktop\Moira")
try:
    from moira.eclipse import EclipseCalculator
    print("import ok")
    calc = EclipseCalculator()
    print("calc ok")
    data = calc.calculate_jd(2451564.696875)
    print(f"calculate ok: is_lunar={data.is_lunar_eclipse}")
except Exception:
    traceback.print_exc()
