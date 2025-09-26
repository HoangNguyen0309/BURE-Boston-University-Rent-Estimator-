# apartments_boston_scraper.py
# ------------------------------------------------------------
# Apartments.com (Boston, MA) scraper — Selenium-only page fetches, NO clicks.
# - Collects property URLs from search pages (?page=N)
# - Loads each property in headless Selenium, parses rendered DOM
# - Extracts: .rentLabel, .detailsLabel (beds/baths), .pricingColumn, .sqftColumn
# - Extracts amenities: "Community Amenities" + "Apartment Features"
# - Auto-fallback to built-in HTML parser if lxml isn't installed
# - Builds amenity one-hot columns in a single concat (fast; no fragmentation warnings)
# - Outputs CSV + XLSX

import re
import time
import argparse
from contextlib import suppress
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SEARCH_URL_DEFAULT = "https://www.apartments.com/boston-ma/"
DETAIL_RE = re.compile(r"^https?://(www\.)?apartments\.com/.+-boston-ma/[^/]+/?$", re.I)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ----------------------------- helpers
def build_page_url(base_url: str, page_num: int) -> str:
    parts = list(urlparse(base_url))
    q = dict(parse_qsl(parts[4]))
    q["page"] = str(page_num)
    parts[4] = urlencode(q)
    return urlunparse(parts)

def parse_price_any(text):
    if not text: return None
    m = re.search(r"\$\s*([\d,]+)", text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None

def parse_beds(details_text):
    if not details_text: return None
    txt = details_text.lower()
    if "studio" in txt: return 0
    m = re.search(r"(\d+(\.\d+)?)\s*-\s*(\d+(\.\d+)?)\s*beds?", txt)
    if m:
        v = float(m.group(1));  return int(v) if v.is_integer() else v
    m = re.search(r"(\d+(\.\d+)?)\s*beds?", txt)
    if m:
        v = float(m.group(1));  return int(v) if v.is_integer() else v
    return None

def parse_baths(details_text):
    if not details_text: return None
    txt = details_text.lower()
    m = re.search(r"(\d+(\.\d+)?)\s*-\s*(\d+(\.\d+)?)\s*baths?", txt)
    if m:
        v = float(m.group(1));  return int(v) if v.is_integer() else v
    m = re.search(r"(\d+(\.\d+)?)\s*baths?", txt)
    if m:
        v = float(m.group(1));  return int(v) if v.is_integer() else v
    return None

def parse_sqft(text):
    if not text: return None
    m = re.search(r"([\d,]+)\s*(sq\s*\.?ft|sf|ft2|ft²|square\s*feet)", text, re.I)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return None
    return None

def sanitize_amenity_label(label: str) -> str:
    s = (label or "").strip()
    s = re.sub(r"[\s/,+()\-]+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s: s = "Amenity"
    if not re.match(r"^[A-Za-z_]", s): s = "A_" + s
    return f"Amenity_{s}"

def get_soup(html: str) -> BeautifulSoup:
    """Try lxml first (faster); fall back to built-in html.parser."""
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")

# ----------------------------- drivers
def make_driver(headless=True, win_size="1280,1700", block_resources=True):
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--window-size={win_size}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(f"--user-agent={UA}")
    opts.page_load_strategy = "eager"
    # Speed: don’t render images
    opts.add_argument("--blink-settings=imagesEnabled=false")

    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(45)

    if block_resources:
        with suppress(Exception):
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setBlockedURLs", {
                "urls": [
                    "*.png","*.jpg","*.jpeg","*.gif","*.webp","*.svg",
                    "*.woff","*.woff2","*.ttf","*.otf",
                    "*googletagmanager*","*google-analytics*","*doubleclick*",
                    "*facebook*","*hotjar*","*segment*"
                ]
            })
    return driver

# ----------------------------- parsing
def parse_property_html(html: str, url: str):
    rows = []
    soup = get_soup(html)

    # Property name / address
    prop_name = None
    for sel in ["h1", "[data-testid='propertyName']", "[class*='PropertyName']"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            prop_name = el.get_text(strip=True)
            break

    address = None
    for sel in ["[data-testid='property-address']", "[class*='Address']", "address", "[itemprop='address']"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            address = el.get_text(" ", strip=True)
            break

    # Floorplan rows anchored on .detailsLabel
    detail_nodes = soup.select(".detailsLabel")
    seen = set()
    for det in detail_nodes:
        row = det
        # walk up to a plausible row container
        for _ in range(4):
            if not row: break
            if row.name in ("tr", "div"):
                if row.select_one(".rentLabel, .pricingColumn, .sqftColumn, .detailsLabel"):
                    break
            row = row.parent
        if not row: continue

        rent_el  = row.select_one(".rentLabel")
        price_el = row.select_one(".pricingColumn")
        sqft_el  = row.select_one(".sqftColumn")

        rent_raw  = rent_el.get_text(" ", strip=True) if rent_el else ""
        details   = det.get_text(" ", strip=True)
        price_raw = price_el.get_text(" ", strip=True) if price_el else ""
        sqft_raw  = sqft_el.get_text(" ", strip=True) if sqft_el else ""

        sig = (rent_raw, details, price_raw, sqft_raw)
        if sig in seen: continue
        seen.add(sig)

        rows.append({
            "property_name": prop_name or None,
            "address": address or None,
            "listing_url": url,
            "rentLabel_raw": rent_raw or None,
            "detailsLabel_raw": details or None,
            "pricingColumn_raw": price_raw or None,
            "sqftColumn_raw": sqft_raw or None,
            "beds": parse_beds(details),
            "baths": parse_baths(details),
            "price": parse_price_any(rent_raw) or parse_price_any(price_raw),
            "sqft": parse_sqft(sqft_raw),
        })

    # Ensure at least one row (so we still save amenities if no floorplans detected)
    if not rows:
        rows.append({
            "property_name": prop_name or None,
            "address": address or None,
            "listing_url": url,
            "rentLabel_raw": None,
            "detailsLabel_raw": None,
            "pricingColumn_raw": None,
            "sqftColumn_raw": None,
            "beds": None,
            "baths": None,
            "price": None,
            "sqft": None,
        })

    # Amenities
    def collect_amenities_by_heading(soup: BeautifulSoup, heading_text: str):
        items = []
        for tag in ["h2", "h3", "h4", "div", "span"]:
            for h in soup.select(tag):
                ht = h.get_text(" ", strip=True).lower()
                if heading_text.lower() in ht:
                    parent = h.parent
                    containers = []
                    if parent:
                        containers += parent.select("ul, div")
                    for c in containers:
                        for li in c.select("li"):
                            t = li.get_text(" ", strip=True)
                            if t and heading_text.lower() not in t.lower():
                                items.append(t)
        out, seen_items = [], set()
        for x in items:
            if x not in seen_items:
                seen_items.add(x)
                out.append(x)
        return out

    community_amenities = collect_amenities_by_heading(soup, "community amenities")
    apartment_features  = collect_amenities_by_heading(soup, "apartment features")

    for r in rows:
        r["community_amenities_raw"] = "; ".join(community_amenities) if community_amenities else None
        r["apartment_features_raw"]  = "; ".join(apartment_features) if apartment_features else None
        r["_community_amenity_list"] = community_amenities
        r["_apartment_feature_list"] = apartment_features

    return rows

# ----------------------------- collection
def collect_property_urls(search_url, max_pages=2, headless=True):
    driver = make_driver(headless=headless, win_size="1280,1500")
    urls = set()
    try:
        for p in range(1, max_pages + 1):
            page_url = build_page_url(search_url, p)
            print(f"[Search] Page {p}: {page_url}")
            driver.get(page_url)
            time.sleep(0.8)
            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for a in anchors:
                with suppress(Exception):
                    href = a.get_attribute("href") or ""
                    if DETAIL_RE.search(href):
                        urls.add(href)
            print(f"  Collected {len(urls)} URLs so far...")
    finally:
        with suppress(Exception):
            driver.quit()
    return sorted(urls)

# ----------------------------- property scrape (Selenium, no clicks)
def scrape_property_via_selenium(driver, url, wait_sec=18, settle=0.8):
    driver.get(url)
    with suppress(Exception):
        WebDriverWait(driver, wait_sec).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".detailsLabel")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pricingColumn")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".rentLabel")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sqftColumn")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
            )
        )
    time.sleep(settle)
    html = driver.page_source
    return parse_property_html(html, url)

# ----------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Apartments.com Boston scraper (Selenium-only page fetches, no clicks).")
    ap.add_argument("--url", default=SEARCH_URL_DEFAULT, help="Search URL (default: Boston).")
    ap.add_argument("--max-pages", type=int, default=2, help="How many search pages to fetch.")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless.")
    ap.add_argument("--property-timeout", type=int, default=18, help="Seconds to wait for property DOM.")
    ap.add_argument("--sleep", type=float, default=0.3, help="Polite delay between properties.")
    ap.add_argument("--out-prefix", default="apartments_boston", help="Output prefix for files.")
    args = ap.parse_args()

    # 1) Collect property URLs
    prop_urls = collect_property_urls(args.url, max_pages=args.max_pages, headless=args.headless)
    print(f"Total property URLs: {len(prop_urls)}")

    # 2) One headless driver to scrape properties (no clicks)
    prop_driver = make_driver(headless=args.headless, win_size="1280,1700", block_resources=True)

    all_rows = []
    try:
        for i, u in enumerate(prop_urls, 1):
            try:
                rows = scrape_property_via_selenium(prop_driver, u, wait_sec=args.property_timeout, settle=0.8)
                all_rows.extend(rows)
                print(f"[{i}/{len(prop_urls)}] rows+={len(rows)}  → {u}")
            except Exception as e:
                print(f"[{i}/{len(prop_urls)}] ERROR {u} → {e}")
            time.sleep(args.sleep)
    finally:
        with suppress(Exception):
            prop_driver.quit()

    # 3) DataFrame & amenity one-hot columns (efficient concat)
    df = pd.DataFrame(all_rows)

    def series_list(col):
        return list(df[col]) if col in df.columns else []

    all_labels = set()
    for labels in series_list("_community_amenity_list"):
        if isinstance(labels, list):
            for lab in labels:
                if isinstance(lab, str) and lab.strip():
                    all_labels.add(lab.strip())
    for labels in series_list("_apartment_feature_list"):
        if isinstance(labels, list):
            for lab in labels:
                if isinstance(lab, str) and lab.strip():
                    all_labels.add(lab.strip())

    # Build all amenity columns at once (prevents fragmentation)
    amenity_data = {}
    for lab in sorted(all_labels):
        col = sanitize_amenity_label(lab)
        amenity_data[col] = df.apply(
            lambda r: (
                (isinstance(r.get("_community_amenity_list"), list) and lab in r["_community_amenity_list"])
                or (isinstance(r.get("_apartment_feature_list"), list) and lab in r["_apartment_feature_list"])
            ),
            axis=1
        )
    if amenity_data:
        df = pd.concat([df, pd.DataFrame(amenity_data)], axis=1)
        one_hot_cols = list(amenity_data.keys())
    else:
        one_hot_cols = []

    # Order columns
    core_cols = [
        "property_name", "address", "listing_url",
        "rentLabel_raw", "pricingColumn_raw", "sqftColumn_raw", "detailsLabel_raw",
        "price", "sqft", "beds", "baths",
        "community_amenities_raw", "apartment_features_raw"
    ]
    cols = core_cols + one_hot_cols
    cols = [c for c in cols if c in df.columns]
    df = df.reindex(columns=cols)

    # 4) Save
    xlsx_path = f"{args.out_prefix}_floorplans.xlsx"
    csv_path  = f"{args.out_prefix}_floorplans.csv"
    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nSaved {len(df)} rows → {xlsx_path}\nSaved {len(df)} rows → {csv_path}")

if __name__ == "__main__":
    main()
