# bostonpads_allston_scraper.py
# ------------------------------------------
# Collects Allston listing detail URLs from BostonPads,
# then parses each listing and writes Excel + CSV.
#
# Install:
#   pip install undetected-chromedriver selenium requests beautifulsoup4 pandas openpyxl
#
# Run:
#   python bostonpads_allston_scraper.py
# Optional args:
#   python bostonpads_allston_scraper.py --url https://bostonpads.com/allston-ma-apartments/ --headless
#
# Notes:
# - Uses undetected-chromedriver to avoid simple bot checks.
# - First run WITHOUT --headless so you can watch it load.
# - If you get 0 URLs, increase --max-scrolls or try without headless.

import re
import time
import argparse
import random
from urllib.parse import urlparse, urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup

# Selenium / undetected-chromedriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEFAULT_START_URL = "https://bostonpads.com/allston-ma-apartments/"
BASE_DOMAIN = "bostonpads.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Matches detail pages like .../allston-ma-apartments/<slug>-<id>/
DETAIL_RE = re.compile(
    r"https?://(www\.)?bostonpads\.com/allston-ma-apartments/.+?-\d+/?$",
    re.I
)

# ---------------------------
# Utilities & parsing helpers
# ---------------------------

def is_same_domain(url, base_domain=BASE_DOMAIN):
    try:
        host = urlparse(url).netloc.lower()
        return host.endswith(base_domain)
    except Exception:
        return False

def get_soup(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def normalize_price(raw):
    if not raw:
        return None
    txt = raw.replace(",", "")
    m = re.search(r"\$?\s*([0-9][0-9]*)", txt)
    return int(m.group(1)) if m else None

def parse_beds_baths(text):
    beds = baths = None
    if not text:
        return beds, baths
    bm = re.search(r"(\d+(\.\d+)?)\s*(bd|bed|beds|br)\b", text, re.I)
    if bm:
        try: beds = float(bm.group(1))
        except: pass
    am = re.search(r"(\d+(\.\d+)?)\s*(ba|bath|baths)\b", text, re.I)
    if am:
        try: baths = float(am.group(1))
        except: pass
    if beds is not None and isinstance(beds, float) and beds.is_integer():
        beds = int(beds)
    if baths is not None and isinstance(baths, float) and baths.is_integer():
        baths = int(baths)
    return beds, baths

AMENITY_KEYWORDS = {
    "laundry":       [r"laundry", r"in-?unit laundry", r"washer", r"dryer", r"laundry in building"],
    "parking":       [r"parking", r"garage"],
    "pets_allowed":  [r"pet", r"cats? ok", r"dogs? ok", r"pet friendly"],
    "no_pets":       [r"\bno pets\b", r"pets not allowed"],
    "ac":            [r"air conditioning", r"\bac\b", r"central air"],
    "heating":       [r"\bheating\b", r"heat.*included"],
    "utilities_inc": [r"utilities included", r"heat.*included", r"hot water.*included", r"electric.*included"],
    "dishwasher":    [r"dishwasher"],
    "elevator":      [r"elevator"],
    "balcony":       [r"balcony", r"patio", r"deck", r"porch", r"terrace"],
    "hardwood":      [r"hardwood", r"wood floors"],
    "gym":           [r"gym", r"fitness"],
    "pool":          [r"pool"],
    "furnished":     [r"furnished"],
}

def extract_amenities_from_text(text):
    out = {k: False for k in AMENITY_KEYWORDS}
    if not text:
        out["amenities_raw"] = None
        return out
    lower = text.lower()
    found = []
    for key, patterns in AMENITY_KEYWORDS.items():
        for p in patterns:
            if re.search(p, lower, re.I):
                out[key] = True
                found.append(key)
                break
    out["amenities_raw"] = ", ".join(sorted(set(found))) if found else None
    return out

CANDIDATE_SELECTORS = {
    "title":      ["h1", ".listing-title", ".property-title"],
    "price":      [".price", ".listing-price", ".rent", "div:has(.price) .amount"],
    "address":    [".address", ".listing-address", ".property-address"],
    "meta":       [".listing-info", ".property-meta", ".beds-baths", ".detail-list", ".property-details", ".facts"],
    "description":[".description", "#description", ".prop-description", ".listing-description", "[class*='description']"],
    "posted":     [".posted-date", ".listing-posted", "[class*='posted']"]
}

def qtext(soup, selectors):
    for sel in selectors:
        try:
            el = soup.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)
        except Exception:
            pass
    return None

def extract_bullets_and_features(soup):
    chunks = []
    for sel in [
        "ul", ".amenities", ".features", ".property-features",
        "table", ".facts", ".details", ".property-details", "dl"
    ]:
        for el in soup.select(sel):
            txt = el.get_text(" ", strip=True)
            if txt and len(txt) > 10:
                chunks.append(txt)
    return " | ".join(chunks) if chunks else None

def parse_listing(url):
    soup = get_soup(url, timeout=35)

    title = qtext(soup, CANDIDATE_SELECTORS["title"])
    price_raw = qtext(soup, CANDIDATE_SELECTORS["price"])
    price = normalize_price(price_raw)
    address = qtext(soup, CANDIDATE_SELECTORS["address"])
    meta_text = qtext(soup, CANDIDATE_SELECTORS["meta"]) or ""
    description = qtext(soup, CANDIDATE_SELECTORS["description"])
    posted_date = qtext(soup, CANDIDATE_SELECTORS["posted"])

    beds, baths = parse_beds_baths(meta_text or "")
    sqft = None
    m = re.search(r"(\d{3,5})\s*(sq\s?ft|ft2|ft²|sq\.?\s*ft)", meta_text, re.I)
    if m:
        try: sqft = int(m.group(1))
        except: pass

    features_blob = extract_bullets_and_features(soup)
    amen_text = " | ".join([t for t in [meta_text, description, features_blob] if t])
    amen = extract_amenities_from_text(amen_text)

    # Agent / phone (best-effort)
    agent = None
    phone = None
    for sel in [".agent-name", ".listing-agent", "[class*='agent']"]:
        el = soup.select_one(sel)
        if el:
            agent = el.get_text(" ", strip=True)
            break
    tel_a = soup.select_one("a[href^='tel:']")
    if tel_a:
        phone = tel_a.get("href", "").replace("tel:", "").strip()

    return {
        "title": title,
        "price": price,
        "price_raw": price_raw,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "address": address,
        "posted_date": posted_date,
        "agent": agent,
        "agent_phone": phone,
        "listing_url": url,
        "description": description,
        **amen
    }

# ---------------------------
# URL collector (UC + scroll)
# ---------------------------

def collect_listing_urls(start_url=DEFAULT_START_URL, max_scrolls=140, min_new_per_round=2,
                         stagnation_rounds=5, headless=False):
    """
    Loads the area page, triggers client-side loading (scroll), and returns detail-page URLs.
    """
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1600")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    try:
        driver.get(start_url)

        # Try to accept/collapse cookie banners if present (best-effort)
        for sel in [
            "#onetrust-accept-btn-handler",
            "button[aria-label*='Accept']",
            "button.cookie-accept"
        ]:
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                ).click()
                break
            except Exception:
                pass

        # Ensure some anchors exist before scrolling
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]"))
        )

        seen = set()
        stagnant = 0

        for i in range(1, max_scrolls + 1):
            # Scroll in chunks to trigger incremental loads
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight * 0.9);")
            time.sleep(1.1 + random.random() * 0.7)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            before = len(seen)
            for a in anchors:
                href = a.get_attribute("href") or ""
                if DETAIL_RE.search(href):
                    seen.add(href)

            gained = len(seen) - before
            print(f"scroll {i:03d}: +{gained} (total {len(seen)})")

            # If not gaining much, count stagnation
            if gained < min_new_per_round:
                stagnant += 1
            else:
                stagnant = 0

            if stagnant >= stagnation_rounds:
                break

        # Final sweep at bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = a.get_attribute("href") or ""
            if DETAIL_RE.search(href):
                seen.add(href)

        print(f"Collected {len(seen)} unique detail URLs")
        return sorted(seen)

    finally:
        driver.quit()

# -----------
# Main driver
# -----------

def main():
    ap = argparse.ArgumentParser(description="Scrape BostonPads Allston listings to Excel + CSV.")
    ap.add_argument("--url", default=DEFAULT_START_URL, help="Area page (default: Allston)")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless")
    ap.add_argument("--max-scrolls", type=int, default=140, help="Max scroll rounds")
    ap.add_argument("--out-prefix", default="bostonpads_allston", help="Output file prefix")
    args = ap.parse_args()

    print(f"Collecting listing URLs from: {args.url}")
    urls = collect_listing_urls(
        start_url=args.url,
        max_scrolls=args.max_scrolls,
        headless=args.headless
    )

    # Keep only detail pages & dedupe
    urls = [u for u in urls if DETAIL_RE.search(u)]
    urls = sorted(set(urls))
    print(f"Total unique candidate listing URLs: {len(urls)}")

    rows = []
    for i, u in enumerate(urls, 1):
        try:
            row = parse_listing(u)
            rows.append(row)
            print(f"[{i}/{len(urls)}] {row.get('title') or 'Untitled'} | "
                  f"${row.get('price')} | {row.get('beds')}bd/{row.get('baths')}ba")
            time.sleep(0.4)  # polite delay
        except Exception as e:
            print(f"Failed to parse {u}: {e}")

    df = pd.DataFrame(rows)

    # Order columns: core fields first, then amenities, then description
    amen_cols = list(AMENITY_KEYWORDS.keys()) + ["amenities_raw"]
    cols = ["title", "price", "price_raw", "beds", "baths", "sqft",
            "address", "posted_date", "agent", "agent_phone",
            "listing_url"] + amen_cols + ["description"]
    cols = [c for c in cols if c in df.columns]
    df = df.reindex(columns=cols)

    xlsx_path = f"{args.out_prefix}_listings.xlsx"
    csv_path  = f"{args.out_prefix}_listings.csv"
    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8")

    print(f"\nWrote {len(df)} rows to:\n - {xlsx_path}\n - {csv_path}")

if __name__ == "__main__":
    main()
