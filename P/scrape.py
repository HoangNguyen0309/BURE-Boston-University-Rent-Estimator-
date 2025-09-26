# bostonpads_scrape.py
"""
Scrapes BostonPads listing pages and outputs an Excel file.
Fields extracted (best-effort): title, address/neighborhood, price, beds, baths, sqft,
description, listing_url, posted_date, agent/phone (if visible).
Adjust selectors if site structure changes.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin

BASE = "https://bostonpads.com"
START_URL = "https://bostonpads.com/allston-ma-apartments/"  # starting search page
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; YourNameBot/1.0; +mailto:your@email.example)"
}

def get_soup(url, session):
    r = session.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def find_listing_links_from_search(soup):
    """
    Find listing links on a search results page.
    This uses heuristics: most listing links include '/listing' or '/apartments/' or '/rentals/'.
    Adjust patterns if needed.
    """
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # heuristics - common path fragments for listing pages
        if re.search(r"(listing|apartments|rentals|/properties/|/for-rent)", href, re.I):
            if href.startswith("http"):
                links.add(href)
            else:
                links.add(urljoin(BASE, href))
    return links

def parse_listing_page(soup, url):
    """Extract best-effort fields from a listing's page"""
    def q(sel):
        el = soup.select_one(sel)
        return el.get_text(strip=True) if el else None

    # Common fields (may need selector tuning)
    title = q("h1") or q(".listing-title") or q(".property-title")
    price = q(".price") or q(".listing-price") or q(".rent")
    address = q(".address") or q(".property-address") or q(".listing-address")
    # beds/baths/sqft often appear together (try to parse)
    meta_text = None
    for sel in [".listing-info", ".property-meta", ".beds-baths", ".detail-list"]:
        el = soup.select_one(sel)
        if el:
            meta_text = el.get_text(" ", strip=True)
            break
    # try fallback: search for patterns like "2 bd", "1 bath", "750 ft"
    beds = baths = sqft = None
    if meta_text:
        m = re.search(r"(\d+)\s*(bd|br|bed)", meta_text, re.I)
        if m: beds = m.group(1)
        m = re.search(r"(\d+(\.\d+)?)\s*(ba|bath)", meta_text, re.I)
        if m: baths = m.group(1)
        m = re.search(r"(\d{3,5})\s*(sqft|ft2|ft²|sq ft)", meta_text, re.I)
        if m: sqft = m.group(1)

    description = q(".description") or q("#description") or q(".prop-description") or q(".listing-description")
    posted = q(".posted-date") or q(".listing-posted") or None

    # contact / agent
    contact = None
    agent = q(".agent-name") or q(".listing-agent") or None
    phone = q(".agent-phone") or q(".phone") or None
    # fallback: search for tel: links
    tel = None
    tel_a = soup.select_one("a[href^='tel:']")
    if tel_a:
        tel = tel_a["href"].replace("tel:", "")

    return {
        "title": title,
        "price": price,
        "address": address,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "description": description,
        "posted_date": posted,
        "agent": agent,
        "agent_phone": phone or tel,
        "listing_url": url
    }

def crawl(start_url, max_listings=1000, delay=1.0):
    session = requests.Session()
    to_visit_search_pages = [start_url]
    visited_search_pages = set()
    listing_urls = set()
    listings = []

    while to_visit_search_pages and len(listing_urls) < max_listings:
        page = to_visit_search_pages.pop(0)
        if page in visited_search_pages:
            continue
        try:
            soup = get_soup(page, session)
        except Exception as e:
            print(f"Failed to fetch {page}: {e}")
            visited_search_pages.add(page)
            continue
        visited_search_pages.add(page)

        # Find pagination links (heuristic)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(r"page=\d+|/page/\d+|/p/\d+", href, re.I):
                nextp = href if href.startswith("http") else urljoin(BASE, href)
                if nextp not in visited_search_pages and nextp not in to_visit_search_pages:
                    to_visit_search_pages.append(nextp)

        new_links = find_listing_links_from_search(soup)
        for link in new_links:
            if len(listing_urls) >= max_listings:
                break
            if link not in listing_urls and link.startswith(BASE):
                listing_urls.add(link)

        print(f"[search] {page} -> found {len(new_links)} candidate links (total listings queued: {len(listing_urls)})")
        time.sleep(delay)

    # Visit each listing and parse
    for idx, lurl in enumerate(list(listing_urls)):
        if idx >= max_listings: break
        try:
            soup = get_soup(lurl, session)
            data = parse_listing_page(soup, lurl)
            listings.append(data)
            print(f"[{idx+1}/{len(listing_urls)}] scraped: {data.get('title') or lurl}")
        except Exception as e:
            print(f"Failed to parse {lurl}: {e}")
        time.sleep(delay)

    return listings

def save_to_excel(listings, outpath="bostonpads_listings.xlsx"):
    df = pd.DataFrame(listings)
    df.to_excel(outpath, index=False)
    print(f"Wrote {len(listings)} rows to {outpath}")

if __name__ == "__main__":
    print("Starting crawl of BostonPads...")
    L = crawl(START_URL, max_listings=500, delay=1.0)
    save_to_excel(L, outpath="bostonpads_listings.xlsx")
