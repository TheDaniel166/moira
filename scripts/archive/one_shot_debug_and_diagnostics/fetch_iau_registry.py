import urllib.request
import re

URL = "https://www.pas.rochester.edu/~emamajek/WGSN/IAU-CSN.txt"

def fetch_iau_data():
    print(f"Fetching {URL}...")
    with urllib.request.urlopen(URL) as response:
        content = response.read().decode('utf-8')
    
    lines = content.splitlines()
    registry = []
    
    # Example line: 
    # Acamar            Acamar            HR 897       tet01 θ1    Eri A    02583-4018  2.88  V  13847  18622  44.565311 -40.304672 2016-07-20 *
    # regex for name (word/space), skip, designation, skip, skip, skip, skip, skip, mag(float), skip, hip(int or _), hd(int or _), ra(float), dec(float)
    
    # We'll use a more flexible approach: just find the indices for HIP, HD, RA, Dec based on knowing they are the last 5-6 columns
    for line in lines:
        if not line.strip() or line.startswith("#") or line.startswith("Name/"):
            continue
        
        # Skip if it looks like the citation/header info
        if "https://" in line or "delay" in line or "WGSN" in line:
            continue
            
        parts = line.split()
        if len(parts) < 8:
            continue
            
        try:
            # Name starts at 0 and go to ~17
            name = line[0:17].strip()
            
            # The coordinates are always the 4th and 3rd from the end (before date)
            # Actually, let's use fixed width for the coordinates since they look very aligned in the source
            # RA(J2000) starts around column 104, Dec(J2000) around 115
            # Dates start at 127 (but let's be careful)
            # Coordinates start around column 103 in the IAU-CSN.txt
            
            ra_str = line[103:114].strip()
            dec_str = line[114:126].strip()
            hip_str = line[89:96].strip()
            hd_str = line[96:103].strip()
            mag_str = line[80:85].strip()
            
            if ra_str and dec_str and "." in ra_str:
                registry.append({
                    "name": name,
                    "v_mag": mag_str,
                    "hip": hip_str,
                    "hd": hd_str,
                    "ra": ra_str,
                    "dec": dec_str
                })
        except:
            continue
            
    return registry

if __name__ == "__main__":
    registry = fetch_iau_data()
    print(f"Parsed {len(registry)} stars.")
    # Show Aldebaran
    for star in registry:
        if star['name'] == "Aldebaran":
            print(f"Target Found: {star}")
    
    # Write to a temporary JSON for next steps
    import json
    with open("/tmp/iau_registry.json", "w") as f:
        json.dump(registry, f, indent=2)
    print("Saved to /tmp/iau_registry.json")
