from fastapi import APIRouter
from app.schemas import ModelStatusRead
from app.mock_data import MOCK_MODEL_STATE, INITIAL_WEIGHTS, INITIAL_BIAS
import datetime

router = APIRouter(prefix="/model", tags=["Model"])

@router.get("", response_model=ModelStatusRead)
def get_model():
    return MOCK_MODEL_STATE

@router.post("/reset", response_model=ModelStatusRead)
def reset_model():
    MOCK_MODEL_STATE["active_version"] = "v1"
    MOCK_MODEL_STATE["n_labels"] = 0
    MOCK_MODEL_STATE["training_agreement_pct"] = None
    MOCK_MODEL_STATE["weights"] = INITIAL_WEIGHTS.copy()
    MOCK_MODEL_STATE["bias"] = INITIAL_BIAS
    MOCK_MODEL_STATE["history"] = [
        {
            "version": "v1",
            "n_labels": 0,
            "training_agreement_pct": None,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
    ]
    return MOCK_MODEL_STATE

