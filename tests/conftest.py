import pytest

from package_folder.ml_logic.data import clean_data
from package_folder.ml_logic.demo_data import generate_demo_data


@pytest.fixture
def toy_dataframe():
    """
    Clean demonstration dataset, matching the schema declared in params.py.

    For raw, uncleaned data, call `generate_demo_data()` directly. To test a
    specific edge case (missing value, duplicate, unknown category), build the
    DataFrame inside the test concerned: that reads better than a generic
    fixture.
    """
    return clean_data(generate_demo_data(100))
