"""
Feature definitions for the risk model. Keeping this in one place means
training and inference can never quietly drift out of sync with each other.
"""
import numpy as np

FEATURE_NAMES = ["rainfall_mm_24h", "soil_moisture_pct", "slope_angle_deg", "historical_landslide_count"]

# Rough normalization ranges — tune these once real data is available.
RAINFALL_CAP = 180.0        # mm in 24h considered "extreme" for the region
SOIL_MOISTURE_CAP = 100.0   # %
SLOPE_CAP = 60.0            # degrees
HISTORY_CAP = 10.0          # landslide incidents on record


def build_features(rainfall_mm_24h: float, soil_moisture_pct: float,
                    slope_angle_deg: float, historical_landslide_count: float) -> np.ndarray:
    """Returns a single feature row, shape (1, 4), in FEATURE_NAMES order."""
    return np.array([[
        rainfall_mm_24h,
        soil_moisture_pct,
        slope_angle_deg,
        historical_landslide_count,
    ]], dtype=float)
