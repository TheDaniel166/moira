import csv
import json
from pathlib import Path

# Paths
clean_csv_path = Path("moira/data/modern-iau-star-names-clean.csv")
lore_path = Path("moira/data/star_lore.json")
registry_path = Path("moira/data/star_registry.csv")
provenance_path = Path("moira/data/star_provenance.json")

# Define the corrupted-to-clean mapping we found
# This ensures deterministic mapping even if there is any spacing/etc differences
name_mapping = {
    "Bats??": "Batsũ̀",
    "Bibh?": "Bibhā",
    "Chaso?": "Chasoň",
    "S?maya": "Sāmaya"
}

# Also parse all clean rows to build lore updates for all IAU stars
iau_data = {}
with open(clean_csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['proper names'].strip()
        culture = row['Ethnic-Cultural_Group_or_Language'].strip()
        origin = row['Origin'].strip()
        iau_data[name] = {
            "culture": culture,
            "origin": origin
        }

# 1. Update star_lore.json
with open(lore_path, 'r', encoding='utf-8') as f:
    lore = json.load(f)

new_lore = {}
for key, val in lore.items():
    # Determine new key name
    new_key = name_mapping.get(key, key)
    
    # Update nested culture_map values if they were corrupted
    culture_map = val.get("culture_map", {})
    new_culture_map = {}
    for cult_name, star_name in culture_map.items():
        # Correct the star name inside culture_map
        new_star_name = name_mapping.get(star_name, star_name)
        new_cult_name = cult_name
        # Correct any question marks inside culture name if they exist
        for old, new in name_mapping.items():
            new_cult_name = new_cult_name.replace(old.lower(), new.lower())
        new_culture_map[new_cult_name] = new_star_name
    
    val["culture_map"] = new_culture_map
    
    # If it is an IAU star, update the mythology and culture map from the clean CSV data
    if new_key in iau_data:
        val["mythology"] = iau_data[new_key]["origin"]
        culture_str = iau_data[new_key]["culture"]
        val["culture_map"] = {culture_str.lower(): new_key} if culture_str else {}
        
    new_lore[new_key] = val

with open(lore_path, 'w', encoding='utf-8') as f:
    json.dump(new_lore, f, indent=2, ensure_ascii=False)
print("Updated star_lore.json successfully.")

# 2. Update star_registry.csv
registry_rows = []
with open(registry_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        name = row['name'].strip()
        if name in name_mapping:
            safe_old = name.encode('ascii', 'backslashreplace').decode('ascii')
            safe_new = name_mapping[name].encode('ascii', 'backslashreplace').decode('ascii')
            print(f"Updating registry name: {safe_old} -> {safe_new}")
            row['name'] = name_mapping[name]
        registry_rows.append(row)

with open(registry_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(registry_rows)
print("Updated star_registry.csv successfully.")

# 3. Update star_provenance.json
with open(provenance_path, 'r', encoding='utf-8') as f:
    provenance = json.load(f)

new_provenance = {}
for key, val in provenance.items():
    new_key = name_mapping.get(key, key)
    new_provenance[new_key] = val

with open(provenance_path, 'w', encoding='utf-8') as f:
    json.dump(new_provenance, f, indent=2, ensure_ascii=False)
print("Updated star_provenance.json successfully.")
