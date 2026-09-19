"""
Encodeurs personnalisés pour scikit-learn.

Emplacement prévu pour tes transformations « maison » — encodage geohash,
découpage temporel, agrégations métier… — sous forme de classes exposant
l'interface `fit` / `transform` attendue par scikit-learn, afin de les
brancher dans le ColumnTransformer de `preprocessor.build_preprocessor()` :

    from sklearn.compose import ColumnTransformer
    from package_folder.ml_logic.encoders import MonEncodeur

    ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ("metier", MonEncodeur(), ["ma_colonne"]),
    ])

Ce fichier ne contenait que quatre imports (`math`, `numpy`, `pandas`,
`pygeohash`) et AUCUNE ligne de code : les exemples prévus n'ont jamais été
écrits, et le lint les signalait comme du code mort. Plutôt que de laisser
des imports factices, il ne reste ici qu'un mode d'emploi — à toi d'y mettre
un encodeur réellement utilisé.
"""
