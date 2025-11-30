# bure_ml/prediction.py

import os
import numpy as np
from django.conf import settings
from joblib import load


MODEL_PATH = os.path.join(settings.BASE_DIR, "ml_models", "allston_linear_model.joblib")

# Load once at import (thread-safe for reads in sklearn)
_bundle = load(MODEL_PATH)
_model = _bundle["model"]
_FEATURES = _bundle["features"]


def predict_price(feature_dict: dict) -> float:
    """
    feature_dict: mapping from feature name -> value.
      Any missing feature is assumed to be 0.

    Example:
      {
        "baths": 1,
        "beds": 2,
        "sqft": 700,
        "Amenity_Concierge": 1,
        ...
      }
    """
    x = np.zeros(len(_FEATURES), dtype=float)
    for i, fname in enumerate(_FEATURES):
        x[i] = float(feature_dict.get(fname, 0.0))

    # sklearn expects shape (1, n_features)
    price_pred = _model.predict(x.reshape(1, -1))[0]
    return float(price_pred)