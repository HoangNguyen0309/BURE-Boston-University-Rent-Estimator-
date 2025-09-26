# bostonpads_click_scraper.py
# -----------------------------------------------------------
# Hybrid BostonPads scraper:
#  - On area pages: infinite-scroll harvest + follow "Next" pages
#  - On detail pages: click into each listing and scrape fields
#  - One-hot encodes amenity labels from .bpo-amenity-element
#
# Install:
#   pip install --upgrade pip
#   pip install undetected-chromedriver selenium pandas openpyxl
#
# Run (watch the browser the first time):
#   python bostonpads_click_scraper.py --url https://bostonpads.com/allston-ma-apartments/
# Then you can add --headless and increase --max-pages if needed.

import re
import time
import argparse
import random
from urllib.parse import urlparse, urljoin

import pandas as pd

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -----------------------------
# Config
# -----------------------------
BASE_DOMAIN = "bostonpads.com"
DEFAULT_URL = "https://bostonpads.com/allston-ma-apartments/"

DETAIL_RE = re.compile(
    r"https?://(www\.)?bostonpads\.com/(allston-ma-apartments|brighton-ma-apartments|boston-apartments)/.+?-\d+/?$",
    re.I
)

SELECTORS = {
    # core fields
    "title": ["h1", ".listing-title", ".property-title", "[class*='bpo-title']"],
    "price": [".price", ".listing-price", ".rent", ".bpo-price"],
    "address": [".address", ".listing-address", ".property-address", ".bpo-address"],
    "meta": [".listing-info", ".property-meta", ".beds-baths", ".detail-list", ".property-details", ".facts", "[class*='beds']"],
    "description": [".description", "#description", ".prop-description", ".listing-description", "[class*='description']"],
    "posted": [".posted-date", ".listing-posted", "[class*='posted']"],
    # amenity scan zones (extra safety)
    "amenities_blobs": [".amenities", ".features", ".property-features", ".facts", ".details", ".property-details", "ul", "dl", "table"],
    # reveal buttons (best-effort)
    "show_more": ["button[aria-label*='More']", "button:contains('Show more')", "button[aria-expanded='false']"],
    "reveal_phone": ["button[aria-label*='phone']", "button:contains('Show Phone')", "button[class*='phone']"]
}

# Keyword-to-boolean amenity flags (coarse, common)
AMENITY_KEYWORDS = {
    "laundry":       [r"laundry", r"in-?unit laundry", r"washer", r"dryer", r"laundry in building"],
    "parking":       [r"parking", r"garage"],
    "pets_allowed":  [r"pet friendly", r"cats? ok", r"dogs? ok", r"\bpets?\b"],
    "no_pets":       [r"\bno pets\b", r"pets not allowed"],
    "ac":            [r"air conditioning", r"\bac\b", r"central air"],
    "heating":       [r"\bheating\b", r"heat.*included"],
    "utilities_inc": [r"utilities included", r"hot water.*included", r"heat.*included", r"electric.*included"],
    "dishwasher":    [r"dishwasher"],
    "elevator":      [r"elevator"],
    "balcony":       [r"balcony", r"patio", r"deck", r"porch", r"terrace"],
    "hardwood":      [r"hardwood", r"wood floors"],
    "gym":           [r"gym", r"fitness"],
    "pool":          [r"pool"],
    "furnished":     [r"furnished"],
}

# -----------------------------
# Utility helpers
# -----------------------------
def is_same_domain(url):
    try:
        return urlparse(url).netloc.lower().endswith(BASE_DOMAIN)
    except Exception:
        return False

def text_of(driver, selectors):
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            t = el.text.strip()
            if t:
                return t
        except Exception:
            continue
    return None

def harvest_texts(driver, selectors):
    chunks = []
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                try:
                    tx = el.text.strip()
                    if tx and len(tx) > 8:
                        chunks.append(tx)
                except StaleElementReferenceException:
                    pass
        except Exception:
            continue
    return " | ".join(chunks) if chunks else ""

def normalize_price(raw):
    if not raw:
        return None
    txt = raw.replace(",", "")
    m = re.search(r"\$?\s*([0-9][0-9]*)", txt)
    return int(m.group(1)) if m else None

def parse_sqft(text):
    if not text:
        return None
    m = re.search(r"(\d{3,5})\s*(sq\s?ft|ft2|ft²|sq\.?\s*ft)", text, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

# For robust bed/bath parsing
BED_PATTERNS = [r"(\d+(\.\d+)?)\s*(bedrooms?|beds?|bd|br)\b", r"^\s*(\d+(\.\d+)?)\s*$"]
BATH_PATTERNS = [r"(\d+(\.\d+)?)\s*(bathrooms?|baths?|ba)\b", r"^\s*(\d+(\.\d+)?)\s*$"]

def _parse_numeric(txt, patterns):
    if not txt:
        return None
    low = txt.lower().strip()
    for pat in patterns:
        m = re.search(pat, low, re.I)
        if m:
            try:
                val = float(m.group(1))
                return int(val) if float(val).is_integer() else val
            except Exception:
                pass
    return None

def _parse_beds_text(txt):
    if not txt:
        return None
    if "studio" in txt.lower():
        return 0
    return _parse_numeric(txt, BED_PATTERNS)

def _parse_baths_text(txt):
    return _parse_numeric(txt, BATH_PATTERNS)

def extract_amenity_flags(text):
    out = {k: False for k in AMENITY_KEYWORDS}
    lower = (text or "").lower()
    found = []
    for key, pats in AMENITY_KEYWORDS.items():
        for p in pats:
            if re.search(p, lower, re.I):
                out[key] = True
                found.append(key)
                break
    out["amenities_raw"] = ", ".join(sorted(set(found))) if found else None
    return out

def sanitize_amenity_label(label: str) -> str:
    """Turn raw amenity label into a safe column name like 'Amenity_In_Unit_Laundry'."""
    s = label.strip()
    s = re.sub(r"[\s/,+()\-]+", "_", s)     # spaces & separators -> _
    s = re.sub(r"[^A-Za-z0-9_]", "", s)     # strip non-alnum
    s = re.sub(r"_+", "_", s).strip("_")    # collapse underscores
    if not s:
        s = "Amenity"
    # ensure it starts with a letter for Excel friendliness
    if not re.match(r"^[A-Za-z_]", s):
        s = "A_" + s
    return f"Amenity_{s}"

def maybe_click_buttons(driver, selectors):
    for sel in selectors:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for b in btns:
                if b.is_displayed() and b.is_enabled():
                    try:
                        b.click()
                        time.sleep(0.5)
                    except Exception:
                        pass
        except Exception:
            continue

# -----------------------------
# Area-page hybrid collector
# -----------------------------
def collect_all_listing_urls_hybrid(area_url, headless=False, max_pages=30, scrolls_per_page=40,
                                    min_new_per_round=2, stagnation_rounds=4):
    """On each page: infinite-scroll to load cards, harvest detail links; if a Next link exists, follow it."""
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1700")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    all_urls = set()
    try:
        current = area_url
        for p in range(max_pages):
            print(f"[Page {p+1}] Visiting {current}")
            driver.get(current)
            # Accept cookies if present
            for sel in ["#onetrust-accept-btn-handler", "button[aria-label*='Accept']", "button.cookie-accept"]:
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel))).click()
                    break
                except Exception:
                    pass

            try:
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]")))
            except TimeoutException:
                pass

            # Infinite scroll harvest on this page
            stagnant = 0
            for i in range(1, scrolls_per_page + 1):
                # Harvest
                anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
                before = len(all_urls)
                for a in anchors:
                    href = a.get_attribute("href") or ""
                    if is_same_domain(href) and DETAIL_RE.search(href):
                        all_urls.add(href)
                gained = len(all_urls) - before
                print(f"  scroll {i:02d}: +{gained} (page total so far {len(all_urls)})")

                # Scroll to load more
                driver.execute_script("window.scrollBy(0, document.body.scrollHeight * 0.9);")
                time.sleep(1.0 + random.random() * 0.8)

                stagnant = stagnant + 1 if gained < min_new_per_round else 0
                if stagnant >= stagnation_rounds:
                    break

            # One last sweep at the bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)
            for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
                href = a.get_attribute("href") or ""
                if is_same_domain(href) and DETAIL_RE.search(href):
                    all_urls.add(href)

            # Try to follow "Next" pagination if present
            next_link = None
            try:
                el = driver.find_element(By.LINK_TEXT, "Next")
                next_link = el.get_attribute("href")
            except Exception:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
                    next_link = el.get_attribute("href")
                except Exception:
                    pass

            if next_link and is_same_domain(next_link):
                current = urljoin(current, next_link)
            else:
                break  # no more pages

        print(f"Collected {len(all_urls)} unique detail URLs across pages")
        return sorted(all_urls)

    finally:
        driver.quit()

# -----------------------------
# Detail-page scraper (clicks)
# -----------------------------
def scrape_listing_with_clicks(driver, url, page_wait=20):
    driver.get(url)
    try:
        WebDriverWait(driver, page_wait).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".price, .bpo-price")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".address, .bpo-address"))
            )
        )
    except TimeoutException:
        pass

    maybe_click_buttons(driver, SELECTORS.get("show_more", []))
    maybe_click_buttons(driver, SELECTORS.get("reveal_phone", []))
    # small scrolls to trigger lazy content
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight * 0.35);")
        time.sleep(0.4)

    title = text_of(driver, SELECTORS["title"])
    price_raw = text_of(driver, SELECTORS["price"])
    price = normalize_price(price_raw)
    address = text_of(driver, SELECTORS["address"])
    meta_text = text_of(driver, SELECTORS["meta"]) or ""
    description = text_of(driver, SELECTORS["description"])
    posted_date = text_of(driver, SELECTORS["posted"])

    # Beds / baths from the exact classes you provided
    beds_text = None
    baths_text = None
    try:
        beds_text = driver.find_element(By.CSS_SELECTOR, ".bpo-beds-text").text.strip()
    except Exception:
        pass
    try:
        baths_text = driver.find_element(By.CSS_SELECTOR, ".bpo-listing-bath").text.strip()
    except Exception:
        pass

    beds = _parse_beds_text(beds_text) or _parse_beds_text(meta_text) or _parse_beds_text(title or "")
    baths = _parse_baths_text(baths_text) or _parse_baths_text(meta_text) or _parse_baths_text(title or "")

    # As a last resort, parse entire body text
    if beds is None or baths is None:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""
        if beds is None:
            beds = _parse_beds_text(body_text)
        if baths is None:
            baths = _parse_baths_text(body_text)

    sqft = parse_sqft(" | ".join([t for t in [meta_text, title, description] if t]))

    # Amenities from .bpo-amenity-element (raw list + boolean flags)
    amen_item_texts = []
    try:
        amen_els = driver.find_elements(By.CSS_SELECTOR, ".bpo-amenity-element")
        for el in amen_els:
            try:
                t = el.text.strip()
                if t:
                    amen_item_texts.append(t)
            except Exception:
                pass
    except Exception:
        pass
    amenities_blob = " | ".join(amen_item_texts + [meta_text or "", description or ""])
    amen_flags = extract_amenity_flags(amenities_blob)
    amen_flags["amenities_list_raw"] = "; ".join(amen_item_texts) if amen_item_texts else None
    amen_flags["_amenity_labels_list"] = amen_item_texts  # keep list for one-hot later

    # Agent & phone (best-effort)
    agent = None
    phone = None
    try:
        agent_el = driver.find_element(By.CSS_SELECTOR, ".agent-name, .listing-agent, [class*='agent']")
        agent = agent_el.text.strip() or None
    except NoSuchElementException:
        pass
    try:
        tel_el = driver.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
        phone = tel_el.get_attribute("href").replace("tel:", "").strip()
    except NoSuchElementException:
        pass

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
        **amen_flags
    }

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="BostonPads hybrid click-scraper (area pages -> detail pages).")
    ap.add_argument("--url", default=DEFAULT_URL, help="Area URL to start (e.g., Allston).")
    ap.add_argument("--out-prefix", default="bostonpads_allston", help="Output file prefix.")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless.")
    ap.add_argument("--max-pages", type=int, default=30, help="Max paginated pages to follow.")
    ap.add_argument("--scrolls-per-page", type=int, default=40, help="Scroll rounds per page.")
    ap.add_argument("--max-urls", type=int, default=None, help="Limit number of detail URLs (debug).")
    args = ap.parse_args()

    # 1) Collect detail URLs across pages
    urls = collect_all_listing_urls_hybrid(
        area_url=args.url,
        headless=args.headless,
        max_pages=args.max_pages,
        scrolls_per_page=args.scrolls_per_page
    )
    urls = [u for u in urls if DETAIL_RE.search(u)]
    urls = sorted(set(urls))
    if args.max_urls:
        urls = urls[:args.max_urls]
    print(f"Total unique candidate listing URLs: {len(urls)}")

    # 2) Open a single browser for detail scraping
    opts = uc.ChromeOptions()
    if args.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1700")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    rows = []
    try:
        for i, u in enumerate(urls, 1):
            try:
                row = scrape_listing_with_clicks(driver, u)
                rows.append(row)
                print(f"[{i}/{len(urls)}] {row.get('title') or 'Untitled'} | "
                      f"${row.get('price')} | {row.get('beds')}bd/{row.get('baths')}ba")
                time.sleep(0.5)  # be polite
            except Exception as e:
                print(f"Failed: {u} -> {e}")
    finally:
        driver.quit()

    # 3) Build DataFrame
    df = pd.DataFrame(rows)

    # 3a) Build one-hot amenity columns from the raw amenity labels
    # Gather all distinct labels
    all_labels = set()
    for labels in df.get("_amenity_labels_list", []).tolist():
        if isinstance(labels, list):
            for lab in labels:
                if isinstance(lab, str) and lab.strip():
                    all_labels.add(lab.strip())
    # Create columns
    one_hot_columns = []
    for lab in sorted(all_labels):
        col = sanitize_amenity_label(lab)
        one_hot_columns.append(col)
        df[col] = df["_amenity_labels_list"].apply(
            lambda lst: (isinstance(lst, list) and any(lab.strip() == x.strip() for x in lst))
        )

    # 3b) Order columns: core fields, coarse flags, one-hot amenity columns, then description
    coarse_amen_cols = list(AMENITY_KEYWORDS.keys()) + ["amenities_raw", "amenities_list_raw"]
    core_cols = ["title", "price", "price_raw", "beds", "baths", "sqft", "address",
                 "posted_date", "agent", "agent_phone", "listing_url"]
    cols = core_cols + coarse_amen_cols + one_hot_columns + ["description"]
    cols = [c for c in cols if c in df.columns]
    df = df.reindex(columns=cols)

    # 4) Save
    xlsx_path = f"{args.out_prefix}_listings.xlsx"
    csv_path  = f"{args.out_prefix}_listings.csv"
    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nWrote {len(df)} rows to:\n - {xlsx_path}\n - {csv_path}")
    print(f"Added {len(one_hot_columns)} amenity one-hot columns.")

if __name__ == "__main__":
    main()
