# bostonpads_full_scraper.py
# ---------------------------------------------------------
# Collects ALL listing URLs from BostonPads area pages,
# follows pagination ("Next" / ?page=N), clicks into each
# listing detail page, and scrapes details + amenities.
#
# Install:
#   pip install undetected-chromedriver selenium pandas openpyxl
#
# Run:
#   python bostonpads_full_scraper.py --url https://bostonpads.com/allston-ma-apartments/
#
# Notes:
# - First run WITHOUT --headless so you can see behavior.
# - Will follow next-page links if present.
# - Keep delays to avoid hammering the site.

import re
import time
import argparse
import random
from urllib.parse import urlparse, urljoin
import pandas as pd

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DOMAIN = "bostonpads.com"
DETAIL_RE = re.compile(r"https?://(www\.)?bostonpads\.com/.+?-\d+/?$", re.I)

# Fields
SELECTORS = {
    "title": ["h1", ".listing-title", ".property-title"],
    "price": [".price", ".listing-price", ".rent"],
    "address": [".address", ".listing-address", ".property-address"],
    "meta": [".listing-info", ".property-meta", ".beds-baths", ".detail-list", ".facts"],
    "description": [".description", ".listing-description", "#description"],
    "posted": [".posted-date", ".listing-posted"],
    "amenities_blobs": [".amenities", ".features", ".property-features", ".facts", ".details", ".property-details", "ul", "dl"],
}

AMENITY_KEYWORDS = {
    "laundry": [r"laundry", r"washer", r"dryer"],
    "parking": [r"parking", r"garage"],
    "pets_allowed": [r"pet friendly", r"cats? ok", r"dogs? ok"],
    "no_pets": [r"\bno pets\b"],
    "ac": [r"air conditioning", r"\bac\b", r"central air"],
    "heating": [r"heat", r"heating"],
    "utilities_inc": [r"utilities included", r"hot water.*included", r"heat.*included"],
    "dishwasher": [r"dishwasher"],
    "elevator": [r"elevator"],
    "balcony": [r"balcony", r"patio", r"deck", r"porch", r"terrace"],
    "hardwood": [r"hardwood"],
    "gym": [r"gym", r"fitness"],
    "pool": [r"pool"],
    "furnished": [r"furnished"],
}

def is_same_domain(url):
    try:
        return urlparse(url).netloc.lower().endswith(BASE_DOMAIN)
    except:
        return False

def normalize_price(raw):
    if not raw: return None
    txt = raw.replace(",", "")
    m = re.search(r"\$?\s*([0-9]+)", txt)
    return int(m.group(1)) if m else None

def parse_beds_baths(text):
    beds = baths = None
    if text:
        bm = re.search(r"(\d+(\.\d+)?)\s*(bed|bd|br)\b", text, re.I)
        if bm: beds = float(bm.group(1))
        am = re.search(r"(\d+(\.\d+)?)\s*(bath|ba)\b", text, re.I)
        if am: baths = float(am.group(1))
    return int(beds) if beds and beds.is_integer() else beds, \
           int(baths) if baths and baths.is_integer() else baths

def parse_sqft(text):
    m = re.search(r"(\d{3,5})\s*(sq\s?ft|ft2|ft²)", text or "", re.I)
    return int(m.group(1)) if m else None

def extract_amenities(text):
    out = {k: False for k in AMENITY_KEYWORDS}
    lower = (text or "").lower()
    found = []
    for key, pats in AMENITY_KEYWORDS.items():
        for p in pats:
            if re.search(p, lower):
                out[key] = True
                found.append(key)
                break
    out["amenities_raw"] = ", ".join(sorted(set(found))) if found else None
    return out

def text_of(driver, selectors):
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.text.strip(): return el.text.strip()
        except: continue
    return None

def harvest_texts(driver, selectors):
    chunks = []
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                txt = el.text.strip()
                if txt and len(txt) > 8: chunks.append(txt)
        except: continue
    return " | ".join(chunks)

# ------------------------
# Collect ALL listing URLs
# ------------------------
def collect_all_listing_urls(area_url, headless=False, max_pages=20):
    opts = uc.ChromeOptions()
    if headless: opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,1600")
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    all_urls = set()
    try:
        current = area_url
        for p in range(max_pages):
            print(f"[Page {p+1}] Visiting {current}")
            driver.get(current)
            time.sleep(2.5)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for a in anchors:
                href = a.get_attribute("href") or ""
                if is_same_domain(href) and DETAIL_RE.search(href):
                    all_urls.add(href)

            # Look for "Next" page link
            next_link = None
            try:
                next_el = driver.find_element(By.LINK_TEXT, "Next")
                next_link = next_el.get_attribute("href")
            except:
                try:
                    next_el = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
                    next_link = next_el.get_attribute("href")
                except:
                    pass

            if next_link and is_same_domain(next_link):
                current = urljoin(current, next_link)
            else:
                break
        print(f"Collected {len(all_urls)} unique detail URLs across pages")
        return sorted(all_urls)
    finally:
        driver.quit()

# ------------------------
# Scrape a listing in-page
# ------------------------
def scrape_listing(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .price, .address"))
        )
    except TimeoutException:
        pass

    title = text_of(driver, SELECTORS["title"])
    price_raw = text_of(driver, SELECTORS["price"])
    price = normalize_price(price_raw)
    address = text_of(driver, SELECTORS["address"])
    meta_text = text_of(driver, SELECTORS["meta"]) or ""
    description = text_of(driver, SELECTORS["description"])
    posted = text_of(driver, SELECTORS["posted"])
    beds, baths = parse_beds_baths(meta_text)
    sqft = parse_sqft(meta_text)
    agent, phone = None, None
    try:
        agent = driver.find_element(By.CSS_SELECTOR, ".agent-name, .listing-agent").text.strip()
    except: pass
    try:
        phone = driver.find_element(By.CSS_SELECTOR, "a[href^='tel:']").get_attribute("href").replace("tel:", "")
    except: pass
    amenities_text = " | ".join([meta_text, description or "", harvest_texts(driver, SELECTORS["amenities_blobs"])])
    amen = extract_amenities(amenities_text)
    return {
        "title": title, "price": price, "price_raw": price_raw,
        "beds": beds, "baths": baths, "sqft": sqft,
        "address": address, "posted_date": posted,
        "agent": agent, "agent_phone": phone,
        "listing_url": url, "description": description,
        **amen
    }

# ------------------------
# Main
# ------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://bostonpads.com/allston-ma-apartments/", help="Area URL")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--out-prefix", default="bostonpads_allston")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--max-urls", type=int, default=None)
    args = ap.parse_args()

    urls = collect_all_listing_urls(args.url, headless=args.headless, max_pages=args.max_pages)
    if args.max_urls: urls = urls[:args.max_urls]

    opts = uc.ChromeOptions()
    if args.headless: opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,1600")
    driver = uc.Chrome(options=opts)

    rows = []
    try:
        for i, u in enumerate(urls, 1):
            try:
                row = scrape_listing(driver, u)
                rows.append(row)
                print(f"[{i}/{len(urls)}] {row.get('title')} | ${row.get('price')} | {row.get('beds')}bd/{row.get('baths')}ba")
                time.sleep(0.5)
            except Exception as e:
                print(f"Failed {u}: {e}")
    finally:
        driver.quit()

    df = pd.DataFrame(rows)
    amen_cols = list(AMENITY_KEYWORDS.keys()) + ["amenities_raw"]
    cols = ["title", "price", "price_raw", "beds", "baths", "sqft", "address",
            "posted_date", "agent", "agent_phone", "listing_url"] + amen_cols + ["description"]
    df = df.reindex(columns=[c for c in cols if c in df.columns])
    df.to_excel(f"{args.out_prefix}_listings.xlsx", index=False)
    df.to_csv(f"{args.out_prefix}_listings.csv", index=False, encoding="utf-8")
    print(f"\nWrote {len(df)} rows to {args.out_prefix}_listings.(xlsx/csv)")

if __name__ == "__main__":
    main()
