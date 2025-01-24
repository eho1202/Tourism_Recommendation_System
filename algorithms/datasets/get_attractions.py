import os
import requests
from time import sleep
import pandas as pd
import googlemaps
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv('attractions.csv')
api_key = os.getenv('GOOGLE_PLACES_API')

df['Category'] = df['Category'].astype(str)
df['Link'] = df['Link'].astype(str)

# Based on the Name column (B), get Rating, Cost, Category (types), and Link
for i, row in df.iterrows():
    place_name = row['Name']
    
    try:
        place_search_url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        place_search_params = {
            'input': place_name,
            'inputtype': 'textquery',
            'key': api_key,
        }
        place_id = requests.get(place_search_url, params=place_search_params).json()['candidates'][0]['place_id']

        place_detail_url = 'https://maps.googleapis.com/maps/api/place/details/json'
        place_detail_params = {
            'placeid': place_id,
            'key': api_key,
            'fields': 'name,rating,type,price_level,url'
        }
        response = requests.get(place_detail_url, params=place_detail_params).json()
    
        if 'result' in response:
            result = response['result']
            df.at[i, 'Rating'] = result.get('rating')
            df.at[i, 'Category'] = [', '.join(result.get('types', [])).replace('_', ' ')]
            df.at[i, 'Cost'] = result.get('price_level')
            df.at[i, 'Link'] = result.get('url')
        else:
            print(f'Error finding {place_name}')
        
    except Exception as err:
        print(err)
        
    sleep(1)
    
df.to_csv('attractions.csv', index=False)

print("Done")
