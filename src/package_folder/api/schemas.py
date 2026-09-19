from pydantic import BaseModel, ConfigDict, Field

from package_folder.params import TARGET_COLUMN

# ==============================================================================
# 📥 INPUTS
# ==============================================================================
# ⚠️ This schema must mirror EXACTLY the features the model expects (see
# NUMERIC_FEATURES and CATEGORICAL_FEATURES in params.py). It is what protects
# the API: an incomplete or nonsensical request is rejected with a 422 and a
# precise message, BEFORE it ever reaches the model.


class TripFeatures(BaseModel):
    """Characteristics of a single trip, as expected by the model."""

    distance_km: float = Field(..., gt=0, le=1_000, description="Trip distance, in kilometres")
    passengers: int = Field(..., ge=1, le=8, description="Number of passengers")
    hour: int = Field(..., ge=0, le=23, description="Pickup hour (0-23)")
    day_of_week: str = Field(..., description="Day of the week, lowercase English name")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"},
                {"distance_km": 12.5, "passengers": 1, "hour": 23, "day_of_week": "saturday"},
            ]
        }
    )


# ==============================================================================
# 📤 OUTPUTS
# ==============================================================================
class PredictionResponse(BaseModel):
    """Prediction for a single trip."""

    # The field name comes from params.TARGET_COLUMN: renaming the target in the
    # data schema updates the API contract automatically.
    fare: float = Field(..., description=f"Predicted fare ({TARGET_COLUMN})")


class BatchPredictionResponse(BaseModel):
    """Predictions for a batch of trips, in the order of the request."""

    fares: list[float] = Field(..., description="Predicted fares, in the order of the inputs")
