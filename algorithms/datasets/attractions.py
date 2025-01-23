from time import sleep
import pandas as pd
import requests
import googlemaps



df = pd.read_excel('attractions.xlsx')
api_key = ''

# Ensure the columns can work with int and string type values
df['Rating'] = df['Rating'].astype(object)
df['Category'] = df['Category'].astype(object)
df['Cost'] = df['Cost'].astype(object)
df['Link'] = df['Link'].astype(object)

# Based on the Name column (B), get Rating, Cost, Category (type), and Link
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
            df.at[i, 'Rating'] = result.get('rating'),
            df.at[i, 'Category'] = result.get('type'),
            df.at[i, 'Cost'] = result.get('price_level') or None,
            df.at[i, 'Link'] = result.get('url')
        else:
            print(f'Error finding {place_name}')
        
    except Exception as err:
        print(err)
        
    sleep(1)
    
df.to_excel('attractions.xlsx', index=False)

print("Done")
