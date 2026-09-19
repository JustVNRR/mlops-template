"""
Demonstration dataset.

This is the only module of the template that knows a specific domain: which
columns exist, what they mean and how the target is built. Everything
downstream — cleaning, preprocessing, training, the API contract — is driven by
the constants declared in `params.py`, so reorienting the template means
rewriting this file and the `DATA SCHEMA` block, and nothing else.

Keeping the domain confined here is what makes the rest of the code reusable:
`data.py` loads, cleans and persists without knowing what a row represents.
"""

import numpy as np
import pandas as pd

from package_folder.params import DATA_SIZE, TARGET_COLUMN

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _n_samples_from_data_size() -> int:
    """Translate DATA_SIZE ('1k', '200k', 'all', ...) into a row count."""
    if not DATA_SIZE:
        return 2_000

    size = str(DATA_SIZE).strip().lower()
    if size == "all":
        return 50_000
    if size.endswith("k"):
        return int(float(size[:-1]) * 1_000)
    return int(size)


def generate_demo_data(n_samples: int | None = None, seed: int = 42) -> pd.DataFrame:
    """
    Build the synthetic dataset the template ships with.

    The target is a linear combination of the features plus gaussian noise, so
    the reference model reaches a stable MAE and consecutive runs stay
    comparable. The coefficients are known, which lets the tests assert that the
    model recovers the actual relationship rather than merely returning a float.

    Reproducible: the same seed yields the same frame.

    To plug in your own data, replace this function and update the `DATA SCHEMA`
    block of `params.py`.
    """
    n_samples = n_samples if n_samples is not None else _n_samples_from_data_size()
    rng = np.random.default_rng(seed)  # reproducible: same data on every run

    distance_km = rng.uniform(0.5, 30.0, n_samples)
    passengers = rng.integers(1, 5, n_samples)
    hour = rng.integers(0, 24, n_samples)
    day_of_week = rng.choice(DAY_NAMES, n_samples)

    is_night = (hour < 6) | (hour >= 22)
    is_weekend = np.isin(day_of_week, ["saturday", "sunday"])

    fare = (
        3.0  # base fare
        + 1.8 * distance_km  # per-kilometre rate
        + 0.4 * passengers  # passenger surcharge
        + 2.5 * is_night  # night surcharge
        + 1.5 * is_weekend  # weekend surcharge
        + rng.normal(0, 1.5, n_samples)  # irreducible noise
    )

    return pd.DataFrame(
        {
            "distance_km": distance_km,
            "passengers": passengers,
            "hour": hour,
            "day_of_week": day_of_week,
            TARGET_COLUMN: fare,
        }
    )
