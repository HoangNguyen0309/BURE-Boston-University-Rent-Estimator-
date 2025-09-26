# apartments_boston_minimal_amenities.py
# ------------------------------------------------------------
# Apartments.com (Boston, MA) — minimal export + sqft + amenity one-hot + optional aggregation
# Default output: one row per floorplan with:
#   listing_url, price, beds, baths, sqft, <Amenity_... columns as 1/0>
# With --aggregate-per-property: one row per property:
#   listing_url, min_price, max_price, min_beds, max_beds, min_baths, max_baths,
#   min_sqft, max_sqft, <Amenity_... columns as 1/0 (any floorplan has it)>
#
# – Loads each property with headless Selenium (NO clicks)
# – Floorplan selectors: .rentLabel, .detailsLabel, .pricingColumn, .unitLabel.sqftColumn (primary), .sqftColumn (fallback)
# – Amenities ONLY from ".amenitiesSection.amenitiesSectionV2"
# – Parser tries lxml, falls back to html.parser

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

# ---------- helpers
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
        try: return int(m.group(1).replace(",", ""))
        except: return None
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
    # common patterns: "750 Sq Ft", "1,050 sq. ft."
    m = re.search(r"([\d,]+)\s*(sq\s*\.?ft|sf|ft2|ft²|square\s*feet)", text, re.I)
    if m:
        try: return int(m.group(1).replace(",", ""))
        except: return None
    # sometimes just digits in that column
    m2 = re.search(r"^\s*([\d,]{3,})\s*$", text)
    if m2:
        try: return int(m2.group(1).replace(",", ""))
        except: return None
    return None

def get_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")

def safe_amenity_col(name: str) -> str:
    # Create readable, Excel-friendly column names, prefixed to avoid collisions
    s = (name or "").strip()
    s = re.sub(r"\s*[:•\-–]\s*", " ", s)             # normalize separators
    s = re.sub(r"[^\w\s]", " ", s)                   # remove punctuation
    s = re.sub(r"\s+", "_", s).strip("_")            # spaces -> underscores
    if not s: s = "Amenity"
    if not re.match(r"^[A-Za-z_]", s): s = "A_" + s
    return f"Amenity_{s}"

# ---------- selenium driver
def make_driver(headless=True, win_size="1280,1700"):
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
    # block images for speed
    opts.add_argument("--blink-settings=imagesEnabled=false")

    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(45)

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

# ---------- collect listing URLs from search pages
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

# ---------- parse a property page (rendered HTML)
def parse_property_html_minimal(html: str, url: str):
    """
    Return list of dicts with:
      listing_url, price, beds, baths, sqft, community_list (list), features_list (list)
    One row per floorplan (fallback to one row if none).
    """
    soup = get_soup(html)

    detail_nodes = soup.select(".detailsLabel")
    rows = []
    seen = set()
    for det in detail_nodes:
        row = det
        # climb up to a "row-like" ancestor with sibling cells
        for _ in range(4):
            if not row: break
            if row.name in ("tr", "div"):
                if row.select_one(".rentLabel, .pricingColumn, .unitLabel.sqftColumn, .sqftColumn, .detailsLabel"):
                    break
            row = row.parent
        if not row: continue

        rent_el   = row.select_one(".rentLabel")
        price_el  = row.select_one(".pricingColumn")
        sqft_el   = row.select_one(".unitLabel.sqftColumn") or row.select_one(".sqftColumn")

        rent_raw  = rent_el.get_text(" ", strip=True) if rent_el else ""
        price_raw = price_el.get_text(" ", strip=True) if price_el else ""
        sqft_raw  = sqft_el.get_text(" ", strip=True) if sqft_el else ""
        details   = det.get_text(" ", strip=True)

        price_num = parse_price_any(rent_raw) or parse_price_any(price_raw)
        beds = parse_beds(details)
        baths = parse_baths(details)
        sqft = parse_sqft(sqft_raw) or parse_sqft(details)

        sig = (price_num, beds, baths, sqft)
        if sig in seen:
            continue
        seen.add(sig)

        rows.append({
            "listing_url": url,
            "price": price_num,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
        })

    # Amenities ONLY from ".amenitiesSection.amenitiesSectionV2"
    def collect_from_section(section_root):
        items = []
        for li in section_root.select("li"):
            t = li.get_text(" ", strip=True)
            if t:
                items.append(t)
        # dedupe keep order
        out, seen_i = [], set()
        for x in items:
            if x not in seen_i:
                seen_i.add(x)
                out.append(x)
        return out

    community_list = []
    features_list  = []

    for section in soup.select(".amenitiesSection.amenitiesSectionV2"):
        # identify category from a heading inside the section
        title = ""
        with suppress(Exception):
            title_el = section.select_one("h2, h3, h4, [class*='title'], [class*='header']")
            if title_el:
                title = title_el.get_text(" ", strip=True).lower()

        items = collect_from_section(section)
        if "community" in title:
            community_list.extend(items)
        elif "apartment" in title or "features" in title:
            features_list.extend(items)
        else:
            features_list.extend(items)

    # If no floorplans detected, still save one row with amenities
    if not rows:
        rows = [{"listing_url": url, "price": None, "beds": None, "baths": None, "sqft": None}]

    # Attach amenity lists (same for all rows from this property)
    # Keep lists (not strings) so we can one-hot later reliably
    community_list = list(dict.fromkeys(community_list)) if community_list else []
    features_list  = list(dict.fromkeys(features_list))  if features_list  else []
    for r in rows:
        r["_community_list"] = community_list
        r["_features_list"]  = features_list

    return rows

# ---------- load property and parse (no clicks)
def scrape_property_via_selenium(driver, url, wait_sec=18, settle=0.8):
    driver.get(url)
    with suppress(Exception):
        WebDriverWait(driver, wait_sec).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".detailsLabel")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pricingColumn")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".rentLabel")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".unitLabel.sqftColumn")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".amenitiesSection.amenitiesSectionV2")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
            )
        )
    time.sleep(settle)
    html = driver.page_source
    return parse_property_html_minimal(html, url)

# ---------- main
def main():
    ap = argparse.ArgumentParser(description="Apartments.com Boston scraper (minimal + amenity columns + optional aggregation).")
    ap.add_argument("--url", default=SEARCH_URL_DEFAULT, help="Search URL (default: Boston).")
    ap.add_argument("--max-pages", type=int, default=2, help="How many search pages to fetch.")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless.")
    ap.add_argument("--property-timeout", type=int, default=18, help="Seconds to wait for property DOM.")
    ap.add_argument("--sleep", type=float, default=0.3, help="Polite delay between properties.")
    ap.add_argument("--out-prefix", default="apartments_boston_minimal_amenities", help="Output prefix for files.")
    ap.add_argument("--aggregate-per-property", action="store_true", help="Aggregate floorplans to one row per property.")
    args = ap.parse_args()

    # 1) Collect property URLs
    prop_urls = collect_property_urls(args.url, max_pages=args.max_pages, headless=args.headless)
    print(f"Total property URLs: {len(prop_urls)}")

    # 2) One headless driver to scrape properties (no clicks)
    prop_driver = make_driver(headless=args.headless, win_size="1280,1700")

    all_rows = []
    try:
        for i, u in enumerate(prop_urls, 1):
            try:
                rows = scrape_property_via_selenium(prop_driver, u, wait_sec=args.property_timeout, settle=0.8)
                all_rows.extend(rows)
                print(f"[{i}/{len(prop_urls)}] rows+={len(rows)} → {u}")
            except Exception as e:
                print(f"[{i}/{len(prop_urls)}] ERROR {u} → {e}")
            time.sleep(args.sleep)
    finally:
        with suppress(Exception):
            prop_driver.quit()

    # Build DataFrame (keep amenity lists in temp columns)
    df = pd.DataFrame(all_rows, columns=[
        "listing_url", "price", "beds", "baths", "sqft",
        "_community_list", "_features_list"
    ])

    # --- Build amenity one-hot columns efficiently ---
    # Collect all unique amenities across both lists
    all_amens = set()
    for lst_col in ["_community_list", "_features_list"]:
        if lst_col in df.columns:
            for lst in df[lst_col].dropna():
                if isinstance(lst, list):
                    for a in lst:
                        if isinstance(a, str) and a.strip():
                            all_amens.add(a.strip())

    # Map original amenity name -> safe column name
    amen_to_col = {a: safe_amenity_col(a) for a in sorted(all_amens)}

    # Create DataFrame of zeros, then set 1s where present
    amen_df = pd.DataFrame(0, index=df.index, columns=list(amen_to_col.values()))
    for idx, row in df.iterrows():
        present = set()
        for lst_col in ["_community_list", "_features_list"]:
            lst = row.get(lst_col)
            if isinstance(lst, list):
                for a in lst:
                    if isinstance(a, str) and a.strip():
                        present.add(a.strip())
        for a in present:
            amen_col = amen_to_col.get(a)
            if amen_col is not None:
                amen_df.at[idx, amen_col] = 1

    # Combine core fields with amenity one-hots
    df_core = df[["listing_url", "price", "beds", "baths", "sqft"]].copy()
    full_df = pd.concat([df_core, amen_df], axis=1)

    if args.aggregate_per_property:
        # For numeric fields, take min/max; for amenity flags, take max (any plan has it -> 1)
        agg_spec = {
            "price": ["min", "max"],
            "beds": ["min", "max"],
            "baths": ["min", "max"],
            "sqft": ["min", "max"],
        }
        # Build dict for amenities
        for col in amen_df.columns:
            agg_spec[col] = "max"

        grouped = full_df.groupby("listing_url", dropna=False).agg(agg_spec)

        # Flatten multiindex columns for the numeric min/max fields
        grouped.columns = [
            (f"{c[0]}_{c[1]}" if isinstance(c, tuple) else c)
            for c in grouped.columns.to_flat_index()
        ]
        # Rename fields
        rename_map = {
            "price_min": "min_price", "price_max": "max_price",
            "beds_min": "min_beds",   "beds_max": "max_beds",
            "baths_min": "min_baths", "baths_max": "max_baths",
            "sqft_min": "min_sqft",   "sqft_max": "max_sqft",
        }
        grouped = grouped.rename(columns=rename_map).reset_index()
        out_df = grouped
        xlsx_path = f"{args.out_prefix}_aggregated.xlsx"
        csv_path  = f"{args.out_prefix}_aggregated.csv"
    else:
        out_df = full_df
        xlsx_path = f"{args.out_prefix}.xlsx"
        csv_path  = f"{args.out_prefix}.csv"

    out_df.to_excel(xlsx_path, index=False)
    out_df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nSaved {len(out_df)} rows → {xlsx_path}\nSaved {len(out_df)} rows → {csv_path}")

if __name__ == "__main__":
    main()
