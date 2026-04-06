dups = ["AspectData", "FirdarPeriod", "PlanetaryHour", "SectClassification", "SectStateKind", "SectTruth", "star_at"]
import pathlib
lines = pathlib.Path("moira/facade.py").read_text(encoding="utf-8-sig").splitlines()
for dup in dups:
    target = '    "' + dup + '"'
    hits = [i+1 for i, l in enumerate(lines) if target in l]
    print(f"{dup}: lines {hits}")
