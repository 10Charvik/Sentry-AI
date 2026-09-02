"""
First-pass landslide risk model.

There's no real historical landslide dataset wired in yet, so this generates
a *synthetic* training set from a domain heuristic (more rain, wetter soil,
steeper slopes, and more past incidents => higher landslide probability),
adds noise, and fits a plain logistic regression on top of it.

This is deliberately simple: the point of a first pass is a real, working,
swappable prediction step in the pipeline — not a state-of-the-art model.
Once real rainfall/soil-moisture/slope data and actual historical landslide
records exist for the region, replace generate_synthetic_dataset() with a
loader for that data and retrain the same way.

Usage:
    python -m app.ml.train
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score
import joblib
from pathlib import Path

from app.ml.features import (
    FEATURE_NAMES, RAINFALL_CAP, SOIL_MOISTURE_CAP, SLOPE_CAP, HISTORY_CAP,
)

MODEL_PATH = Path(__file__).parent / "risk_model.joblib"

RNG = np.random.default_rng(42)


def generate_synthetic_dataset(n: int = 4000):
    """Synthesizes (features, landslide_occurred) pairs from a hand-tuned
    domain heuristic. Replace this with real historical records + real
    weather/sensor readings once available — the training code below doesn't
    need to change, only this function.
    """
    rainfall = RNG.uniform(0, RAINFALL_CAP, n)
    soil_moisture = RNG.uniform(10, SOIL_MOISTURE_CAP, n)
    slope = RNG.uniform(10, SLOPE_CAP, n)
    history = RNG.poisson(1.5, n).clip(0, HISTORY_CAP)

    # Normalized 0-1 heuristic weights — rain and soil moisture matter most,
    # slope next, history as a smaller prior.
    latent = (
        3.2 * (rainfall / RAINFALL_CAP)
        + 2.6 * (soil_moisture / SOIL_MOISTURE_CAP)
        + 2.0 * (slope / SLOPE_CAP)
        + 1.0 * (history / HISTORY_CAP)
        - 3.4
        + RNG.normal(0, 0.4, n)  # noise so it's not a trivial linear boundary
    )
    probability = 1 / (1 + np.exp(-latent))
    occurred = RNG.binomial(1, probability)

    X = np.column_stack([rainfall, soil_moisture, slope, history])
    y = occurred
    return X, y


def train():
    print("Generating synthetic training data...")
    X, y = generate_synthetic_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000)),
    ])

    print("Training logistic regression...")
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    preds = pipeline.predict(X_test)
    auc = roc_auc_score(y_test, proba)
    acc = accuracy_score(y_test, preds)
    print(f"Held-out AUC: {auc:.3f}  |  Accuracy: {acc:.3f}  (on synthetic data — sanity check only)")

    coefs = pipeline.named_steps["clf"].coef_[0]
    print("Feature weights (standardized):")
    for name, coef in zip(FEATURE_NAMES, coefs):
        print(f"  {name:28s} {coef:+.3f}")

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    train()
