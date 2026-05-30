
import urllib.parse, urllib.request
params = {'format':'text','COMMAND':'1862;','OBJ_DATA':'NO','MAKE_EPHEM':'YES',
          'EPHEM_TYPE':'VECTORS','CENTER':'500@10','START_TIME':'JD2451541.5',
          'STOP_TIME':'JD2451542.5','STEP_SIZE':'1d','OUT_UNITS':'KM-S',
          'CSV_FORMAT':'YES','REF_PLANE':'FRAME'}
resp = urllib.request.urlopen(
    f'https://ssd.jpl.nasa.gov/api/horizons.api?{urllib.parse.urlencode(params)}'
).read().decode('utf-8')
soe_idx = resp.find('$$SOE')
line = resp[soe_idx:].split('\n')[1]
print('RAW LINE:', repr(line[:300]))
parts = line.split(',')
for i, p in enumerate(parts):
    print(f'  [{i}] = {p!r}')
