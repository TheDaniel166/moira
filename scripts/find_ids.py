
import urllib.parse
import urllib.request

for q in ['Apollo', 'Pandora', 'Persephone', 'Amor', 'Icarus', 'Karma']:
    params = {'format': 'text', 'COMMAND': q}
    url = f'https://ssd.jpl.nasa.gov/api/horizons.api?{urllib.parse.urlencode(params)}'
    resp = urllib.request.urlopen(url).read().decode('utf-8')
    print(f'--- {q} ---')
    print(resp[:2000])
