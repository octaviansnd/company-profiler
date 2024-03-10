import time
import json
import csv
import sys
from scripts import scraper
from algoliasearch.search_client import SearchClient


# Algolia client
client = SearchClient.create('WWY1GU3B3V', '9ea74cee828913d317fd5753e5c22111')
algolia = client.init_index('dev_companyprofile')

input_file_path = 'input/sample-websites.csv'
csv_file_path = 'input/sample-websites-company-names.csv'

found_profiles = {}

links = []
responses = []

index = 0
address_fillrate = 0
phone_fillrate = 0
social_fillrate = 0
fillrate = 0

scraping = False


def start():
    global index, scraping, links, responses

    index = 0
    scraping = True

    with open(input_file_path, mode='r', newline='', encoding="utf-8") as file:
        domains = csv.DictReader(file)
        links = ["http://" + row['domain'] for row in domains]

    responses = scraper.get_responses(links)


def update():
    if not scraping:
        return

    global index
    if index == len(responses):
        return finish()

    page_to_scrape = responses[index]
    index += 1

    try:
        if page_to_scrape.url.host in found_profiles:
            return
    except:
        return

    result = scraper.scrape_page(page_to_scrape)
    if not result.failed:
        found_profiles[result.url.host] = result.profile


def finish():
    global scraping
    scraping = False

    json_results = []

    with open(csv_file_path, mode='r', newline='', encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        fieldnames.extend(['addresses', 'phone_numbers', 'social_links'])

        rows = list(reader)
        for row in rows:
            domain = row['domain']

            result = None
            if domain in found_profiles:
                result = found_profiles[domain]
            elif "".join(["www.", domain]) in found_profiles:
                result = found_profiles["".join(["www.", domain])]

            if result:
                global address_fillrate, phone_fillrate, social_fillrate, fillrate
                fillrate += 1
                if result.addresses: address_fillrate += 1
                if result.phone_numbers: phone_fillrate += 1
                if result.social_links: social_fillrate += 1

                addresses = ', '.join(result.addresses)
                row['addresses'] = addresses

                phone_numbers = ', '.join(result.phone_numbers)
                row['phone_numbers'] = phone_numbers
                
                social_links = ', '.join(result.social_links)
                row['social_links'] = social_links

            else:
                row['addresses'] = ''
                row['phone_numbers'] = ''
                row['social_links'] = ''
            
            obj = {
                f"{field}": row[field] for field in fieldnames
            }
            json_results.append(obj)

    algolia.save_objects(json_results, {'autoGenerateObjectIDIfNotExist': True})
    with open('results.json', mode='w', newline='', encoding="utf-8") as file:
        json.dump(json_results, file)

    return 1



def main():
    start_time = time.time()
    start()

    running = True
    while running:
        resp = update()

        if resp == 1:
            print(f"\nSuccessfully crawled {fillrate}/{index} websites ({int(fillrate * 100 / index)}%) in a total time of {int(time.time() - start_time)} seconds.\n")
            print(f"Fill rates\n--------------------")
            print(f"Addresses:\t{int(address_fillrate * 100 / fillrate)}%")
            print(f"Phone numbers:\t{int(phone_fillrate * 100 / fillrate)}%")
            print(f"Social links:\t{int(social_fillrate * 100 / fillrate)}%")
            running = False


if __name__ == '__main__':
    main()
