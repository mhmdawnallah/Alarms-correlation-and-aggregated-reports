import pandas as pd
import plotly.express as px
import maxminddb
import json

country_db = maxminddb.open_database('data/geo_data/GeoLite2-Country.mmdb')
city_db = maxminddb.open_database('data/geo_data/GeoLite2-City.mmdb')
asn_df = pd.read_csv('data/geo_data/GeoLite2-ASN-Blocks-IPv4.csv')
country_name_codes_df = pd.read_csv('data/geo_data/country_codes.csv')
world_cities_df = pd.read_csv('data/geo_data/world_cities.csv')

with open("data/alarms_data/hegemony_alarms.json", "r") as f:
    hegemony_alarms_data = json.load(f)
hegemony_alarms_df = pd.DataFrame(hegemony_alarms_data['results'])

with open("data/alarms_data/network_delay_alarms.json", "r") as f:
    network_delay_alarms_data = json.load(f)
network_delay_alarms_df = pd.DataFrame(network_delay_alarms_data['results'])

with open("data/alarms_data/bgp_alarms.json", "r") as fh:
    bgp_alerts_data = json.load(fh)

asn_to_network_lookup = dict(zip(asn_df['autonomous_system_number'], asn_df['network'].str.split('/', expand=True).iloc[:, 0].tolist()))
world_cities_lookup = dict(zip(world_cities_df['city'].str.title() + ', ' + world_cities_df['country_code'].str.upper(), world_cities_df[['latitude', 'longitude']].values.tolist()))

def get_country_city_from_asn(asn):
    country_name, country_code, city_name = "Unknown", "Unknown", "Unknown"
    ip = asn_to_network_lookup.get(int(asn), None)
    if not ip:
        return country_name, country_code, city_name
    
    country_db_response = country_db.get(ip_address=ip)
    city_db_response = city_db.get(ip_address=ip)
    
    if country_db_response:
        if 'country' in country_db_response:
            country_name = country_db_response['country']['names']['en']
            try:
                country_code = country_name_codes_df[country_name_codes_df['country'] == country_name]['country_code'].values[0]
            except IndexError:
                print(f"Country code not found for {country_name}")
                raise IndexError
                    
    if city_db_response:
        city_name = city_db_response['city']['names']['en'] if 'city' in city_db_response else "Unknown"
    
    return country_name, country_code, city_name

def lookup_latitude_longitude(row):
    lookup_key = row['city'] + ', ' + row['country_code']
    if lookup_key in world_cities_lookup:
        return pd.Series({'latitude': world_cities_lookup[lookup_key][0], 'longitude': world_cities_lookup[lookup_key][1]})
    else:
        return pd.Series({'latitude': None, 'longitude': None})

bgp_alarms = []
for entry in bgp_alerts_data:
    event_type = entry['event_type']
    summary = entry['summary']
    
    for victim in summary['victims']:
        country_name, country_code, city_name = get_country_city_from_asn(victim)
        
        new_entry = {
            'event_type': event_type,
            'country': country_name,
            'country_code': country_code,
            'city': city_name,
            'bgp_traceroute_worthy': int(bool(summary['tr_worthy']))
        }
        bgp_alarms.append(new_entry)

bgp_alarms_df = pd.DataFrame(bgp_alarms)

bgp_alarms_pivot_df = pd.pivot_table(bgp_alarms_df, 
                          index=['country', 'country_code', 'city'], 
                          columns='event_type',
                          values='bgp_traceroute_worthy',
                          aggfunc='count',
                          fill_value=0)

bgp_alarms_pivot_df['bgp_traceroute_worthy'] = bgp_alarms_df.groupby(['country', 'country_code', 'city'])['bgp_traceroute_worthy'].sum().values
bgp_alarms_pivot_df = bgp_alarms_pivot_df.reset_index()
bgp_alarms_pivot_df.columns = ['country', 'country_code', 'city'] + [f"{col}_alarm_counts" for col in bgp_alarms_pivot_df.columns[3:]]

hegemony_alarms_df[['country', 'country_code', 'city']] = hegemony_alarms_df['asn'].apply(lambda x: pd.Series(get_country_city_from_asn(x)))
network_delay_alarms_df[['country', 'country_code', 'city']] = network_delay_alarms_df['startpoint_name'].apply(lambda x: pd.Series(get_country_city_from_asn(x)))

hegemony_counts = hegemony_alarms_df.groupby(['country','country_code','city']).size().reset_index(name='hegemony_alarm_counts')
delay_counts = network_delay_alarms_df.groupby(['country','country_code','city']).size().reset_index(name='delay_alarm_counts')

counts = pd.merge(hegemony_counts, delay_counts, how='outer', on=['country','country_code','city'])
counts = pd.merge(counts, bgp_alarms_pivot_df, how='outer', on=['country','country_code','city'])
counts.drop(counts[counts['country'] == 'Unknown'].index, inplace=True)

counts['hegemony_alarm_counts'] = counts['hegemony_alarm_counts'].fillna(0).astype(int)
counts['delay_alarm_counts'] = counts['delay_alarm_counts'].fillna(0).astype(int)
counts['defcon_alarm_counts'] = counts['defcon_alarm_counts'].fillna(0).astype(int)
counts['moas_alarm_counts'] = counts['moas_alarm_counts'].fillna(0).astype(int)
counts['submoas_alarm_counts'] = counts['submoas_alarm_counts'].fillna(0).astype(int)
counts['edges_alarm_counts'] = counts['moas_alarm_counts'].fillna(0).astype(int)
counts['bgp_traceroute_worthy_alarm_counts'] = counts['bgp_traceroute_worthy_alarm_counts'].fillna(0).astype(int)
counts['total_alarm_counts'] = counts['hegemony_alarm_counts'] + counts['delay_alarm_counts'] + counts['defcon_alarm_counts'] + counts['moas_alarm_counts'] + counts['submoas_alarm_counts'] + counts['edges_alarm_counts']

alarm_merged_counts_df = pd.merge(counts, country_name_codes_df, how='left', on=['country','country_code'])

alarm_merged_counts_df[['latitude', 'longitude']] = alarm_merged_counts_df.apply(lookup_latitude_longitude, axis=1)

alarm_grouped_merged_counts_df = alarm_merged_counts_df.groupby(['country', 'country_code', 'country_alpha3']).sum().reset_index()

alarm_merged_counts_df.to_csv('data/aggregated_alarms_data/alarm_merged_counts.csv')
alarm_grouped_merged_counts_df.to_csv('data/aggregated_alarms_data/alarm_grouped_merged_counts.csv')

LABELS = {'total_alarm_counts': 'Total Alarm Counts', 'hegemony_alarm_counts': 'Hegemony Dependency Alarm Counts',
                            'delay_alarm_counts': 'Network Delay Alarm Counts', 'moas_alarm_counts': 'BGP MOAS Alarm Counts', 
                            'defcon_alarm_counts': 'BGP Defcon Alarm Counts', 'submoas_alarm_counts': 'BGP Sub-MOAS Alarm Counts',
                            'edges_alarm_counts': 'BGP Edges Alarm Counts', 'bgp_traceroute_worthy_alarm_counts': 'BGP Warthy Traceroute Alarm Counts'}
HOVER_DATA = ['total_alarm_counts', 'hegemony_alarm_counts', 'delay_alarm_counts', 'moas_alarm_counts',
              'defcon_alarm_counts', 'submoas_alarm_counts', 'edges_alarm_counts', 'bgp_traceroute_worthy_alarm_counts']

fig = px.choropleth(alarm_grouped_merged_counts_df, locations='country_alpha3', color='total_alarm_counts',
                    hover_name='country', title='Aggregated IHR alarms counts by Country and City', color_continuous_scale='Viridis',
                    hover_data=HOVER_DATA,labels=dict(LABELS,country_alpha3='Country Code'))

fig.add_trace(px.scatter_geo(alarm_merged_counts_df, lat='latitude', lon='longitude', hover_name='city', size='total_alarm_counts',
                             hover_data=HOVER_DATA,labels=LABELS).data[0])

fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
)

fig.update_layout(coloraxis_colorbar=dict(title='Alarm Counts'))

fig.show()