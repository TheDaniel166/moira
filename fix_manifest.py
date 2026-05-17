import json
f = 'moira/kernels/sb441_type13/manifest.json'
d = json.load(open(f, encoding='utf-8'))
for s in d.get('shards', []):
    path = s['path']
    # Normalize slashes to make replacing easier
    path = path.replace('\\', '/')
    if path.startswith('kernels/sb441_type13/'):
        path = path.replace('kernels/sb441_type13/', '')
    s['path'] = path

json.dump(d, open(f, 'w', encoding='utf-8'), indent=2)
print("Manifest paths fixed!")
