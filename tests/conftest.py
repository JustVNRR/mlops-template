import pytest

from package_folder.ml_logic.data import clean_data, generate_toy_data


@pytest.fixture
def toy_dataframe():
    """
    Jeu de démonstration nettoyé, conforme au schéma déclaré dans params.py.

    ⚠️ Les anciennes fixtures `fixture_mock_raw_data` et
    `fixture_mock_cleaned_data` fabriquaient des colonnes inventées
    (feature_1, feature_2, target) qui ne correspondaient à AUCUN schéma du
    projet. Les tests qui s'en servaient validaient donc des données que le
    pipeline n'aurait jamais rencontrées — un test vert qui ne prouvait rien.

    Pour des données brutes non nettoyées, appelle directement
    `generate_toy_data()`. Pour tester un cas limite précis (valeur manquante,
    doublon, catégorie inconnue), construis le DataFrame dans le test concerné :
    c'est plus lisible qu'une fixture générique.
    """
    return clean_data(generate_toy_data(100))
