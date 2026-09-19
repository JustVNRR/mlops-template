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

# Parameters of the demonstration target.
#
# They are deliberately KNOWN and exposed: the tests assert that the model
# recovers the relationship, rather than merely that it returns a float. That
# is the whole advantage of a documented synthetic dataset over a random one.
#
# ⚠️ The keys of NUMERIC_COEFFICIENTS must match the columns built below.
NUMERIC_COEFFICIENTS = {
    "numeric_feature_1": 1.8,
    "numeric_feature_2": 0.4,
    "numeric_feature_3": 0.05,
}

# One effect per category of CATEGORICAL_FEATURES. The values are arbitrary;
# what matters is that they differ, so the feature carries real signal.
CATEGORY_EFFECTS = {"a": 0.0, "b": 1.5, "c": -1.2, "d": 2.4, "e": -0.6}

INTERCEPT = 10.0
NOISE_STD = 1.5


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

    The target is a linear combination of the numeric features, plus a
    per-category effect, plus gaussian noise. The reference model therefore
    reaches a stable MAE and consecutive runs stay comparable.

    Reproducible: the same seed yields the same frame.

    To plug in your own data, replace this function and update the `DATA SCHEMA`
    block of `params.py`.
    """
    n_samples = n_samples if n_samples is not None else _n_samples_from_data_size()
    rng = np.random.default_rng(seed)

    frame = pd.DataFrame(
        {
            # On deliberately different scales: putting them on a common one is
            # exactly what the preprocessing step is for.
            "numeric_feature_1": rng.uniform(0.5, 30.0, n_samples),
            "numeric_feature_2": rng.integers(1, 5, n_samples),
            "numeric_feature_3": rng.integers(0, 24, n_samples),
            # A categorical feature, so the encoder branch is exercised too.
            "categorical_feature_1": rng.choice(list(CATEGORY_EFFECTS), n_samples),
        }
    )

    target = INTERCEPT + frame["categorical_feature_1"].map(CATEGORY_EFFECTS)
    for column, coefficient in NUMERIC_COEFFICIENTS.items():
        target += coefficient * frame[column]

    # Irreducible noise: it sets the floor below which no model can go, which
    # is what makes the MAE assertions meaningful.
    frame[TARGET_COLUMN] = target + rng.normal(0, NOISE_STD, n_samples)

    return frame
