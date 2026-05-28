import csv

old_file = r"moira/data/modern-iau-star-names-clean.csv"
new_file = r"C:\Users\nilad\Downloads\IAU-Catalog of Star Names (always up to date).csv"

old_rows = []
with open(old_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_rows.append(row)

new_rows = []
with open(new_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        new_rows.append(row)

mapping = {}
for old_row in old_rows:
    old_name = old_row['proper names'].strip()
    old_wgsn = old_row['WGSN-id'].strip()
    old_desig = old_row['Designation'].strip()
    old_simbad = old_row['Simbad spelling'].strip()
    
    matched = None
    for new_row in new_rows:
        new_wgsn = new_row['WGSN-id'].strip()
        new_desig = new_row['Designation'].strip()
        new_simbad = new_row['Simbad spelling'].strip()
        
        if old_wgsn and old_wgsn == new_wgsn:
            matched = new_row
            break
        elif old_desig and old_desig == new_desig:
            matched = new_row
            break
        elif old_simbad and old_simbad == new_simbad:
            matched = new_row
            break
            
    if matched:
        new_name = matched['proper names'].strip()
        if old_name != new_name:
            safe_old = old_name.encode('ascii', 'backslashreplace').decode('ascii')
            safe_new = new_name.encode('ascii', 'backslashreplace').decode('ascii')
            print(f"Name change: {safe_old} -> {safe_new}")
            mapping[old_name] = new_name

print(f"Total mapped name changes: {len(mapping)}")
