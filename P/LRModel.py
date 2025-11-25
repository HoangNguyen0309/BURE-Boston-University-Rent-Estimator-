# linear_regression_selected_features_avg_r2.py
# -------------------------------------------------------------
# Trains + evaluates, then saves final LinearRegression model.
# -------------------------------------------------------------

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from joblib import dump

# === Load dataset ===
csv_file = "apartments_boston_allston_minimal_amenities.csv"
df = pd.read_csv(csv_file).dropna()

# Ignore first two columns
df = df.iloc[:, 2:]

# Ensure target exists
if "price" not in df.columns:
    raise ValueError("Column 'price' not found after slicing (df.iloc[:, 2:]).")

# === Selected features ===
selected_features = [
    "baths",
    "beds",
    "sqft",
    "Amenity_Concierge",
    "Amenity_A_24_Hour_Access",
    "Amenity_Washer_Dryer",
    "Amenity_Fitness_Center",
    "Amenity_Double_Vanities",
    "Amenity_Conference_Rooms",
    "Amenity_Island_Kitchen",
    "Amenity_Walk_In_Closets",
    "Amenity_Package_Service",
    "Amenity_On_Site_Retail",
    "Amenity_Air_Conditioning",
    "Amenity_Public_Transportation",
    "Amenity_Bicycle_Storage",
    "Amenity_Elevator",
    "Amenity_EV_Charging",
    "Amenity_Recycling",
    "Amenity_Views",
]

missing = [c for c in selected_features if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

X = df[selected_features]
y = df["price"]

# === Repeat 100 random splits and collect R² ===
train_r2_scores = []
test_r2_scores = []

for seed in range(100):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, shuffle=True
    )
    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)

    train_r2_scores.append(train_r2)
    test_r2_scores.append(test_r2)

train_r2_scores = np.array(train_r2_scores)
test_r2_scores = np.array(test_r2_scores)

def summarize(name, arr):
    print(f"{name} R² — Runs: {len(arr)}")
    print(f"  Average: {arr.mean():.4f}")
    print(f"  Std Dev: {arr.std(ddof=1):.4f}")
    print(f"  Min/Max: {arr.min():.4f} / {arr.max():.4f}")

print("========================================")
summarize("Train", train_r2_scores)
print("----------------------------------------")
summarize("Test", test_r2_scores)
print("========================================")

gap = train_r2_scores - test_r2_scores
print(f"Avg (Train - Test) gap: {gap.mean():.4f}")

# === Train final model on ALL data and save it ===
final_model = LinearRegression()
final_model.fit(X, y)

bundle = {
    "model": final_model,
    "features": selected_features,
}

# You’ll copy this file into your Django project directory (next step).
model_path = "allston_linear_model.joblib"
dump(bundle, model_path)
print(f"Saved final model + features to: {model_path}")
