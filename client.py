import csv
import requests

csv_file = 'input/API-input-sample.csv'

flask_server_url = 'http://localhost:5000/'

with open(csv_file, mode='r', newline='', encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        name = row.get('input name', '')
        website = row.get('input website', '')
        phone_number = row.get('input phone', '')
        facebook_profile = row.get('input_facebook', '')

        response = requests.get(flask_server_url, params={
            'name': name,
            'website': website,
            'phone_number': phone_number,
            'facebook_profile': facebook_profile
        })

        if response.status_code == 200:
            company_profile = response.json()
      
            print(f"Company:\t\t{company_profile['company_commercial_name']}")
            print(f"Available Names:\t{company_profile['company_all_available_names']}")
            print(f"Addresses:\t\t{company_profile['addresses']}")
            print(f"Website:\t\t{company_profile['domain']}")
            print(f"Phone Numbers:\t\t{company_profile['phone_numbers']}")
            print(f"Social Profiles:\t{company_profile['social_links']}")
            print("-----------------------------")
        elif response.status_code == 404:
            print(f"Company profile not found for {name}")
            print("-----------------------------")
        else:
            print(f"Error: {response.json()['message']}")
            print("-----------------------------")

