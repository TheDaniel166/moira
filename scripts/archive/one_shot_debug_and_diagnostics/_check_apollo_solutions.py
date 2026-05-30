#!/usr/bin/env python
"""
Check if Apollo (1862) has multiple ephemeris solutions in Horizons.
"""
import urllib.parse
import urllib.request

# Query Horizons for Apollo's available solutions
params = {
    "format": "text",
    "COMMAND": "'1862;'",
    "OBJ_DATA": "YES",
    "MAKE_EPHEM": "NO",
}

url = f"https://ssd.jpl.nasa.gov/api/horizons.api?{urllib.parse.urlencode(params)}"
print(f"Querying Horizons for Apollo (1862) object data...\n")

with urllib.request.urlopen(url, timeout=30) as r:
    text = r.read().decode()

# Look for solution/ephemeris information
print("=== Searching for Solution/Ephemeris Info ===\n")

lines = text.split('\n')
in_relevant_section = False

for i, line in enumerate(lines):
    # Look for keywords related to solutions, ephemeris, or data arcs
    keywords = ['solution', 'ephemeris', 'data arc', 'JPL#', 'orbit', 'fit', 'arc']
    
    if any(kw.lower() in line.lower() for kw in keywords):
        # Print context around the match
        start = max(0, i - 2)
        end = min(len(lines), i + 3)
        for j in range(start, end):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {lines[j]}")
        print()

print("\n=== Full Response (first 3000 chars) ===")
print(text[:3000])
