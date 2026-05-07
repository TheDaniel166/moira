from moira.moira_native import julian_day, calendar_from_jd, almost_equal

def debug_jd():
    jd_orig = 261817.99425472162
    y, m, d, h = calendar_from_jd(jd_orig)
    jd_back = julian_day(y, m, d, h)
    
    print(f"Original JD:  {jd_orig:.15f}")
    print(f"Calendar:     {y}-{m}-{d} {h:.15f}")
    print(f"Returned JD:  {jd_back:.15f}")
    print(f"Difference:    {jd_back - jd_orig:.15e}")

if __name__ == "__main__":
    debug_jd()
