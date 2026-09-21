import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentMaintenanceCreate,
    EquipmentMaintenanceRead,
    EquipmentRead,
    EquipmentUpdate,
    MaintenanceReminder,
)
from app.services import equipment_service

router = APIRouter(prefix="/equipment", tags=["equipment"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER, UserRole.STOREKEEPER)


@router.get("", response_model=list[EquipmentRead])
def list_equipment(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[EquipmentRead]:
    return equipment_service.list_equipment(db, current_user.company_id)


@router.post("", response_model=EquipmentRead, status_code=201)
def create_equipment(
    payload: EquipmentCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return equipment_service.create_equipment(db, current_user.company_id, payload)


@router.get("/reminders", response_model=list[MaintenanceReminder])
def get_maintenance_reminders(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaintenanceReminder]:
    return equipment_service.get_maintenance_reminders(db, current_user.company_id)


@router.patch("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(
    equipment_id: uuid.UUID,
    payload: EquipmentUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EquipmentRead:
    return equipment_service.update_equipment(db, current_user.company_id, equipment_id, payload)


@router.get("/{equipment_id}/maintenance", response_model=list[EquipmentMaintenanceRead])
def list_maintenance_records(
    equipment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EquipmentMaintenanceRead]:
    return equipment_service.list_maintenance_records(db, current_user.company_id, equipment_id)


@router.post("/{equipment_id}/maintenance", response_model=EquipmentMaintenanceRead, status_code=201)
def add_maintenance_record(
    equipment_id: uuid.UUID,
    payload: EquipmentMaintenanceCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EquipmentMaintenanceRead:
    return equipment_service.add_maintenance_record(db, current_user.company_id, equipment_id, payload)
