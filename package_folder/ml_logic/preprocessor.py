import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from package_folder.params import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """
    Construire le pipeline de transformation des features (NON entraîné).

    ⚠️ Un préprocesseur doit être ENTRAÎNÉ sur les données d'entraînement
    uniquement, puis réutilisé tel quel pour valider, évaluer et prédire.
    C'est pourquoi `build_model()` l'intègre dans un Pipeline scikit-learn :
    il est alors sérialisé avec le modèle, et `model.predict()` applique
    automatiquement la transformation apprise.

    TODO: adapte les transformations à tes colonnes (imputation, features
    temporelles, geohash…) — les listes de colonnes viennent de params.py.
    """
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            # handle_unknown="ignore" : en production, une catégorie jamais vue
            # à l'entraînement produit une ligne de zéros au lieu de lever une
            # exception — une API ne doit pas tomber pour ça.
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",  # toute colonne hors schéma est ignorée
    )


def preprocess_features(X: pd.DataFrame) -> np.ndarray:
    """
    Transformer des features brutes en matrice numérique.

    ⚠️ FONCTION SANS ÉTAT : elle entraîne un préprocesseur NEUF sur `X`.
    Pratique pour explorer un jeu de données ou tester une transformation,
    mais à ne PAS utiliser pour servir un modèle : les moyennes, écarts-types
    et catégories appris ne seraient pas ceux de l'entraînement, ce qui produit
    des prédictions silencieusement fausses (aucune erreur levée).

    En production, appelle directement `model.predict(X)` : le modèle est un
    Pipeline qui embarque déjà ce préprocesseur.
    """
    return build_preprocessor().fit_transform(X)
