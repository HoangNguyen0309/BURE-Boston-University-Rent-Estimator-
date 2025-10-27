# price_quick_plots.py
# Minimal charts: price vs every other column in apartments_boston_minimal_amenities.csv

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "./apartments_boston_fenway_minimal_amenities.csv"
TARGET = "price"
OUTDIR = Path("charts")

def is_binary(series: pd.Series) -> bool:
    vals = pd.unique(series.dropna())
    if len(vals) == 0:
        return False
    # treat {0,1} / booleans as binary
    return set(np.unique(vals)).issubset({0, 1, True, False})

def plot_numeric_scatter(feature: str, x: pd.Series, y: pd.Series, outpath: Path):
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(df) < 3 or df["x"].std() == 0 or df["y"].std() == 0:
        return False
    plt.figure()
    plt.scatter(df["x"], df["y"], alpha=0.6)
    # simple best-fit line
    try:
        m, b = np.polyfit(df["x"], df["y"], 1)
        xs = np.linspace(df["x"].min(), df["x"].max(), 100)
        plt.plot(xs, m*xs + b)
    except Exception:
        pass
    plt.xlabel(feature)
    plt.ylabel(TARGET)
    plt.title(f"{TARGET} vs {feature}")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath.as_posix(), bbox_inches="tight", dpi=150)
    plt.close()
    return True

def plot_binary_box(feature: str, x: pd.Series, y: pd.Series, outpath: Path):
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    if df["x"].nunique() < 2:
        return False
    groups = [df.loc[df["x"] == v, "y"] for v in sorted(df["x"].dropna().unique())[:2]]
    plt.figure()
    plt.boxplot(groups, labels=["0","1"][:len(groups)], showmeans=True)
    plt.xlabel(f"{feature} (0/1)")
    plt.ylabel(TARGET)
    plt.title(f"{TARGET} by {feature}")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath.as_posix(), bbox_inches="tight", dpi=150)
    plt.close()
    return True

def main():
    if not Path(CSV_PATH).exists():
        raise SystemExit(f"CSV not found: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    if TARGET not in df.columns:
        raise SystemExit(f"Target column '{TARGET}' not in CSV.")
    y = df[TARGET]

    OUTDIR.mkdir(parents=True, exist_ok=True)
    saved = 0

    for col in df.columns:
        if col == TARGET:
            continue
        s = df[col]

        # skip empty/constant columns
        if s.dropna().empty or s.dropna().nunique() <= 1:
            continue

        outpath = OUTDIR / f"{TARGET}_vs_{col}.png"

        if pd.api.types.is_numeric_dtype(s):
            if is_binary(s):
                ok = plot_binary_box(col, s.astype(float), y, outpath)
            else:
                ok = plot_numeric_scatter(col, s.astype(float), y, outpath)
        else:
            # very simple: skip high-cardinality text columns to keep it minimal
            if s.dropna().nunique() <= 12:
                # quick categorical boxplot
                df_cat = pd.DataFrame({"x": s.astype("string"), "y": y}).dropna()
                if df_cat["x"].nunique() >= 2:
                    counts = df_cat["x"].value_counts().head(12)
                    keep = counts.index
                    data = [df_cat.loc[df_cat["x"] == k, "y"] for k in keep]
                    plt.figure(figsize=(max(6, len(keep) * 0.8), 4.8))
                    plt.boxplot(data, labels=list(keep), showmeans=True)
                    plt.xticks(rotation=30, ha="right")
                    plt.xlabel(col)
                    plt.ylabel(TARGET)
                    plt.title(f"{TARGET} by {col} (top {len(keep)})")
                    plt.savefig(outpath.as_posix(), bbox_inches="tight", dpi=150)
                    plt.close()
                    ok = True
                else:
                    ok = False
            else:
                ok = False

        if ok:
            print(f"Saved {outpath}")
            saved += 1

    if saved == 0:
        print("No charts were generated (columns may be non-numeric or constant).")
    else:
        print(f"\nDone. Charts saved in: {OUTDIR.resolve()}")

if __name__ == "__main__":
    main()
