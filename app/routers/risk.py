from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import require_admin_key
from app.services.risk_service import recompute_all_zones

router = APIRouter(prefix="/risk", tags=["risk model"])


@router.post("/recompute")
def recompute_risk(db=Depends(get_db), _admin: bool = Depends(require_admin_key)):
    """Re-scores every zone using the trained model and each zone's latest
    sensor reading. Requires the X-API-Key header (see ADMIN_API_KEY in .env).

    This same logic also runs automatically on a timer — see
    app/scheduler.py — so calling this by hand is mostly useful for testing
    or forcing an immediate refresh after new data lands.

    Requires a trained model at app/ml/risk_model.joblib — run
    `python -m app.ml.train` once before calling this.
    """
    try:
        return recompute_all_zones(db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
