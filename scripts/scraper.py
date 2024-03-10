import re
import geopy
import httpx
import asyncio
from bs4 import BeautifulSoup

# Regex pattern for Zipcodes
zipcode_regex_pattern = re.compile(r"(^|\s)[a-zA-Z]{2} \d{4,6}(?:\s|$)")

# Regex pattern for Streets
street_regex_pattern = re.compile(r"(?i)(^|\s)\d{2,7}\b\s+.{5,30}\b\s+(?:road|rd|way|street|st|str|avenue|ave|boulevard|blvd|lane|ln|drive|dr|terrace|ter|place|pl|court|ct)(?:\.|\s|$)")

# Regex pattern for PO
pobox_regex_pattern = re.compile(r"(?i)(?:po|p.o.)\s+(?:box)")

# Regex pattern for numbers
number_regex_pattern = re.compile(r"\d+")

# Regex pattern for phone numbers
phone_number_pattern = re.compile(r'((?:\+\d{2}[-\.\s]??|\d{4}[-\.\s]??)?(?:\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4}))')

# Geolocator
geolocator = geopy.Nominatim(user_agent="company-profiler")

timeout = 100


class CompanyProfile:
    def __init__(self):
        self.social_links = []
        self.phone_numbers = []
        self.addresses = []


class ScrapeResult:
    def __init__(self, _failed, _url, _profile=CompanyProfile()):
        self.failed = _failed
        self.url = _url
        self.profile = _profile


async def get_pages(links, timeout):
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=3000)
    async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, limits=limits, timeout=timeout) as client:
        reqs = [client.get(link, timeout=20) for link in links]
        results = await asyncio.gather(*reqs, return_exceptions=True)

    return results


def get_responses(links):
    responses = []

    i = 0
    step = 16
    while True:
        i += step
        temp = asyncio.run(get_pages(links[max(0, i - step) : min(i, len(links))], timeout))
        responses.extend(temp)
        if i >= len(links):
            break

    return responses


def scrape_page(page, temp_profile=None):
    try:
        if page.status_code != 200:
            print(f"Status code {page.status_code} - {page.request.url}")
            return ScrapeResult(_failed=True, _url=page.request.url)
    except:
        print(f"Error - {page.request.url}")
        return ScrapeResult(_failed=True, _url=page.request.url)
    
    profile = None
    if temp_profile is None:
        profile = CompanyProfile()
    else:
        profile = temp_profile

    url = page.url

    try:
        soup = BeautifulSoup(page.text, "html.parser")
    except:
        print(f"Parsing error - {url}")
        return ScrapeResult(_failed=True, _url=page.request.url)

    # Search for social links
    social_links = []
    try:
        aux_links = [link['href'] for link in soup.find_all("a", href=True)]
        aux_links = [link for link in aux_links if link is not None and len(link) <= 100 and ("facebook" in link or "twitter" in link or "instagram" in link or "linkedin" in link)]
        social_links.extend([link for link in aux_links[:10] if (profile is None) or (profile is not None and link not in profile.social_links)])
    except:
        pass
    profile.social_links.extend(social_links)

    # Search for phone numbers
    phone_numbers = []
    try:
        aux_phones = ["".join(match_phone) for match_phone in re.findall(phone_number_pattern, soup.get_text())]
        phone_numbers.extend([phone for phone in aux_phones[:10] if (profile is None) or (profile is not None and phone not in profile.phone_numbers and len(phone) <= 20)])
    except:
        pass
    profile.phone_numbers.extend(phone_numbers)

    # Search for a street
    street, addr_by_street = None, None
    try:
        street = [val for val in soup.find_all(string=street_regex_pattern) if len(val) <= 100]
        if street:
            street = re.search(street_regex_pattern, street[0].text).group(0)
            street = re.sub(pobox_regex_pattern, '', street)
    except:
        pass
    if street:
        addr_by_street = geolocate_address(street)
        if addr_by_street: addr_by_street = str(addr_by_street)
        if addr_by_street and addr_by_street not in profile.addresses: profile.addresses.append(addr_by_street)

    # Search for a zipcode
    zipcode, addr_by_zipcode = None, None
    try:
        zipcode = [val for val in soup.find_all(string=zipcode_regex_pattern) if len(val) <= 100]
        if zipcode:
            zipcode = re.search(zipcode_regex_pattern, zipcode[0].text).string.strip()
            zipcode = re.sub(pobox_regex_pattern, '', zipcode)
    except:
        pass
    if zipcode:
        addr_by_zipcode = geolocate_address(zipcode)
        if addr_by_zipcode: addr_by_zipcode = str(addr_by_zipcode)
        if addr_by_zipcode and addr_by_zipcode not in profile.addresses: profile.addresses.append(addr_by_zipcode)
    
    # Recursive scraping for other links
    if not temp_profile:
        aux_links = None
        try:
            aux_links = [get_href(url, link['href']) for link in soup.find_all("a", href=True)]
            aux_links = [link for link in aux_links if link is not None]
        except:
            aux_links = []
    
        aux_responses = get_responses(aux_links[:min(len(aux_links), 10)])
        for aux_page in aux_responses:
            scrape_page(aux_page, profile)

    return ScrapeResult(_failed=False, _url=url, _profile=profile)


def get_href(url, href):
    if href[0] == '/':
        return url.join(href)
    elif re.search(f"{url}.{{2,}}", href):
        return href


def geolocate_address(query):
    global geolocator

    try:
        address = geolocator.geocode(query, addressdetails=True, timeout=2)
        return address
    except:
        return None
