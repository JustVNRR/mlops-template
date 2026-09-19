from pydantic import BaseModel, ConfigDict, Field

from package_folder.params import TARGET_COLUMN

# ==============================================================================
# 📥 ENTRÉES
# ==============================================================================
# ⚠️ Ce schéma doit refléter EXACTEMENT les features attendues par le modèle
# (voir NUMERIC_FEATURES et CATEGORICAL_FEATURES dans params.py). C'est lui qui
# protège l'API : une requête incomplète ou aberrante est rejetée en 422 avec
# un message précis, AVANT d'atteindre le modèle.


class TripFeatures(BaseModel):
    """Caractéristiques d'une course, telles qu'attendues par le modèle."""

    distance_km: float = Field(..., gt=0, le=1_000, description="Distance de la course, en kilomètres")
    passengers: int = Field(..., ge=1, le=8, description="Nombre de passagers")
    hour: int = Field(..., ge=0, le=23, description="Heure de prise en charge (0-23)")
    day_of_week: str = Field(..., description="Jour de la semaine, en anglais et en minuscules")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"},
                {"distance_km": 12.5, "passengers": 1, "hour": 23, "day_of_week": "saturday"},
            ]
        }
    )


# ==============================================================================
# 📤 SORTIES
# ==============================================================================
class PredictionResponse(BaseModel):
    """Prédiction pour une course."""

    # Le nom du champ vient de params.TARGET_COLUMN : renommer la cible dans le
    # schéma de données met à jour le contrat d'API automatiquement.
    fare: float = Field(..., description=f"Tarif estimé ({TARGET_COLUMN})")


class BatchPredictionResponse(BaseModel):
    """Prédictions pour un lot de courses, dans l'ordre de la requête."""

    fares: list[float] = Field(..., description="Tarifs estimés, dans l'ordre des entrées")
