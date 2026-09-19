"""
Custom encoders for scikit-learn.

Placeholder for your own transformations — geohash encoding, time slicing,
business aggregations… — as classes exposing the `fit` / `transform` interface
scikit-learn expects, so they can be plugged into the ColumnTransformer built
by `preprocessor.build_preprocessor()`:

    from sklearn.compose import ColumnTransformer
    from package_folder.ml_logic.encoders import MyEncoder

    ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ("business", MyEncoder(), ["my_column"]),
    ])

This file used to hold nothing but four imports (`math`, `numpy`, `pandas`,
`pygeohash`) and no actual code: the intended examples were never written, and
the linter kept flagging them as dead code. Rather than leave dummy imports
behind, all that remains is this how-to — up to you to put a genuinely used
encoder here.
"""
