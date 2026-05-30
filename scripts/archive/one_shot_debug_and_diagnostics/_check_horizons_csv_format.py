#!/usr/bin/env python
"""
Check the actual Horizons CSV column layout for Apollo.
"""
import urllib.parse
import urllib.request

params = {
    "format":     "text",
    "COMMAND":    "'1862;'",  # Apollo
    "OBJ_DATA":   "NO",
    "MAKE_EPHEM": "YES",
    "EPHEM_TYPE": "VECTORS",
    "CENTER":     "'500@10'",  # Heliocentric
    "START_TIME": "JD2451545.0",
    "STOP_TIME":  "JD2451547.0",
    "STEP_SIZE":  "'2d'",
    "OUT_UNITS":  "KM-S",
    "CSV_FORMAT": "YES",
    "REF_PLANE":  "FRAME",
}

url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
print(f"Fetching: {url}\n")

with urllib.request.urlopen(url, timeout=30) as r:
    text = r.read().decode()

# Find the data section
soe_idx = text.find("$$SOE")
eoe_idx = text.find("$$EOE")

if soe_idx == -1 or eoe_idx == -1:
    print("ERROR: Could not find $$SOE/$$EOE markers")
    print("\n=== Full Response ===")
    print(text)
    exit(1)

# Extract everything from $$SOE to $$EOE
data_section = text[soe_idx:eoe_idx]

print("=== Data Section ($$SOE to $$EOE) ===")
print(data_section)
print("\n=== Parsing First Data Line ===")

lines = data_section.split('\n')
for line in lines[1:]:  # Skip $$SOE line itself
    line = line.strip()
    if not line or line.startswith('$$'):
        continue
    
    parts = line.split(',')
    print(f"Total columns: {len(parts)}")
    for i, part in enumerate(parts[:10]):  # Show first 10 columns
        print(f"  Column {i}: '{part.strip()}'")
    break
