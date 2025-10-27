# price_correlations.py
import re
import math
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CSV_NAME = "apartments_boston_fenway_minimal_amenities.csv"  # must be in the same folder

# --- Helpers ---------------------------------------------------------------
def parse_price_cell(cell: str) -> float | None:
    """
    Robustly parse a price cell into a single float (USD).
    Handles examples like:
      "$2,345", "$2,345+", "$2,345/mo", "$2,100 - $2,600", "2100-2600", "2100 to 2600"
    Returns the average for ranges, None if nothing numeric is found.
    """
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return None
    s = str(cell)

    # Normalize separators
    s = s.replace("to", "-").replace("–", "-").replace("—", "-")

    # If it's a range, average endpoints
    m = re.search(r"([$\s]*[\d,]+(?:\.\d+)?)[^\d]+([$\s]*[\d,]+(?:\.\d+)?)", s)
    if m:
        a = float(re.sub(r"[^\d.]", "", m.group(1)))
        b = float(re.sub(r"[^\d.]", "", m.group(2)))
        return (a + b) / 2.0

    # Single value case: strip everything non-numeric (keep dot)
    digits = re.sub(r"[^\d.]", "", s)
    return float(digits) if digits else None

def choose_price_column(df: pd.DataFrame) -> str:
    """
    Try common price column names. Returns the chosen column name or raises if not found.
    """
    candidates = ["price", "min_price", "max_price"]
    for c in candidates:
        if c in df.columns:
            return c
    # Fallback: anything containing 'price'
    for c in df.columns:
        if "price" in c.lower():
            return c
    raise ValueError(
        "No price-like column found. Looked for 'price', 'min_price', 'max_price', "
        "or any column containing 'price'."
    )

# --- Load & clean ----------------------------------------------------------
path = Path("apartments_boston_minimal_amenities.csv")
if not path.exists():
    raise FileNotFoundError(f"CSV not found at {path.resolve()}")

df = pd.read_csv(path)
df.columns = df.columns.str.strip()  # cleanup accidental trailing spaces

price_col = choose_price_column(df)

# Build a clean numeric price series
price_numeric = df[price_col].apply(parse_price_cell)
df_clean = df.copy()
df_clean["__PRICE__"] = pd.to_numeric(price_numeric, errors="coerce")
df_clean = df_clean.dropna(subset=["__PRICE__"])

# Keep only numeric columns for correlation (including one-hot amenity columns)
numeric_df = df_clean.select_dtypes(include=["number"])

# If price isn't already numeric in numeric_df, ensure we align on the cleaned price
# (use the cleaned __PRICE__ column as the reference price series)
price_series = df_clean["__PRICE__"]

# --- Correlations ----------------------------------------------------------
# Corr of each numeric column vs price
corr = numeric_df.corrwith(price_series)

# Drop the correlation of price with itself if price was already among numeric_df
if "__PRICE__" in corr.index:
    corr = corr.drop("__PRICE__")

corr = corr.sort_values(ascending=False)

# --- Output: table + plot --------------------------------------------------
print("\nPearson Correlation Coefficients (Price vs Other Numeric Columns):\n")
print(corr.to_frame("PCC"))

# Optional: save to CSV
corr.to_csv("price_correlations.csv", header=["PCC"])
print("\nSaved table to price_correlations.csv")

# Plot (single chart, default matplotlib style/colors)
plt.figure(figsize=(11, 6))
corr.plot(kind="bar")
plt.title("Pearson Correlation (Price vs Other Attributes)")
plt.ylabel("Correlation Coefficient (PCC)")
plt.xlabel("Attributes")
plt.grid(True)
plt.tight_layout()
plt.show()
