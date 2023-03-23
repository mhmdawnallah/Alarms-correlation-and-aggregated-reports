import requests
import json
import time

API_URL = 'https://api.grip.inetintel.cc.gatech.edu/json/events'

# Set up the API parameters
params = {
    'length': 10,
    'start': 0,
    'ts_start': '2022-01-09T19:01',
    'ts_end': '2023-03-08T19:01',
    'min_susp': 0,
    'max_susp': 100,
    'event_type': 'all'
}

response = requests.get(API_URL, params=params,headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=10)

data = json.loads(response.text)
total_records = int(data['recordsTotal'])

all_records = []
for i in range(0, total_records, 10):
    params['start'] = i
    try:
        response = requests.get(API_URL, params=params, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=10)
        data = json.loads(response.text)
        print(json.dumps(data, indent=4))
        all_records.extend(data['data'])
        time.sleep(1)
    except requests.exceptions.ReadTimeout:
        break
    
with open('alarms_data/bgp_alarms.json', 'w') as f:
    json.dump(all_records, f)
