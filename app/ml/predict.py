"""
Loads the trained pipeline once and exposes a single predict_risk() call.
Import this from routers rather than touching joblib/model files directly.
"""
from pathlib import Path
from functools import lru_cache

import joblib

from app.ml.features import build_features

MODEL_PATH = Path(__file__).parent / "risk_model.joblib"


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. Run `python -m app.ml.train` first."
        )
    return joblib.load(MODEL_PATH)


def predict_risk(rainfall_mm_24h: float, soil_moisture_pct: float,
                  slope_angle_deg: float, historical_landslide_count: float) -> float:
    """Returns a landslide risk probability in [0, 1]."""
    model = _load_model()
    X = build_features(rainfall_mm_24h, soil_moisture_pct, slope_angle_deg, historical_landslide_count)
    return float(model.predict_proba(X)[0, 1])
