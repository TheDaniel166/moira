import moira.facade as f
dups = [n for n in set(f.__all__) if f.__all__.count(n) > 1]
print("remaining duplicates:", sorted(dups))
print("total __all__ entries:", len(f.__all__))
