import pytest

from package_folder.ml_logic.data import clean_data, generate_toy_data


@pytest.fixture
def toy_dataframe():
    """
    Clean demonstration dataset, matching the schema declared in params.py.

    ⚠️ The former `fixture_mock_raw_data` and `fixture_mock_cleaned_data`
    fixtures built invented columns (feature_1, feature_2, target) that matched
    NO schema in the project. Tests using them validated data the pipeline would
    never actually encounter — a green test that proved nothing.

    For raw, uncleaned data, call `generate_toy_data()` directly. To test a
    specific edge case (missing value, duplicate, unknown category), build the
    DataFrame inside the test concerned: that reads better than a generic
    fixture.
    """
    return clean_data(generate_toy_data(100))
