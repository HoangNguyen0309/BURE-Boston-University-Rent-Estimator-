# linear_regression_selected_features_avg_r2.py
# -------------------------------------------------------------
# Repeated train/test evaluation (100 runs) for Linear Regression
# predicting 'price' from selected features.
# -------------------------------------------------------------

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# === Load dataset ===
csv_file = "apartments_boston_allston_minimal_amenities.csv"
df = pd.read_csv(csv_file).dropna()

# Ignore first two columns
df = df.iloc[:, 2:]

# === Selected features ===
selected_features = [
    "baths","beds","sqft",
    "Amenity_Concierge","Amenity_A_24_Hour_Access","Amenity_Washer_Dryer",
    "Amenity_Fitness_Center","Amenity_Conference_Rooms",
    "Amenity_Island_Kitchen","Amenity_Walk_In_Closets","Amenity_Package_Service",
    "Amenity_On_Site_Retail","Amenity_Air_Conditioning","Amenity_Public_Transportation",
    "Amenity_Bicycle_Storage","Amenity_Elevator","Amenity_EV_Charging",
    "Amenity_Recycling","Amenity_Views","Amenity_Furnished_Units_Available"
]

missing = [c for c in selected_features if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

X = df[selected_features]
y = df["price"]

# === Repeat 100 random splits and collect R² ===
r2_scores = []
for seed in range(100):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, shuffle=True
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2_scores.append(r2_score(y_test, y_pred))

r2_scores = np.array(r2_scores)
print(f"Runs: {len(r2_scores)}")
print(f"Average R²: {r2_scores.mean():.4f}")
print(f"Std Dev R²: {r2_scores.std(ddof=1):.4f}")
print(f"Min/Max R²: {r2_scores.min():.4f} / {r2_scores.max():.4f}")
