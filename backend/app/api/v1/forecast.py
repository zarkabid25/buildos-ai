import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.forecast import ConsumptionRate, MaterialAnomaly, MaterialForecast
from app.services import forecast_service
from app.services.material_service import get_material

router = APIRouter(prefix="/inventory", tags=["forecast"])


@router.get("/forecast", response_model=list[MaterialForecast])
def list_forecasts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialForecast]:
    return forecast_service.list_forecasts(db, current_user.company_id)


@router.get("/materials/{material_id}/forecast", response_model=MaterialForecast)
def material_forecast(
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaterialForecast:
    material = get_material(db, current_user.company_id, material_id)
    return forecast_service.get_material_forecast(db, current_user.company_id, material)


@router.get("/materials/{material_id}/consumption", response_model=ConsumptionRate)
def material_consumption(
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsumptionRate:
    material = get_material(db, current_user.company_id, material_id)
    return forecast_service.get_consumption_rate(db, current_user.company_id, material)


@router.get("/anomalies", response_model=list[MaterialAnomaly])
def anomalies(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialAnomaly]:
    return forecast_service.detect_anomalies(db, current_user.company_id)
