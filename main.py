import pandas as pd
import geopandas as gpd
import pycountry

import plotly.express as px
import requests
import plotly.graph_objs as go
import maxminddb
import json

# Load the MaxMind GeoLite2 databases
country_db = maxminddb.open_database('geo_data/GeoLite2-Country.mmdb')
city_db = maxminddb.open_database('geo_data/GeoLite2-City.mmdb')
asn_df = pd.read_csv('geo_data/GeoLite2-ASN-Blocks-IPv4.csv')
country_name_codes_df = pd.read_csv('geo_data/country_codes.csv')
world_cities_df = pd.read_csv('geo_data/world_cities.csv')

asn_to_network_lookup = dict(zip(asn_df['autonomous_system_number'], asn_df['network'].str.split('/', expand=True).iloc[:, 0].tolist()))
# I wanna create world_cities_lookup the key is the city name in addition to the country code seperated by a comma and the value is the value is the latitude and longitude
world_cities_lookup = dict(zip(world_cities_df['city'].str.title() + ', ' + world_cities_df['country_code'].str.upper(), world_cities_df[['latitude', 'longitude']].values.tolist()))

def get_country_city_from_asn(asn):
    ip = asn_to_network_lookup.get(int(asn), None)
    if not ip:
        return "Unknown", "Unknown"
    
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
        else:
            country_name = "Unknown"
            
    if city_db_response:
        city_name = city_db_response['city']['names']['en'] if 'city' in city_db_response else "Unknown"
    return country_name, country_code, city_name
 
with open("alarms_data/hegemony_alarms.json", "r") as f:
    hegemony_alarms_data = json.load(f)
hegemony_alarms_df = pd.DataFrame(hegemony_alarms_data['results'])

with open("alarms_data/network_delay_alarms.json", "r") as f:
    network_delay_alarms_data = json.load(f)
network_delay_alarms_df = pd.DataFrame(network_delay_alarms_data['results'])

hegemony_alarms_df[['country', 'country_code', 'city']] = hegemony_alarms_df['asn'].apply(lambda x: pd.Series(get_country_city_from_asn(x)))
network_delay_alarms_df[['country', 'country_code', 'city']] = network_delay_alarms_df['startpoint_name'].apply(lambda x: pd.Series(get_country_city_from_asn(x)))

# Aggregate the alarms by country and continent
hegemony_counts = hegemony_alarms_df.groupby(['country','country_code','city']).size().reset_index(name='hegemony_alarm_counts')
delay_counts = network_delay_alarms_df.groupby(['country','country_code','city']).size().reset_index(name='delay_alarm_counts')

# Merge the two counts datasets
counts = pd.merge(hegemony_counts, delay_counts, how='outer', on=['country','country_code','city'])

counts['hegemony_alarm_counts'] = counts['hegemony_alarm_counts'].fillna(0).astype(int)
counts['delay_alarm_counts'] = counts['delay_alarm_counts'].fillna(0).astype(int)
counts['total_alarm_counts'] = counts['hegemony_alarm_counts'] + counts['delay_alarm_counts']

merged_counts_df = pd.merge(counts, country_name_codes_df, how='left', on=['country','country_code'])
merged_counts_df['country_alpha3'] = merged_counts_df['country_code'].apply(lambda x: pycountry.countries.get(alpha_2=x).alpha_3)

# Define a function to look up the latitude and longitude values for a given row
def lookup_latitude_longitude(row):
    lookup_key = row['city'] + ', ' + row['country_code']
    if lookup_key in world_cities_lookup:
        return pd.Series({'latitude': world_cities_lookup[lookup_key][0], 'longitude': world_cities_lookup[lookup_key][1]})
    else:
        return pd.Series({'latitude': None, 'longitude': None})

# Use apply() to apply the lookup function to each row of the dataframe
merged_counts_df[['latitude', 'longitude']] = merged_counts_df.apply(lookup_latitude_longitude, axis=1)

        
print(merged_counts_df)
counts.drop(counts[counts['country'] == 'Unknown'].index, inplace=True)
grouped_merged_data = merged_counts_df.groupby(['country', 'country_code', 'country_alpha3']).sum().reset_index()

fig = px.choropleth(grouped_merged_data, locations='country_alpha3', color='total_alarm_counts',
                    hover_name='country', title='Aggregated IHR alarms counts by Country and City', color_continuous_scale='Viridis',
                    hover_data=['total_alarm_counts', 'hegemony_alarm_counts', 'delay_alarm_counts'],
                    labels={'country_alpha3': 'Country Code', 'total_alarm_counts': 'Total Alarm Counts', 'hegemony_alarm_counts': 'Hegemony Dependency Alarm Counts', 'delay_alarm_counts': 'Network Delay Alarm Counts'})

fig.add_trace(px.scatter_geo(merged_counts_df, lat='latitude', lon='longitude', hover_name='city', size='total_alarm_counts',
                             hover_data=['total_alarm_counts', 'hegemony_alarm_counts', 'delay_alarm_counts'],
                             labels={'total_alarm_counts': 'Total Alarm Counts', 'hegemony_alarm_counts': 'Hegemony Dependency Alarm Counts', 'delay_alarm_counts': 'Network Delay Alarm Counts'}).data[0])


fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
)

fig.update_layout(coloraxis_colorbar=dict(title='Alarm Counts'))

fig.write_html('figures/alarms_map_figure.html', auto_open=True)
