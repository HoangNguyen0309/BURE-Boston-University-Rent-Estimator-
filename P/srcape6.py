# apartments_boston_scraper.py
# ------------------------------------------------------------
# Scrapes Apartments.com (Boston, MA):
# - Follows numbered pagination from the search page
# - Visits each property detail page
# - Extracts per-floorplan fields: rentLabel, detailsLabel, pricingColumn, sqftColumn
# - Parses beds/baths/sqft, keeps raw strings too
# - Scrapes "Community Amenities" and "Apartment Features"
# - One-hot encodes each amenity label
#
# Install:
#   pip install --upgrade pip
#   pip install undetected-chromedriver selenium pandas openpyxl
#
# Run (watch the browser the first time):
#   python apartments_boston_scraper.py --headless   # (omit --headless for visible)
#
# Notes:
# - Be polite; do not hammer the site. Consider lowering max_pages for testing.
# - If Apartments.com layout changes, update CSS/XPath selectors below.

import re
import time
import argparse
from urllib.parse import urljoin

import pandas as pd

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SEARCH_URL_DEFAULT = "https://www.apartments.com/boston-ma/"
APARTMENTS_DOMAIN = "apartments.com"

# Detail page URL heuristic: ".../something-boston-ma/<hash>/" or similar
DETAIL_RE = re.compile(r"https?://(www\.)?apartments\.com/.+-boston-ma/[^/]+/?$", re.I)

# -----------------------------
# Utilities
# -----------------------------
def safe_text(el):
    try:
        return el.text.strip()
    except Exception:
        return ""

def try_find(driver, by, val, all_=False):
    try:
        return (driver.find_elements if all_ else driver.find_element)(by, val)
    except Exception:
        return [] if all_ else None

def click_if_present(driver, css):
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, css)
        for b in btns:
            if b.is_displayed() and b.is_enabled():
                try:
                    b.click()
                    time.sleep(0.4)
                except:
                    pass
    except:
        pass

def parse_beds(details_text):
    """
    detailsLabel often contains "1 Bed", "2 Beds", "Studio", or ranges like "1-2 Beds".
    """
    if not details_text:
        return None
    txt = details_text.lower()
    if "studio" in txt:
        return 0
    # prefer the first number in a beds context
    m = re.search(r"(\d+(\.\d+)?)\s*-\s*(\d+(\.\d+)?)\s*beds?", txt)
    if m:
        # take the lower bound for a single row
        try:
            v = float(m.group(1))
            return int(v) if v.is_integer() else v
        except:
            pass
    m = re.search(r"(\d+(\.\d+)?)\s*beds?", txt)
    if m:
        try:
            v = float(m.group(1))
            return int(v) if v.is_integer() else v
        except:
            pass
    return None

def parse_baths(details_text):
    """
    detailsLabel may also contain baths, including half baths and ranges.
    """
    if not details_text:
        return None
    txt = details_text.lower()
    m = re.search(r"(\d+(\.\d+)?)\s*-\s*(\d+(\.\d+)?)\s*baths?", txt)
    if m:
        try:
            v = float(m.group(1))
            return int(v) if v.is_integer() else v
        except:
            pass
    m = re.search(r"(\d+(\.\d+)?)\s*baths?", txt)
    if m:
        try:
            v = float(m.group(1))
            return int(v) if v.is_integer() else v
        except:
            pass
    return None

def parse_price_any(text):
    if not text:
        return None
    # find first $1234 or $1,234
    m = re.search(r"\$\s*([\d,]+)", text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except:
            return None
    return None

def parse_sqft(text):
    if not text:
        return None
    m = re.search(r"([\d,]+)\s*(sq\s*\.?ft|sf|ft2|ft²|square\s*feet)", text, re.I)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except:
            return None
    return None

def sanitize_amenity_label(label: str) -> str:
    s = (label or "").strip()
    s = re.sub(r"[\s/,+()\-]+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "Amenity"
    if not re.match(r"^[A-Za-z_]", s):
        s = "A_" + s
    return f"Amenity_{s}"

# -----------------------------
# Collect listing URLs via pagination
# -----------------------------
def collect_listing_urls(search_url, max_pages=20, headless=False):
    """
    Follows numeric pagination (2,3,...) from the Boston search page
    and collects property detail URLs.
    """
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1700")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    detail_urls = set()
    visited_pages = set()

    try:
        page_queue = [search_url]
        pages_processed = 0
        while page_queue and pages_processed < max_pages:
            url = page_queue.pop(0)
            if url in visited_pages:
                continue

            print(f"[Page {pages_processed+1}] {url}")
            driver.get(url)

            # Cookie banners / consent (best-effort)
            for sel in [
                "#onetrust-accept-btn-handler",
                "button[aria-label*='Accept']",
                "button.cookie-accept",
                "button#truste-consent-button"
            ]:
                click_if_present(driver, sel)

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]"))
                )
            except TimeoutException:
                pass

            # Harvest detail links on this page
            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            before = len(detail_urls)
            for a in anchors:
                href = a.get_attribute("href") or ""
                if DETAIL_RE.search(href):
                    detail_urls.add(href)
            print(f"  +{len(detail_urls) - before} detail URLs (total {len(detail_urls)})")

            # Queue next numeric pages
            next_candidates = []
            # Common pagination anchors include "?page=2", rel="next", or numeric link text
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    txt = (a.text or "").strip()
                except StaleElementReferenceException:
                    continue
                if not href:
                    continue
                is_numeric = bool(re.fullmatch(r"\d+", txt))
                is_next = (a.get_attribute("rel") or "").lower() == "next"
                is_page_qs = "page=" in href
                if (is_numeric or is_next or is_page_qs) and href.startswith("https://www.apartments.com/"):
                    next_candidates.append(href)

            # keep order, avoid duplicates
            for nxt in next_candidates:
                if nxt not in visited_pages and nxt not in page_queue:
                    page_queue.append(nxt)

            visited_pages.add(url)
            pages_processed += 1
            time.sleep(0.8)  # be polite

        print(f"Collected {len(detail_urls)} unique detail URLs across {len(visited_pages)} pages")
        return sorted(detail_urls)
    finally:
        driver.quit()

# -----------------------------
# Scrape a single property page
# -----------------------------
def scrape_property(driver, url):
    """
    On a property detail page, gather:
    - property_name, address
    - floorplan rows: rentLabel, detailsLabel (beds/baths), pricingColumn, sqftColumn
    - amenities: "Community Amenities", "Apartment Features"
    Returns a list of dicts (one per floorplan row; at least one row).
    """
    rows = []
    driver.get(url)

    try:
        WebDriverWait(driver, 25).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='PropertyName']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rentLabel'], .rentLabel"))
            )
        )
    except TimeoutException:
        pass

    # Property name / address (best-effort)
    prop_name = ""
    for sel in ["h1", "[data-testid='propertyName']", "[class*='PropertyName']"]:
        el = try_find(driver, By.CSS_SELECTOR, sel)
        if el:
            prop_name = safe_text(el)
            if prop_name:
                break

    address = ""
    for sel in ["[data-testid='property-address']", "[class*='Address']", "address", "[itemprop='address']"]:
        el = try_find(driver, By.CSS_SELECTOR, sel)
        if el:
            address = safe_text(el)
            if address:
                break

    # Expand any “show more” buttons that might hide plan rows or amenities
    for sel in [
        "button[aria-expanded='false']",
        "button[aria-label*='more']",
        "button:contains('More')"
    ]:
        click_if_present(driver, sel)

    time.sleep(0.3)

    # ---- Floorplan rows ----
    # Apartments.com typically has a grid/table of floorplans
    # The user gave these class hints: rentLabel, detailsLabel, pricingColumn, sqftColumn
    plan_containers = try_find(driver, By.CSS_SELECTOR, "[class*='pricingGrid'], [data-testid='pricingGrid']", all_=True)
    if not plan_containers:
        # Fall back to scanning common row containers
        plan_containers = try_find(driver, By.CSS_SELECTOR, "[class*='pricing'], [class*='floorplan']", all_=True)

    # Flatten to a list of candidate rows
    candidate_rows = []
    for cont in plan_containers:
        try:
            # Attempt to capture any direct rows/cards inside
            rows_in = cont.find_elements(By.CSS_SELECTOR, "[class*='row'], [class*='GridRow'], [class*='card'], .pricingColumn, .sqftColumn, .detailsLabel")
            candidate_rows.extend(rows_in if rows_in else [cont])
        except Exception:
            continue

    # If nothing obvious found, just look across the page for the individual columns
    if not candidate_rows:
        candidate_rows = driver.find_elements(By.CSS_SELECTOR, ".rentLabel, .detailsLabel, .pricingColumn, .sqftColumn")

    # For each *visual row*, read the four fields if present
    # We'll try to group by nearest shared parent row when possible
    seen = set()
    for row_el in candidate_rows:
        try:
            # Identify per-row cells
            rent_el = None
            det_el  = None
            price_el= None
            sqft_el = None

            # Try to scope within the row element first
            for sel, var in [
                (".rentLabel", "rent_el"),
                (".detailsLabel", "det_el"),
                (".pricingColumn", "price_el"),
                (".sqftColumn", "sqft_el"),
            ]:
                _els = row_el.find_elements(By.CSS_SELECTOR, sel)
                if _els:
                    if var == "rent_el":   rent_el = _els[0]
                    if var == "det_el":    det_el  = _els[0]
                    if var == "price_el":  price_el= _els[0]
                    if var == "sqft_el":   sqft_el = _els[0]

            # If a row doesn't carry enough info, skip it
            if not any([rent_el, det_el, price_el, sqft_el]):
                continue

            rent_raw  = safe_text(rent_el)   if rent_el  else ""
            details   = safe_text(det_el)    if det_el   else ""
            price_raw = safe_text(price_el)  if price_el else ""
            sqft_raw  = safe_text(sqft_el)   if sqft_el  else ""

            # Make a simple signature to dedupe obvious duplicates
            sig = (rent_raw, details, price_raw, sqft_raw)
            if sig in seen:
                continue
            seen.add(sig)

            beds = parse_beds(details)
            baths = parse_baths(details)
            price_num = parse_price_any(rent_raw) or parse_price_any(price_raw)
            sqft_num = parse_sqft(sqft_raw)

            rows.append({
                "property_name": prop_name or None,
                "address": address or None,
                "listing_url": url,
                # floorplan-level fields
                "rentLabel_raw": rent_raw or None,
                "detailsLabel_raw": details or None,
                "pricingColumn_raw": price_raw or None,
                "sqftColumn_raw": sqft_raw or None,
                # parsed numbers
                "beds": beds,
                "baths": baths,
                "price": price_num,
                "sqft": sqft_num,
            })
        except Exception:
            continue

    # Ensure at least one row even if no table parsed (so we still capture amenities)
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

    # ---- Amenities ----
    # Strategy: find headings that contain "Community Amenities" and "Apartment Features"
    def collect_amenities_by_heading(heading_text):
        items = []
        # Try common heading tags that contain the phrase
        for tag in ["h2", "h3", "h4", "div", "span"]:
            xpath = f".//{tag}[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{heading_text.lower()}')]"
            try:
                heads = driver.find_elements(By.XPATH, xpath)
            except Exception:
                heads = []
            for h in heads:
                try:
                    # The amenities are usually in the sibling/parent containers as <li> items
                    parent = h.find_element(By.XPATH, "./ancestor-or-self::*[position()=1]")
                except Exception:
                    parent = None

                # Search nearby lists
                containers = []
                if parent:
                    try:
                        containers += parent.find_elements(By.XPATH, ".//ul|.//div")
                    except Exception:
                        pass

                # Collect <li> texts within containers
                for c in containers:
                    try:
                        lis = c.find_elements(By.TAG_NAME, "li")
                    except Exception:
                        lis = []
                    for li in lis:
                        t = safe_text(li)
                        if t and t.lower() != heading_text.lower():
                            items.append(t)

        # De-duplicate while preserving order
        seen_i = set()
        out = []
        for x in items:
            if x not in seen_i:
                seen_i.add(x)
                out.append(x)
        return out

    community_amenities = collect_amenities_by_heading("community amenities")
    apartment_features  = collect_amenities_by_heading("apartment features")

    # Attach amenities to each row for this property
    for r in rows:
        r["community_amenities_raw"] = "; ".join(community_amenities) if community_amenities else None
        r["apartment_features_raw"]  = "; ".join(apartment_features)  if apartment_features  else None
        r["_community_amenity_list"] = community_amenities
        r["_apartment_feature_list"] = apartment_features

    return rows

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Apartments.com Boston scraper (per-floorplan + amenities).")
    ap.add_argument("--url", default=SEARCH_URL_DEFAULT, help="Search URL (default: Boston, MA).")
    ap.add_argument("--headless", action="store_true", help="Run Chrome headless.")
    ap.add_argument("--max-pages", type=int, default=20, help="Max search pages to follow.")
    ap.add_argument("--max-urls", type=int, default=None, help="Limit property URLs for a quick test.")
    ap.add_argument("--out-prefix", default="apartments_boston", help="Output file prefix.")
    args = ap.parse_args()

    # 1) Collect property URLs
    urls = collect_listing_urls(args.url, max_pages=args.max_pages, headless=args.headless)
    if args.max_urls:
        urls = urls[:args.max_urls]
    print(f"Total unique property URLs: {len(urls)}")

    # 2) Scrape properties (reusing a single driver)
    opts = uc.ChromeOptions()
    if args.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1700")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)

    all_rows = []
    try:
        for i, u in enumerate(urls, 1):
            try:
                rows = scrape_property(driver, u)
                all_rows.extend(rows)
                print(f"[{i}/{len(urls)}] {rows[0].get('property_name') or 'Property'} "
                      f"| floorplans: {len(rows)}")
                time.sleep(0.5)  # be polite
            except Exception as e:
                print(f"Failed: {u} -> {e}")
    finally:
        driver.quit()

    df = pd.DataFrame(all_rows)

    # Build amenity one-hot columns (Community + Apartment Features)
    all_labels = set()
    for col in ["_community_amenity_list", "_apartment_feature_list"]:
        for labels in df.get(col, []).tolist():
            if isinstance(labels, list):
                for lab in labels:
                    if isinstance(lab, str) and lab.strip():
                        all_labels.add(lab.strip())

    one_hot_cols = []
    for lab in sorted(all_labels):
        col = sanitize_amenity_label(lab)
        one_hot_cols.append(col)
        def has_label(lst):
            if not isinstance(lst, list):
                return False
            return any((isinstance(x, str) and x.strip() == lab) for x in lst)
        df[col] = df.apply(
            lambda r: has_label(r.get("_community_amenity_list", [])) or has_label(r.get("_apartment_feature_list", [])),
            axis=1
        )

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

    # Save
    xlsx_path = f"{args.out_prefix}_floorplans.xlsx"
    csv_path  = f"{args.out_prefix}_floorplans.csv"
    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nWrote {len(df)} floorplan rows to:\n - {xlsx_path}\n - {csv_path}")
    print(f"Added {len(one_hot_cols)} amenity one-hot columns.")

if __name__ == "__main__":
    main()
